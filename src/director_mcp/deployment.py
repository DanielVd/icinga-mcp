"""Read Director deployment status and pending activity metadata."""

import re
import subprocess

from pydantic import BaseModel

from .settings import DirectorActivitySettings


CHECKSUM_PATTERN = r"^[0-9a-fA-F]{40}$"


class ActivityEntry(BaseModel):
    id: int
    object_type: str
    object_name: str
    action: str
    author: str
    change_time: str


class ActivitySnapshot(BaseModel):
    pending_count: int
    changes: list[ActivityEntry]


class DeploymentPreview(ActivitySnapshot):
    active_config_checksum: str | None
    active_activity_checksum: str | None
    has_more: bool


class DeploymentVerification(BaseModel):
    expected_checksum: str
    active_checksum: str | None
    active_stage: str | None
    active: bool
    status: str


def read_pending_activity(settings: DirectorActivitySettings, activity: str | None, limit: int) -> ActivitySnapshot:
    if activity is not None and not re.fullmatch(CHECKSUM_PATTERN, activity):
        raise ValueError("Director returned an invalid activity checksum")
    if not 1 <= limit <= 100:
        raise ValueError("Activity limit must be between 1 and 100")
    baseline = activity.lower() if activity else "none"
    command = [
        "ssh", "-F", "/dev/null", "-T", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
        "-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={settings.known_hosts}",
        "-o", "ConnectTimeout=5", "-i", str(settings.identity_file),
        "--", settings.ssh_target, f"pending-activity {baseline} {limit}",
    ]
    try:
        process = subprocess.run(command, capture_output=True, check=True, timeout=12)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("Director activity reader failed. Check the SSH connection and the activity baseline.") from exc
    try:
        return ActivitySnapshot.model_validate_json(process.stdout)
    except ValueError as exc:
        raise RuntimeError("Director activity reader returned an invalid snapshot") from exc
