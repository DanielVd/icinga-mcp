"""Icinga2 MCP Server."""

import os
import json
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from .client import Icinga2Client

ICINGA_HOST = os.getenv("ICINGA_HOST", "vm-icinga.fritz.box")
ICINGA_USER = os.getenv("ICINGA_USER", "root")
ICINGA_PASSWORD = os.getenv("ICINGA_PASSWORD", "f18de2c07d6c2b66")
ICINGA_VERIFY_SSL = os.getenv("ICINGA_VERIFY_SSL", "false").lower() == "true"

mcp = FastMCP("icinga2-mcp", host="0.0.0.0", port=8092)


def get_client() -> Icinga2Client:
    return Icinga2Client(ICINGA_HOST, ICINGA_USER, ICINGA_PASSWORD, ICINGA_VERIFY_SSL)


@mcp.tool()
def get_api_status() -> str:
    """Get Icinga2 API status and version information."""
    client = get_client()
    status = client.get_api_status()
    return json.dumps(status, indent=2)


@mcp.tool()
def get_icinga_application_status() -> str:
    """Get Icinga2 application status (checks, notifications, uptime)."""
    client = get_client()
    status = client.get_status("IcingaApplication")
    return json.dumps(status, indent=2)


@mcp.tool()
def list_hosts(host_filter: str = Field(default="", description="Optional Icinga2 filter expression")) -> str:
    """List all monitored hosts. Optional filter uses Icinga2 filter syntax."""
    client = get_client()
    hosts = client.list_hosts(host_filter if host_filter else None)
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
    return json.dumps(result, indent=2)


@mcp.tool()
def get_host(host_name: str = Field(description="Host name")) -> str:
    """Get detailed information about a single host."""
    client = get_client()
    host = client.get_host(host_name)
    return json.dumps(host, indent=2)


@mcp.tool()
def list_services(host: str = Field(default="", description="Filter by host name"),
                  service_filter: str = Field(default="", description="Optional Icinga2 filter expression")) -> str:
    """List all services. Optionally filter by host or Icinga2 filter expression."""
    client = get_client()
    host_param = host if host else None
    filter_param = service_filter if service_filter else None
    services = client.list_services(host_param, filter_param)
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
    return json.dumps(result, indent=2)


@mcp.tool()
def get_service(host_name: str = Field(description="Host name"),
                service_name: str = Field(description="Service name")) -> str:
    """Get detailed information about a single service."""
    client = get_client()
    service = client.get_service(host_name, service_name)
    return json.dumps(service, indent=2)


@mcp.tool()
def list_hostgroups() -> str:
    """List all hostgroups."""
    client = get_client()
    groups = client.list_hostgroups()
    result = []
    for g in groups:
        attrs = g.get("attrs", {})
        result.append({
            "name": attrs.get("name"),
            "display_name": attrs.get("display_name"),
            "members": attrs.get("members", []),
        })
    return json.dumps(result, indent=2)


@mcp.tool()
def list_servicegroups() -> str:
    """List all servicegroups."""
    client = get_client()
    groups = client.list_servicegroups()
    result = []
    for g in groups:
        attrs = g.get("attrs", {})
        result.append({
            "name": attrs.get("name"),
            "display_name": attrs.get("display_name"),
            "members": attrs.get("members", []),
        })
    return json.dumps(result, indent=2)


@mcp.tool()
def list_downtimes(host: str = Field(default="", description="Filter by host name")) -> str:
    """List all active downtimes. Optionally filter by host."""
    client = get_client()
    host_param = host if host else None
    downtimes = client.list_downtimes(host_param)
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
    return json.dumps(result, indent=2)


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
    return json.dumps(result, indent=2)


@mcp.tool()
def remove_downtime(downtime_name: str = Field(description="Downtime name to remove")) -> str:
    """Remove an existing downtime."""
    client = get_client()
    result = client.remove_downtime(downtime_name)
    return json.dumps(result, indent=2)


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
    return json.dumps(result, indent=2)


@mcp.tool()
def remove_acknowledgement(host: str = Field(description="Host name"),
                           service: str = Field(default="", description="Service name (optional)")) -> str:
    """Remove acknowledgement from a host or service."""
    client = get_client()
    service_param = service if service else None
    result = client.remove_acknowledgement(host, service_param)
    return json.dumps(result, indent=2)


@mcp.tool()
def reschedule_check(host: str = Field(description="Host name"),
                     service: str = Field(default="", description="Service name (optional)"),
                     force: bool = Field(default=True, description="Force check")) -> str:
    """Reschedule a check for a host or service."""
    client = get_client()
    service_param = service if service else None
    result = client.reschedule_check(host, service_param, force)
    return json.dumps(result, indent=2)


@mcp.tool()
def list_check_commands() -> str:
    """List all available check commands."""
    client = get_client()
    commands = client.get_check_commands()
    result = []
    for c in commands:
        attrs = c.get("attrs", {})
        result.append({
            "name": attrs.get("name"),
            "command": attrs.get("command"),
            "timeout": attrs.get("timeout"),
        })
    return json.dumps(result, indent=2)


@mcp.tool()
def list_timeperiods() -> str:
    """List all configured timeperiods."""
    client = get_client()
    periods = client.list_timeperiods()
    result = []
    for p in periods:
        attrs = p.get("attrs", {})
        result.append({
            "name": attrs.get("name"),
            "display_name": attrs.get("display_name"),
            "ranges": attrs.get("ranges"),
        })
    return json.dumps(result, indent=2)


@mcp.tool()
def list_users() -> str:
    """List all configured users."""
    client = get_client()
    users = client.list_users()
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
    return json.dumps(result, indent=2)


@mcp.tool()
def list_notifications(host: str = Field(default="", description="Filter by host name")) -> str:
    """List all notifications. Optionally filter by host."""
    client = get_client()
    host_param = host if host else None
    notifications = client.list_notifications(host_param)
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
    return json.dumps(result, indent=2)


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
    return json.dumps(result, indent=2)


def main():
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
