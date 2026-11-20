"""MCP tools for a local Linuxfabrik monitoring-plugins checkout."""

import ast
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .plugin_catalog import PluginCatalogEntry, load_from_path


def register_catalog_tools(server: FastMCP, catalog_path: Path) -> None:
    check_plugins = catalog_path.resolve()
    catalog = load_from_path(check_plugins)

    def find_plugin(name: str) -> PluginCatalogEntry:
        entry = catalog.plugins.get(name)
        if entry is None:
            raise ValueError(f"Unknown plugin {name!r}. Use list_plugins to find available names.")
        return entry

    @server.tool()
    def catalog_info() -> dict[str, Any]:
        """Report the Linuxfabrik catalog source, build timestamp and plugin count."""
        return {
            "source": catalog.source,
            "built_at": catalog.built_at,
            "monitoring_plugins_ref": catalog.monitoring_plugins_ref,
            "plugin_count": len(catalog.plugins),
        }

    @server.tool()
    def list_plugins(runs_on: str | None = None, name_contains: str | None = None) -> list[dict[str, Any]]:
        """List Linuxfabrik plugins, optionally filtered by platform and a name substring."""
        platform = runs_on.casefold() if runs_on else ""
        needle = name_contains.casefold() if name_contains else ""
        return [
            {
                "name": entry.name,
                "version": entry.version,
                "runs_on": entry.runs_on,
                "description": (entry.description or "")[:200] or None,
            }
            for _, entry in sorted(catalog.plugins.items())
            if needle in entry.name.casefold()
            and (not platform or platform == (entry.runs_on or "").casefold())
        ]

    @server.tool()
    def explain_plugin(name: str) -> dict[str, Any]:
        """Explain a Linuxfabrik plugin's arguments, thresholds, states, perfdata and Director mapping."""
        return find_plugin(name).model_dump(mode="json")

    @server.tool()
    def find_plugin_for_check_command(check_command: str) -> dict[str, Any] | None:
        """Look up the Linuxfabrik plugin that declares a given Director check command."""
        for entry in catalog.plugins.values():
            if check_command in entry.director_check_commands:
                return entry.model_dump(mode="json")
        return None

    @server.tool()
    def read_plugin_source(name: str, function: str | None = None) -> dict[str, Any]:
        """Read an indexed Linuxfabrik plugin's source or one of its top-level functions."""
        entry = find_plugin(name)
        path = (check_plugins.parent / entry.source_path).resolve()
        if not path.is_relative_to(check_plugins) or not path.is_file():
            raise ValueError(f"Source for plugin {name!r} is unavailable in the configured checkout")
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ValueError(f"Could not read source for plugin {name!r}") from exc
        result = {"name": name, "source_path": entry.source_path}
        if function is not None:
            definitions = {
                node.name: node
                for node in ast.parse(source).body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            if function not in definitions:
                names = ", ".join(sorted(definitions)) or "(none)"
                raise ValueError(f"Unknown function {function!r}. Available functions: {names}")
            source = ast.get_source_segment(source, definitions[function]) or ""
            result["function"] = function
        result.update(source=source, line_count=len(source.splitlines()))
        return result
