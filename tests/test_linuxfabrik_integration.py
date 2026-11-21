import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from director_mcp.server import mcp as director_mcp
from icinga2_mcp.client import Icinga2Client
from icinga2_mcp.server import get_client, list_hosts, mcp
from icinga2_mcp.settings import Icinga2Settings


class CoreIntegrationTests(unittest.TestCase):
    def tearDown(self):
        get_client.cache_clear()

    def test_named_instances_require_explicit_target_and_separate_write_credentials(self):
        env = {
            "ICINGA_INSTANCES__PROD__URL": "https://prod.example:5665/v1",
            "ICINGA_INSTANCES__PROD__USER": "reader",
            "ICINGA_INSTANCES__PROD__PASSWORD": "read-secret",
            "ICINGA_INSTANCES__STAGING__URL": "https://staging.example:8443/v1",
            "ICINGA_INSTANCES__STAGING__USER": "reader",
            "ICINGA_INSTANCES__STAGING__PASSWORD": "read-secret",
            "ICINGA_INSTANCES__STAGING__WRITE_USER": "writer",
            "ICINGA_INSTANCES__STAGING__WRITE_PASSWORD": "write-secret",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Icinga2Settings(_env_file=None)

        with patch("icinga2_mcp.server.get_settings", return_value=settings):
            with self.assertRaisesRegex(ValueError, "Specify the Core instance"):
                get_client()
            with self.assertRaisesRegex(ValueError, "Writes are disabled"):
                get_client("prod", write=True)
            read = get_client("staging")
            write = get_client("staging", write=True)

        self.assertEqual(read.auth, ("reader", "read-secret"))
        self.assertEqual(write.auth, ("writer", "write-secret"))
        self.assertEqual(write.action_author, "writer")
        self.assertEqual(write.base_url, "https://staging.example:8443/v1")
        self.assertTrue(write.verify)

    def test_problems_use_current_state_and_limit_returned_rows_without_losing_counts(self):
        with patch("icinga2_mcp.server.get_client") as get_mock_client:
            client = get_mock_client.return_value
            client.list_hosts.return_value = [
                {"attrs": {"name": name, "state": 1, "last_state": 0}}
                for name in ("z-host", "a-host")
            ]
            client.list_services.return_value = [
                {"attrs": {"name": "disk", "state": 2, "last_check_result": {"output": "x" * 600}}}
            ]
            response = asyncio.run(mcp.call_tool("get_problems", {"instance": "prod", "limit": 1}))
            result = response.structuredContent
            self.assertEqual(json.loads(response.content[0].text), result)
            tool = next(tool for tool in asyncio.run(mcp.list_tools()) if tool.name == "get_problems")
            self.assertEqual(set(tool.outputSchema["required"]), {
                "hosts", "services", "host_problem_count", "service_problem_count",
            })
            self.assertEqual(client.list_hosts.call_args.args, ("host.state != 0",))
            self.assertEqual(client.list_services.call_args.kwargs["service_filter"], "service.state != 0")
            self.assertEqual(result["host_problem_count"], 2)
            self.assertEqual(result["hosts"][0]["name"], "a-host")
            self.assertEqual(result["hosts"][0]["state"], "DOWN")
            self.assertEqual(len(result["services"][0]["output"]), 500)
            self.assertEqual(len(json.loads(list_hosts("", state="down", name_contains="A-HOST"))), 1)
            self.assertEqual(client.list_hosts.call_args.args, ("host.state == 1",))

    def test_discovery_distinguishes_runtime_tools_from_director_definitions(self):
        core_tools = {tool.name: tool for tool in asyncio.run(mcp.list_tools())}
        director_tools = {tool.name: tool for tool in asyncio.run(director_mcp.list_tools())}
        for name in ("list_hosts", "list_services", "get_host", "get_service"):
            with self.subTest(tool=name):
                self.assertIn("Icinga 2 Core", core_tools[name].description)
                self.assertIn("definition", director_tools[name].description)

    def test_named_actions_use_exact_targets_and_configured_writer(self):
        client = Icinga2Client("icinga.example", "writer", "secret", action_author="writer")
        with patch.object(client, "_post") as post:
            client.add_downtime("web", "requested-author", "maintenance", 60, "disk", start_time=100)
            post.assert_called_once_with("actions/schedule-downtime", {
                "service": "web!disk", "author": "writer", "comment": "maintenance",
                "start_time": 100, "end_time": 160, "fixed": True, "all_services": False,
            })
            with self.assertRaisesRegex(ValueError, "Specify either"):
                client.remove_downtime("downtime-1", host="web")
            post.assert_called_once()

    def test_object_queries_send_filters_in_json_without_changing_unfiltered_reads(self):
        client = Icinga2Client("icinga.example", "reader", "secret")
        with patch.object(client, "_request", return_value={"results": []}) as request:
            client.list_hosts("host.state != 0", attrs=["state"])
            request.assert_called_once_with(
                "POST", "objects/hosts",
                json={"filter": "host.state != 0", "attrs": ["state"]},
                headers={"X-HTTP-Method-Override": "GET"},
            )
            request.reset_mock()
            client.list_services(attrs=["state"])
            request.assert_called_once_with("GET", "objects/services", params={"attrs": ["state"]})

    def test_exact_object_queries_send_names_with_spaces_in_json(self):
        client = Icinga2Client("icinga.example", "reader", "secret")
        headers = {"X-HTTP-Method-Override": "GET"}
        with patch.object(client, "_request", return_value={"results": [{"name": "web!Disk Usage"}]}) as request:
            self.assertEqual(client.get_service("web", "Disk Usage")["name"], "web!Disk Usage")
            request.assert_called_once_with(
                "POST", "objects/services", json={"service": "web!Disk Usage"}, headers=headers,
            )
        with patch.object(client, "_request", return_value={"results": [{"name": "web server"}]}) as request:
            self.assertEqual(client.get_host("web server")["name"], "web server")
            request.assert_called_once_with(
                "POST", "objects/hosts", json={"host": "web server"}, headers=headers,
            )


class CatalogMcpTests(unittest.TestCase):
    def test_stdio_exposes_catalog_only_for_a_catalog_only_setup(self):
        async def check_tools(root: Path, check_plugins: Path):
            server = StdioServerParameters(
                command=sys.executable,
                args=["-m", "icinga2_mcp.server"],
                cwd=root,
                env={
                    "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
                    "ICINGA_TRANSPORT": "stdio",
                    "ICINGA_PLUGIN_CATALOG_PATH": str(check_plugins),
                },
            )
            async with stdio_client(server) as (receive, send):
                async with ClientSession(receive, send) as session:
                    await session.initialize()
                    self.assertEqual({tool.name for tool in (await session.list_tools()).tools}, {
                        "health_check", "catalog_info", "list_plugins", "explain_plugin",
                        "find_plugin_for_check_command", "read_plugin_source",
                    })
                    info = await session.call_tool("catalog_info", {})
                    self.assertFalse(info.isError)
                    self.assertEqual(info.structuredContent["plugin_count"], 1)
                    detail = await session.call_tool("explain_plugin", {"name": "probe"})
                    self.assertEqual(detail.structuredContent["runs_on"], "Linux")
                    match = await session.call_tool("find_plugin_for_check_command", {
                        "check_command": "cmd-probe",
                    })
                    self.assertFalse(match.isError)
                    self.assertEqual(match.structuredContent["result"]["name"], "probe")
                    source = await session.call_tool("read_plugin_source", {"name": "probe", "function": "main"})
                    self.assertEqual(source.structuredContent["source"], "def main():\n    return 0")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            check_plugins = root / "check-plugins"
            plugin = check_plugins / "probe"
            director = plugin / "icingaweb2-module-director"
            director.mkdir(parents=True)
            (plugin / "probe").write_text('__version__ = "1"\n\ndef main():\n    return 0\n', encoding="utf-8")
            (plugin / "README.md").write_text(
                "## Fact Sheet\n\n| Fact | Value |\n|----|----|\n| Runs on | Linux |\n", encoding="utf-8"
            )
            (director / "probe.json").write_text('{"Command":{"cmd-probe":{}}}', encoding="utf-8")
            asyncio.run(asyncio.wait_for(check_tools(root, check_plugins), timeout=15))
