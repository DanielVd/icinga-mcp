"""Icinga2 MCP Server."""

import json
from functools import lru_cache
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from .client import Icinga2Client
from .settings import Icinga2Settings

mcp = FastMCP("icinga2-mcp", host="0.0.0.0", port=8092)


HOST_LIST_ATTRS = [
    "name",
    "display_name",
    "address",
    "last_state",
    "state_type",
    "check_command",
    "groups",
    "last_check",
    "next_check",
    "acknowledgement",
    "downtime_depth",
]
SERVICE_LIST_ATTRS = [
    "name",
    "host_name",
    "display_name",
    "state",
    "state_type",
    "check_command",
    "last_check",
    "next_check",
    "acknowledgement",
    "downtime_depth",
    "last_check_result",
]
GROUP_LIST_ATTRS = ["name", "display_name", "members"]
DOWNTIME_LIST_ATTRS = [
    "name",
    "host_name",
    "service_name",
    "author",
    "comment",
    "start_time",
    "end_time",
    "duration",
    "triggered_by_id",
]
CHECK_COMMAND_LIST_ATTRS = ["name", "command", "timeout"]
TIMEPERIOD_LIST_ATTRS = ["name", "display_name", "ranges"]
USER_LIST_ATTRS = ["name", "display_name", "email", "states", "types", "groups"]
NOTIFICATION_LIST_ATTRS = ["name", "host_name", "service_name", "command", "interval", "period", "states", "types"]


def json_response(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


@lru_cache(maxsize=1)
def get_settings() -> Icinga2Settings:
    return Icinga2Settings()


@lru_cache(maxsize=1)
def get_client() -> Icinga2Client:
    settings = get_settings()
    return Icinga2Client(settings.host, settings.user, settings.password, settings.verify_ssl)


@mcp.tool()
def get_api_status() -> str:
    """Get Icinga2 API status and version information."""
    client = get_client()
    status = client.get_api_status()
    return json_response(status)


@mcp.tool()
def get_icinga_application_status() -> str:
    """Get Icinga2 application status (checks, notifications, uptime)."""
    client = get_client()
    status = client.get_status("IcingaApplication")
    return json_response(status)


@mcp.tool()
def list_hosts(host_filter: str = Field(default="", description="Optional Icinga2 filter expression")) -> str:
    """List all monitored hosts. Optional filter uses Icinga2 filter syntax."""
    client = get_client()
    hosts = client.list_hosts(host_filter if host_filter else None, attrs=HOST_LIST_ATTRS)
    result = []
    for h in hosts:
        attrs = h.get("attrs", {})
        result.append({
            "name": attrs.get("name"),
            "display_name": attrs.get("display_name"),
            "address": attrs.get("address"),
            "state": "UP" if attrs.get("last_state") == 0 else "DOWN",
            "state_type": attrs.get("state_type"),
            "check_command": attrs.get("check_command"),
            "groups": attrs.get("groups", []),
            "last_check": attrs.get("last_check"),
            "next_check": attrs.get("next_check"),
            "acknowledgement": attrs.get("acknowledgement"),
            "downtime_depth": attrs.get("downtime_depth"),
        })
    return json_response(result)


@mcp.tool()
def get_host(host_name: str = Field(description="Host name")) -> str:
    """Get detailed information about a single host."""
    client = get_client()
    host = client.get_host(host_name)
    return json_response(host)


@mcp.tool()
def list_services(host: str = Field(default="", description="Filter by host name"),
                  service_filter: str = Field(default="", description="Optional Icinga2 filter expression")) -> str:
    """List all services. Optionally filter by host or Icinga2 filter expression."""
    client = get_client()
    host_param = host if host else None
    filter_param = service_filter if service_filter else None
    services = client.list_services(host_param, filter_param, attrs=SERVICE_LIST_ATTRS)
    result = []
    for s in services:
        attrs = s.get("attrs", {})
        result.append({
            "name": attrs.get("name"),
            "host_name": attrs.get("host_name"),
            "display_name": attrs.get("display_name"),
            "state": attrs.get("state"),
            "state_text": {0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN"}.get(attrs.get("state"), "UNKNOWN"),
            "state_type": attrs.get("state_type"),
            "check_command": attrs.get("check_command"),
            "last_check": attrs.get("last_check"),
            "next_check": attrs.get("next_check"),
            "acknowledgement": attrs.get("acknowledgement"),
            "downtime_depth": attrs.get("downtime_depth"),
            "output": (attrs.get("last_check_result") or {}).get("output", ""),
        })
    return json_response(result)


@mcp.tool()
def get_service(host_name: str = Field(description="Host name"),
                service_name: str = Field(description="Service name")) -> str:
    """Get detailed information about a single service."""
    client = get_client()
    service = client.get_service(host_name, service_name)
    return json_response(service)


@mcp.tool()
def list_hostgroups() -> str:
    """List all hostgroups."""
    client = get_client()
    groups = client.list_hostgroups(attrs=GROUP_LIST_ATTRS)
    result = []
    for g in groups:
        attrs = g.get("attrs", {})
        result.append({
            "name": attrs.get("name"),
            "display_name": attrs.get("display_name"),
            "members": attrs.get("members", []),
        })
    return json_response(result)


@mcp.tool()
def list_servicegroups() -> str:
    """List all servicegroups."""
    client = get_client()
    groups = client.list_servicegroups(attrs=GROUP_LIST_ATTRS)
    result = []
    for g in groups:
        attrs = g.get("attrs", {})
        result.append({
            "name": attrs.get("name"),
            "display_name": attrs.get("display_name"),
            "members": attrs.get("members", []),
        })
    return json_response(result)


@mcp.tool()
def list_downtimes(host: str = Field(default="", description="Filter by host name")) -> str:
    """List all active downtimes. Optionally filter by host."""
    client = get_client()
    host_param = host if host else None
    downtimes = client.list_downtimes(host_param, attrs=DOWNTIME_LIST_ATTRS)
    result = []
    for d in downtimes:
        attrs = d.get("attrs", {})
        result.append({
            "name": attrs.get("name"),
            "host_name": attrs.get("host_name"),
            "service_name": attrs.get("service_name"),
            "author": attrs.get("author"),
            "comment": attrs.get("comment"),
            "start_time": attrs.get("start_time"),
            "end_time": attrs.get("end_time"),
            "duration": attrs.get("duration"),
            "triggered_by_id": attrs.get("triggered_by_id"),
        })
    return json_response(result)


@mcp.tool()
def add_downtime(host: str = Field(description="Host name"),
                 author: str = Field(description="Author name"),
                 comment: str = Field(description="Comment for downtime"),
                 duration: int = Field(default=3600, description="Duration in seconds (default 3600)"),
                 service: str = Field(default="", description="Service name (optional, for service downtime)")) -> str:
    """Schedule downtime for a host or service."""
    client = get_client()
    service_param = service if service else None
    result = client.add_downtime(host, author, comment, duration, service_param)
    return json_response(result)


@mcp.tool()
def remove_downtime(downtime_name: str = Field(description="Downtime name to remove")) -> str:
    """Remove an existing downtime."""
    client = get_client()
    result = client.remove_downtime(downtime_name)
    return json_response(result)


@mcp.tool()
def add_acknowledgement(host: str = Field(description="Host name"),
                        author: str = Field(description="Author name"),
                        comment: str = Field(description="Comment for acknowledgement"),
                        service: str = Field(default="", description="Service name (optional, for service acknowledgement)"),
                        sticky: bool = Field(default=True, description="Sticky acknowledgement"),
                        notify: bool = Field(default=True, description="Send notification"),
                        persistent: bool = Field(default=False, description="Persistent comment")) -> str:
    """Acknowledge a problem on a host or service."""
    client = get_client()
    service_param = service if service else None
    result = client.add_acknowledgement(host, author, comment, service_param, sticky, notify, persistent)
    return json_response(result)


@mcp.tool()
def remove_acknowledgement(host: str = Field(description="Host name"),
                           service: str = Field(default="", description="Service name (optional)")) -> str:
    """Remove acknowledgement from a host or service."""
    client = get_client()
    service_param = service if service else None
    result = client.remove_acknowledgement(host, service_param)
    return json_response(result)


@mcp.tool()
def reschedule_check(host: str = Field(description="Host name"),
                     service: str = Field(default="", description="Service name (optional)"),
                     force: bool = Field(default=True, description="Force check")) -> str:
    """Reschedule a check for a host or service."""
    client = get_client()
    service_param = service if service else None
    result = client.reschedule_check(host, service_param, force)
    return json_response(result)


@mcp.tool()
def list_check_commands() -> str:
    """List all available check commands."""
    client = get_client()
    commands = client.get_check_commands(attrs=CHECK_COMMAND_LIST_ATTRS)
    result = []
    for c in commands:
        attrs = c.get("attrs", {})
        result.append({
            "name": attrs.get("name"),
            "command": attrs.get("command"),
            "timeout": attrs.get("timeout"),
        })
    return json_response(result)


@mcp.tool()
def list_timeperiods() -> str:
    """List all configured timeperiods."""
    client = get_client()
    periods = client.list_timeperiods(attrs=TIMEPERIOD_LIST_ATTRS)
    result = []
    for p in periods:
        attrs = p.get("attrs", {})
        result.append({
            "name": attrs.get("name"),
            "display_name": attrs.get("display_name"),
            "ranges": attrs.get("ranges"),
        })
    return json_response(result)


@mcp.tool()
def list_users() -> str:
    """List all configured users."""
    client = get_client()
    users = client.list_users(attrs=USER_LIST_ATTRS)
    result = []
    for u in users:
        attrs = u.get("attrs", {})
        result.append({
            "name": attrs.get("name"),
            "display_name": attrs.get("display_name"),
            "email": attrs.get("email"),
            "states": attrs.get("states"),
            "types": attrs.get("types"),
            "groups": attrs.get("groups", []),
        })
    return json_response(result)


@mcp.tool()
def list_notifications(host: str = Field(default="", description="Filter by host name")) -> str:
    """List all notifications. Optionally filter by host."""
    client = get_client()
    host_param = host if host else None
    notifications = client.list_notifications(host_param, attrs=NOTIFICATION_LIST_ATTRS)
    result = []
    for n in notifications:
        attrs = n.get("attrs", {})
        result.append({
            "name": attrs.get("name"),
            "host_name": attrs.get("host_name"),
            "service_name": attrs.get("service_name"),
            "command": attrs.get("command"),
            "interval": attrs.get("interval"),
            "period": attrs.get("period"),
            "states": attrs.get("states"),
            "types": attrs.get("types"),
        })
    return json_response(result)


@mcp.tool()
def process_check_result(host: str = Field(description="Host name"),
                         exit_status: int = Field(description="Exit status (0=OK, 1=WARNING, 2=CRITICAL, 3=UNKNOWN)"),
                         output: str = Field(description="Plugin output"),
                         service: str = Field(default="", description="Service name (optional)"),
                         check_source: str = Field(default="mcp-server", description="Check source identifier")) -> str:
    """Process a passive check result for a host or service."""
    client = get_client()
    service_param = service if service else None
    result = client.process_check_result(host, service_param, exit_status, output, check_source)
    return json_response(result)


def main():
    get_settings()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
