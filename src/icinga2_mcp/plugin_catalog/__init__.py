# SPDX-License-Identifier: Unlicense

"""Linuxfabrik monitoring-plugins catalog: schema, parser, loader.

The catalog is a static, queryable description of every plugin in the
`monitoring-plugins` repository: its argparse arguments, perfdata metrics,
state rules, Icinga Director command mapping and general metadata.

The catalog is built from a local check-plugins directory.
"""

from icinga2_mcp.plugin_catalog.loader import load_from_path
from icinga2_mcp.plugin_catalog.schema import (
    Catalog,
    PluginArg,
    PluginCatalogEntry,
    PluginPerfdata,
    PluginStateRule,
)

__all__ = [
    'Catalog',
    'PluginArg',
    'PluginCatalogEntry',
    'PluginPerfdata',
    'PluginStateRule',
    'load_from_path',
]
