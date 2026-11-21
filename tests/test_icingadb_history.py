import asyncio
from datetime import datetime, timezone
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from icinga2_mcp.history import HistoryClient, get_history
from icinga2_mcp.server import configure_tools
from icinga2_mcp.settings import HistorySettings, Icinga2Settings


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.config = HistorySettings(url="https://monitoring.example/icingaweb2",
                                      user="history-reader", password="example-password")

    def test_exact_query_returns_a_bounded_page_with_ack_actor(self):
        client = HistoryClient(self.config)
        start = datetime(2026, 2, 1, tzinfo=timezone.utc)
        end = datetime(2026, 2, 2, tzinfo=timezone.utc)
        row = {"event_type": "ack_set", "event_time": "2026-02-01T12:00:00Z",
               "host": {"name": "host-1"}, "service": {"name": "Disk & Storage"},
               "acknowledgement": {"author": "operator", "comment": "Checking"}}
        response = Mock(status_code=200, **{"json.return_value": [row, row]})
        with patch.object(client.session, "get", return_value=response) as request:
            result = client.get_events(host="host-1", service="Disk & Storage", start=start,
                                       end=end, event_type="ack_set", limit=1)
        url = request.call_args.args[0]
        self.assertIn("/icingaweb2/icingadb/history?", url)
        self.assertIn("service.name=Disk%20%26%20Storage&event_type=ack_set&limit=2&format=json", url)
        self.assertIn("event_time>=2026-02-01T00%3A00%3A00%2B00%3A00", url)
        self.assertTrue(result.has_more)
        self.assertEqual([event.author for event in result.events], ["operator"])

    def test_history_rejects_reversed_or_unbounded_intervals(self):
        with patch("icinga2_mcp.history.get_history_client") as client:
            with self.assertRaisesRegex(ValueError, "31 days"):
                get_history("host-1", start=datetime(2026, 2, 1, tzinfo=timezone.utc),
                            end=datetime(2026, 1, 1, tzinfo=timezone.utc))
            with self.assertRaisesRegex(ValueError, "without wildcards"):
                get_history("host-*")
        client.assert_not_called()

    def test_history_only_settings_advertise_the_history_tool(self):
        server = FastMCP("history-test")
        settings = Icinga2Settings(history=self.config, _env_file=None)
        asyncio.run(configure_tools(server, settings))
        tools = asyncio.run(server.list_tools())
        self.assertEqual([item.name for item in tools], ["get_history"])
