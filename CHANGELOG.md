# Changelog

Notable changes are recorded here. This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-11-21

### Added

- Contribution, support, security, operations and release documentation.
- EditorConfig, GitHub issue forms, and workflow definitions for tests, builds, dependency auditing and CodeQL.
- Dependabot configuration for Python and GitHub Actions version updates.
- MIT license for the original project code and documentation, with REUSE and wheel metadata for the bundled Linuxfabrik code under the Unlicense.

### Changed

- Clarified the installation, permissions, TLS defaults and optional backend configuration.
- Expanded the repository guidance for coding agents.

### Security

- Require MCP SDK 1.30 or later in the 1.x series and pydantic-settings 2.14.2 or later for upstream security fixes. Resolve dependencies in a fresh virtual environment when upgrading.

## [0.2.0] - 2026-11-21

### Added

- Active problem triage with severity, host group, duration, acknowledgement and downtime filters.
- Named Core instances, optional Linuxfabrik plugin metadata and Icinga DB Web history.
- Optional Director activity preview and active deployment checksum verification.
- A Python wheel attached to the GitHub Release.

### Changed

- `get_problems` exposes summary fields directly in MCP `structuredContent`. Its JSON text response still uses the existing field layout.

### Fixed

- Core object lookups and filters with spaces.
- Director updates that return an empty HTTP 304 when no changes are needed.

## [0.1.1] - 2026-05-19

### Changed

- GitHub release notes describe README and metadata alignment. The current `v0.1.0` and `v0.1.1` tags refer to the same source commit.

## [0.1.0] - 2026-05-19

### Added

- Initial GitHub release with MCP servers for Icinga 2 and Icinga Director.

[Unreleased]: https://github.com/DanielVd/icinga-mcp/compare/v0.2.1...main
[0.2.1]: https://github.com/DanielVd/icinga-mcp/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/DanielVd/icinga-mcp/releases/tag/v0.2.0
[0.1.1]: https://github.com/DanielVd/icinga-mcp/releases/tag/v0.1.1
[0.1.0]: https://github.com/DanielVd/icinga-mcp/releases/tag/v0.1.0
