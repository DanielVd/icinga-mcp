"""Read incident history from the Icinga DB Web JSON export."""

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import quote

import requests
from pydantic import AwareDatetime, BaseModel, Field

from .settings import HistorySettings, Icinga2Settings


EventType = Literal[
    "state_change", "notification", "ack_set", "ack_clear", "comment_add",
    "comment_remove", "downtime_start", "downtime_end", "flapping_start", "flapping_end",
]
DETAIL_KEYS = {
    "state_change": "state", "notification": "notification", "ack_set": "acknowledgement",
    "ack_clear": "acknowledgement", "comment_add": "comment", "comment_remove": "comment",
    "downtime_start": "downtime", "downtime_end": "downtime",
    "flapping_start": "flapping", "flapping_end": "flapping",
}
ACTOR_FIELDS = {
    "ack_set": "author", "ack_clear": "cleared_by", "comment_add": "author",
    "comment_remove": "removed_by", "downtime_start": "author", "downtime_end": "cancelled_by",
}


class HistoryEvent(BaseModel):
    timestamp: AwareDatetime
    event_type: str
    host: str
    service: str | None = None
    state: int | None = None
    state_type: str | None = None
    author: str | None = None
    detail: str | None = None


class HistoryResult(BaseModel):
    start: AwareDatetime
    end: AwareDatetime
    has_more: bool
    events: list[HistoryEvent]


class HistoryClient:
    def __init__(self, settings: HistorySettings):
        self.url = str(settings.url).rstrip("/") + "/icingadb/history"
        self.timeout = settings.timeout
        self.session = requests.Session()
        self.session.auth = (settings.user, settings.password.get_secret_value())
        self.session.verify = str(settings.ca_bundle) if settings.ca_bundle else settings.verify_ssl
        self.session.headers["Accept"] = "application/json"

    def get_events(self, *, host: str, service: str | None, start: datetime, end: datetime,
                   event_type: EventType | None, limit: int) -> HistoryResult:
        filters = [
            f"event_time>={quote(start.isoformat(timespec='seconds'), safe='')}",
            f"event_time<={quote(end.isoformat(timespec='seconds'), safe='')}",
            f"host.name={quote(host, safe='')}",
        ]
        if service:
            filters.append(f"service.name={quote(service, safe='')}")
        if event_type:
            filters.append(f"event_type={quote(event_type, safe='')}")
        query = "&".join([*filters, f"limit={limit + 1}", "format=json"])
        try:
            response = self.session.get(f"{self.url}?{query}", timeout=self.timeout, allow_redirects=False)
        except requests.RequestException as exc:
            raise RuntimeError("Could not reach Icinga DB Web history") from exc
        if response.status_code != 200:
            raise RuntimeError(f"Icinga DB Web history returned HTTP {response.status_code}")
        try:
            rows = response.json()
        except ValueError as exc:
            raise RuntimeError("Icinga DB Web history returned invalid JSON") from exc
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise RuntimeError("Icinga DB Web history did not return an event list")
        return HistoryResult(start=start, end=end, has_more=len(rows) > limit,
                             events=[parse_event(row) for row in rows[:limit]])


def parse_event(row: dict) -> HistoryEvent:
    event_type = row["event_type"]
    host = (row.get("host") or {}).get("name", "")
    service = (row.get("service") or {}).get("name")
    detail = row.get(DETAIL_KEYS.get(event_type, "")) or {}
    state_type = detail.get("state_type") if event_type == "state_change" else None
    raw_state = detail.get("soft_state" if state_type == "soft" else "hard_state") if state_type else None
    message = detail.get("output") if event_type == "state_change" else detail.get("comment")
    return HistoryEvent(timestamp=row["event_time"], event_type=event_type, host=host, service=service,
                        state=raw_state, state_type=state_type, author=detail.get(ACTOR_FIELDS.get(event_type, "")),
                        detail=message[:500] if isinstance(message, str) else None)


@lru_cache(maxsize=1)
def get_history_client() -> HistoryClient:
    settings = Icinga2Settings().history
    if settings is None:
        raise ValueError("Configure ICINGA_HISTORY to read Icinga DB Web history")
    return HistoryClient(settings)


def get_history(
    host: Annotated[str, Field(min_length=1)], service: str | None = None,
    start: AwareDatetime | None = None, end: AwareDatetime | None = None,
    event_type: EventType | None = None, limit: Annotated[int, Field(ge=1, le=200)] = 50,
) -> HistoryResult:
    """Read recent state changes, acknowledgements, downtimes or other Icinga DB Web events.

    Provide an exact host and optionally a service. Start and end must include timezones.
    The default window is 24 hours. The longest allowed window is 31 days.
    """
    if not host.strip() or "*" in host or (service and "*" in service):
        raise ValueError("Specify an exact host and service without wildcards")
    now = datetime.now(timezone.utc)
    end = end.astimezone(timezone.utc) if end is not None else now
    start = start.astimezone(timezone.utc) if start is not None else end - timedelta(days=1)
    if not timedelta(0) < end - start <= timedelta(days=31):
        raise ValueError("History start must precede end by at most 31 days")
    return get_history_client().get_events(
        host=host, service=service, start=start, end=end, event_type=event_type, limit=limit,
    )
