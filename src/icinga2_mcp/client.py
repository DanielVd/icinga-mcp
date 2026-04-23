"""Icinga2 API client."""

import requests
from urllib3.exceptions import InsecureRequestWarning
from typing import Optional

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Icinga2Client:
    """Client for Icinga2 REST API."""

    def __init__(self, host: str, user: str, password: str, verify_ssl: bool = False):
        self.base_url = f"https://{host}:5665/v1"
        self.auth = (user, password)
        self.verify = verify_ssl
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.verify = self.verify
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        resp = self.session.get(f"{self.base_url}/{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict) -> dict:
        resp = self.session.post(f"{self.base_url}/{path}", json=data)
        resp.raise_for_status()
        return resp.json()

    def get_api_status(self) -> dict:
        """Get Icinga2 API status and version info."""
        return self._get("")

    def get_status(self, type_name: str = "IcingaApplication") -> dict:
        """Get Icinga2 status information."""
        return self._get(f"status/{type_name}")

    def list_hosts(self, host_filter: Optional[str] = None) -> list:
        """List all hosts with optional filter."""
        params = {}
        if host_filter:
            params["filter"] = host_filter
        result = self._get("objects/hosts", params)
        return result.get("results", [])

    def get_host(self, name: str) -> dict:
        """Get single host by name."""
        result = self._get(f"objects/hosts/{name}")
        return result.get("results", [{}])[0]

    def list_services(self, host: Optional[str] = None, service_filter: Optional[str] = None) -> list:
        """List all services, optionally filtered by host."""
        params = {}
        if service_filter:
            params["filter"] = service_filter
        if host:
            result = self._get(f"objects/services", {"host": host, **params})
        else:
            result = self._get("objects/services", params)
        return result.get("results", [])

    def get_service(self, host: str, service: str) -> dict:
        """Get single service by host and name."""
        result = self._get(f"objects/services/{host}/{service}")
        return result.get("results", [{}])[0]

    def list_hostgroups(self) -> list:
        """List all hostgroups."""
        result = self._get("objects/hostgroups")
        return result.get("results", [])

    def list_servicegroups(self) -> list:
        """List all servicegroups."""
        result = self._get("objects/servicegroups")
        return result.get("results", [])

    def list_downtimes(self, host: Optional[str] = None) -> list:
        """List all downtimes, optionally filtered by host."""
        params = {}
        if host:
            params["filter"] = f'host.name=="{host}"'
        result = self._get("objects/downtimes", params)
        return result.get("results", [])

    def add_downtime(self, host: str, author: str, comment: str,
                     duration: int = 3600, service: Optional[str] = None) -> dict:
        """Add downtime for host or service."""
        data = {
            "type": "Downtime",
            "filter": f'host.name=="{host}"' + (f' && service.name=="{service}"' if service else ""),
            "author": author,
            "comment": comment,
            "duration": duration,
            "all_services": service is None,
        }
        return self._post("actions/schedule-downtime", data)

    def remove_downtime(self, downtime_name: str) -> dict:
        """Remove downtime by name."""
        data = {
            "type": "Downtime",
            "filter": f'name=="{downtime_name}"',
            "author": "mcp-server",
            "comment": "Removed via MCP",
        }
        return self._post("actions/remove-downtime", data)

    def add_acknowledgement(self, host: str, author: str, comment: str,
                            service: Optional[str] = None, sticky: bool = True,
                            notify: bool = True, persistent: bool = False) -> dict:
        """Add acknowledgement for host or service."""
        data = {
            "type": "Service" if service else "Host",
            "filter": f'host.name=="{host}"' + (f' && name=="{service}"' if service else ""),
            "author": author,
            "comment": comment,
            "sticky": sticky,
            "notify": notify,
            "persistent": persistent,
        }
        return self._post("actions/acknowledge-problem", data)

    def remove_acknowledgement(self, host: str, service: Optional[str] = None) -> dict:
        """Remove acknowledgement for host or service."""
        data = {
            "type": "Service" if service else "Host",
            "filter": f'host.name=="{host}"' + (f' && name=="{service}"' if service else ""),
            "author": "mcp-server",
            "comment": "Removed via MCP",
        }
        return self._post("actions/remove-acknowledgement", data)

    def reschedule_check(self, host: str, service: Optional[str] = None,
                         force: bool = True) -> dict:
        """Reschedule check for host or service."""
        obj_type = "Service" if service else "Host"
        filter_str = f'host.name=="{host}"'
        if service:
            filter_str += f' && name=="{service}"'
        data = {
            "type": obj_type,
            "filter": filter_str,
            "force": force,
        }
        return self._post("actions/reschedule-check", data)

    def list_objects(self, obj_type: str) -> list:
        """List all objects of given type."""
        result = self._get(f"objects/{obj_type}")
        return result.get("results", [])

    def get_check_commands(self) -> list:
        """List all check commands."""
        result = self._get("objects/checkcommands")
        return result.get("results", [])

    def list_timeperiods(self) -> list:
        """List all timeperiods."""
        result = self._get("objects/timeperiods")
        return result.get("results", [])

    def list_users(self) -> list:
        """List all users."""
        result = self._get("objects/users")
        return result.get("results", [])

    def list_notifications(self, host: Optional[str] = None) -> list:
        """List all notifications."""
        params = {}
        if host:
            params["filter"] = f'host.name=="{host}"'
        result = self._get("objects/notifications", params)
        return result.get("results", [])

    def process_check_result(self, host: str, service: Optional[str],
                             exit_status: int, output: str,
                             check_source: str = "mcp-server") -> dict:
        """Process passive check result."""
        data = {
            "exit_status": exit_status,
            "plugin_output": output,
            "check_source": check_source,
        }
        if service:
            endpoint = f"process-check-result/{host}/{service}"
        else:
            endpoint = f"process-check-result/{host}"
        return self._post(f"actions/{endpoint}", data)
