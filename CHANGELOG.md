# Changelog

All notable user-facing changes to `heatcheck-action`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project
itself versions via [SemVer](https://semver.org/spec/v2.0.0.html).

The version of `heatcheck-action` is the version of the wrapper Action
plus the bundled scanner binary; bumping either drives a new release.
Pin to a floating `@v1` for auto-bumps within v1.x, or an immutable
`@v1.0.X` for byte-identical scan results across re-runs.

## [Unreleased]

## [1.6.0] - 2026-05-18

### Added
- **Go scanning now covers directories and whole repos.** Directory
  and repository scans include `.go` automatically (previously a
  directory scan analyzed Python only and silently skipped Go). Go
  is type-checked per package via `go list`, so real multi-package
  modules scan correctly — large repositories complete instead of
  timing out.
- **`skipped` in the JSON report.** Go files Go itself excludes from
  the active build (build tag / cgo-only) are reported as *skipped*
  — listed in the JSON `skipped` array, as SARIF execution
  notifications, and in text/HTML output — instead of being
  misreported as analysis failures or silently dropped.

### Fixed
- **A scan that analyzed nothing can no longer read as clean.** When
  every requested input is build-excluded (nothing was actually
  analyzed), the scan now exits `3` with `healthy: false` in all
  output modes (JSON, SARIF, text, HTML report) — previously this
  could surface as `healthy: true` / exit `0`, a false "clean" for
  CI consumers. Build-excluded files alongside analyzed files remain
  informational (listed, do not fail the run).
- Build-tag/cgo-gated Go files are no longer misclassified as bridge
  failures on real repositories (eliminated the spurious analysis
  errors that affected essentially every Go repo using build tags).

### Notes
- **Python scanning is byte-identical to v1.5.1 / v1.5.0 / v1.4.1 —
  unchanged.** All changes are Go-path and output-reporting only.
- Go scanning still requires the **`go` toolchain on the runner**
  (GitHub-hosted `ubuntu-*` / `macos-*` ship it; the container image
  remains Python-only).
- If you branch on the exit code, treat **`3` as not-clean** (not
  just `0`/`1`): see [docs/non-github-actions.md](docs/non-github-actions.md#exit-codes).

## [1.5.1] - 2026-05-17

### Fixed
- **Go analysis now works in the distributed binary.** The Go
  bridge source is **embedded in the binary** instead of loaded
  relative to the working directory, so Go scanning works in the
  standalone binary, the GitHub Action, and anywhere the binary
  runs — not just inside a source checkout. This makes the v1.5.0
  Go feature actually usable; it was non-functional for every real
  consumer in v1.5.0 (failed loud `bridge unavailable`). **Python
  scanning is byte-identical to v1.5.0 / v1.4.1 — unchanged.** A
  CI guard now asserts the embedded bridge is byte-identical to
  its source and scans correctly from a non-checkout directory, so
  this class of defect cannot regress.

### Notes
- Go scanning requires the **`go` toolchain on the runner**.
  GitHub-hosted `ubuntu-*` / `macos-*` runners ship Go — no setup
  step needed; the Action adds none. Self-hosted / minimal runners
  must provide `go` (e.g. an `actions/setup-go` step). Without it,
  a `.go` scan fails loud — never a silent clean. The **container
  image (`ghcr.io/.../heatcheck`) is Python-only** (no `go`
  toolchain in the image); use the standalone binary on a Go-
  enabled host for Go. See the README "Go support" section and
  `docs/non-github-actions.md`.
- Go's recognized sinks: HC-001 path traversal, HC-002 command
  injection, HC-004 unsafe `gob` deserialize, HC-005 SQL
  injection, HC-006 SSRF, HC-007 `html/template` injection —
  type-driven, interprocedural, cross-package. Documented
  accurately in the README (v1.5.0 docs did not mention Go).
- Scanner rebuilt against Heat `e5460e1`; Python findings
  byte-identical to v1.5.0 / v1.4.1.

## [1.5.0] - 2026-05-17

### Added
- **Go is now a supported language.** heatcheck analyzes `.go`
  files alongside Python — the *same* interprocedural taint
  engine, type-driven via `go/types`. Catches SQL injection
  (HC-005), command injection (HC-002), path traversal (HC-001),
  SSRF (HC-006), SSTI/XSS via `html/template` bypass conversions
  (HC-007), and unsafe `encoding/gob` deserialization (HC-004),
  with `path/filepath.Base` recognized as a path launderer. Taint
  resolves through local helper functions, receiver methods
  (pointer/value), and across packages within a Go module
  (`go list`-driven resolution). Requires the Go toolchain on
  PATH for Go scans; its absence fails loud, never a silent
  clean. Pass a `.go` file explicitly — directory scans stay
  Python-only for now.
- **MCP `fix_verify` verb.** Applies the mechanical fixes, then
  re-scans the result and reports any fix that didn't clear its
  finding plus any regression the rewrite introduced — the
  closed-loop check detection-only tools can't make. Joins
  `scan` / `scan_path` / `explain` / `suggest_fix` /
  `apply_fixes`.
- **`--report PATH`.** Write the HTML report to an explicit path
  instead of `.heatcheck/report.html`, so concurrent runs (an
  agent driving heatcheck-MCP from two editors in one repo,
  parallel CI / pre-commit) don't collide on a single file.
  `--no-report` still takes precedence; default behavior is
  unchanged when the flag is absent.

### Fixed
- **Concurrency-safe AST bridge.** The Python AST bridge was
  written to a fixed `/tmp` path that every invocation rewrote
  then `python3`-exec'd. Concurrent heatcheck processes could
  race — one truncating the file while another exec'd it →
  corrupt bridge → a clean file spuriously flagged or a real
  finding missed. Each process now uses a per-process bridge
  path. Affects any concurrent use (agents/MCP, parallel
  pre-commit); sequential scans were never affected.

### Changed
- **Scanner** rebuilt against Heat `89fc10d`. Python scan
  findings are **byte-identical** to v1.4.1 — every Go / MCP /
  CLI addition above is additive and the Python path is
  unchanged (verified zero-regression across the suite). The
  binary version is stamped from the release tag (since v1.4.1).

### Known issues
- **Go analysis is non-functional in this build** (fixed in
  1.5.1). The Go bridge source was loaded relative to the working
  directory rather than embedded in the binary, so the standalone
  binary, GitHub Action, and container all fail loud with
  `could not analyze Go: bridge unavailable` for any `.go` scan.
  It fails **loud, never silent** — **Python scanning is
  unaffected and byte-identical to v1.4.1**. Upgrade to **1.5.1**
  for working Go support; Python-only users are not impacted.

## [1.4.1] - 2026-05-16

### Fixed
- **Scanner self-reported version was wrong.** `heatcheck_version()`
  feeds `--version`, the LSP `serverInfo`, and the SARIF
  `tool.driver.version` (which surfaces in GitHub code-scanning).
  It was a hand-maintained constant that drifted — stuck at
  `1.2.1` across v1.3.0 → v1.4.0 — so every released binary
  misreported its version and the code-scanning provenance/audit
  trail was wrong. The release build now stamps the version from
  the release tag (the tag is the single source of truth and the
  build hard-fails if stamping doesn't take), so from v1.4.1 on
  `--version` and the SARIF tool version match the release. Local
  / `install.sh` / LSP-dev builds report a `0.0.0-dev` sentinel
  rather than a stale number.

### Changed
- **Scanner** rebuilt against Heat `336bdba`. The only scanner
  change vs v1.4.0 is the version-sentinel cleanup — **scan
  findings are byte-identical to v1.4.0**, no detection or output
  behavior change.

## [1.4.0] - 2026-05-16

### Changed
- **~30× faster cold scans.** The scanner previously spawned one
  `python3` AST-bridge subprocess per source file — CPython startup
  + `import ast,json` paid per file dominated runtime on large
  repos, and cross-module import resolution re-spawned the bridge
  for every importer of a shared module. It now drives a single
  persistent Python AST worker for the whole multi-file scan, with
  a parse cache so a module imported by N files is parsed once.
  Measured on a 452-file corpus (including a 21k-line file):
  **63.85s → 2.12s**. Scan **findings are byte-identical** to
  v1.3.4 — this is purely a performance change, no detection or
  output behavior changes. Single-file `--fix`, `--self-test` and
  the LSP server are unchanged (they keep the one-shot path), and
  a worker failure transparently falls back to the old per-file
  spawn, so results are unaffected even if the worker can't start.
- **Scanner** rebuilt against Heat `a4bb2f1`.
- Verified byte-identical findings vs v1.3.4 on 452 real files
  (incl. multi-chunk reassembly of a 21k-line file), the
  interprocedural eval corpus, and text + JSON modes. Suites:
  self-test 5/5, regression corpus GUARD 13/13, output/SARIF/FP
  format suites all green.

## [1.3.4] - 2026-05-16

### Fixed
- **False positive: cross-module Pydantic/dataclass mass assignment
  (HC-014).** `User(**request.json)` is exempt from HC-014 when the
  constructed class is a Pydantic/dataclass schema (the schema *is*
  the field whitelist). That exemption previously only covered
  schemas defined in the same module; an imported schema —
  `from app.schemas import S; … S(**body)` — still fired HC-014
  (the langserve `StreamLogParameters` / `StreamEventsParameters`
  shape, 2 false positives). `collect_imports` now runs the same
  Pydantic detector over each imported module, so cross-module
  schemas get the exemption too. Suppress-only by construction:
  it can only add receivers to the HC-014 exemption set, never
  introduce a finding — a non-schema imported class (e.g. an ORM
  model) still fires.

### Changed
- **Scanner** rebuilt against Heat `f32c459`.
- Regression corpus GUARD 13/13 — adds a cross-module Pydantic
  FP-clean guard and a cross-module ORM-model guard (the latter
  must still fire, proving the exemption stays schema-scoped).
- Verified with a 9-repo native FP-movement guard vs v1.3.3: zero
  finding movement on 8 real repos; only the intended langserve
  HC-014 pair removed.

## [1.3.3] - 2026-05-16

### Fixed
- **False positive: SQLAlchemy `session.execute(<Select>)`.** A
  `Select`/Core-or-ORM statement passed to a SQLAlchemy
  Session/Engine `.execute()`/`.executemany()` is fully
  parameterized — there is no string-SQL boundary. heatcheck
  previously fired HC-005 when the statement arrived from a helper
  via tuple-unpack and inherited `user_input` from filter arguments
  (the `x, _ = paginated_select(statement=base_query, filters=[…]);
  session.execute(x)` shape — 4 false positives in Airflow's
  `api_fastapi`). Now narrowed: on a SQLAlchemy session/engine
  receiver, only a raw-SQL-string expression (f-string / concat /
  `%` / `.format()` / `text(<tainted>)`) fires. The injectable
  `session.execute(text(<tainted>))` form is still caught at the
  `text()` sink, so this removes false positives with no new false
  negative; DB-API `cursor.execute("…"+u)` is a different receiver
  and is unaffected.

### Changed
- **Scanner** rebuilt against Heat `4ec72f9`.
- Regression corpus GUARD 11/11 — adds the `paginated_select`
  FP-clean guard plus false-negative guards (`cursor.execute(concat)`
  and `session.execute(text(f-string))` must still fire).

## [1.3.2] - 2026-05-16

### Added
- **Absolute-package-import resolution — completes the cross-module
  taint chain.** Module resolution previously only looked relative to
  the importing file's directory, so absolute package imports
  (`from myapp.models import X` resolved against the package root —
  the common real-world layout) computed the wrong path and the
  imported module was never analyzed. Resolution now walks up to the
  package root. Combined with v1.3.0 (request-bag aliasing) and
  v1.3.1 (`ClassName.staticmethod` resolution), attacker input
  flowing **across files** — request handler → imported helper / DAO
  class → sink — is now caught. Verified end-to-end on a real
  package: the `request.post()` → `Cls.create(data['k'])` →
  `%`-format `cur.execute()` SQLi shape, previously a confirmed
  false negative, is now reported.

### Changed
- **Scanner** rebuilt against Heat `23e9c90`.
- Regression corpus GUARD 8/8 — the absolute-package-import
  cross-module case is now a hard guard (was the last forward-looking
  xfail; only an unrelated `sys.argv` case remains).

## [1.3.1] - 2026-05-16

### Added
- **Cross-module `ClassName.staticmethod()` taint resolution.** Calls
  like `Student.create(data['k'])` where `Student` is defined in the
  same module or a dir-relative import now step into the method body
  with caller argument tags. `collect_functions` previously skipped
  class bodies entirely, so static/class methods were never resolved
  for interprocedural analysis — even though the call-site dispatch
  already computed the right key. Closes the same-module and
  dir-relative cross-file half of the cross-module gap (e.g. the
  `request.post()` → `Cls.create(data['k'])` → `%`-format
  `cur.execute()` SQLi shape).

### Changed
- **Scanner** rebuilt against Heat `768b93c`.
- Regression corpus: the cross-module SQLi case is now a hard GUARD
  (was a forward-looking xfail); a new xfail isolates the remaining
  absolute-package-import resolution gap.

### Known limitation
- Absolute *package* imports (`from myapp.models import X` resolved
  against the package root — the common real-world layout) are still
  resolved dir-relative and may not locate the target module, so
  cross-module taint across that import style is not yet caught.
  Tracked; the broad "cross-module" capability is intentionally not
  yet claimed in the README until this lands.

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
