"""Icinga Director REST API client."""

import os
from datetime import datetime
from typing import Optional

import requests
from requests.adapters import HTTPAdapter


DEFAULT_TIMEOUT = float(os.getenv("DIRECTOR_REQUEST_TIMEOUT", "30"))
DEFAULT_POOL_CONNECTIONS = int(os.getenv("DIRECTOR_POOL_CONNECTIONS", "20"))
DEFAULT_POOL_MAXSIZE = int(os.getenv("DIRECTOR_POOL_MAXSIZE", "50"))


class DirectorClient:
    """Client for Icinga Director REST API."""

    def __init__(self, base_url: str, user: str, password: str, verify_ssl: bool = False):
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = DEFAULT_TIMEOUT
        self.session = requests.Session()
        self.session.auth = (user, password)
        self.session.verify = verify_ssl
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        adapter = HTTPAdapter(
            pool_connections=DEFAULT_POOL_CONNECTIONS,
            pool_maxsize=DEFAULT_POOL_MAXSIZE,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        resp = self.session.get(f"{self.base_url}/{path}", params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict, params: Optional[dict] = None) -> dict:
        resp = self.session.post(f"{self.base_url}/{path}", json=data, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, data: dict, params: Optional[dict] = None) -> dict:
        resp = self.session.put(f"{self.base_url}/{path}", json=data, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str, params: Optional[dict] = None) -> dict:
        resp = self.session.delete(f"{self.base_url}/{path}", params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # Hosts

    def list_hosts(self) -> list:
        """List all hosts from Director."""
        result = self._get("hosts")
        return result.get("objects", [])

    def get_host(self, name: str, resolved: bool = False, with_services: bool = False) -> dict:
        """Get single host by name."""
        params = {"name": name}
        if resolved:
            params["resolved"] = "1"
        if with_services:
            params["withServices"] = "1"
        return self._get("host", params=params)

    def create_host(self, host_data: dict) -> dict:
        """Create a new host."""
        return self._post("host", host_data)

    def update_host(self, name: str, host_data: dict) -> dict:
        """Update existing host."""
        return self._post("host", host_data, params={"name": name})

    def replace_host(self, name: str, host_data: dict) -> dict:
        """Replace host entirely (PUT)."""
        return self._put("host", host_data, params={"name": name})

    def delete_host(self, name: str) -> dict:
        """Delete host."""
        return self._delete("host", params={"name": name})

    def get_host_ticket(self, name: str) -> str:
        """Get agent ticket for host."""
        return self._get("host/ticket", params={"name": name})

    # Services

    def list_services(self) -> list:
        """List all services from Director."""
        result = self._get("services")
        return result.get("objects", [])

    def get_service(self, name: str, host: Optional[str] = None) -> dict:
        """Get single service."""
        params = {"name": name}
        if host:
            params["host"] = host
        return self._get("service", params=params)

    def create_service(self, service_data: dict, host: Optional[str] = None,
                       allow_overrides: bool = False) -> dict:
        """Create a new service."""
        params = {}
        if host:
            params["host"] = host
        if allow_overrides:
            params["allowOverrides"] = "1"
        return self._post("service", service_data, params=params)

    def update_service(self, name: str, service_data: dict,
                       host: Optional[str] = None) -> dict:
        """Update existing service."""
        params = {"name": name}
        if host:
            params["host"] = host
        return self._post("service", service_data, params=params)

    def delete_service(self, name: str, host: Optional[str] = None) -> dict:
        """Delete service."""
        params = {"name": name}
        if host:
            params["host"] = host
        return self._delete("service", params=params)

    # Service Apply Rules

    def list_service_apply_rules(self) -> list:
        """List all service apply rules."""
        result = self._get("serviceapplyrules")
        return result.get("objects", [])

    # Hostgroups

    def list_hostgroups(self) -> list:
        """List all hostgroups."""
        result = self._get("hostgroups")
        return result.get("objects", [])

    def get_hostgroup(self, name: str) -> dict:
        """Get single hostgroup."""
        return self._get("hostgroup", params={"name": name})

    def create_hostgroup(self, group_data: dict) -> dict:
        """Create hostgroup."""
        return self._post("hostgroup", group_data)

    def update_hostgroup(self, name: str, group_data: dict) -> dict:
        """Update hostgroup."""
        return self._post("hostgroup", group_data, params={"name": name})

    def delete_hostgroup(self, name: str) -> dict:
        """Delete hostgroup."""
        return self._delete("hostgroup", params={"name": name})

    # Servicegroups

    def list_servicegroups(self) -> list:
        """List all servicegroups."""
        result = self._get("servicegroups")
        return result.get("objects", [])

    def get_servicegroup(self, name: str) -> dict:
        """Get single servicegroup."""
        return self._get("servicegroup", params={"name": name})

    def create_servicegroup(self, group_data: dict) -> dict:
        """Create servicegroup."""
        return self._post("servicegroup", group_data)

    def update_servicegroup(self, name: str, group_data: dict) -> dict:
        """Update servicegroup."""
        return self._post("servicegroup", group_data, params={"name": name})

    def delete_servicegroup(self, name: str) -> dict:
        """Delete servicegroup."""
        return self._delete("servicegroup", params={"name": name})

    # Commands

    def list_commands(self) -> list:
        """List all commands."""
        result = self._get("commands")
        return result.get("objects", [])

    def get_command(self, name: str) -> dict:
        """Get single command."""
        return self._get("command", params={"name": name})

    def create_command(self, command_data: dict) -> dict:
        """Create command."""
        return self._post("command", command_data)

    def update_command(self, name: str, command_data: dict) -> dict:
        """Update command."""
        return self._post("command", command_data, params={"name": name})

    def delete_command(self, name: str) -> dict:
        """Delete command."""
        return self._delete("command", params={"name": name})

    # Templates

    def list_templates(self, object_type: str = "host") -> list:
        """List templates (host or service)."""
        endpoint = "hosts" if object_type == "host" else "services"
        result = self._get(endpoint)
        objects = result.get("objects", [])
        return [o for o in objects if o.get("object_type") == "template"]

    # Service Sets

    def list_service_sets(self) -> list:
        """List all service sets."""
        result = self._get("servicesets")
        return result.get("objects", [])

    def get_service_set(self, name: str) -> dict:
        """Get single service set."""
        return self._get("serviceset", params={"name": name})

    def create_service_set(self, set_data: dict) -> dict:
        """Create service set."""
        return self._post("serviceset", set_data)

    def update_service_set(self, name: str, set_data: dict) -> dict:
        """Update service set."""
        return self._post("serviceset", set_data, params={"name": name})

    def delete_service_set(self, name: str) -> dict:
        """Delete service set."""
        return self._delete("serviceset", params={"name": name})

    # Zones

    def list_zones(self) -> list:
        """List all zones."""
        result = self._get("zones")
        return result.get("objects", [])

    def get_zone(self, name: str) -> dict:
        """Get single zone."""
        return self._get("zone", params={"name": name})

    def create_zone(self, zone_data: dict) -> dict:
        """Create zone."""
        return self._post("zone", zone_data)

    def update_zone(self, name: str, zone_data: dict) -> dict:
        """Update zone."""
        return self._post("zone", zone_data, params={"name": name})

    def delete_zone(self, name: str) -> dict:
        """Delete zone."""
        return self._delete("zone", params={"name": name})

    # Endpoints

    def list_endpoints(self) -> list:
        """List all endpoints."""
        result = self._get("endpoints")
        return result.get("objects", [])

    def get_endpoint(self, name: str) -> dict:
        """Get single endpoint."""
        return self._get("endpoint", params={"name": name})

    def create_endpoint(self, endpoint_data: dict) -> dict:
        """Create endpoint."""
        return self._post("endpoint", endpoint_data)

    def update_endpoint(self, name: str, endpoint_data: dict) -> dict:
        """Update endpoint."""
        return self._post("endpoint", endpoint_data, params={"name": name})

    def delete_endpoint(self, name: str) -> dict:
        """Delete endpoint."""
        return self._delete("endpoint", params={"name": name})

    # Timeperiods

    def list_timeperiods(self) -> list:
        """List all timeperiods."""
        result = self._get("timeperiods")
        return result.get("objects", [])

    def get_timeperiod(self, name: str) -> dict:
        """Get single timeperiod."""
        return self._get("timeperiod", params={"name": name})

    def create_timeperiod(self, period_data: dict) -> dict:
        """Create timeperiod."""
        return self._post("timeperiod", period_data)

    def update_timeperiod(self, name: str, period_data: dict) -> dict:
        """Update timeperiod."""
        return self._post("timeperiod", period_data, params={"name": name})

    def delete_timeperiod(self, name: str) -> dict:
        """Delete timeperiod."""
        return self._delete("timeperiod", params={"name": name})

    # Users

    def list_users(self) -> list:
        """List all users."""
        result = self._get("users")
        return result.get("objects", [])

    def get_user(self, name: str) -> dict:
        """Get single user."""
        return self._get("user", params={"name": name})

    def create_user(self, user_data: dict) -> dict:
        """Create user."""
        return self._post("user", user_data)

    def update_user(self, name: str, user_data: dict) -> dict:
        """Update user."""
        return self._post("user", user_data, params={"name": name})

    def delete_user(self, name: str) -> dict:
        """Delete user."""
        return self._delete("user", params={"name": name})

    # Usergroups

    def list_usergroups(self) -> list:
        """List all usergroups."""
        result = self._get("usergroups")
        return result.get("objects", [])

    def get_usergroup(self, name: str) -> dict:
        """Get single usergroup."""
        return self._get("usergroup", params={"name": name})

    def create_usergroup(self, group_data: dict) -> dict:
        """Create usergroup."""
        return self._post("usergroup", group_data)

    def update_usergroup(self, name: str, group_data: dict) -> dict:
        """Update usergroup."""
        return self._post("usergroup", group_data, params={"name": name})

    def delete_usergroup(self, name: str) -> dict:
        """Delete usergroup."""
        return self._delete("usergroup", params={"name": name})

    # Notifications

    def list_notifications(self) -> list:
        """List all notifications."""
        result = self._get("notifications")
        return result.get("objects", [])

    def get_notification(self, name: str) -> dict:
        """Get single notification."""
        return self._get("notification", params={"name": name})

    def create_notification(self, notification_data: dict) -> dict:
        """Create notification."""
        return self._post("notification", notification_data)

    def update_notification(self, name: str, notification_data: dict) -> dict:
        """Update notification."""
        return self._post("notification", notification_data, params={"name": name})

    def delete_notification(self, name: str) -> dict:
        """Delete notification."""
        return self._delete("notification", params={"name": name})

    # Scheduled Downtimes

    def list_downtimes(self) -> list:
        """List all scheduled downtimes."""
        result = self._get("scheduleddowntimes")
        return result.get("objects", [])

    def get_downtime(self, name: str) -> dict:
        """Get single scheduled downtime."""
        return self._get("scheduleddowntime", params={"name": name})

    def create_downtime(self, downtime_data: dict) -> dict:
        """Create scheduled downtime."""
        return self._post("scheduleddowntime", downtime_data)

    def update_downtime(self, name: str, downtime_data: dict) -> dict:
        """Update scheduled downtime."""
        return self._post("scheduleddowntime", downtime_data, params={"name": name})

    def delete_downtime(self, name: str) -> dict:
        """Delete scheduled downtime."""
        return self._delete("scheduleddowntime", params={"name": name})

    # Deployment

    def deploy(self) -> dict:
        """Deploy pending changes."""
        return self._post("config/deploy", {})

    def get_deployment_status(self, configs: Optional[str] = None,
                              activities: Optional[str] = None) -> dict:
        """Get deployment status."""
        params = {}
        if configs:
            params["configs"] = configs
        if activities:
            params["activities"] = activities
        return self._get("config/deployment-status", params=params)

    # Activity Log

    def get_activity_log(self, limit: int = 50) -> list:
        """Get activity log."""
        result = self._get("activitylog", params={"limit": limit})
        return result.get("entries", [])

    # Data Lists

    def list_datalists(self) -> list:
        """List all data lists."""
        result = self._get("datalists")
        return result.get("objects", [])

    def get_datalist(self, name: str) -> dict:
        """Get single data list."""
        return self._get("datalist", params={"name": name})

    def create_datalist(self, datalist_data: dict) -> dict:
        """Create data list."""
        return self._post("datalist", datalist_data)

    def update_datalist(self, name: str, datalist_data: dict) -> dict:
        """Update data list."""
        return self._post("datalist", datalist_data, params={"name": name})

    def delete_datalist(self, name: str) -> dict:
        """Delete data list."""
        return self._delete("datalist", params={"name": name})

    # Datafields

    def list_datafields(self) -> list:
        """List all data fields."""
        result = self._get("datafields")
        return result.get("objects", [])

    def get_datafield(self, name: str) -> dict:
        """Get single data field."""
        return self._get("datafield", params={"varname": name})

    def create_datafield(self, datafield_data: dict) -> dict:
        """Create data field."""
        return self._post("datafield", datafield_data)

    def update_datafield(self, name: str, datafield_data: dict) -> dict:
        """Update data field."""
        return self._post("datafield", datafield_data, params={"varname": name})

    def delete_datafield(self, name: str) -> dict:
        """Delete data field."""
        return self._delete("datafield", params={"varname": name})

    # Import Sources

    def list_import_sources(self) -> list:
        """List all import sources."""
        result = self._get("importsources")
        return result.get("objects", [])

    def get_import_source(self, name: str) -> dict:
        """Get single import source."""
        return self._get("importsource", params={"name": name})

    def create_import_source(self, source_data: dict) -> dict:
        """Create import source."""
        return self._post("importsource", source_data)

    def update_import_source(self, name: str, source_data: dict) -> dict:
        """Update import source."""
        return self._post("importsource", source_data, params={"name": name})

    def delete_import_source(self, name: str) -> dict:
        """Delete import source."""
        return self._delete("importsource", params={"name": name})

    # Sync Rules

    def list_sync_rules(self) -> list:
        """List all sync rules."""
        result = self._get("syncrules")
        return result.get("objects", [])

    def get_sync_rule(self, name: str) -> dict:
        """Get single sync rule."""
        return self._get("syncrule", params={"name": name})

    def create_sync_rule(self, rule_data: dict) -> dict:
        """Create sync rule."""
        return self._post("syncrule", rule_data)

    def update_sync_rule(self, name: str, rule_data: dict) -> dict:
        """Update sync rule."""
        return self._post("syncrule", rule_data, params={"name": name})

    def delete_sync_rule(self, name: str) -> dict:
        """Delete sync rule."""
        return self._delete("syncrule", params={"name": name})

    # Jobs

    def list_jobs(self) -> list:
        """List all jobs."""
        result = self._get("jobs")
        return result.get("objects", [])

    def get_job(self, name: str) -> dict:
        """Get single job."""
        return self._get("job", params={"name": name})

    def create_job(self, job_data: dict) -> dict:
        """Create job."""
        return self._post("job", job_data)

    def update_job(self, name: str, job_data: dict) -> dict:
        """Update job."""
        return self._post("job", job_data, params={"name": name})

    def delete_job(self, name: str) -> dict:
        """Delete job."""
        return self._delete("job", params={"name": name})

    def run_job(self, name: str) -> dict:
        """Run a job."""
        return self._post("job", {}, params={"name": name, "run": "1"})

    # Branches

    def list_branches(self) -> list:
        """List all branches."""
        result = self._get("branches")
        return result.get("objects", [])

    def get_branch(self, name: str) -> dict:
        """Get single branch."""
        return self._get("branch", params={"name": name})

    def create_branch(self, branch_data: dict) -> dict:
        """Create branch."""
        return self._post("branch", branch_data)

    def update_branch(self, name: str, branch_data: dict) -> dict:
        """Update branch."""
        return self._post("branch", branch_data, params={"name": name})

    def delete_branch(self, name: str) -> dict:
        """Delete branch."""
        return self._delete("branch", params={"name": name})

    def merge_branch(self, name: str) -> dict:
        """Merge branch."""
        return self._post("branch", {}, params={"name": name, "merge": "1"})
