# Architecture and operations

## Data flow

Both commands are Python entry points in one setuptools package. MCP calls enter FastMCP handlers, which validate parameters and call the appropriate backend.

| Component | Backend | Purpose |
| --- | --- | --- |
| Core server | Icinga 2 REST API | Live inventory, check results, and monitoring actions |
| Core history | Icinga DB Web JSON history | Read-only event timeline, when configured |
| Core plugin catalog | Local Linuxfabrik plugin checkout | Read and index plugin metadata and source |
| Director server | Icinga Web 2 Director REST API | Configuration and deployments |
| Director activity reader | SSH forced command and local MariaDB socket | Read-only audit metadata, when configured |

Icinga and Director retain monitoring state and configuration. The MCP processes keep configuration and clients in memory. The optional plugin index is rebuilt from the checkout on startup.

## Deployment safeguards

Run each HTTP server under a supervisor with its working directory set to the location of your `.env`. Both servers bind to loopback by default. Use an authenticated HTTPS reverse proxy for remote clients when the proxy can reach the private loopback listener. For a proxy on a separate host, bind to the intended interface and configure listener TLS and a bearer token. Have the proxy verify the upstream certificate and forward the client's Authorization header. Preserve HTTP streaming and the MCP session headers. Both servers support stdio for clients that launch a subprocess.

Credentials for the upstream services belong to the MCP servers. MCP calls use those credentials, so the backend audit identity may be a shared service account. Writes and Director agent ticket generation require opting in at the server. Limit the backend accounts to the operations they must perform. A client-side tool filter controls display. The listener, proxy and backend permissions enforce access.

Avoid wildcard Core API roles. For named Core instances, give the read account only the object and status permissions required for discovery and queries. Create a separate write account with the specific action permissions required by the deployment. Give the Director account only the permissions needed for the enabled operations. A bearer token protects the listener while backend permissions limit the impact of a compromised server or backend credential.

Monitoring data and upstream error details may reach the client and its logs. Review access to the endpoints and redact output before pasting it into tickets or public reports. See [TLS and credentials](configuration.md#core-and-director-settings) and the [security policy](../SECURITY.md).

## Read-only health checks

- Core `health_check` reports configuration and optional backend availability. Call `get_problems` to also check connectivity and read permissions on the Icinga API.
- Director `list_hosts` with `{"limit": 1, "summary": true}` tests the Director REST path.
- When checking a reverse proxy, verify MCP initialization, tool discovery and a real read through the same URL and network route used by the client.

For Open WebUI, use an MCP Streamable HTTP connection under its admin integrations settings and enable that server in the chat. Tool-name filters can exclude `get_problems` or `list_services`. From a container, use the reachable service or proxy address. [Open WebUI MCP guide](https://docs.openwebui.com/features/extensibility/mcp/)

## Director deployment preview

`preview_pending_deployment` reads audit entries newer than the activity checksum of the configuration currently active in Icinga 2. It reports object names, actions, authors and timestamps, with the total number of pending entries. Several entries can refer to the same object. The preview is an audit summary and performs no rendering or deployment.

For MariaDB deployments, install [the activity reader](../tools/director_activity_reader.py) on the Director database host. It expects `/usr/bin/mysql`, a local Unix socket and a database named `director`. Use a dedicated OS and SSH account named `director-mcp-audit`. Restrict its key to the installed reader with the OpenSSH `restrict,command="…"` authorized-key options. The matching MariaDB account needs only these privileges.

```sql
CREATE USER 'director-mcp-audit'@'localhost' IDENTIFIED VIA unix_socket;
GRANT SELECT (id, checksum, object_type, object_name, action_name, author, change_time)
    ON director.director_activity_log TO 'director-mcp-audit'@'localhost';
```

On the MCP host set `DIRECTOR_ACTIVITY__SSH_TARGET` to `director-mcp-audit@<host>` and configure `DIRECTOR_ACTIVITY__IDENTITY_FILE` and `DIRECTOR_ACTIVITY__KNOWN_HOSTS`. Use a dedicated key and verify the host key before deploying. Restart Director MCP to advertise the preview tool, then test it in read-only mode.

After an authorized deployment, pass the checksum returned by `deploy_pending_changes` to `verify_deployment`. This reads Director's reported status and checks which checksum is currently active.

## Upgrade and rollback

Record the running version and the location of its configuration. Read the [changelog](../CHANGELOG.md), install the chosen release in the service environment, and restart the affected MCP process. Repeat the read-only health checks. To roll back, restore the previous package and compatible settings, then restart it. MCP upgrades leave Icinga and Director managed separately. Back up those systems and their databases through your existing Icinga procedures. Keep local configuration and SSH key backups outside Git.

Build a fresh virtual environment for security upgrades so that dependencies are resolved again. Installing only the new wheel in an existing environment can leave older transitive packages in place. Run `python -m pip check` in the replacement environment and audit it before switching the service. See [release verification](releasing.md#supply-chain-records).

When upgrading from 0.2.x to 0.3.x, inventory existing clients before changing the bind address. Configure TLS trust for each backend, then set the proxy route or client credentials before switching remote endpoints. Enable write tools explicitly only where required. Keep the old environment and matching proxy and client configuration until both servers pass the read-only checks through their regular route. Roll back the service, proxy and client configuration together if any part of the route fails.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Connection refused or invalid MCP response | Verify the listener, endpoint path, Streamable HTTP transport and network route from the client. |
| Authentication or permission error | Verify the upstream URL, account credentials and permissions for the requested operation. |
| TLS verification error | Verify the endpoint hostname and CA trust. Use the appropriate CA bundle and verification settings. |
| Tool is missing | Check the tool server selected in the chat, any client-side filter, and the optional backend settings. Restart the MCP process after config changes. |
| History or preview times out | Narrow the history window, or verify the preview reader's SSH and MariaDB connectivity. See [timeouts and connection settings](configuration.md). |
| Director activity endpoint returns 404 | Endpoint availability varies with the Director installation. Use the configured activity reader for the pending preview. |
