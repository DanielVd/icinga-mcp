#!/usr/bin/python3
"""Forced SSH command serving read-only Director activity metadata."""

import json
import os
import re
import subprocess


def pending_query(activity: str, limit: int) -> str:
    if not re.fullmatch(r"none|[0-9a-f]{40}", activity) or not 1 <= limit <= 100:
        raise ValueError("Invalid activity checksum or limit")
    baseline = ("SELECT 0 AS id" if activity == "none" else
                f"SELECT (SELECT id FROM director_activity_log WHERE checksum = UNHEX('{activity}')) AS id")
    return f"""
WITH baseline AS ({baseline}), pending AS (
    SELECT a.id, a.object_type, a.object_name, a.action_name, a.author, a.change_time
      FROM director_activity_log a JOIN baseline b ON a.id > b.id
     ORDER BY a.id DESC LIMIT {limit}
)
SELECT JSON_OBJECT(
    'baseline_found', b.id IS NOT NULL,
    'pending_count', (SELECT COUNT(*) FROM director_activity_log a WHERE a.id > b.id),
    'changes', (SELECT COALESCE(JSON_ARRAYAGG(JSON_OBJECT(
        'id', id, 'object_type', object_type, 'object_name', object_name,
        'action', action_name, 'author', author, 'change_time', change_time
    ) ORDER BY id DESC), JSON_ARRAY()) FROM pending)
) FROM baseline b;
"""


def main() -> None:
    args = os.environ.get("SSH_ORIGINAL_COMMAND", "").split()
    if len(args) != 3 or args[0] != "pending-activity" or not re.fullmatch(r"[0-9]{1,3}", args[2]):
        raise SystemExit("Expected pending-activity CHECKSUM LIMIT")
    try:
        sql = pending_query(args[1], int(args[2]))
        result = subprocess.run(
            ["/usr/bin/mysql", "--no-defaults", "--protocol=socket", "--user=director-mcp-audit",
             "--database=director", "--batch", "--raw", "--skip-column-names", "--execute", sql],
            capture_output=True, check=True, timeout=8,
        )
        snapshot = json.loads(result.stdout)
        if not snapshot.pop("baseline_found"):
            raise ValueError("Active configuration activity is absent from the audit log")
        if isinstance(snapshot.get("changes"), str):
            snapshot["changes"] = json.loads(snapshot["changes"])
    except (KeyError, ValueError, OSError, subprocess.SubprocessError):
        raise SystemExit("Could not read the Director activity snapshot") from None
    print(json.dumps(snapshot, ensure_ascii=False))


if __name__ == "__main__":
    main()
