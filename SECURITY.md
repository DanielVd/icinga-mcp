# Security policy

This policy covers the MCP servers, distributed artifacts and the optional Director activity reader. For vulnerabilities in Icinga, Open WebUI or another upstream project, use that project's reporting channel. The [GitHub releases](https://github.com/DanielVd/icinga-mcp/releases) identify published versions. A support window and response deadline have yet to be established.

## Report a vulnerability

Use **Report a vulnerability** on the repository's [Security Advisories page](https://github.com/DanielVd/icinga-mcp/security/advisories) to report privately. If the form is unavailable, use an existing private channel with the maintainer, or open a [GitHub issue](https://github.com/DanielVd/icinga-mcp/issues/new) to request one. Keep the public request generic. Share the technical details only after a private channel is established.

Include the affected version or commit, component or endpoint, required privileges, and a minimal description of the impact. Share sanitized diagnostic data. Keep passwords, tokens, keys, internal addresses and exploit material out of public discussions.

## Handling and disclosure

The maintainer reviews whether the report applies to the project, identifies affected versions, and coordinates a fix and disclosure with the reporter and any relevant upstream team. Agree on disclosure timing as part of that process. When a fix or mitigation is available, communicate the affected versions, impact and upgrade or mitigation steps through an advisory or release notes.

## Deployment boundaries

Both MCP HTTP listeners accept calls without built-in client authentication. Use a trusted network boundary or authenticated proxy and least-privilege Icinga accounts. Enable TLS verification for upstream HTTPS and use trusted CA certificates. Core and Director can perform writes according to the permissions of their backend accounts. Treat exposed secrets as compromised and rotate them even if the source references are removed later. See the [deployment guide](docs/operations.md#deployment-safeguards) and [configuration guide](docs/configuration.md).
