# Contributing

Use [GitHub Issues](https://github.com/DanielVd/icinga-mcp/issues) for reproducible bugs and feature requests. Include the version, affected server and tool, and the expected outcome. Search existing issues before opening a new one. Report security issues through the [security policy](SECURITY.md).

## Development

From the repository root, create an isolated environment and install the checkout.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
python -m pip check
python -m pip wheel --no-deps --wheel-dir dist .
```

The minimum supported Python version is declared in [pyproject.toml](pyproject.toml). Tests use the standard library's `unittest` and mock backend requests. A subset exercises MCP discovery and tool calls. The build uses setuptools and produces a wheel under `dist/`.

The CI definition tests and builds on Linux with Python 3.10 and 3.14. It also audits the resolved Python 3.14 dependencies. See the [CI workflow](.github/workflows/ci.yml) and [CodeQL workflow](.github/workflows/codeql.yml).

Follow the adjacent Python style and the [editor settings](.editorconfig). The repository has no configured formatter, linter or type-checking command. Add a dependency only when the standard library or an existing dependency does not meet the need. Record compatibility effects in the PR.

## Pull requests

1. Branch from the current default branch and keep the change focused.
2. Verify the relevant public behavior and report the exact checks you ran. For live smoke tests, use read-only calls unless the test explicitly calls for a live change.
3. Update the README or detailed guide if installation, configuration or user-facing tools change. Record notable changes under **Unreleased** in the [changelog](CHANGELOG.md).
4. Use Conventional Commits and a concise English PR title. For example, `fix(core): preserve spaces in object queries`. Complete the [PR template](.github/pull_request_template.md) and describe any migration.

Keep real credentials, SSH keys, hostnames, addresses and private monitoring output out of branches and PRs. Use fixtures and public placeholders. Maintainers review changes before publishing releases. See the [release process](docs/releasing.md).
