import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from director_mcp.deployment import ActivitySnapshot
from director_mcp.server import preview_pending_deployment, verify_deployment


class DirectorDeploymentTests(unittest.TestCase):
    def test_verification_checks_active_checksum_separately_from_reported_status(self):
        expected = "a" * 40
        response = {"active_configuration": {"config": "b" * 40, "stage_name": "stage-1"},
                    "configs": {expected: "deployed"}}
        with patch("director_mcp.server.get_client") as get_client:
            get_client.return_value.get_deployment_status.return_value = response
            historical = verify_deployment(expected.upper())
            active = verify_deployment("b" * 40)
        self.assertFalse(historical.active)
        self.assertEqual(historical.status, "deployed")
        self.assertTrue(active.active)
        self.assertEqual(active.status, "active")

    def test_preview_uses_active_baseline_and_never_deploys(self):
        settings = Mock()
        client = Mock()
        active = {"config": "c" * 40, "activity": "a" * 40}
        client.get_deployment_status.return_value = {"active_configuration": active}
        snapshot = ActivitySnapshot(pending_count=4, changes=[])
        with patch("director_mcp.server.get_settings", return_value=settings):
            with patch("director_mcp.server.get_client", return_value=client):
                with patch("director_mcp.server.read_pending_activity", return_value=snapshot) as reader:
                    result = preview_pending_deployment(limit=2)
        reader.assert_called_once_with(settings.activity, active["activity"], 2)
        self.assertEqual(result.pending_count, 4)
        self.assertTrue(result.has_more)
        client.deploy.assert_not_called()

    def test_forced_reader_rejects_unexpected_commands(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/director_activity_reader.py")],
            env={"SSH_ORIGINAL_COMMAND": "pending-activity not-a-checksum 20"},
            capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")

    def test_reader_query_contains_only_activity_metadata(self):
        spec = importlib.util.spec_from_file_location("reader", ROOT / "tools/director_activity_reader.py")
        reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reader)
        sql = reader.pending_query("a" * 40, 20)
        self.assertIn("WHERE checksum = UNHEX(", sql)
        self.assertIn("LIMIT 20", sql)
        self.assertNotIn("old_properties", sql)
        self.assertNotIn("new_properties", sql)
        with self.assertRaises(ValueError):
            reader.pending_query("none", 101)
