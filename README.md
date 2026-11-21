# icinga-mcp

[![Latest Release](https://img.shields.io/github/v/release/DanielVd/icinga-mcp)](https://github.com/DanielVd/icinga-mcp/releases/latest)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

MCP servers for Icinga2 and Icinga Director automation.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Integration](#integration)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)
- [Attribution](#attribution)

## Features

- Icinga2 monitoring queries, active problems, and named Core instances
- Optional Linuxfabrik monitoring-plugins catalog
- Director configuration automation
- Streamable HTTP MCP transport

## Requirements

- Python 3.10+
- Icinga2 API enabled
- Icinga Director installed

## Installation

```bash
git clone https://github.com/DanielVd/icinga-mcp.git
cd icinga-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

## Quick Start

```bash
icinga2-mcp
director-mcp
```

## Configuration

Set required credentials in `.env` (`ICINGA_*`, `DIRECTOR_*`).

### Named Core instances

The existing `ICINGA_HOST`, `ICINGA_USER` and `ICINGA_PASSWORD` settings configure a single instance named `default`. That API account is used for both reads and writes. For named instances and separate permissions, use settings such as:

```ini
ICINGA_INSTANCES__PROD__URL=https://prod.example:5665/v1
ICINGA_INSTANCES__PROD__USER=monitoring-reader
ICINGA_INSTANCES__PROD__PASSWORD=<read-password>
ICINGA_INSTANCES__PROD__CA_BUNDLE=/path/to/icinga-ca.pem

ICINGA_INSTANCES__STAGING__URL=https://staging.example:5665/v1
ICINGA_INSTANCES__STAGING__USER=monitoring-reader
ICINGA_INSTANCES__STAGING__PASSWORD=<read-password>
ICINGA_INSTANCES__STAGING__WRITE_USER=monitoring-operator
ICINGA_INSTANCES__STAGING__WRITE_PASSWORD=<write-password>
```

Named instances take precedence over the single-instance settings. Include the API path `/v1` in each URL. Certificate verification defaults to on for named instances. Set `CA_BUNDLE` when the server certificate uses a private CA. Use restricted Icinga API accounts for each role.

Call `health_check` to discover instance names. For nested environment variables, names such as `PROD` become `prod`. Pass `instance` to Core tools when more than one is configured. A named instance is read-only unless both write credentials are set. The server exposes write tools only when at least one instance can use them. For named instances, acknowledgements and downtimes use the configured write account as their author.

### Linuxfabrik plugin catalog

Clone the [Linuxfabrik monitoring-plugins repository](https://github.com/Linuxfabrik/monitoring-plugins), then add to the server environment or `.env`:

```ini
ICINGA_PLUGIN_CATALOG_PATH=/path/to/monitoring-plugins/check-plugins
```

The server indexes plugin metadata and source at startup. Restart it to refresh the catalog after updating the checkout. `list_plugins` filters by platform or name, `explain_plugin` shows arguments, states and metrics, and `find_plugin_for_check_command` matches Director check commands. `read_plugin_source` returns the source or one top-level function without running the plugin. `catalog_info` reports the catalog size. These tools also work without any Core credentials.

### Incident history

Set `ICINGA_HISTORY__URL` to the Icinga Web 2 root URL and configure an account with access to the Icinga DB Web history view.

```ini
ICINGA_HISTORY__URL=https://monitoring.example/icingaweb2
ICINGA_HISTORY__USER=<icinga-web-user>
ICINGA_HISTORY__PASSWORD=<icinga-web-password>
# ICINGA_HISTORY__CA_BUNDLE=/path/to/ca.pem
```

`get_history` takes an exact host, an optional service or event type, and optional ISO 8601 start and end times with timezones. It defaults to the last 24 hours and accepts a maximum window of 31 days. Set a shorter window if the result reports `has_more`. The history backend is independent of the Core instance settings.

### Filter active problems

`get_problems` can filter by `scope`, `severity`, exact `host_group`, `min_duration_minutes`, `acknowledged` and `in_downtime`. A severity filter selects services by default. Set `scope` to `both` to also include matching down hosts. Duration is time in the current state. The two counts include all matches after filtering, even if the response lists fewer entries.

## Integration

Use the `/mcp` HTTP endpoints on ports `8092` for Core and `8093` for Director. Set `ICINGA_TRANSPORT=stdio` to run Core as an MCP client subprocess.

## Troubleshooting

- auth errors: check API user/password
- timeout errors: tune request timeout settings

## Security Notes

- never commit `.env`
- use least-privilege Icinga accounts

## Attribution

The Linuxfabrik catalog parser, loader and schema were adapted from [Linuxfabrik MCP Server for Icinga at `fd681ab`](https://github.com/linuxfabrik/mcp-server-icinga/tree/fd681abda91bec51c0a42fd4cf3122f3ad94df8d/src/mcp_server_icinga/plugin_catalog). See the [Unlicense](src/icinga2_mcp/plugin_catalog/LICENSE) and [copyright notice](src/icinga2_mcp/plugin_catalog/COPYRIGHT) for those files.
