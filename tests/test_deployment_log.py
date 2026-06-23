import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from director_mcp.client import DirectorClient
from director_mcp.deployment_log import (
    parse_deployment_list,
    parse_log_text,
    parse_startup_log,
)
from director_mcp.server import get_client, get_deployment_log as server_get_deployment_log


DEPLOYMENT_LIST_HTML = """
<table class="deployment-status">
<tbody>
<tr class="succeeded running"><td><a href="/director/deployment?id=1110">smt-web09c (33f0bbc)</a></td><td>just now</td></tr>
<tr class="succeeded active"><td><a href="/director/deployment?id=1109">smt-web09c (4030ac5)</a></td><td>earlier</td></tr>
<tr class="failed"><td><a href="/director/deployment?id=1108">smt-web09c (deadbee)</a></td><td>older</td></tr>
</tbody>
</table>
"""

# Mirrors the real /director/deployment?id=<id> markup: loglevel/application spans
# inside <pre class="logfile">, plus an indented continuation line.
DEPLOYMENT_DETAIL_HTML = """
<table class="name-value-table">
<tr><th>Stage name</th><td>8107e823-59e0-429c-90c5-28ee4031cd11</td></tr>
<tr><th>Startup</th><td><div class="succeeded">Succeeded <i class="icon icon-ok"></i> </div></td></tr>
</table>
<h2>Startup Log</h2><pre class="logfile">[2026-06-23 09:37:01 +0200] <span class="loglevel information">information</span>/<span class="application">cli</span>: Icinga application loader (version: r2.16.1-1)
[2026-06-23 09:37:01 +0200] <span class="loglevel warning">warning</span>/<span class="application">Checkable</span>: CheckCommand 'disk-windows' used by 'Archimedes.SMT.COM.LOCAL!disk_windows'
  (in [stage]/zones.d/master/service_apply.conf: 1:0-1:27) is DEPRECATED and will be removed in v2.18.
[2026-06-23 09:37:01 +0200] <span class="loglevel warning">warning</span>/<span class="application">IdoMysqlConnection</span>: This feature is DEPRECATED and will be removed in v2.18.
[2026-06-23 09:37:01 +0200] <span class="loglevel information">information</span>/<span class="application">cli</span>: Finished validating the configuration file(s).</pre>
"""


class ParseDeploymentListTests(unittest.TestCase):
    def test_extracts_rows_in_order_with_status(self) -> None:
        rows = parse_deployment_list(DEPLOYMENT_LIST_HTML)
        self.assertEqual([r["id"] for r in rows], [1110, 1109, 1108])
        self.assertEqual(rows[0]["label"], "smt-web09c (33f0bbc)")
        self.assertTrue(rows[0]["succeeded"])
        self.assertFalse(rows[0]["active"])
        self.assertTrue(rows[1]["active"])
        self.assertFalse(rows[2]["succeeded"])

    def test_empty_page_returns_empty_list(self) -> None:
        self.assertEqual(parse_deployment_list("<html>no deployments</html>"), [])


class ParseStartupLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = parse_startup_log(DEPLOYMENT_DETAIL_HTML)

    def test_extracts_stage_and_status(self) -> None:
        self.assertEqual(self.result["stage_name"], "8107e823-59e0-429c-90c5-28ee4031cd11")
        self.assertTrue(self.result["startup_succeeded"])

    def test_summary_and_warning_count(self) -> None:
        self.assertEqual(self.result["summary"], {"information": 2, "warning": 2})
        self.assertEqual(self.result["warning_count"], 2)
        self.assertEqual(len(self.result["warnings"]), 2)

    def test_warnings_are_parsed_with_facility(self) -> None:
        facilities = {w["facility"] for w in self.result["warnings"]}
        self.assertEqual(facilities, {"Checkable", "IdoMysqlConnection"})
        for warn in self.result["warnings"]:
            self.assertEqual(warn["level"], "warning")

    def test_continuation_line_is_folded_into_message(self) -> None:
        checkable = next(w for w in self.result["warnings"] if w["facility"] == "Checkable")
        self.assertIn("CheckCommand 'disk-windows'", checkable["message"])
        self.assertIn("is DEPRECATED and will be removed in v2.18.", checkable["message"])
        # The continuation must be on the same entry, not a separate one.
        self.assertNotIn("\n", checkable["message"])

    def test_missing_logfile_yields_empty_entries(self) -> None:
        result = parse_startup_log("<div>no log here</div>")
        self.assertEqual(result["entries"], [])
        self.assertEqual(result["warning_count"], 0)
        self.assertIsNone(result["stage_name"])


class ParseLogTextTests(unittest.TestCase):
    def test_handles_plain_lines_and_levels(self) -> None:
        text = (
            "[2026-06-23 09:37:01 +0200] critical/config: Error in line 5\n"
            "[2026-06-23 09:37:01 +0200] information/cli: done\n"
        )
        entries = parse_log_text(text)
        self.assertEqual(entries[0]["level"], "critical")
        self.assertEqual(entries[0]["facility"], "config")
        self.assertEqual(entries[0]["message"], "Error in line 5")
        self.assertEqual(entries[1]["level"], "information")

    def test_blank_and_leading_continuation_lines(self) -> None:
        # A continuation line with no preceding entry must not crash or create one.
        entries = parse_log_text("   orphan continuation\n\n")
        self.assertEqual(entries, [])


class ClientDeploymentLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = DirectorClient("https://director.local/director", "web", "secret")

    def _fake_session(self):
        session = Mock()

        def fake_get(url, **kwargs):
            resp = Mock()
            resp.raise_for_status.return_value = None
            if "config/deployments" in url:
                resp.text = DEPLOYMENT_LIST_HTML
            else:
                resp.text = DEPLOYMENT_DETAIL_HTML
            return resp

        session.get.side_effect = fake_get
        return session

    def test_web_root_is_derived_from_base_url(self) -> None:
        self.assertEqual(self.client._web_root(), "https://director.local")

    def test_get_deployment_log_picks_latest_and_parses(self) -> None:
        with patch.object(self.client, "_web_login_session", return_value=self._fake_session()):
            result = self.client.get_deployment_log()
        # Latest deployment id from the list (first row).
        self.assertEqual(result["deployment_id"], 1110)
        self.assertEqual(result["warning_count"], 2)
        self.assertTrue(result["startup_succeeded"])

    def test_get_deployment_log_honours_explicit_id(self) -> None:
        session = self._fake_session()
        with patch.object(self.client, "_web_login_session", return_value=session):
            result = self.client.get_deployment_log(1108)
        self.assertEqual(result["deployment_id"], 1108)
        # With an explicit id, the deployments list is not requested.
        requested = [call.args[0] for call in session.get.call_args_list]
        self.assertFalse(any("config/deployments" in url for url in requested))

    def test_login_failure_raises(self) -> None:
        with patch.object(self.client, "_web_login_session", side_effect=RuntimeError("login failed")):
            with self.assertRaises(RuntimeError):
                self.client.get_deployment_log()


class ServerToolTests(unittest.TestCase):
    def setUp(self) -> None:
        get_client.cache_clear()

    def tearDown(self) -> None:
        get_client.cache_clear()

    def test_tool_returns_compact_json(self) -> None:
        with patch("director_mcp.server.get_client") as mock_get_client:
            mock_get_client.return_value.get_deployment_log.return_value = {
                "deployment_id": 1110,
                "warning_count": 2,
            }
            payload = json.loads(server_get_deployment_log(deployment_id=0))

        mock_get_client.return_value.get_deployment_log.assert_called_once_with(None)
        self.assertEqual(payload["deployment_id"], 1110)


if __name__ == "__main__":
    unittest.main()
