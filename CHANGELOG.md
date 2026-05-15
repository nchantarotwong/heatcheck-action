# Changelog

All notable user-facing changes to `heatcheck-action`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project
itself versions via [SemVer](https://semver.org/spec/v2.0.0.html).

The version of `heatcheck-action` is the version of the wrapper Action
plus the bundled scanner binary; bumping either drives a new release.
Pin to a floating `@v1` for auto-bumps within v1.x, or an immutable
`@v1.0.X` for byte-identical scan results across re-runs.

## [Unreleased]

## [1.0.3] - 2026-05-14

### Changed
- **Scanner** rebuilt against Heat `83733029` — newer compiler and
  language fixes ship in the binary. No user-visible behavior change
  for valid scans.
- **Scanner** text-mode (`heatcheck FILE.py`, without `--json`) now
  exits `1` when violations are found, matching `--json` mode and
  the `--help`-documented contract. JSON-mode exit semantics
  unchanged.

### Added
- **Container image** at `ghcr.io/nchantarotwong/heatcheck` — multi-arch
  (linux/amd64 + linux/arm64), one tag per release (`vX.Y.Z`, plus
  floating `vX` and `latest` for stable releases). Pinnable by digest
  for supply-chain-sensitive environments.
- **`docs/non-github-actions.md`** — guide for GitLab CI, Jenkins,
  generic Docker, and pre-commit setups using the container or the
  raw binary release.
- **`examples/gitlab-ci.yml`**, **`examples/Jenkinsfile`**,
  **`examples/docker-run.sh`**, **`examples/.pre-commit-config.yaml`** —
  drop-in snippets matching the per-CI sections in the docs.
- Top-level README callout pointing non-GHA users at the new docs so
  the GHA-flavored repo name doesn't gate discovery.

### Fixed
- Container Dockerfile installs `libxml2` and `libsqlite3-0` at
  runtime. The slim base image didn't ship them and the binary links
  against both; first v1.0.2 image-build attempt failed at the
  in-Dockerfile `heatcheck --version` smoke step.

### Internal
- `actions/*` bumped to Node.js 24-compatible majors across workflows,
  `action.yml`, README example snippets, and `examples/`. Clears the
  Node 20 deprecation warnings ahead of GitHub's June 2026 forced
  upgrade. `checkout` v4→v6, `setup-python` v5→v6, `upload-artifact`
  v4→v7, `download-artifact` v4→v8, `cache` v4→v5.

### Forthcoming (tracked, not in this release)
- **SARIF output** (`heatcheck --sarif`) — enables native ingestion in
  GitLab Ultimate SAST, Azure DevOps, SonarQube, and GitHub Code
  Scanning. Docs already show the wiring; the flag will exit `2` on
  releases prior to its inclusion.

## [1.0.2] - 2026-05-13

### Fixed
- Scanner stability on large codebases. A use-after-free in the
  scanner's scope-exit cleanup could SEGV after the JSON report had
  already been written. Mostly silent under typical workloads; more
  likely to fire on large projects with many files. Scan accuracy is
  unchanged.

## [1.0.1] - 2026-05-13

### Changed
- Action `name:` renamed `heatcheck` → `heatcheck-action` so it could
  be listed on the GitHub Marketplace (names must be unique).
- Functionally identical to 1.0.0; same scanner binaries.

## [1.0.0] - 2026-05-13

### Added
- Initial public release. Static taint analysis for AI-generated
  Python — catches SQL injection (HC-005), command injection
  (HC-002), eval/exec (HC-003), unsafe deserialize (HC-004), SSRF
  (HC-006), template injection (HC-007), NoSQL injection (HC-008),
  XPath injection (HC-009), LDAP injection (HC-010), XXE / billion-
  laughs (HC-011), and TLS verification disabled (HC-012). Also
  path traversal (HC-001).
- Zero-config — source tags inferred from recognized imports
  (Flask, FastAPI, Django, SQLAlchemy, requests, MCP server
  decorators).
- Inline PR annotations, workflow summary, JSON report artifact,
  HTML report (optional).
- Platforms: Linux x86_64, Linux arm64, macOS arm64.
