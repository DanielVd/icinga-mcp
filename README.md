# icinga-mcp

[![Latest release](https://img.shields.io/github/v/release/DanielVd/icinga-mcp)](https://github.com/DanielVd/icinga-mcp/releases/latest)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)

Self-hosted Model Context Protocol (MCP) servers for an existing Icinga installation. Use Core to inspect live problems and run checks. Use Director to inspect or manage configuration.

| Server | Typical use | Default endpoint |
| --- | --- | --- |
| `icinga2-mcp` | Live host and service state, problem triage, checks, acknowledgements and downtimes | `http://127.0.0.1:8092/mcp` |
| `director-mcp` | Director inventory, configuration changes and deployment verification | `http://127.0.0.1:8093/mcp` |

The project publishes GitHub Releases and is currently in the SemVer `0.x` series. Check the [changelog](CHANGELOG.md) before upgrading.

## Quick start

1. Install Python 3.10 or later and Git. For Core, have a reachable Icinga 2 API and an API account. For Director, have a reachable Icinga Web 2 Director module and an account with Director API access.
2. Clone the repository and create a virtual environment. These commands use a POSIX shell.

   ```sh
   git clone https://github.com/DanielVd/icinga-mcp.git
   cd icinga-mcp
   python3 -m venv .venv
   . .venv/bin/activate
   python -m pip install -e .
   cp .env.example .env
   ```

3. Replace the placeholders in `.env` for the server you want to run. Core uses `ICINGA_HOST`, `ICINGA_USER` and `ICINGA_PASSWORD`. Director uses `DIRECTOR_BASE_URL`, `DIRECTOR_USER` and `DIRECTOR_PASSWORD`. See the [configuration guide](docs/configuration.md) for permissions and TLS.
4. From the repository root, run `.venv/bin/icinga2-mcp` or `.venv/bin/director-mcp`. Start each server in its own terminal if you want both.
5. In the client, add the appropriate endpoint using **Streamable HTTP**. Use an address reachable from the client host or container. If the client filters tool names, include the tools you want it to call.

Test the connection with a read-only call.

| Server | Tool | Arguments |
| --- | --- | --- |
| Core | `get_problems` | `{"limit": 5}` |
| Director | `list_hosts` | `{"limit": 5, "summary": true}` |

The [release page](https://github.com/DanielVd/icinga-mcp/releases/latest) also provides a Python wheel. Install the downloaded wheel with `python -m pip install <wheel-path>` and use `.env.example` from the matching source release as a starting point.

## What you can do

- Request a triage summary. For example, ask Core for critical services without an acknowledgement or downtime. Use `get_problems` with `{"severity":"CRITICAL","acknowledged":false,"in_downtime":false}`.
- Inspect a single live host or service with the Core tools. State and output are available through Core. Director shows configured objects.
- Use separate read and write credentials for a [named Core instance](docs/configuration.md#named-core-instances).
- Enable [Icinga DB Web history](docs/configuration.md#incident-history) or the [Linuxfabrik plugin catalog](docs/configuration.md#linuxfabrik-plugin-catalog).
- Verify whether a Director configuration checksum is active. Enable the [optional activity reader](docs/operations.md#director-deployment-preview) to see pending changes before a deployment.

## Documentation

- [Configuration and environment variables](docs/configuration.md)
- [Architecture, deployment and troubleshooting](docs/operations.md)
- [Development, build and tests](CONTRIBUTING.md#development)
- [Releasing and supply-chain records](docs/releasing.md)
- [Security reporting](SECURITY.md) and [support](SUPPORT.md)
- [Repository guidance for coding agents](AGENTS.md)

## Security and licensing

HTTP listeners bind to all interfaces by default and accept clients without built-in MCP authentication. Restrict access to a trusted network or an authenticated proxy, and grant backend accounts only the required permissions. See [deployment safeguards](docs/operations.md#deployment-safeguards).

The original project code and documentation are available under the [MIT License](LICENSE). The vendored Linuxfabrik catalog retains its [Unlicense text](src/icinga2_mcp/plugin_catalog/LICENSE) and [attribution notice](src/icinga2_mcp/plugin_catalog/COPYRIGHT). It was adapted from [Linuxfabrik MCP Server for Icinga at `fd681ab`](https://github.com/linuxfabrik/mcp-server-icinga/tree/fd681abda91bec51c0a42fd4cf3122f3ad94df8d/src/mcp_server_icinga/plugin_catalog). [REUSE.toml](REUSE.toml) records which license applies to each part of the repository.
