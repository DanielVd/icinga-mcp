"""Icinga2 API client."""

import os
import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException

DEFAULT_TIMEOUT = float(os.getenv("ICINGA_REQUEST_TIMEOUT", "30"))
DEFAULT_POOL_CONNECTIONS = int(os.getenv("ICINGA_POOL_CONNECTIONS", "20"))
DEFAULT_POOL_MAXSIZE = int(os.getenv("ICINGA_POOL_MAXSIZE", "50"))


class Icinga2Client:
    """Client for Icinga2 REST API."""

    def __init__(self, host: str, user: str, password: str, verify_ssl: bool | str = False, *,
                 base_url: str | None = None, action_author: str | None = None):
        self.base_url = base_url.rstrip("/") if base_url else f"https://{host}:5665/v1"
        self.auth = (user, password)
        self.action_author = action_author
        self.verify = verify_ssl
        self.timeout = DEFAULT_TIMEOUT
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.verify = self.verify
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
        return self._request("GET", path, params=params)

    def _post(self, path: str, data: dict) -> dict:
        return self._request("POST", path, json=data)

    def _query_objects(self, path: str, params: dict) -> dict:
        if params.keys() & {"filter", "host", "service"}:
            return self._request("POST", path, json=params, headers={"X-HTTP-Method-Override": "GET"})
        return self._get(path, params)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            resp = self.session.request(method, f"{self.base_url}/{path}", timeout=self.timeout, **kwargs)
            resp.raise_for_status()
        except RequestException as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", "request-error")
            response_text = getattr(getattr(exc, "response", None), "text", "") or str(exc)
            detail = response_text.strip().replace("\n", " ")[:500]
            raise RuntimeError(f"Icinga2 API request failed for {method} {path}: {status_code} {detail}") from exc

        try:
            return resp.json()
        except ValueError as exc:
            raise RuntimeError(f"Icinga2 API returned invalid JSON for {method} {path}") from exc

    def get_api_status(self) -> dict:
        """Get Icinga2 API status and version info."""
        return self._get("")

    def get_status(self, type_name: str = "IcingaApplication") -> dict:
        """Get Icinga2 status information."""
        return self._get(f"status/{type_name}")

    def list_hosts(self, host_filter: Optional[str] = None, attrs: Optional[list[str]] = None,
                   *, filter_vars: dict | None = None) -> list:
        """List all hosts with optional filter."""
        params = {}
        if host_filter:
            params["filter"] = host_filter
            if filter_vars:
                params["filter_vars"] = filter_vars
        if attrs:
            params["attrs"] = attrs
        result = self._query_objects("objects/hosts", params)
        return result.get("results", [])

    def get_host(self, name: str) -> dict:
        """Get single host by name."""
        result = self._query_objects("objects/hosts", {"host": name})
        return self._single_result(result, f"Host {name!r}")

    def list_services(
        self,
        host: Optional[str] = None,
        service_filter: Optional[str] = None,
        attrs: Optional[list[str]] = None,
        *,
        filter_vars: dict | None = None,
    ) -> list:
        """List all services, optionally filtered by host."""
        params = {}
        if service_filter:
            params["filter"] = service_filter
            if filter_vars:
                params["filter_vars"] = filter_vars
        if attrs:
            params["attrs"] = attrs
        if host:
            host_constraint = "service.host_name == target_host"
            params["filter"] = f"({service_filter}) && {host_constraint}" if service_filter else host_constraint
            params["filter_vars"] = {**(filter_vars or {}), "target_host": host}
        result = self._query_objects("objects/services", params)
        return result.get("results", [])

    def get_service(self, host: str, service: str) -> dict:
        """Get single service by host and name."""
        result = self._query_objects("objects/services", {"service": f"{host}!{service}"})
        return self._single_result(result, f"Service {service!r} on {host!r}")

    @staticmethod
    def _single_result(result: dict, description: str) -> dict:
        rows = result.get("results", [])
        if not rows:
            raise ValueError(f"{description} was not found")
        return rows[0]

    @staticmethod
    def _action_target(host: str, service: str | None) -> dict:
        if not host:
            raise ValueError("Host name cannot be empty")
        if service:
            return {"service": f"{host}!{service}"}
        return {"host": host}

    def list_hostgroups(self, attrs: Optional[list[str]] = None) -> list:
        """List all hostgroups."""
        params = {"attrs": attrs} if attrs else None
        result = self._get("objects/hostgroups", params)
        return result.get("results", [])

    def list_servicegroups(self, attrs: Optional[list[str]] = None) -> list:
        """List all servicegroups."""
        params = {"attrs": attrs} if attrs else None
        result = self._get("objects/servicegroups", params)
        return result.get("results", [])

    def list_downtimes(self, host: Optional[str] = None, attrs: Optional[list[str]] = None) -> list:
        """List all downtimes, optionally filtered by host."""
        params = {}
        if host:
            params["filter"] = "downtime.host_name == target_host"
            params["filter_vars"] = {"target_host": host}
        if attrs:
            params["attrs"] = attrs
        result = self._query_objects("objects/downtimes", params)
        return result.get("results", [])

    def add_downtime(self, host: str, author: str, comment: str,
                     duration: int = 3600, service: Optional[str] = None, *,
                     start_time: int | None = None, all_services: bool | None = None) -> dict:
        """Add downtime for host or service."""
        if duration <= 0:
            raise ValueError("Downtime duration must be positive")
        if service and all_services:
            raise ValueError("all_services is only valid for a host downtime")
        start = int(time.time()) if start_time is None else start_time
        data = {
            **self._action_target(host, service),
            "author": self.action_author or author,
            "comment": comment,
            "start_time": start,
            "end_time": start + duration,
            "fixed": True,
            "all_services": service is None if all_services is None else all_services,
        }
        return self._post("actions/schedule-downtime", data)

    def remove_downtime(self, downtime_name: str, *, host: str | None = None,
                        service: str | None = None) -> dict:
        """Remove one downtime by name or the downtimes on an exact host or service."""
        if bool(downtime_name) == bool(host) or (service and not host):
            raise ValueError("Specify either downtime_name or host (with optional service)")
        target = {"downtime": downtime_name} if downtime_name else self._action_target(host or "", service)
        data = {
            **target,
            "author": self.action_author or "mcp-server",
            "comment": "Removed via MCP",
        }
        return self._post("actions/remove-downtime", data)

    def add_acknowledgement(self, host: str, author: str, comment: str,
                            service: Optional[str] = None, sticky: bool = True,
                            notify: bool = True, persistent: bool = False, *,
                            expiry_seconds: int | None = None) -> dict:
        """Add acknowledgement for host or service."""
        data = {
            **self._action_target(host, service),
            "author": self.action_author or author,
            "comment": comment,
            "sticky": sticky,
            "notify": notify,
            "persistent": persistent,
        }
        if expiry_seconds is not None:
            if expiry_seconds <= 0:
                raise ValueError("Acknowledgement expiry must be positive")
            data["expiry"] = int(time.time()) + expiry_seconds
        return self._post("actions/acknowledge-problem", data)

    def remove_acknowledgement(self, host: str, service: Optional[str] = None) -> dict:
        """Remove acknowledgement for host or service."""
        data = {
            **self._action_target(host, service),
            "author": self.action_author or "mcp-server",
            "comment": "Removed via MCP",
        }
        return self._post("actions/remove-acknowledgement", data)

    def reschedule_check(self, host: str, service: Optional[str] = None,
                         force: bool = True) -> dict:
        """Reschedule check for host or service."""
        data = {
            **self._action_target(host, service),
            "force": force,
        }
        return self._post("actions/reschedule-check", data)

    def list_objects(self, obj_type: str) -> list:
        """List all objects of given type."""
        result = self._get(f"objects/{obj_type}")
        return result.get("results", [])

    def get_check_commands(self, attrs: Optional[list[str]] = None) -> list:
        """List all check commands."""
        params = {"attrs": attrs} if attrs else None
        result = self._get("objects/checkcommands", params)
        return result.get("results", [])

    def list_timeperiods(self, attrs: Optional[list[str]] = None) -> list:
        """List all timeperiods."""
        params = {"attrs": attrs} if attrs else None
        result = self._get("objects/timeperiods", params)
        return result.get("results", [])

    def list_users(self, attrs: Optional[list[str]] = None) -> list:
        """List all users."""
        params = {"attrs": attrs} if attrs else None
        result = self._get("objects/users", params)
        return result.get("results", [])

    def list_notifications(self, host: Optional[str] = None, attrs: Optional[list[str]] = None) -> list:
        """List all notifications."""
        params = {}
        if host:
            params["filter"] = "notification.host_name == target_host"
            params["filter_vars"] = {"target_host": host}
        if attrs:
            params["attrs"] = attrs
        result = self._query_objects("objects/notifications", params)
        return result.get("results", [])

    def process_check_result(self, host: str, service: Optional[str],
                             exit_status: int, output: str,
                             check_source: str = "mcp-server") -> dict:
        """Process passive check result."""
        data = {
            **self._action_target(host, service),
            "exit_status": exit_status,
            "plugin_output": output,
            "check_source": check_source,
        }
        return self._post("actions/process-check-result", data)
