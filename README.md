# Icinga MCP Servers

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Two MCP (Model Context Protocol) servers for integrating Icinga2 monitoring and Icinga Director configuration management with AI assistants.

## Overview

| Server | Purpose | Transport | Default Port |
|--------|---------|-----------|--------------|
| **Icinga2 MCP** | Runtime monitoring via Icinga2 REST API | Streamable HTTP | 8090 |
| **Director MCP** | Configuration management via Director REST API | Streamable HTTP | 8091 |

## Quick Start

```bash
# Clone and setup
git clone https://code.danielvedovato.it/daniel/icinga-mcp.git
cd icinga-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your credentials
```

## Configuration

All settings via environment variables or `.env` file:

### Icinga2 MCP

| Variable | Description | Default |
|----------|-------------|---------|
| `ICINGA_HOST` | Icinga2 API hostname | `vm-icinga.fritz.box` |
| `ICINGA_USER` | API user | `root` |
| `ICINGA_PASSWORD` | API password | *(required)* |
| `ICINGA_VERIFY_SSL` | Verify SSL certificates | `false` |

### Director MCP

| Variable | Description | Default |
|----------|-------------|---------|
| `DIRECTOR_BASE_URL` | Director REST API base URL | `https://monitoring.fritz.box/director` |
| `DIRECTOR_USER` | Icinga Web 2 username | `daniel` |
| `DIRECTOR_PASSWORD` | Icinga Web 2 password | *(required)* |
| `DIRECTOR_VERIFY_SSL` | Verify SSL certificates | `false` |

## Running

```bash
source .venv/bin/activate

# Icinga2 MCP (port 8090)
python -m src.icinga2_mcp.server

# Director MCP (port 8091)
python -m src.director_mcp.server
```

## LibreChat Integration

Add to `librechat.yaml`:

```yaml
mcpSettings:
  allowedDomains:
    - "<your-mcp-host>"

mcpServers:
  icinga2-mcp:
    type: streamable-http
    url: http://<host>:8090/mcp
  director-mcp:
    type: streamable-http
    url: http://<host>:8091/mcp
```

## Icinga2 MCP Tools (19)

### Status
| Tool | Description |
|------|-------------|
| `get_api_status` | API status and version info |
| `get_icinga_application_status` | Checks, notifications, uptime |

### Hosts
| Tool | Description |
|------|-------------|
| `list_hosts` | List all monitored hosts (optional filter) |
| `get_host` | Detailed host information |

### Services
| Tool | Description |
|------|-------------|
| `list_services` | List all services (filter by host or expression) |
| `get_service` | Detailed service information |

### Groups
| Tool | Description |
|------|-------------|
| `list_hostgroups` | List all hostgroups |
| `list_servicegroups` | List all servicegroups |

### Downtimes
| Tool | Description |
|------|-------------|
| `list_downtimes` | List active downtimes |
| `add_downtime` | Schedule host or service downtime |
| `remove_downtime` | Remove existing downtime |

### Acknowledgements
| Tool | Description |
|------|-------------|
| `add_acknowledgement` | Acknowledge problem on host/service |
| `remove_acknowledgement` | Remove acknowledgement |

### Operations
| Tool | Description |
|------|-------------|
| `reschedule_check` | Force immediate check execution |
| `process_check_result` | Submit passive check result |

### Reference
| Tool | Description |
|------|-------------|
| `list_check_commands` | List available check commands |
| `list_timeperiods` | List configured timeperiods |
| `list_users` | List configured users |
| `list_notifications` | List notification objects |

## Director MCP Tools (103)

### Hosts
| Tool | Description |
|------|-------------|
| `list_hosts` | List all hosts |
| `get_host` | Get host with resolved properties and services |
| `create_host` | Create new host |
| `update_host` | Modify existing host |
| `delete_host` | Remove host |
| `get_host_ticket` | Get agent ticket for host |

### Services
| Tool | Description |
|------|-------------|
| `list_services` | List all services |
| `get_service` | Get service details |
| `create_service` | Create new service |
| `update_service` | Modify existing service |
| `delete_service` | Remove service |
| `list_service_apply_rules` | List service apply rules |

### Groups
| Tool | Description |
|------|-------------|
| `list_hostgroups` / `get_hostgroup` | List/get hostgroups |
| `create_hostgroup` / `update_hostgroup` / `delete_hostgroup` | Manage hostgroups |
| `list_servicegroups` / `get_servicegroup` | List/get servicegroups |
| `create_servicegroup` / `update_servicegroup` / `delete_servicegroup` | Manage servicegroups |

### Commands
| Tool | Description |
|------|-------------|
| `list_commands` / `get_command` | List/get commands |
| `create_command` / `update_command` / `delete_command` | Manage commands |

### Infrastructure
| Tool | Description |
|------|-------------|
| `list_zones` / `get_zone` | List/get zones |
| `create_zone` / `update_zone` / `delete_zone` | Manage zones |
| `list_endpoints` / `get_endpoint` | List/get endpoints |
| `create_endpoint` / `update_endpoint` / `delete_endpoint` | Manage endpoints |

### Templates & Sets
| Tool | Description |
|------|-------------|
| `list_templates` | List host or service templates |
| `list_service_sets` / `get_service_set` | List/get service sets |
| `create_service_set` / `update_service_set` / `delete_service_set` | Manage service sets |

### Timeperiods
| Tool | Description |
|------|-------------|
| `list_timeperiods` / `get_timeperiod` | List/get timeperiods |
| `create_timeperiod` / `update_timeperiod` / `delete_timeperiod` | Manage timeperiods |

### Users & Notifications
| Tool | Description |
|------|-------------|
| `list_users` / `get_user` | List/get users |
| `create_user` / `update_user` / `delete_user` | Manage users |
| `list_usergroups` / `get_usergroup` | List/get usergroups |
| `create_usergroup` / `update_usergroup` / `delete_usergroup` | Manage usergroups |
| `list_notifications` / `get_notification` | List/get notifications |
| `create_notification` / `update_notification` / `delete_notification` | Manage notifications |

### Scheduled Downtimes
| Tool | Description |
|------|-------------|
| `list_downtimes` / `get_downtime` | List/get scheduled downtimes |
| `create_downtime` / `update_downtime` / `delete_downtime` | Manage scheduled downtimes |

### Deployment
| Tool | Description |
|------|-------------|
| `deploy_pending_changes` | Deploy configuration to Icinga2 |
| `get_deployment_status` | Get deployment status (active/failed/undeployed) |
| `get_activity_log` | View recent configuration changes |

### Data Management
| Tool | Description |
|------|-------------|
| `list_datalists` / `get_datalist` | List/get data lists |
| `create_datalist` / `update_datalist` / `delete_datalist` | Manage data lists |
| `list_datafields` / `get_datafield` | List/get data fields |
| `create_datafield` / `update_datafield` / `delete_datafield` | Manage data fields |

### Import & Sync
| Tool | Description |
|------|-------------|
| `list_import_sources` / `get_import_source` | List/get import sources |
| `create_import_source` / `update_import_source` / `delete_import_source` | Manage import sources |
| `list_sync_rules` / `get_sync_rule` | List/get sync rules |
| `create_sync_rule` / `update_sync_rule` / `delete_sync_rule` | Manage sync rules |

### Jobs
| Tool | Description |
|------|-------------|
| `list_jobs` / `get_job` | List/get jobs |
| `create_job` / `update_job` / `delete_job` | Manage jobs |
| `run_job` | Execute a job |

### Branches
| Tool | Description |
|------|-------------|
| `list_branches` / `get_branch` | List/get branches |
| `create_branch` / `update_branch` / `delete_branch` | Manage branches |
| `merge_branch` | Merge branch into main config |

## API References

- [Icinga2 REST API Documentation](https://icinga.com/docs/icinga2/latest/doc/12-icinga2-api/)
- [Icinga Director REST API Documentation](https://github.com/Icinga/icingaweb2-module-director/blob/master/doc/70-REST-API.md)

## License

MIT
