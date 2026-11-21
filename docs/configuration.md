# Configuration

The servers load `.env` from their working directory. Process environment variables take precedence. Start from the repository's [example](../.env.example) and configure the backend you intend to use. Keep credentials in the deployment environment or in a local file readable only by the service account.

## Core and Director settings

| Setting | Purpose | Default |
| --- | --- | --- |
| `ICINGA_HOST` | Legacy Core API hostname. The client constructs `https://<host>:5665/v1` | Required for legacy Core |
| `ICINGA_USER`, `ICINGA_PASSWORD` | Legacy Core API credentials used for reads and writes | Required for legacy Core |
| `ICINGA_VERIFY_SSL`, `ICINGA_CA_BUNDLE` | Verify the legacy Core API certificate and optionally use a private CA bundle | `true`, unset |
| `DIRECTOR_BASE_URL` | Director module URL, for example `https://monitoring.example/icingaweb2/director` | Required for Director |
| `DIRECTOR_USER`, `DIRECTOR_PASSWORD` | Icinga Web 2 credentials for Director | Required for Director |
| `DIRECTOR_VERIFY_SSL`, `DIRECTOR_CA_BUNDLE` | Verify the Director API certificate and optionally use a private CA bundle | `true`, unset |

For Core problem and inventory queries, grant the API account access to the applicable host and service objects. Some Icinga 2 versions and configurations also require permission to use filter expressions. ACKs, rescheduling and other write tools require their corresponding Core action permissions. Director REST access requires `director/api` and permission for the requested operation. Consult the backend documentation for the version you operate. [Icinga 2 API](https://icinga.com/docs/icinga-2/latest/doc/12-icinga2-api/) · [Director REST API](https://icinga.com/docs/icinga-director/latest/doc/70-REST-API/)

Both backends use HTTPS with certificate verification enabled. Use the per-backend `*_CA_BUNDLE` setting for an internal CA. Configurations that previously set `*_VERIFY_SSL=false` must set it to `true` to enable verification. Named Core instances and history have separate TLS settings.

## MCP transport and writes

Prefix each setting with `ICINGA_` for Core or `DIRECTOR_` for Director.

| Setting suffix | Purpose | Default |
| --- | --- | --- |
| `TRANSPORT` | `streamable-http` or `stdio` | `streamable-http` |
| `MCP_HOST`, `MCP_PORT` | Local bind address and port | `127.0.0.1`, Core `8092`, Director `8093` |
| `MCP_ALLOWED_HOSTS` | JSON array of HTTP Host headers, including ports where sent by clients | Loopback hosts |
| `MCP_ALLOWED_ORIGINS` | JSON array of allowed browser origins | Empty. Clients without Origin are supported |
| `MCP_BEARER_TOKEN` | Shared HTTP token with at least 32 random URL-safe characters | Unset |
| `MCP_TLS_CERT`, `MCP_TLS_KEY` | Listener certificate (including intermediates if needed) and private key | Unset |
| `ALLOW_WRITES` | Expose and permit mutation tools. For Director this also controls agent ticket generation | `false` |

Non-loopback HTTP binds require a TLS certificate, key, bearer token and an explicit Host allowlist. Send the token in the `Authorization` header with the `Bearer` scheme. This is a shared credential for one server. Every holder has the same MCP access. Use separate credentials for Core and Director and restrict network access to the required clients. On loopback, an authenticating reverse proxy can enforce client identity while keeping the upstream listener private. See the [deployment guide](operations.md#deployment-safeguards).

The following settings are read from the **process environment** when the client modules are imported. Export them before startup or set them in the service manager.

| Core and Director suffix | Purpose | Default |
| --- | --- | --- |
| `REQUEST_TIMEOUT` | Request timeout in seconds | `30` |
| `POOL_CONNECTIONS` | Number of cached connection pools | `20` |
| `POOL_MAXSIZE` | Number of reusable connections kept per pool | `50` |

Prefix each suffix with `ICINGA_` or `DIRECTOR_`.

## Named Core instances

Named instances take precedence over the legacy Core credentials. Include the full API URL with `/v1`. A named instance uses separate read and write accounts and enables writes for that instance when `ICINGA_ALLOW_WRITES=true` and both write fields are set. Acknowledgements and downtimes use the configured write account as their author.

```ini
ICINGA_INSTANCES__PROD__URL=https://core.example:5665/v1
ICINGA_INSTANCES__PROD__USER=monitoring-reader
ICINGA_INSTANCES__PROD__PASSWORD=<read-password>
# ICINGA_INSTANCES__PROD__CA_BUNDLE=/path/to/icinga-ca.pem
# ICINGA_INSTANCES__PROD__WRITE_USER=monitoring-operator
# ICINGA_INSTANCES__PROD__WRITE_PASSWORD=<write-password>
```

Certificate verification defaults to enabled for named instances. The optional `VERIFY_SSL` field controls it. Instance names from nested environment variables are normalized to lowercase. Call `health_check` to discover names and pass `instance` when more than one instance is configured.

## Incident history

Set the Icinga Web 2 root URL and use an account allowed to read the Icinga DB Web history view. The history connection is independent of the configured Core instances.

```ini
ICINGA_HISTORY__URL=https://monitoring.example/icingaweb2
ICINGA_HISTORY__USER=<history-user>
ICINGA_HISTORY__PASSWORD=<history-password>
# ICINGA_HISTORY__CA_BUNDLE=/path/to/ca.pem
# ICINGA_HISTORY__TIMEOUT=15
```

History uses HTTPS with certificate verification enabled by default. The optional `ICINGA_HISTORY__VERIFY_SSL` field controls it. `get_history` takes an exact host, an optional service or event type, and optional ISO 8601 start and end times with time zones. The default window is 24 hours and the maximum is 31 days. Narrow the query if `has_more` is true.

## Linuxfabrik plugin catalog

Clone [Linuxfabrik monitoring-plugins](https://github.com/Linuxfabrik/monitoring-plugins) and set `ICINGA_PLUGIN_CATALOG_PATH` to its `check-plugins` directory. Core indexes metadata at startup. Restart it to refresh the catalog after updating the checkout. `list_plugins` finds plugins, `explain_plugin` describes them, `find_plugin_for_check_command` maps Director commands, and `read_plugin_source` reads source text. The catalog supports standalone use after removing the legacy Core credential placeholders from `.env`.

## Director activity reader

The optional preview uses `DIRECTOR_ACTIVITY__SSH_TARGET`, `DIRECTOR_ACTIVITY__IDENTITY_FILE` and `DIRECTOR_ACTIVITY__KNOWN_HOSTS`. See the [installation and privilege requirements](operations.md#director-deployment-preview).
