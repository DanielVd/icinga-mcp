"""Icinga Director MCP Server."""

import json
from functools import lru_cache
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from .client import DirectorClient
from .settings import DirectorSettings

mcp = FastMCP("director-mcp", host="0.0.0.0", port=8093)


def json_response(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def paginate(items: list, limit: int, offset: int) -> list:
    if offset < 0:
        offset = 0
    if limit <= 0:
        return items[offset:]
    return items[offset:offset + limit]


def summarize_host(host: dict) -> dict:
    return {
        "object_name": host.get("object_name"),
        "object_type": host.get("object_type"),
        "address": host.get("address"),
        "display_name": host.get("display_name"),
        "imports": host.get("imports", []),
        "disabled": host.get("disabled"),
    }


def summarize_service(service: dict) -> dict:
    return {
        "object_name": service.get("object_name"),
        "object_type": service.get("object_type"),
        "host": service.get("host"),
        "display_name": service.get("display_name"),
        "check_command": service.get("check_command"),
        "imports": service.get("imports", []),
        "disabled": service.get("disabled"),
    }


@lru_cache(maxsize=1)
def get_settings() -> DirectorSettings:
    return DirectorSettings()


@lru_cache(maxsize=1)
def get_client() -> DirectorClient:
    settings = get_settings()
    return DirectorClient(settings.base_url, settings.user, settings.password, settings.verify_ssl)


def parse_json_field(field_name: str, raw_value: str) -> dict:
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON: {exc.msg}") from exc


# === HOSTS ===

@mcp.tool()
def list_hosts(limit: int = Field(default=0, description="Max returned hosts, 0 = all"),
               offset: int = Field(default=0, description="Skip first N hosts"),
               summary: bool = Field(default=False, description="Return compact host summary")) -> str:
    """List hosts configured in Icinga Director. Use limit/offset for large inventories."""
    client = get_client()
    hosts = client.list_hosts()
    page = paginate(hosts, limit, offset)
    if summary:
        page = [summarize_host(host) for host in page]
    return json_response({
        "total": len(hosts),
        "count": len(page),
        "limit": limit,
        "offset": offset,
        "results": page,
    })


@mcp.tool()
def get_host(host_name: str = Field(description="Host name"),
             resolved: bool = Field(default=False, description="Resolve inherited properties"),
             with_services: bool = Field(default=False, description="Include attached services")) -> str:
    """Get detailed information about a single host from Director."""
    client = get_client()
    host = client.get_host(host_name, resolved, with_services)
    return json_response(host)


@mcp.tool()
def create_host(object_name: str = Field(description="Host name"),
                object_type: str = Field(default="object", description="object or template"),
                address: str = Field(default="", description="Host address"),
                display_name: str = Field(default="", description="Display name"),
                imports: str = Field(default="", description="Comma-separated template imports"),
                vars_json: str = Field(default="", description="JSON string of custom variables")) -> str:
    """Create a new host in Icinga Director."""
    client = get_client()
    host_data = {
        "object_name": object_name,
        "object_type": object_type,
    }
    if address:
        host_data["address"] = address
    if display_name:
        host_data["display_name"] = display_name
    if imports:
        host_data["imports"] = [i.strip() for i in imports.split(",")]
    if vars_json:
        host_data["vars"] = parse_json_field("vars_json", vars_json)

    result = client.create_host(host_data)
    return json_response(result)


@mcp.tool()
def update_host(host_name: str = Field(description="Host name to update"),
                address: str = Field(default="", description="Host address"),
                display_name: str = Field(default="", description="Display name"),
                imports: str = Field(default="", description="Comma-separated template imports"),
                vars_json: str = Field(default="", description="JSON string of custom variables")) -> str:
    """Update an existing host in Icinga Director."""
    client = get_client()
    host_data = {}
    if address:
        host_data["address"] = address
    if display_name:
        host_data["display_name"] = display_name
    if imports:
        host_data["imports"] = [i.strip() for i in imports.split(",")]
    if vars_json:
        host_data["vars"] = parse_json_field("vars_json", vars_json)

    result = client.update_host(host_name, host_data)
    return json_response(result)


@mcp.tool()
def delete_host(host_name: str = Field(description="Host name to delete")) -> str:
    """Delete a host from Icinga Director."""
    client = get_client()
    result = client.delete_host(host_name)
    return json_response(result)


@mcp.tool()
def get_host_ticket(host_name: str = Field(description="Host name")) -> str:
    """Get agent ticket for a host."""
    client = get_client()
    result = client.get_host_ticket(host_name)
    return json_response({"ticket": result})


# === SERVICES ===

@mcp.tool()
def list_services(limit: int = Field(default=0, description="Max returned services, 0 = all"),
                  offset: int = Field(default=0, description="Skip first N services"),
                  summary: bool = Field(default=False, description="Return compact service summary")) -> str:
    """List services configured in Icinga Director. Use limit/offset for large inventories."""
    client = get_client()
    services = client.list_services()
    page = paginate(services, limit, offset)
    if summary:
        page = [summarize_service(service) for service in page]
    return json_response({
        "total": len(services),
        "count": len(page),
        "limit": limit,
        "offset": offset,
        "results": page,
    })


@mcp.tool()
def get_service(service_name: str = Field(description="Service name"),
                host_name: str = Field(default="", description="Host name (for host-specific services)")) -> str:
    """Get detailed information about a single service from Director."""
    client = get_client()
    host_param = host_name if host_name else None
    service = client.get_service(service_name, host_param)
    return json_response(service)


@mcp.tool()
def create_service(object_name: str = Field(description="Service name"),
                   object_type: str = Field(default="object", description="object or template"),
                   check_command: str = Field(default="", description="Check command"),
                   display_name: str = Field(default="", description="Display name"),
                   imports: str = Field(default="", description="Comma-separated template imports"),
                   vars_json: str = Field(default="", description="JSON string of custom variables"),
                   host_name: str = Field(default="", description="Host name (for host-specific services)")) -> str:
    """Create a new service in Icinga Director."""
    client = get_client()
    service_data = {
        "object_name": object_name,
        "object_type": object_type,
    }
    if check_command:
        service_data["check_command"] = check_command
    if display_name:
        service_data["display_name"] = display_name
    if imports:
        service_data["imports"] = [i.strip() for i in imports.split(",")]
    if vars_json:
        service_data["vars"] = parse_json_field("vars_json", vars_json)

    host_param = host_name if host_name else None
    result = client.create_service(service_data, host_param)
    return json_response(result)


@mcp.tool()
def update_service(service_name: str = Field(description="Service name to update"),
                   check_command: str = Field(default="", description="Check command"),
                   display_name: str = Field(default="", description="Display name"),
                   vars_json: str = Field(default="", description="JSON string of custom variables"),
                   host_name: str = Field(default="", description="Host name")) -> str:
    """Update an existing service in Icinga Director."""
    client = get_client()
    service_data = {}
    if check_command:
        service_data["check_command"] = check_command
    if display_name:
        service_data["display_name"] = display_name
    if vars_json:
        service_data["vars"] = parse_json_field("vars_json", vars_json)

    host_param = host_name if host_name else None
    result = client.update_service(service_name, service_data, host_param)
    return json_response(result)


@mcp.tool()
def delete_service(service_name: str = Field(description="Service name to delete"),
                   host_name: str = Field(default="", description="Host name")) -> str:
    """Delete a service from Icinga Director."""
    client = get_client()
    host_param = host_name if host_name else None
    result = client.delete_service(service_name, host_param)
    return json_response(result)


# === SERVICE APPLY RULES ===

@mcp.tool()
def list_service_apply_rules() -> str:
    """List all service apply rules."""
    client = get_client()
    rules = client.list_service_apply_rules()
    return json_response(rules)


# === HOSTGROUPS ===

@mcp.tool()
def list_hostgroups() -> str:
    """List all hostgroups."""
    client = get_client()
    groups = client.list_hostgroups()
    return json_response(groups)


@mcp.tool()
def get_hostgroup(group_name: str = Field(description="Hostgroup name")) -> str:
    """Get single hostgroup."""
    client = get_client()
    group = client.get_hostgroup(group_name)
    return json_response(group)


@mcp.tool()
def create_hostgroup(object_name: str = Field(description="Hostgroup name"),
                     display_name: str = Field(default="", description="Display name"),
                     assign_filter: str = Field(default="", description="Assign filter")) -> str:
    """Create a hostgroup."""
    client = get_client()
    group_data = {"object_name": object_name}
    if display_name:
        group_data["display_name"] = display_name
    if assign_filter:
        group_data["assign_filter"] = assign_filter
    result = client.create_hostgroup(group_data)
    return json_response(result)


@mcp.tool()
def update_hostgroup(group_name: str = Field(description="Hostgroup name"),
                     display_name: str = Field(default="", description="Display name"),
                     assign_filter: str = Field(default="", description="Assign filter")) -> str:
    """Update a hostgroup."""
    client = get_client()
    group_data = {}
    if display_name:
        group_data["display_name"] = display_name
    if assign_filter:
        group_data["assign_filter"] = assign_filter
    result = client.update_hostgroup(group_name, group_data)
    return json_response(result)


@mcp.tool()
def delete_hostgroup(group_name: str = Field(description="Hostgroup name")) -> str:
    """Delete a hostgroup."""
    client = get_client()
    result = client.delete_hostgroup(group_name)
    return json_response(result)


# === SERVICEGROUPS ===

@mcp.tool()
def list_servicegroups() -> str:
    """List all servicegroups."""
    client = get_client()
    groups = client.list_servicegroups()
    return json_response(groups)


@mcp.tool()
def get_servicegroup(group_name: str = Field(description="Servicegroup name")) -> str:
    """Get single servicegroup."""
    client = get_client()
    group = client.get_servicegroup(group_name)
    return json_response(group)


@mcp.tool()
def create_servicegroup(object_name: str = Field(description="Servicegroup name"),
                        display_name: str = Field(default="", description="Display name"),
                        assign_filter: str = Field(default="", description="Assign filter")) -> str:
    """Create a servicegroup."""
    client = get_client()
    group_data = {"object_name": object_name}
    if display_name:
        group_data["display_name"] = display_name
    if assign_filter:
        group_data["assign_filter"] = assign_filter
    result = client.create_servicegroup(group_data)
    return json_response(result)


@mcp.tool()
def update_servicegroup(group_name: str = Field(description="Servicegroup name"),
                        display_name: str = Field(default="", description="Display name"),
                        assign_filter: str = Field(default="", description="Assign filter")) -> str:
    """Update a servicegroup."""
    client = get_client()
    group_data = {}
    if display_name:
        group_data["display_name"] = display_name
    if assign_filter:
        group_data["assign_filter"] = assign_filter
    result = client.update_servicegroup(group_name, group_data)
    return json_response(result)


@mcp.tool()
def delete_servicegroup(group_name: str = Field(description="Servicegroup name")) -> str:
    """Delete a servicegroup."""
    client = get_client()
    result = client.delete_servicegroup(group_name)
    return json_response(result)


# === COMMANDS ===

@mcp.tool()
def list_commands() -> str:
    """List all check commands."""
    client = get_client()
    commands = client.list_commands()
    return json_response(commands)


@mcp.tool()
def get_command(command_name: str = Field(description="Command name")) -> str:
    """Get single command."""
    client = get_client()
    command = client.get_command(command_name)
    return json_response(command)


@mcp.tool()
def create_command(object_name: str = Field(description="Command name"),
                   object_type: str = Field(default="object", description="object or template"),
                   command: str = Field(default="", description="Command line"),
                   methods_execute: str = Field(default="", description="Methods execute")) -> str:
    """Create a command."""
    client = get_client()
    command_data = {
        "object_name": object_name,
        "object_type": object_type,
    }
    if command:
        command_data["command"] = command
    if methods_execute:
        command_data["methods_execute"] = methods_execute
    result = client.create_command(command_data)
    return json_response(result)


@mcp.tool()
def update_command(command_name: str = Field(description="Command name"),
                   command: str = Field(default="", description="Command line"),
                   methods_execute: str = Field(default="", description="Methods execute")) -> str:
    """Update a command."""
    client = get_client()
    command_data = {}
    if command:
        command_data["command"] = command
    if methods_execute:
        command_data["methods_execute"] = methods_execute
    result = client.update_command(command_name, command_data)
    return json_response(result)


@mcp.tool()
def delete_command(command_name: str = Field(description="Command name")) -> str:
    """Delete a command."""
    client = get_client()
    result = client.delete_command(command_name)
    return json_response(result)


# === TEMPLATES ===

@mcp.tool()
def list_templates(object_type: str = Field(default="host", description="host or service")) -> str:
    """List all templates (host or service)."""
    client = get_client()
    templates = client.list_templates(object_type)
    return json_response(templates)


# === SERVICE SETS ===

@mcp.tool()
def list_service_sets() -> str:
    """List all service sets."""
    client = get_client()
    sets = client.list_service_sets()
    return json_response(sets)


@mcp.tool()
def get_service_set(set_name: str = Field(description="Service set name")) -> str:
    """Get single service set."""
    client = get_client()
    s = client.get_service_set(set_name)
    return json_response(s)


@mcp.tool()
def create_service_set(object_name: str = Field(description="Service set name"),
                       description: str = Field(default="", description="Description")) -> str:
    """Create a service set."""
    client = get_client()
    set_data = {"object_name": object_name}
    if description:
        set_data["description"] = description
    result = client.create_service_set(set_data)
    return json_response(result)


@mcp.tool()
def update_service_set(set_name: str = Field(description="Service set name"),
                       description: str = Field(default="", description="Description")) -> str:
    """Update a service set."""
    client = get_client()
    set_data = {}
    if description:
        set_data["description"] = description
    result = client.update_service_set(set_name, set_data)
    return json_response(result)


@mcp.tool()
def delete_service_set(set_name: str = Field(description="Service set name")) -> str:
    """Delete a service set."""
    client = get_client()
    result = client.delete_service_set(set_name)
    return json_response(result)


# === ZONES ===

@mcp.tool()
def list_zones() -> str:
    """List all zones."""
    client = get_client()
    zones = client.list_zones()
    return json_response(zones)


@mcp.tool()
def get_zone(zone_name: str = Field(description="Zone name")) -> str:
    """Get single zone."""
    client = get_client()
    zone = client.get_zone(zone_name)
    return json_response(zone)


@mcp.tool()
def create_zone(object_name: str = Field(description="Zone name"),
                object_type: str = Field(default="object", description="object or template"),
                parent: str = Field(default="", description="Parent zone")) -> str:
    """Create a zone."""
    client = get_client()
    zone_data = {
        "object_name": object_name,
        "object_type": object_type,
    }
    if parent:
        zone_data["parent"] = parent
    result = client.create_zone(zone_data)
    return json_response(result)


@mcp.tool()
def update_zone(zone_name: str = Field(description="Zone name"),
                parent: str = Field(default="", description="Parent zone")) -> str:
    """Update a zone."""
    client = get_client()
    zone_data = {}
    if parent:
        zone_data["parent"] = parent
    result = client.update_zone(zone_name, zone_data)
    return json_response(result)


@mcp.tool()
def delete_zone(zone_name: str = Field(description="Zone name")) -> str:
    """Delete a zone."""
    client = get_client()
    result = client.delete_zone(zone_name)
    return json_response(result)


# === ENDPOINTS ===

@mcp.tool()
def list_endpoints() -> str:
    """List all endpoints."""
    client = get_client()
    endpoints = client.list_endpoints()
    return json_response(endpoints)


@mcp.tool()
def get_endpoint(endpoint_name: str = Field(description="Endpoint name")) -> str:
    """Get single endpoint."""
    client = get_client()
    endpoint = client.get_endpoint(endpoint_name)
    return json_response(endpoint)


@mcp.tool()
def create_endpoint(object_name: str = Field(description="Endpoint name"),
                    host: str = Field(default="", description="Host address"),
                    port: int = Field(default=0, description="Port")) -> str:
    """Create an endpoint."""
    client = get_client()
    endpoint_data = {"object_name": object_name}
    if host:
        endpoint_data["host"] = host
    if port:
        endpoint_data["port"] = port
    result = client.create_endpoint(endpoint_data)
    return json_response(result)


@mcp.tool()
def update_endpoint(endpoint_name: str = Field(description="Endpoint name"),
                    host: str = Field(default="", description="Host address"),
                    port: int = Field(default=0, description="Port")) -> str:
    """Update an endpoint."""
    client = get_client()
    endpoint_data = {}
    if host:
        endpoint_data["host"] = host
    if port:
        endpoint_data["port"] = port
    result = client.update_endpoint(endpoint_name, endpoint_data)
    return json_response(result)


@mcp.tool()
def delete_endpoint(endpoint_name: str = Field(description="Endpoint name")) -> str:
    """Delete an endpoint."""
    client = get_client()
    result = client.delete_endpoint(endpoint_name)
    return json_response(result)


# === TIMEPERIODS ===

@mcp.tool()
def list_timeperiods() -> str:
    """List all timeperiods."""
    client = get_client()
    periods = client.list_timeperiods()
    return json_response(periods)


@mcp.tool()
def get_timeperiod(period_name: str = Field(description="Timeperiod name")) -> str:
    """Get single timeperiod."""
    client = get_client()
    period = client.get_timeperiod(period_name)
    return json_response(period)


@mcp.tool()
def create_timeperiod(object_name: str = Field(description="Timeperiod name"),
                      display_name: str = Field(default="", description="Display name"),
                      prefer_ranges: bool = Field(default=False, description="Prefer ranges")) -> str:
    """Create a timeperiod."""
    client = get_client()
    period_data = {
        "object_name": object_name,
        "prefer_ranges": prefer_ranges,
    }
    if display_name:
        period_data["display_name"] = display_name
    result = client.create_timeperiod(period_data)
    return json_response(result)


@mcp.tool()
def update_timeperiod(period_name: str = Field(description="Timeperiod name"),
                      display_name: str = Field(default="", description="Display name"),
                      prefer_ranges: bool = Field(default=False, description="Prefer ranges")) -> str:
    """Update a timeperiod."""
    client = get_client()
    period_data = {}
    if display_name:
        period_data["display_name"] = display_name
    period_data["prefer_ranges"] = prefer_ranges
    result = client.update_timeperiod(period_name, period_data)
    return json_response(result)


@mcp.tool()
def delete_timeperiod(period_name: str = Field(description="Timeperiod name")) -> str:
    """Delete a timeperiod."""
    client = get_client()
    result = client.delete_timeperiod(period_name)
    return json_response(result)


# === USERS ===

@mcp.tool()
def list_users() -> str:
    """List all users."""
    client = get_client()
    users = client.list_users()
    return json_response(users)


@mcp.tool()
def get_user(user_name: str = Field(description="User name")) -> str:
    """Get single user."""
    client = get_client()
    user = client.get_user(user_name)
    return json_response(user)


@mcp.tool()
def create_user(object_name: str = Field(description="User name"),
                display_name: str = Field(default="", description="Display name"),
                email: str = Field(default="", description="Email address"),
                states: list = Field(default_factory=lambda: ["Up", "Down", "Ok", "Warning", "Critical", "Unknown"],
                                     description="States to notify for"),
                types: list = Field(default_factory=lambda: ["Problem", "Recovery", "Acknowledgement", "Downtime", "FlappingStart", "FlappingEnd"],
                                    description="Notification types")) -> str:
    """Create a user."""
    client = get_client()
    user_data = {
        "object_name": object_name,
        "states": states,
        "types": types,
    }
    if display_name:
        user_data["display_name"] = display_name
    if email:
        user_data["email"] = email
    result = client.create_user(user_data)
    return json_response(result)


@mcp.tool()
def update_user(user_name: str = Field(description="User name"),
                display_name: str = Field(default="", description="Display name"),
                email: str = Field(default="", description="Email address")) -> str:
    """Update a user."""
    client = get_client()
    user_data = {}
    if display_name:
        user_data["display_name"] = display_name
    if email:
        user_data["email"] = email
    result = client.update_user(user_name, user_data)
    return json_response(result)


@mcp.tool()
def delete_user(user_name: str = Field(description="User name")) -> str:
    """Delete a user."""
    client = get_client()
    result = client.delete_user(user_name)
    return json_response(result)


# === USERGROUPS ===

@mcp.tool()
def list_usergroups() -> str:
    """List all usergroups."""
    client = get_client()
    groups = client.list_usergroups()
    return json_response(groups)


@mcp.tool()
def get_usergroup(group_name: str = Field(description="Usergroup name")) -> str:
    """Get single usergroup."""
    client = get_client()
    group = client.get_usergroup(group_name)
    return json_response(group)


@mcp.tool()
def create_usergroup(object_name: str = Field(description="Usergroup name"),
                     display_name: str = Field(default="", description="Display name")) -> str:
    """Create a usergroup."""
    client = get_client()
    group_data = {"object_name": object_name}
    if display_name:
        group_data["display_name"] = display_name
    result = client.create_usergroup(group_data)
    return json_response(result)


@mcp.tool()
def update_usergroup(group_name: str = Field(description="Usergroup name"),
                     display_name: str = Field(default="", description="Display name")) -> str:
    """Update a usergroup."""
    client = get_client()
    group_data = {}
    if display_name:
        group_data["display_name"] = display_name
    result = client.update_usergroup(group_name, group_data)
    return json_response(result)


@mcp.tool()
def delete_usergroup(group_name: str = Field(description="Usergroup name")) -> str:
    """Delete a usergroup."""
    client = get_client()
    result = client.delete_usergroup(group_name)
    return json_response(result)


# === NOTIFICATIONS ===

@mcp.tool()
def list_notifications() -> str:
    """List all notifications."""
    client = get_client()
    notifications = client.list_notifications()
    return json_response(notifications)


@mcp.tool()
def get_notification(notification_name: str = Field(description="Notification name")) -> str:
    """Get single notification."""
    client = get_client()
    notification = client.get_notification(notification_name)
    return json_response(notification)


@mcp.tool()
def create_notification(object_name: str = Field(description="Notification name"),
                        object_type: str = Field(default="object", description="object or template"),
                        command: str = Field(default="", description="Notification command"),
                        states: list = Field(default_factory=lambda: ["Up", "Down", "Ok", "Warning", "Critical", "Unknown"],
                                             description="States"),
                        types: list = Field(default_factory=lambda: ["Problem", "Recovery"],
                                            description="Types")) -> str:
    """Create a notification."""
    client = get_client()
    notification_data = {
        "object_name": object_name,
        "object_type": object_type,
        "states": states,
        "types": types,
    }
    if command:
        notification_data["command"] = command
    result = client.create_notification(notification_data)
    return json_response(result)


@mcp.tool()
def update_notification(notification_name: str = Field(description="Notification name"),
                        command: str = Field(default="", description="Notification command")) -> str:
    """Update a notification."""
    client = get_client()
    notification_data = {}
    if command:
        notification_data["command"] = command
    result = client.update_notification(notification_name, notification_data)
    return json_response(result)


@mcp.tool()
def delete_notification(notification_name: str = Field(description="Notification name")) -> str:
    """Delete a notification."""
    client = get_client()
    result = client.delete_notification(notification_name)
    return json_response(result)


# === SCHEDULED DOWNTIMES ===

@mcp.tool()
def list_downtimes() -> str:
    """List all scheduled downtimes."""
    client = get_client()
    downtimes = client.list_downtimes()
    return json_response(downtimes)


@mcp.tool()
def get_downtime(downtime_name: str = Field(description="Downtime name")) -> str:
    """Get single scheduled downtime."""
    client = get_client()
    downtime = client.get_downtime(downtime_name)
    return json_response(downtime)


@mcp.tool()
def create_downtime(object_name: str = Field(description="Downtime name"),
                    assign_filter: str = Field(default="", description="Assign filter"),
                    author: str = Field(default="", description="Author"),
                    comment: str = Field(default="", description="Comment")) -> str:
    """Create a scheduled downtime."""
    client = get_client()
    downtime_data = {"object_name": object_name}
    if assign_filter:
        downtime_data["assign_filter"] = assign_filter
    if author:
        downtime_data["author"] = author
    if comment:
        downtime_data["comment"] = comment
    result = client.create_downtime(downtime_data)
    return json_response(result)


@mcp.tool()
def update_downtime(downtime_name: str = Field(description="Downtime name"),
                    author: str = Field(default="", description="Author"),
                    comment: str = Field(default="", description="Comment")) -> str:
    """Update a scheduled downtime."""
    client = get_client()
    downtime_data = {}
    if author:
        downtime_data["author"] = author
    if comment:
        downtime_data["comment"] = comment
    result = client.update_downtime(downtime_name, downtime_data)
    return json_response(result)


@mcp.tool()
def delete_downtime(downtime_name: str = Field(description="Downtime name")) -> str:
    """Delete a scheduled downtime."""
    client = get_client()
    result = client.delete_downtime(downtime_name)
    return json_response(result)


# === DEPLOYMENT ===

@mcp.tool()
def deploy_pending_changes() -> str:
    """Deploy pending changes to Icinga2."""
    client = get_client()
    result = client.deploy()
    return json_response(result)


@mcp.tool()
def get_deployment_status(configs: str = Field(default="", description="Comma-separated config checksums"),
                          activities: str = Field(default="", description="Comma-separated activity checksums")) -> str:
    """Get deployment status."""
    client = get_client()
    configs_param = configs if configs else None
    activities_param = activities if activities else None
    result = client.get_deployment_status(configs_param, activities_param)
    return json_response(result)


# === ACTIVITY LOG ===

@mcp.tool()
def get_activity_log(limit: int = Field(default=50, description="Number of entries")) -> str:
    """Get Director activity log."""
    client = get_client()
    log = client.get_activity_log(limit)
    return json_response(log)


# === DATA LISTS ===

@mcp.tool()
def list_datalists() -> str:
    """List all data lists."""
    client = get_client()
    datalists = client.list_datalists()
    return json_response(datalists)


@mcp.tool()
def get_datalist(datalist_name: str = Field(description="Data list name")) -> str:
    """Get single data list."""
    client = get_client()
    datalist = client.get_datalist(datalist_name)
    return json_response(datalist)


@mcp.tool()
def create_datalist(object_name: str = Field(description="Data list name"),
                    owner: str = Field(default="", description="Owner")) -> str:
    """Create a data list."""
    client = get_client()
    datalist_data = {"object_name": object_name}
    if owner:
        datalist_data["owner"] = owner
    result = client.create_datalist(datalist_data)
    return json_response(result)


@mcp.tool()
def update_datalist(datalist_name: str = Field(description="Data list name"),
                    owner: str = Field(default="", description="Owner")) -> str:
    """Update a data list."""
    client = get_client()
    datalist_data = {}
    if owner:
        datalist_data["owner"] = owner
    result = client.update_datalist(datalist_name, datalist_data)
    return json_response(result)


@mcp.tool()
def delete_datalist(datalist_name: str = Field(description="Data list name")) -> str:
    """Delete a data list."""
    client = get_client()
    result = client.delete_datalist(datalist_name)
    return json_response(result)


# === DATAFIELDS ===

@mcp.tool()
def list_datafields() -> str:
    """List all data fields."""
    client = get_client()
    datafields = client.list_datafields()
    return json_response(datafields)


@mcp.tool()
def get_datafield(varname: str = Field(description="Variable name")) -> str:
    """Get single data field."""
    client = get_client()
    datafield = client.get_datafield(varname)
    return json_response(datafield)


@mcp.tool()
def create_datafield(varname: str = Field(description="Variable name"),
                     caption: str = Field(default="", description="Caption"),
                     datatype: str = Field(default="string", description="Data type")) -> str:
    """Create a data field."""
    client = get_client()
    datafield_data = {
        "varname": varname,
        "datatype": datatype,
    }
    if caption:
        datafield_data["caption"] = caption
    result = client.create_datafield(datafield_data)
    return json_response(result)


@mcp.tool()
def update_datafield(varname: str = Field(description="Variable name"),
                     caption: str = Field(default="", description="Caption")) -> str:
    """Update a data field."""
    client = get_client()
    datafield_data = {}
    if caption:
        datafield_data["caption"] = caption
    result = client.update_datafield(varname, datafield_data)
    return json_response(result)


@mcp.tool()
def delete_datafield(varname: str = Field(description="Variable name")) -> str:
    """Delete a data field."""
    client = get_client()
    result = client.delete_datafield(varname)
    return json_response(result)


# === IMPORT SOURCES ===

@mcp.tool()
def list_import_sources() -> str:
    """List all import sources."""
    client = get_client()
    sources = client.list_import_sources()
    return json_response(sources)


@mcp.tool()
def get_import_source(source_name: str = Field(description="Import source name")) -> str:
    """Get single import source."""
    client = get_client()
    source = client.get_import_source(source_name)
    return json_response(source)


@mcp.tool()
def create_import_source(object_name: str = Field(description="Import source name"),
                         source_type: str = Field(default="", description="Source type")) -> str:
    """Create an import source."""
    client = get_client()
    source_data = {
        "object_name": object_name,
        "source_type": source_type,
    }
    result = client.create_import_source(source_data)
    return json_response(result)


@mcp.tool()
def update_import_source(source_name: str = Field(description="Import source name"),
                         source_type: str = Field(default="", description="Source type")) -> str:
    """Update an import source."""
    client = get_client()
    source_data = {}
    if source_type:
        source_data["source_type"] = source_type
    result = client.update_import_source(source_name, source_data)
    return json_response(result)


@mcp.tool()
def delete_import_source(source_name: str = Field(description="Import source name")) -> str:
    """Delete an import source."""
    client = get_client()
    result = client.delete_import_source(source_name)
    return json_response(result)


# === SYNC RULES ===

@mcp.tool()
def list_sync_rules() -> str:
    """List all sync rules."""
    client = get_client()
    rules = client.list_sync_rules()
    return json_response(rules)


@mcp.tool()
def get_sync_rule(rule_name: str = Field(description="Sync rule name")) -> str:
    """Get single sync rule."""
    client = get_client()
    rule = client.get_sync_rule(rule_name)
    return json_response(rule)


@mcp.tool()
def create_sync_rule(object_name: str = Field(description="Sync rule name"),
                     import_source: str = Field(default="", description="Import source"),
                     purge_action: str = Field(default="", description="Purge action")) -> str:
    """Create a sync rule."""
    client = get_client()
    rule_data = {
        "object_name": object_name,
        "import_source": import_source,
    }
    if purge_action:
        rule_data["purge_action"] = purge_action
    result = client.create_sync_rule(rule_data)
    return json_response(result)


@mcp.tool()
def update_sync_rule(rule_name: str = Field(description="Sync rule name"),
                     import_source: str = Field(default="", description="Import source"),
                     purge_action: str = Field(default="", description="Purge action")) -> str:
    """Update a sync rule."""
    client = get_client()
    rule_data = {}
    if import_source:
        rule_data["import_source"] = import_source
    if purge_action:
        rule_data["purge_action"] = purge_action
    result = client.update_sync_rule(rule_name, rule_data)
    return json_response(result)


@mcp.tool()
def delete_sync_rule(rule_name: str = Field(description="Sync rule name")) -> str:
    """Delete a sync rule."""
    client = get_client()
    result = client.delete_sync_rule(rule_name)
    return json_response(result)


# === JOBS ===

@mcp.tool()
def list_jobs() -> str:
    """List all jobs."""
    client = get_client()
    jobs = client.list_jobs()
    return json_response(jobs)


@mcp.tool()
def get_job(job_name: str = Field(description="Job name")) -> str:
    """Get single job."""
    client = get_client()
    job = client.get_job(job_name)
    return json_response(job)


@mcp.tool()
def create_job(object_name: str = Field(description="Job name"),
               job_type: str = Field(default="", description="Job type"),
               action: str = Field(default="", description="Action")) -> str:
    """Create a job."""
    client = get_client()
    job_data = {
        "object_name": object_name,
        "job_type": job_type,
    }
    if action:
        job_data["action"] = action
    result = client.create_job(job_data)
    return json_response(result)


@mcp.tool()
def update_job(job_name: str = Field(description="Job name"),
               action: str = Field(default="", description="Action")) -> str:
    """Update a job."""
    client = get_client()
    job_data = {}
    if action:
        job_data["action"] = action
    result = client.update_job(job_name, job_data)
    return json_response(result)


@mcp.tool()
def delete_job(job_name: str = Field(description="Job name")) -> str:
    """Delete a job."""
    client = get_client()
    result = client.delete_job(job_name)
    return json_response(result)


@mcp.tool()
def run_job(job_name: str = Field(description="Job name")) -> str:
    """Run a job."""
    client = get_client()
    result = client.run_job(job_name)
    return json_response(result)


# === BRANCHES ===

@mcp.tool()
def list_branches() -> str:
    """List all branches."""
    client = get_client()
    branches = client.list_branches()
    return json_response(branches)


@mcp.tool()
def get_branch(branch_name: str = Field(description="Branch name")) -> str:
    """Get single branch."""
    client = get_client()
    branch = client.get_branch(branch_name)
    return json_response(branch)


@mcp.tool()
def create_branch(object_name: str = Field(description="Branch name"),
                  description: str = Field(default="", description="Description")) -> str:
    """Create a branch."""
    client = get_client()
    branch_data = {"object_name": object_name}
    if description:
        branch_data["description"] = description
    result = client.create_branch(branch_data)
    return json_response(result)


@mcp.tool()
def update_branch(branch_name: str = Field(description="Branch name"),
                  description: str = Field(default="", description="Description")) -> str:
    """Update a branch."""
    client = get_client()
    branch_data = {}
    if description:
        branch_data["description"] = description
    result = client.update_branch(branch_name, branch_data)
    return json_response(result)


@mcp.tool()
def delete_branch(branch_name: str = Field(description="Branch name")) -> str:
    """Delete a branch."""
    client = get_client()
    result = client.delete_branch(branch_name)
    return json_response(result)


@mcp.tool()
def merge_branch(branch_name: str = Field(description="Branch name")) -> str:
    """Merge a branch."""
    client = get_client()
    result = client.merge_branch(branch_name)
    return json_response(result)


def main():
    get_settings()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
