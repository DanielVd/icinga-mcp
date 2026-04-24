import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from director_mcp.server import list_hosts as director_list_hosts
from icinga2_mcp.server import HOST_LIST_ATTRS, get_client, json_response, list_hosts as icinga_list_hosts


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
                    "last_state": 0,
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


if __name__ == "__main__":
    unittest.main()
