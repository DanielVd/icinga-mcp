import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from director_mcp.client import DirectorClient
from director_mcp.server import list_hosts as director_list_hosts
from director_mcp.server import parse_json_field
from director_mcp.settings import DirectorSettings
from icinga2_mcp.client import Icinga2Client
from icinga2_mcp.server import HOST_LIST_ATTRS, get_client, json_response, list_hosts as icinga_list_hosts
from icinga2_mcp.settings import Icinga2Settings
from requests import HTTPError, Response


class PerfApiTests(unittest.TestCase):
    def setUp(self) -> None:
        get_client.cache_clear()

    def tearDown(self) -> None:
        get_client.cache_clear()

    def test_json_response_is_compact(self) -> None:
        self.assertEqual(json_response({"a": 1, "b": 2}), '{"a":1,"b":2}')

    def test_icinga_list_hosts_uses_attr_projection(self) -> None:
        fake_hosts = [
            {
                "attrs": {
                    "name": "host-1",
                    "display_name": "Host 1",
                    "address": "10.0.0.1",
                    "state": 0,
                    "last_state": 1,
                    "state_type": 1,
                    "check_command": "hostalive",
                    "groups": ["linux"],
                    "last_check": 1,
                    "next_check": 2,
                    "acknowledgement": 0,
                    "downtime_depth": 0,
                }
            }
        ]
        with patch("icinga2_mcp.server.get_client") as mock_get_client:
            client = mock_get_client.return_value
            client.list_hosts.return_value = fake_hosts

            payload = json.loads(icinga_list_hosts(""))

            client.list_hosts.assert_called_once_with(None, attrs=HOST_LIST_ATTRS)
            self.assertEqual(payload[0]["name"], "host-1")
            self.assertEqual(payload[0]["state"], "UP")

    def test_director_list_hosts_supports_pagination_and_summary(self) -> None:
        fake_hosts = [
            {"object_name": "a", "object_type": "object", "address": "10.0.0.1", "display_name": "A", "imports": []},
            {"object_name": "b", "object_type": "object", "address": "10.0.0.2", "display_name": "B", "imports": []},
            {"object_name": "c", "object_type": "object", "address": "10.0.0.3", "display_name": "C", "imports": []},
        ]
        with patch("director_mcp.server.get_client") as mock_get_client:
            client = mock_get_client.return_value
            client.list_hosts.return_value = fake_hosts

            payload = json.loads(director_list_hosts(limit=2, offset=1, summary=True))

            self.assertEqual(payload["total"], 3)
            self.assertEqual(payload["count"], 2)
            self.assertEqual([host["object_name"] for host in payload["results"]], ["b", "c"])

    def test_parse_json_field_rejects_invalid_json(self) -> None:
        with self.assertRaises(ValueError):
            parse_json_field("vars_json", "{bad")

    def test_settings_load_expected_env_prefixes(self) -> None:
        env = {
            "ICINGA_HOST": "icinga.local",
            "ICINGA_USER": "api",
            "ICINGA_PASSWORD": "secret",
            "DIRECTOR_BASE_URL": "https://director.local/director",
            "DIRECTOR_USER": "web",
            "DIRECTOR_PASSWORD": "topsecret",
        }
        with patch.dict(os.environ, env, clear=False):
            icinga_settings = Icinga2Settings()
            director_settings = DirectorSettings()

        self.assertEqual(icinga_settings.host, "icinga.local")
        self.assertEqual(director_settings.base_url, "https://director.local/director")

    def test_icinga_client_wraps_http_errors(self) -> None:
        client = Icinga2Client("icinga.local", "api", "secret")
        response = Mock(status_code=401, text="denied")
        error = HTTPError(response=response)
        fake_response = Mock()
        fake_response.raise_for_status.side_effect = error
        with patch.object(client.session, "request", return_value=fake_response):
            with self.assertRaises(RuntimeError) as ctx:
                client._get("objects/hosts")

        self.assertIn("Icinga2 API request failed", str(ctx.exception))

    def test_director_client_wraps_invalid_json(self) -> None:
        client = DirectorClient("https://director.local/director", "web", "secret")
        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.side_effect = ValueError("bad json")
        with patch.object(client.session, "request", return_value=fake_response):
            with self.assertRaises(RuntimeError) as ctx:
                client._get("hosts")

        self.assertIn("invalid JSON", str(ctx.exception))

    def test_director_no_change_writes_handle_empty_not_modified_responses(self) -> None:
        client = DirectorClient("https://director.local/director", "web", "secret")
        response = Response()
        response.status_code = 304
        payload = {"display_name": "Existing name"}

        for method, update in (("POST", client.update_host), ("PUT", client.replace_host)):
            with self.subTest(method=method):
                with patch.object(client.session, "request", return_value=response) as request:
                    self.assertEqual(update("host-1", payload), {"changed": False, "status": "not_modified"})
                request.assert_called_once_with(
                    method, "https://director.local/director/host",
                    timeout=client.timeout, json=payload, params={"name": "host-1"},
                )

    def test_director_successful_write_keeps_the_upstream_object(self) -> None:
        client = DirectorClient("https://director.local/director", "web", "secret")
        response = Response()
        response.status_code = 200
        response._content = b'{"object_name":"host-1","display_name":"New name"}'

        with patch.object(client.session, "request", return_value=response):
            result = client.update_host("host-1", {"display_name": "New name"})

        self.assertEqual(result, {"object_name": "host-1", "display_name": "New name"})


if __name__ == "__main__":
    unittest.main()
