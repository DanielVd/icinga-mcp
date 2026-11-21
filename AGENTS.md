# Working on icinga-mcp

## Repository layout

- `src/icinga2_mcp` exposes Icinga Core runtime monitoring, actions and Icinga DB Web history.
- `src/director_mcp` exposes Director configuration and deployment operations.
- `tools/director_activity_reader.py` reads deployment audit metadata through a separate restricted account.
- `tests` covers API clients and the MCP interface. Setup and environment variables are documented in the [README](README.md).

## Verification

Run the suite from the repository root with the project's virtual environment.

```sh
.venv/bin/python -m unittest discover -s tests -v
```

- For MCP changes, verify tool discovery and the relevant tool call through the SDK.
- Use mock responses for writes. Keep live checks read-only unless a specific live action was requested.
- Preserve tool names, arguments and response formats unless the requested change requires a migration. Document any migration in the PR.

## Commits and pull requests

- Keep each PR focused on one independently verifiable change.
- Write Conventional Commit subjects and PR titles in English, such as `fix(core): preserve spaces in object queries`.
- Use the configured Git author and credit Codex as co-author when it contributed to the changes.
- Use the [PR template](.github/pull_request_template.md). Record the verification performed and any compatibility impact.

## Public repository

Keep credentials, local environment files, private hostnames and internal addresses out of commits and PRs. Use placeholders in examples and redact private values from logs before sharing them.
