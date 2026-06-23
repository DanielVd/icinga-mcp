"""Parsing helpers for Icinga Director deployment pages.

The Director REST API exposes only ``config/deploy`` and
``config/deployment-status`` (checksums). The actual Icinga2 startup log of a
deployment -- where validation warnings and errors live -- is only rendered in
the web UI at ``/director/deployment?id=<id>``. These helpers turn that HTML
into structured data and are intentionally network-free so they can be unit
tested against captured fixtures.
"""

import html
import re
from collections import Counter

# A deployment row in the list at /director/config/deployments, e.g.:
#   <tr class="succeeded running"><td><a href="/director/deployment?id=1110">smt-web09c (33f0bbc)</a></td>...
_DEPLOYMENT_ROW_RE = re.compile(
    r'<tr class="(?P<classes>[^"]*)">.*?'
    r'href="[^"]*?/deployment\?id=(?P<id>\d+)"[^>]*>(?P<label>[^<]*)</a>',
    re.S,
)

_STAGE_RE = re.compile(r"<th>\s*Stage name\s*</th>\s*<td>([^<]+)</td>", re.S)
_STARTUP_RE = re.compile(
    r'<th>\s*Startup\s*</th>\s*<td>\s*<div class="(succeeded|failed)"', re.S
)
_LOGFILE_RE = re.compile(r'<pre class="logfile">(.*?)</pre>', re.S)
_TAG_RE = re.compile(r"<[^>]+>")

# A log line: [2026-06-23 09:37:01 +0200] warning/Checkable: message
_LOG_LINE_RE = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\]\s+(?P<level>\w+)/(?P<facility>\w+):\s*(?P<message>.*)$"
)

# Levels that warrant attention when reviewing a deployment.
ALERT_LEVELS = ("warning", "critical")


def _strip_html(fragment: str) -> str:
    return html.unescape(_TAG_RE.sub("", fragment))


def parse_deployment_list(page_html: str) -> list:
    """Parse the deployment list page into ``[{id, label, succeeded, active}]``.

    Rows are returned in document order (newest first, as Director renders them).
    """
    deployments = []
    for match in _DEPLOYMENT_ROW_RE.finditer(page_html):
        classes = match.group("classes").split()
        deployments.append(
            {
                "id": int(match.group("id")),
                "label": _strip_html(match.group("label")).strip(),
                "succeeded": "succeeded" in classes,
                "active": "active" in classes,
            }
        )
    return deployments


def parse_startup_log(detail_html: str) -> dict:
    """Parse a /director/deployment?id=<id> detail page.

    Returns the stage name, whether startup succeeded, the parsed log entries,
    a per-level summary and the subset of entries at an alert level
    (warning/critical).
    """
    stage_match = _STAGE_RE.search(detail_html)
    startup_match = _STARTUP_RE.search(detail_html)
    log_match = _LOGFILE_RE.search(detail_html)

    entries = parse_log_text(_strip_html(log_match.group(1)) if log_match else "")
    summary = Counter(entry["level"] for entry in entries)
    warnings = [e for e in entries if e["level"] in ALERT_LEVELS]

    return {
        "stage_name": stage_match.group(1).strip() if stage_match else None,
        "startup_succeeded": (startup_match.group(1) == "succeeded") if startup_match else None,
        "summary": dict(summary),
        "warning_count": sum(summary.get(level, 0) for level in ALERT_LEVELS),
        "warnings": warnings,
        "entries": entries,
    }


def parse_log_text(text: str) -> list:
    """Parse cleaned Icinga2 startup-log text into structured entries.

    Continuation lines (indented wraps of the previous message) are folded back
    into the preceding entry's message.
    """
    entries = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        match = _LOG_LINE_RE.match(line)
        if match:
            entries.append(
                {
                    "timestamp": match.group("timestamp"),
                    "level": match.group("level"),
                    "facility": match.group("facility"),
                    "message": match.group("message").strip(),
                }
            )
        elif entries:
            entries[-1]["message"] = f"{entries[-1]['message']} {line.strip()}".strip()
    return entries
