# Icinga MCP Servers

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.0+-orange.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Two [Model Context Protocol](https://modelcontextprotocol.io/) servers that enable AI assistants to interact with [Icinga2](https://icinga.com/products/icinga-2/) monitoring and [Icinga Director](https://github.com/Icinga/icingaweb2-module-director) configuration management.

## What This Project Does

**Icinga2 MCP** lets AI assistants query your monitoring infrastructure in real-time: check host and service status, schedule downtimes, acknowledge alerts, and submit passive check results.

**Director MCP** gives AI assistants full CRUD access to Icinga Director configuration: create hosts and services, manage templates, deploy configurations, and handle the complete Icinga object lifecycle.

Together they provide **122 tools** for complete Icinga infrastructure management through any MCP-compatible AI client (LibreChat, Cursor, Claude Desktop, etc.).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AI Client (MCP)                        │
│              (LibreChat, Cursor, Claude Desktop)             │
└──────────────────────┬──────────────────────────────────────┘
                       │ streamable-http
          ┌────────────┴────────────┐
          │                         │
   ┌──────▼──────┐          ┌───────▼──────┐
   │ Icinga2 MCP │          │ Director MCP │
   │  (19 tools) │          │ (103 tools)  │
   │  port 8092  │          │  port 8093   │
   └──────┬──────┘          └───────┬──────┘
          │                         │
          │ Icinga2 REST API        │ Director REST API
          │ (port 5665)             │ (Icinga Web 2)
          │                         │
   ┌──────▼─────────────────────────▼──────┐
   │          Icinga2 + Director           │
   │        (your-icinga-server)           │
   └───────────────────────────────────────┘
```

## Prerequisites

- Python 3.10+
- Icinga2 with API enabled (`api` feature)
- Icinga Director module installed
- Icinga Web 2 user with `director/api` permission

## Installation

```bash
# Clone the repository
git clone https://github.com/DanielVd/icinga-mcp.git
cd icinga-mcp

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package and dependencies
pip install -e .

# Create configuration
cp .env.example .env
```

## Configuration

Edit `.env` with your Icinga credentials:

```ini
# Icinga2 MCP
ICINGA_HOST=<your-icinga-host>
ICINGA_USER=<api-user>
ICINGA_PASSWORD=<your-api-password>
ICINGA_VERIFY_SSL=false

# Director MCP
DIRECTOR_BASE_URL=https://<your-icinga-host>/director
DIRECTOR_USER=<your-icingaweb2-user>
DIRECTOR_PASSWORD=<your-icingaweb2-password>
DIRECTOR_VERIFY_SSL=false
```

All settings can also be passed as environment variables.

## Running

```bash
source .venv/bin/activate

# Start Icinga2 MCP server (port 8092)
python -m src.icinga2_mcp.server

# Start Director MCP server (port 8093)
python -m src.director_mcp.server
```

Both servers use **streamable-http** transport and bind to `0.0.0.0` by default.

## Integration

### LibreChat

Add to your `librechat.yaml`:

```yaml
mcpSettings:
  allowedDomains:
    - "<your-mcp-host>"

mcpServers:
  icinga2-mcp:
    type: streamable-http
    url: http://<host>:8092/mcp
  director-mcp:
    type: streamable-http
    url: http://<host>:8093/mcp
```

### Cursor / VS Code

Add to `.cursor/mcp.json` or VS Code MCP settings:

```json
{
  "mcpServers": {
    "icinga2": {
      "url": "http://localhost:8092/mcp"
    },
    "director": {
      "url": "http://localhost:8093/mcp"
    }
  }
}
```

## Icinga2 MCP Tools (19)

Runtime monitoring operations via Icinga2 REST API.

### Status and Discovery
| Tool | Description |
|------|-------------|
| `get_api_status` | API version and authentication info |
| `get_icinga_application_status` | System uptime, check rates, problem counts |
| `list_check_commands` | Available check commands |
| `list_timeperiods` | Configured timeperiods |
| `list_users` | Notification users |

### Hosts and Services
| Tool | Description |
|------|-------------|
| `list_hosts` | All hosts (supports Icinga2 filter) |
| `get_host` | Full host details with state and last check |
| `list_services` | All services (filter by host or expression) |
| `get_service` | Full service details with output and perfdata |

### Groups
| Tool | Description |
|------|-------------|
| `list_hostgroups` | Hostgroup membership |
| `list_servicegroups` | Servicegroup membership |

### Incident Management
| Tool | Description |
|------|-------------|
| `list_downtimes` | Active downtimes |
| `add_downtime` | Schedule downtime (host or service) |
| `remove_downtime` | Cancel downtime |
| `add_acknowledgement` | Acknowledge a problem |
| `remove_acknowledgement` | Remove acknowledgement |

### Operations
| Tool | Description |
|------|-------------|
| `reschedule_check` | Force immediate check |
| `process_check_result` | Submit passive check result |
| `list_notifications` | Notification configuration |

## Director MCP Tools (103)

Full configuration lifecycle via Director REST API.

### Hosts (6 tools)
`list_hosts` · `get_host` · `create_host` · `update_host` · `delete_host` · `get_host_ticket`

### Services (6 tools)
`list_services` · `get_service` · `create_service` · `update_service` · `delete_service` · `list_service_apply_rules`

### Groups (12 tools)
`list_hostgroups` · `get_hostgroup` · `create_hostgroup` · `update_hostgroup` · `delete_hostgroup`
`list_servicegroups` · `get_servicegroup` · `create_servicegroup` · `update_servicegroup` · `delete_servicegroup`

### Commands (5 tools)
`list_commands` · `get_command` · `create_command` · `update_command` · `delete_command`

### Infrastructure (12 tools)
`list_zones` · `get_zone` · `create_zone` · `update_zone` · `delete_zone`
`list_endpoints` · `get_endpoint` · `create_endpoint` · `update_endpoint` · `delete_endpoint`

### Templates and Sets (7 tools)
`list_templates` · `list_service_sets` · `get_service_set` · `create_service_set` · `update_service_set` · `delete_service_set`

### Timeperiods (5 tools)
`list_timeperiods` · `get_timeperiod` · `create_timeperiod` · `update_timeperiod` · `delete_timeperiod`

### Users and Notifications (15 tools)
`list_users` · `get_user` · `create_user` · `update_user` · `delete_user`
`list_usergroups` · `get_usergroup` · `create_usergroup` · `update_usergroup` · `delete_usergroup`
`list_notifications` · `get_notification` · `create_notification` · `update_notification` · `delete_notification`

### Scheduled Downtimes (5 tools)
`list_downtimes` · `get_downtime` · `create_downtime` · `update_downtime` · `delete_downtime`

### Deployment (3 tools)
`deploy_pending_changes` · `get_deployment_status` · `get_activity_log`

### Data Management (9 tools)
`list_datalists` · `get_datalist` · `create_datalist` · `update_datalist` · `delete_datalist`
`list_datafields` · `get_datafield` · `create_datafield` · `update_datafield` · `delete_datafield`

### Import and Sync (9 tools)
`list_import_sources` · `get_import_source` · `create_import_source` · `update_import_source` · `delete_import_source`
`list_sync_rules` · `get_sync_rule` · `create_sync_rule` · `update_sync_rule` · `delete_sync_rule`

### Jobs (6 tools)
`list_jobs` · `get_job` · `create_job` · `update_job` · `delete_job` · `run_job`

### Branches (6 tools)
`list_branches` · `get_branch` · `create_branch` · `update_branch` · `delete_branch` · `merge_branch`

## Example Usage

### Check all hosts and their status

Ask your AI assistant: *"Show me all hosts that are currently DOWN"*

The assistant calls `list_hosts`, filters results, and returns:
```json
{
  "name": "server01.example.com",
  "state": "DOWN",
  "last_check": "2026-04-22T23:00:00Z",
  "output": "CRITICAL - Host unreachable"
}
```

### Create a new monitored host

Ask: *"Add a new host called web01.example.com at 192.168.1.50 with ping check"*

The assistant calls:
1. `create_host` with `object_name`, `address`, `imports`
2. `deploy_pending_changes` to push config to Icinga2

### Schedule maintenance window

Ask: *"Schedule downtime for nas.example.com tonight from 2am to 4am"*

The assistant calls `add_downtime` with host, author, comment, and duration.

### Deploy pending configuration changes

Ask: *"Are there any pending changes in Director? Deploy them if so."*

The assistant calls `get_deployment_status`, then `deploy_pending_changes`.

## API References

- [Icinga2 REST API](https://icinga.com/docs/icinga2/latest/doc/12-icinga2-api/)
- [Icinga Director REST API](https://github.com/Icinga/icingaweb2-module-director/blob/master/doc/70-REST-API.md)
- [Model Context Protocol](https://modelcontextprotocol.io/introduction)

## Project Structure

```
icinga-mcp/
├── src/
│   ├── icinga2_mcp/
│   │   ├── __init__.py
│   │   ├── client.py          # Icinga2 REST API client
│   │   └── server.py          # MCP server (19 tools)
│   └── director_mcp/
│       ├── __init__.py
│       ├── client.py          # Director REST API client
│       └── server.py          # MCP server (103 tools)
├── .env.example               # Environment template
├── .gitignore
├── pyproject.toml
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT. See [LICENSE](LICENSE) for details.

## Maintainer

Daniel Vedovato: [GitHub](https://github.com/DanielVd) · [Gitea](https://code.danielvedovato.it/forgeadmin)
