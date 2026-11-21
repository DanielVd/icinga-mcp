"""Icinga2 MCP Server."""

import asyncio
import json
import time
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field

from .client import Icinga2Client
from .history import get_history
from .plugin_tools import register_catalog_tools
from .settings import Icinga2Settings

mcp = FastMCP("icinga2-mcp", host="0.0.0.0", port=8092)


HOST_LIST_ATTRS = [
    "name",
    "display_name",
    "address",
    "address6",
    "state",
    "state_type",
    "check_command",
    "groups",
    "last_check",
    "next_check",
    "acknowledgement",
    "downtime_depth",
    "last_state_change",
    "last_check_result",
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
    "last_state_change",
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
HOST_STATES = {0: "UP", 1: "DOWN"}
SERVICE_STATES = {0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN"}
WRITE_TOOLS = (
    "add_downtime", "remove_downtime", "add_acknowledgement",
    "remove_acknowledgement", "reschedule_check", "process_check_result",
)


class ProblemsSummary(BaseModel):
    hosts: list[dict]
    services: list[dict]
    host_problem_count: int
    service_problem_count: int


def summarize_host(row: dict) -> dict:
    attrs = row.get("attrs", {})
    check_result = attrs.get("last_check_result") or {}
    return {
        "name": attrs.get("name") or row.get("name"),
        "display_name": attrs.get("display_name"),
        "address": attrs.get("address"),
        "address6": attrs.get("address6"),
        "state": HOST_STATES.get(attrs.get("state"), "UNKNOWN"),
        "state_type": attrs.get("state_type"),
        "check_command": attrs.get("check_command"),
        "groups": attrs.get("groups", []),
        "last_check": attrs.get("last_check"),
        "next_check": attrs.get("next_check"),
        "acknowledgement": attrs.get("acknowledgement"),
        "downtime_depth": attrs.get("downtime_depth"),
        "last_state_change": attrs.get("last_state_change"),
        "output": check_result.get("output") or "",
        "performance_data": check_result.get("performance_data"),
    }


def summarize_service(row: dict) -> dict:
    attrs = row.get("attrs", {})
    check_result = attrs.get("last_check_result") or {}
    return {
        "name": attrs.get("name") or row.get("name"),
        "full_name": row.get("name"),
        "host_name": attrs.get("host_name"),
        "display_name": attrs.get("display_name"),
        "state": attrs.get("state"),
        "state_text": SERVICE_STATES.get(attrs.get("state"), "UNKNOWN"),
        "state_type": attrs.get("state_type"),
        "check_command": attrs.get("check_command"),
        "last_check": attrs.get("last_check"),
        "next_check": attrs.get("next_check"),
        "acknowledgement": attrs.get("acknowledgement"),
        "downtime_depth": attrs.get("downtime_depth"),
        "last_state_change": attrs.get("last_state_change"),
        "output": check_result.get("output") or "",
        "performance_data": check_result.get("performance_data"),
    }


def json_response(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


@lru_cache(maxsize=1)
def get_settings() -> Icinga2Settings:
    return Icinga2Settings()


@lru_cache(maxsize=None)
def get_client(instance: str | None = None, *, write: bool = False) -> Icinga2Client:
    settings = get_settings()
    if not settings.instances:
        if settings.host is None or settings.user is None or settings.password is None:
            raise ValueError("No Icinga 2 Core instance is configured")
        if instance not in (None, "default"):
            raise ValueError("The configured Core instance is named 'default'")
        return Icinga2Client(settings.host, settings.user, settings.password.get_secret_value(),
                             settings.verify_ssl)

    names = ", ".join(sorted(settings.instances))
    if instance is None:
        if len(settings.instances) != 1:
            raise ValueError(f"Specify the Core instance. Available instances: {names}")
        instance = next(iter(settings.instances))
    if instance not in settings.instances:
        raise ValueError(f"Unknown Core instance {instance!r}. Available instances: {names}")

    connection = settings.instances[instance]
    user, password = connection.user, connection.password
    if write:
        if connection.write_user is None or connection.write_password is None:
            raise ValueError(f"Writes are disabled for Core instance {instance!r}")
        user, password = connection.write_user, connection.write_password
    verify_ssl = str(connection.ca_bundle) if connection.ca_bundle else connection.verify_ssl
    return Icinga2Client("", user, password.get_secret_value(), verify_ssl,
                         base_url=str(connection.url), action_author=user if write else None)


@mcp.tool()
def health_check() -> str:
    """Report configured Core instances and plugin catalog availability without network calls."""
    settings = get_settings()
    instances = {name: {"write_enabled": connection.write_user is not None}
                 for name, connection in sorted(settings.instances.items())}
    if not instances and settings.host:
        instances["default"] = {"write_enabled": True}
    try:
        package_version = version("icinga-mcp")
    except PackageNotFoundError:
        package_version = None
    return json_response({
        "name": "icinga2-mcp",
        "version": package_version,
        "instances": instances,
        "plugin_catalog_configured": settings.plugin_catalog_path is not None,
        "history_configured": settings.history is not None,
    })


@mcp.tool()
def get_problems(
    instance: str | None = None, limit: int = 100,
    scope: Literal["host", "service", "both"] | None = None,
    severity: Literal["WARNING", "CRITICAL", "UNKNOWN"] | None = None,
    host_group: Annotated[str, Field(min_length=1)] | None = None,
    min_duration_minutes: Annotated[int, Field(ge=1, le=525600)] | None = None,
    acknowledged: bool | None = None, in_downtime: bool | None = None,
) -> Annotated[CallToolResult, ProblemsSummary]:
    """Report live Icinga 2 Core problems for both hosts and services.

    Filter by exact host group, time in the current state, acknowledgement or downtime.
    A service severity implies service scope unless an explicit scope is supplied.
    The limit applies separately to each list. Counts include all filtered matches.
    """
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    scope = scope or ("service" if severity else "both")
    if scope == "host" and severity:
        raise ValueError("Service severity requires service or both scope")
    params = {"filter_vars": {"problem_group": host_group}} if host_group else {}
    cutoff = int(time.time()) - 60 * min_duration_minutes if min_duration_minutes else None
    client = get_client(instance)
    hosts = []
    services = []
    if scope in {"host", "both"}:
        expression = problem_filter("host", None, host_group, cutoff, acknowledged, in_downtime)
        hosts = [summarize_host(row) for row in client.list_hosts(expression, attrs=HOST_LIST_ATTRS, **params)]
    if scope in {"service", "both"}:
        expression = problem_filter("service", severity, host_group, cutoff, acknowledged, in_downtime)
        services = [summarize_service(row) for row in
                    client.list_services(service_filter=expression, attrs=SERVICE_LIST_ATTRS, **params)]
    hosts.sort(key=lambda row: row["name"] or "")
    services.sort(key=lambda row: (row["host_name"] or "", row["name"] or ""))
    for row in hosts[:limit] + services[:limit]:
        row["output"] = row["output"][:500]
        row.pop("performance_data")
    summary = {
        "hosts": hosts[:limit], "services": services[:limit],
        "host_problem_count": len(hosts), "service_problem_count": len(services),
    }
    return CallToolResult(
        content=[TextContent(type="text", text=json_response(summary))],
        structuredContent=summary,
    )


def problem_filter(object_type: str, severity: str | None, host_group: str | None,
                   cutoff: int | None, acknowledged: bool | None, in_downtime: bool | None) -> str:
    expression = f"{object_type}.state != 0"
    if severity:
        expression = with_state_filter(object_type, "", severity, SERVICE_STATES)
    conditions = [expression]
    if host_group:
        conditions.append("problem_group in host.groups")
    if cutoff is not None:
        conditions.extend([f"{object_type}.last_state_change > 0", f"{object_type}.last_state_change <= {cutoff}"])
    if acknowledged is not None:
        operator = "!=" if acknowledged else "=="
        conditions.append(f"{object_type}.acknowledgement {operator} 0")
    if in_downtime is not None:
        operator = ">" if in_downtime else "=="
        conditions.append(f"{object_type}.downtime_depth {operator} 0")
    return " && ".join(conditions)


@mcp.tool()
def get_api_status(instance: str | None = None) -> str:
    """Get Icinga2 API status and version information."""
    client = get_client(instance)
    status = client.get_api_status()
    return json_response(status)


@mcp.tool()
def get_icinga_application_status(instance: str | None = None) -> str:
    """Get Icinga2 application status (checks, notifications, uptime)."""
    client = get_client(instance)
    status = client.get_status("IcingaApplication")
    return json_response(status)


@mcp.tool()
def list_hosts(host_filter: str = Field(default="", description="Optional Icinga2 filter expression"),
               instance: str | None = None, state: str | None = None,
               name_contains: str | None = None) -> str:
    """List live Icinga 2 Core hosts and their current UP or DOWN state. Filter by state, name or Icinga expression."""
    client = get_client(instance)
    host_filter = with_state_filter("host", host_filter, state, HOST_STATES)
    hosts = client.list_hosts(host_filter, attrs=HOST_LIST_ATTRS)
    return json_response([summarize_host(row) for row in hosts if matches_name(row, name_contains)])


@mcp.tool()
def get_host(host_name: str = Field(description="Host name"),
             instance: str | None = None) -> str:
    """Get a monitored host's current runtime state and latest check result from Icinga 2 Core."""
    client = get_client(instance)
    host = client.get_host(host_name)
    return json_response(host)


@mcp.tool()
def list_services(host: str = Field(default="", description="Filter by host name"),
                  service_filter: str = Field(default="", description="Optional Icinga2 filter expression"),
                  instance: str | None = None, state: str | None = None,
                  name_contains: str | None = None) -> str:
    """List live Icinga 2 Core services and their current OK, WARNING, CRITICAL or UNKNOWN state.

    Filter by host, state, name substring or Icinga expression. Use get_problems for a combined problem summary.
    """
    client = get_client(instance)
    host_param = host if host else None
    filter_param = with_state_filter("service", service_filter, state, SERVICE_STATES)
    services = client.list_services(host_param, filter_param, attrs=SERVICE_LIST_ATTRS)
    return json_response([summarize_service(row) for row in services if matches_name(row, name_contains)])


def with_state_filter(object_type: str, expression: str, state: str | None,
                      states: dict[int, str]) -> str | None:
    if state is None:
        return expression or None
    code = next((code for code, label in states.items() if label == state.upper()), None)
    if code is None:
        raise ValueError(f"Invalid {object_type} state. Expected one of: {', '.join(states.values())}")
    condition = f"{object_type}.state == {code}"
    return f"({expression}) && {condition}" if expression else condition


def matches_name(row: dict, name_contains: str | None) -> bool:
    if not name_contains:
        return True
    name = row.get("attrs", {}).get("name") or row.get("name") or ""
    return name_contains.casefold() in name.casefold()


@mcp.tool()
def get_service(host_name: str = Field(description="Host name"),
                service_name: str = Field(description="Service name"),
                instance: str | None = None) -> str:
    """Get a monitored service's current runtime state and latest check result from Icinga 2 Core."""
    client = get_client(instance)
    service = client.get_service(host_name, service_name)
    return json_response(service)


@mcp.tool()
def list_hostgroups(instance: str | None = None) -> str:
    """List all hostgroups."""
    client = get_client(instance)
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
def list_servicegroups(instance: str | None = None) -> str:
    """List all servicegroups."""
    client = get_client(instance)
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
def list_downtimes(host: str = Field(default="", description="Filter by host name"),
                   instance: str | None = None) -> str:
    """List all active downtimes. Optionally filter by host."""
    client = get_client(instance)
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
                 service: str = Field(default="", description="Service name (optional, for service downtime)"),
                 instance: str | None = None, start_time: int | None = None,
                 all_services: bool | None = None) -> str:
    """Schedule downtime for a host or service."""
    client = get_client(instance, write=True)
    service_param = service if service else None
    result = client.add_downtime(host, author, comment, duration, service_param,
                                 start_time=start_time, all_services=all_services)
    return json_response(result)


@mcp.tool()
def remove_downtime(downtime_name: str = "", instance: str | None = None,
                    host: str | None = None, service: str | None = None) -> str:
    """Remove one downtime by name or all downtimes for the specified host or service."""
    client = get_client(instance, write=True)
    result = client.remove_downtime(downtime_name, host=host, service=service)
    return json_response(result)


@mcp.tool()
def add_acknowledgement(host: str = Field(description="Host name"),
                        author: str = Field(description="Author name"),
                        comment: str = Field(description="Comment for acknowledgement"),
                        service: str = Field(default="", description="Service name (optional, for service acknowledgement)"),
                        sticky: bool = Field(default=True, description="Sticky acknowledgement"),
                        notify: bool = Field(default=True, description="Send notification"),
                        persistent: bool = Field(default=False, description="Persistent comment"),
                        instance: str | None = None, expiry_seconds: int | None = None) -> str:
    """Acknowledge a problem on a host or service."""
    client = get_client(instance, write=True)
    service_param = service if service else None
    result = client.add_acknowledgement(host, author, comment, service_param, sticky, notify, persistent,
                                        expiry_seconds=expiry_seconds)
    return json_response(result)


@mcp.tool()
def remove_acknowledgement(host: str = Field(description="Host name"),
                           service: str = Field(default="", description="Service name (optional)"),
                           instance: str | None = None) -> str:
    """Remove acknowledgement from a host or service."""
    client = get_client(instance, write=True)
    service_param = service if service else None
    result = client.remove_acknowledgement(host, service_param)
    return json_response(result)


@mcp.tool()
def reschedule_check(host: str = Field(description="Host name"),
                     service: str = Field(default="", description="Service name (optional)"),
                     force: bool = Field(default=True, description="Force check"),
                     instance: str | None = None) -> str:
    """Reschedule a check for a host or service."""
    client = get_client(instance, write=True)
    service_param = service if service else None
    result = client.reschedule_check(host, service_param, force)
    return json_response(result)


@mcp.tool()
def list_check_commands(instance: str | None = None) -> str:
    """List all available check commands."""
    client = get_client(instance)
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
def list_timeperiods(instance: str | None = None) -> str:
    """List all configured timeperiods."""
    client = get_client(instance)
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
def list_users(instance: str | None = None) -> str:
    """List all configured users."""
    client = get_client(instance)
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
def list_notifications(host: str = Field(default="", description="Filter by host name"),
                       instance: str | None = None) -> str:
    """List all notifications. Optionally filter by host."""
    client = get_client(instance)
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
                         check_source: str = Field(default="mcp-server", description="Check source identifier"),
                         instance: str | None = None) -> str:
    """Process a passive check result for a host or service."""
    client = get_client(instance, write=True)
    service_param = service if service else None
    result = client.process_check_result(host, service_param, exit_status, output, check_source)
    return json_response(result)


async def configure_tools(server: FastMCP, settings: Icinga2Settings) -> None:
    if not settings.instances and not settings.host:
        for tool in await server.list_tools():
            if tool.name != "health_check":
                server.remove_tool(tool.name)
    elif settings.instances and all(instance.write_user is None for instance in settings.instances.values()):
        for name in WRITE_TOOLS:
            server.remove_tool(name)

    if settings.plugin_catalog_path is not None:
        register_catalog_tools(server, settings.plugin_catalog_path)
    if settings.history is not None:
        server.add_tool(get_history)


def main():
    settings = get_settings()
    mcp.settings.host = settings.mcp_host
    mcp.settings.port = settings.mcp_port
    asyncio.run(configure_tools(mcp, settings))
    mcp.run(transport=settings.transport)


if __name__ == "__main__":
    main()
