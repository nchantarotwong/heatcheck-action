# Changelog

All notable user-facing changes to `heatcheck-action`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project
itself versions via [SemVer](https://semver.org/spec/v2.0.0.html).

The version of `heatcheck-action` is the version of the wrapper Action
plus the bundled scanner binary; bumping either drives a new release.
Pin to a floating `@v1` for auto-bumps within v1.x, or an immutable
`@v1.0.X` for byte-identical scan results across re-runs.

## [Unreleased]

## [1.3.0] - 2026-05-15

### Added
- **Request-bag aliasing is now a taint source.** `data = request.form`
  (also `.args` / `.values` / `.headers` / `.cookies`, Django `.POST` /
  `.GET`, Starlette `.query_params`, and aiohttp `await request.post()`),
  then `data['k']` flowing to a sink, is now detected. Previously only
  direct `request.form['k']` and `.to_dict()` were recognized — the
  aliased-bag handler shape is one of the most common in real Flask /
  aiohttp / FastAPI code, so this closes a broad false-negative class.
  Allowlist-filtered dicts stay clean: zero finding movement across an
  8 real-repo re-scan, so no new false positives.

### Fixed
- **Scanner stability on cross-file imports (RT-0105).** The bag-alias
  read volume exposed a pre-existing use-after-free in the runtime's
  struct-valued container ARC ownership, triggered when analyzing a
  module that imports another module. Fixed in the bundled scanner
  (Heat #869/#870). Scanning projects with cross-file imports no longer
  risks an RT-0105 abort.

### Changed
- **Scanner** rebuilt against Heat `59980f7` — bag-alias taint source
  plus the RT-0105 runtime fix.
- Added a regression corpus to the scanner test suite that pins the
  v1.2.x false-positive fixes and the new bag-alias behavior, with
  the remaining cross-module / `sys.argv` gaps wired as acceptance
  tests.

## [1.2.1] - 2026-05-15

### Added
- **HC-013 `weak-credential-hash`** (severity 8.0 / high). New umbrella
  source tag `@credential` covers any user-supplied string from a field
  named like `password`, `passwd`, `pwd`, `secret`, `token`, `api_key`,
  etc. Flow into a fast-hash sink (`hashlib.md5/sha1/sha2*`, `crypt.crypt`)
  fires HC-013. `bcrypt`, `argon2`, `passlib`, `hashlib.scrypt`, and
  `hashlib.pbkdf2_hmac` sanitize the tag.
- **HC-014 `mass-assignment`** (severity 8.5 / high). New flow tag
  `@unfiltered_dict` applied to `request.json`, `request.form.to_dict()`,
  `await request.json()`, `request.data` (DRF), `json.loads(request.body)`.
  Splatting an `@unfiltered_dict` into a constructor or `.update()`/
  `.update_from_dict()`/`.fill()`/`.from_dict()` fires HC-014. Pydantic
  `BaseModel` subclasses and `@dataclass`-decorated classes act as the
  whitelist. Explicit-key allowlist comprehensions also sanitize.

### Fixed (false-positive reductions, surfaced by an Open WebUI scan)
- **Env vars no longer tagged as `@user_input`**. `os.environ.get(K)`,
  `os.environ[K]`, and `os.getenv(K)` are now treated as operator-
  controlled, not attacker-controlled. They no longer pull HC-001 /
  HC-002 / HC-006 chains by themselves.
- **Basename-class path sanitizers recognized**. `os.path.basename(x)`,
  `pathlib.Path(x).name`, and `urlparse(x).path.split('/')[-1]` clear
  `@user_input → @path_safe`. Eliminates HC-001 false positives on the
  conventional safe upload pattern (`basename(filename) + os.path.join`).
- **HC-006 skipped when the f-string host is a literal**. URLs of the
  form `f"https://api.example.com/{user}"` no longer fire HC-006 — real
  SSRF requires attacker-controlled host, not just attacker-controlled
  path on a fixed host. Truly user-controlled hosts (`f"https://{user}/"`)
  still fire.

### Changed
- **Scanner** rebuilt against Heat `1e38661` — bundles HC-013, HC-014,
  and the three false-positive fixes above.
- README "What heatcheck catches" table now lists HC-013 and HC-014.

## [1.1.0] - 2026-05-14

### Added
- **SARIF 2.1.0 output** via `heatcheck --sarif`. Emits the
  OASIS-standard format that GitHub Code Scanning, GitLab Ultimate
  SAST, Azure DevOps, SonarQube, and most other SAST consumers
  ingest natively. Each heatcheck sink code (`HC-005` etc.) maps
  to a SARIF rule with a `properties.security-severity` score;
  results carry source/sink locations relative to a `%SRCROOT%`
  base ID. Mutually exclusive with `--json`. Validated end-to-end
  against GitHub Code Scanning during the v1.1.0-rc1 prerelease.

### Changed
- **Scanner** rebuilt against Heat `5925375` — adds SARIF emission
  plus any Heat compiler/language changes since v1.0.3.
- `docs/non-github-actions.md` SARIF section is no longer marked
  "forthcoming"; the GitLab Ultimate SAST and GitHub Code Scanning
  wiring is now live. `examples/gitlab-ci.yml` comment drops the
  "(in progress)" qualifier on the SARIF variant.

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
