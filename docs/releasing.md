# Releasing

This project publishes tagged releases and Python wheels on [GitHub Releases](https://github.com/DanielVd/icinga-mcp/releases). Publishing is a maintainer action. Obtain release approval before creating tags or publishing an artifact.

## Prepare the release

1. Review the [changelog](../CHANGELOG.md), then agree on the next version using [SemVer](https://semver.org/spec/v2.0.0.html). Document any breaking tool or configuration changes, including those in the `0.x` series.
2. Update `project.version` in [pyproject.toml](../pyproject.toml) and move the corresponding changelog entries into a dated version section. Submit the version change using the [PR workflow](../CONTRIBUTING.md#pull-requests).
3. From the approved release commit in a clean checkout, run the tests and build the wheel.

   ```sh
   python -m unittest discover -s tests -v
   python -m pip check
   python -m pip wheel --no-deps --wheel-dir dist .
   ```

4. Verify the wheel version and entry points in an isolated environment. Inspect the tracked source and artifact for local configuration and credentials.

## Publish and verify

Create the GitHub Release for `v<version>` from the approved commit. Attach the reviewed wheel and include user-facing changes, migration details and verification results. Confirm that the published tag points to the approved commit and that the downloadable wheel matches the reviewed artifact. The source archive includes the optional Director helper under `tools/`.

After a separately authorized rollout, verify startup, tool discovery and read-only calls through the intended client route. See [upgrade and rollback](operations.md#upgrade-and-rollback).

## Supply-chain records

The package declares dependency ranges in `pyproject.toml`. Builds can resolve different dependency versions over time. Record the target Python version and resolved environment for release verification when a reproducible inventory is needed.

From a separate tools environment, audit the project's resolved dependencies with `pip-audit --skip-editable --path <site-packages>`. Review reported advisories, available fixes and audit coverage before making a release decision. [pip-audit](https://github.com/pypa/pip-audit)

An SPDX or CycloneDX SBOM can describe the resolved build or deployment environment. With `cyclonedx-bom` installed in the tools environment and `dist/` created by the build, generate a CycloneDX inventory from the project environment. Inspect it for local paths or private package indexes before sharing. [CycloneDX Python](https://github.com/CycloneDX/cyclonedx-python)

```sh
cyclonedx-py environment .venv/bin/python --spec-version 1.7 --output-format JSON --output-file dist/sbom.cdx.json
```

GitHub's SPDX export requires a dependency graph and represents GitHub's graph, so its scope can differ from an installed environment. Current releases do not document a published SBOM or a signed provenance attestation. Record the artifact, build context and verification procedure before claiming SLSA provenance. [GitHub SBOM export](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/establish-provenance-and-integrity/export-dependencies-as-sbom) · [SLSA specification](https://slsa.dev/spec/v1.2/)
