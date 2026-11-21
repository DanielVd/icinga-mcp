import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError
from requests import HTTPError, Response
from starlette.testclient import TestClient

from director_mcp import server as director
from director_mcp.client import DirectorClient
from director_mcp.settings import DirectorSettings
from icinga2_mcp import server as core
from icinga2_mcp.client import Icinga2Client
from icinga2_mcp.settings import Icinga2Settings
from icinga_mcp.transport import http_app


TOKEN = "test-token-for-isolated-mcp-verification"


def core_settings(**kwargs):
    return Icinga2Settings(
        _env_file=None, host="icinga.example", user="test", password="placeholder", **kwargs,
    )


def director_settings(**kwargs):
    return DirectorSettings(
        _env_file=None, base_url="https://icinga.example/director",
        user="test", password="placeholder", **kwargs,
    )


class SettingsSecurityTests(unittest.TestCase):
    def test_tls_and_local_read_only_defaults(self):
        for settings in (core_settings(), director_settings()):
            with self.subTest(settings=type(settings).__name__):
                self.assertEqual(settings.mcp_host, "127.0.0.1")
                self.assertTrue(settings.verify_ssl)
                self.assertFalse(settings.allow_writes)

    def test_remote_listener_requires_tls_auth_and_hosts(self):
        for settings in (core_settings, director_settings):
            with self.subTest(settings=settings.__name__):
                with self.assertRaisesRegex(ValidationError, "requires TLS and a bearer token"):
                    settings(mcp_host="192.0.2.10", mcp_bearer_token=TOKEN)
                with TemporaryDirectory() as tmp:
                    path = Path(tmp, "example.pem")
                    path.touch()
                    params = dict(mcp_tls_cert=path, mcp_tls_key=path, mcp_bearer_token=TOKEN,
                                  mcp_host="192.0.2.10")
                    with self.assertRaisesRegex(ValidationError, "allowed HTTP Host"):
                        settings(**params)
                    self.assertEqual(settings(**params, mcp_allowed_hosts=["mcp.example"]).mcp_host,
                                     "192.0.2.10")
                    with self.assertRaisesRegex(ValidationError, "CA bundle requires TLS verification"):
                        settings(ca_bundle=path, verify_ssl=False)

    def test_core_read_only_cannot_create_a_write_client(self):
        with patch.object(core, "get_settings", return_value=core_settings()):
            with self.assertRaisesRegex(ValueError, "write tools are disabled"):
                core.get_client(write=True)


class HttpSecurityTests(unittest.TestCase):
    def test_authenticated_core_write_uses_only_a_mock_backend(self):
        app = FastMCP("isolated-write-test", json_response=True)
        app.add_tool(core.reschedule_check)
        headers = {"Accept": "application/json, text/event-stream"}
        with TestClient(http_app(app, core_settings(allow_writes=True, mcp_bearer_token=TOKEN)),
                        base_url="http://127.0.0.1:8092", headers=headers) as client:
            init = {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                           "clientInfo": {"name": "test", "version": "1"}},
            }
            for method in ("POST", "GET", "DELETE"):
                self.assertEqual(client.request(method, "/mcp").status_code, 401)
            self.assertEqual(client.post("/mcp", json=init, headers={"Authorization": "Bearer invalid"}).status_code,
                             401)
            auth = {"Authorization": f"Bearer {TOKEN}"}
            self.assertEqual(client.post("/mcp", json=init,
                                         headers={**auth, "Origin": "https://untrusted.example"}).status_code, 403)
            response = client.post("/mcp", json=init, headers=auth)
            self.assertEqual(response.status_code, 200)
            session = {**auth, "Mcp-Session-Id": response.headers["Mcp-Session-Id"],
                       "MCP-Protocol-Version": response.json()["result"]["protocolVersion"]}
            client.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=session)
            with patch.object(core, "get_client") as backend:
                backend.return_value.reschedule_check.return_value = {"results": [{"code": 200}]}
                response = client.post("/mcp", json={
                    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "reschedule_check", "arguments": {"host": "synthetic-test", "service": ""}},
                }, headers=session)
                tool_result = response.json()["result"]
                self.assertFalse(tool_result.get("isError"), tool_result)
                self.assertEqual(json.loads(tool_result["content"][0]["text"])["results"][0]["code"], 200)
                backend.assert_called_once_with(None, write=True)
                backend.return_value.reschedule_check.assert_called_once_with("synthetic-test", None, True)

    def test_director_hides_and_blocks_writes_and_ticket_generation(self):
        server = FastMCP("director-read-only")
        for tool in (director.list_hosts, director.deploy_pending_changes, director.get_host_ticket):
            server.add_tool(tool)
        asyncio.run(director.configure_tools(server, director_settings()))
        self.assertEqual([tool.name for tool in asyncio.run(server.list_tools())], ["list_hosts"])
        client = DirectorClient("https://icinga.example/director", "test", "placeholder", allow_writes=False)
        with patch.object(client.session, "request") as request:
            for operation in (client.deploy, lambda: client.get_host_ticket("synthetic-test")):
                with self.assertRaisesRegex(RuntimeError, "are disabled"):
                    operation()
            request.assert_not_called()


class BackendSecurityTests(unittest.TestCase):
    def test_clients_do_not_forward_backend_error_bodies_or_follow_redirects(self):
        for client in (Icinga2Client("icinga.example", "test", "placeholder"),
                       DirectorClient("https://icinga.example/director", "test", "placeholder")):
            with self.subTest(client=type(client).__name__):
                response = Response()
                response.status_code = 401
                response._content = b"backend-secret-placeholder"
                with patch.object(client.session, "request", side_effect=HTTPError(response=response)) as request:
                    with self.assertRaisesRegex(RuntimeError, "401") as error:
                        client._get("hosts")
                    self.assertNotIn("backend-secret-placeholder", str(error.exception))
                    self.assertFalse(request.call_args.kwargs["allow_redirects"])
                response.status_code = 302
                response.headers["Location"] = "https://untrusted.example/different-path"
                with patch.object(client.session, "request", return_value=response):
                    with self.assertRaisesRegex(RuntimeError, "unexpected redirect"):
                        client._get("hosts")


if __name__ == "__main__":
    unittest.main()
