# Working on icinga-mcp

## Repository layout

- `src/icinga2_mcp` contains the FastMCP runtime monitoring server, the Icinga 2 REST client and optional Icinga DB Web history and Linuxfabrik plugin catalog.
- `src/director_mcp` contains the FastMCP Director server, its REST client and deployment inspection.
- `tools/director_activity_reader.py` reads Director audit metadata through a restricted SSH command and local MariaDB socket.
- `tests` contains `unittest` client and MCP tests. The Python package uses setuptools and declares its dependencies in [pyproject.toml](pyproject.toml).

## Development

Use the repository virtual environment. See [CONTRIBUTING.md](CONTRIBUTING.md#development) for setup.

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
.venv/bin/python -m pip wheel --no-deps --wheel-dir dist .
```

Inspect adjacent modules before editing. Prefer scoped changes, reuse the existing clients and settings, and follow [.editorconfig](.editorconfig) and the local Python style. The repository has no configured formatter or linter. Keep dependency changes justified and maintain support for the declared Python floor.
Preserve existing license and copyright files. Refer project-wide licensing decisions to the maintainer.

## Validation and safety

- Verify tool discovery and the relevant call through MCP when changing a tool. Preserve public names, parameters and response formats unless a migration is part of the request.
- Use mocks for writes. Keep live checks read-only unless the user requests a specific action.
- Keep credentials, local environment files, SSH keys and private monitoring data out of commits, fixtures and PRs. Use placeholders and sanitize diagnostics.
- Obtain authorization before destructive operations, production changes, remote publication or repository settings changes. Respect existing access controls.
- Update the relevant README or guide and the [changelog](CHANGELOG.md) when user-facing behavior changes. Refer to [SECURITY.md](SECURITY.md) for reporting policy.

## Commits and pull requests

Keep each PR focused. Write Conventional Commits and English PR titles. Use the configured Git author and credit Codex as co-author when it contributed. Follow the [PR template](.github/pull_request_template.md) and [release instructions](docs/releasing.md).

## Definition of done

Review the final diff and run the relevant checks. Report results that actually ran, skipped checks, compatibility changes and remaining risks. Confirm that documentation matches the implementation and that modified files contain no private configuration.
