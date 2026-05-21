# heatcheck-action

[![test](https://github.com/nchantarotwong/heatcheck-action/actions/workflows/test.yml/badge.svg)](https://github.com/nchantarotwong/heatcheck-action/actions/workflows/test.yml)
[![release](https://img.shields.io/github/v/release/nchantarotwong/heatcheck-action)](https://github.com/nchantarotwong/heatcheck-action/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

> Block the injection bugs LLMs ship past green tests — static taint
> analysis for Python and Go, covering SQLi, command injection, SSRF,
> path traversal, XXE, and template injection.

heatcheck walks a project's AST, traces provenance through
assignments, returns, and tuple-unpacks, and reports cases where
attacker-controlled input reaches a sink that requires a sanitized
value. The sink catalog is prioritized for the injection patterns we
see in AI-assisted code — not ported from a generic linter.

**Python** is the primary surface (the full sink catalog: HC-001…HC-014
across Flask, FastAPI, Django, SQLAlchemy, requests, MCP, …).
**Go** runs through the *same* taint engine — six sinks
(HC-001/002/004/005/006/007), type-driven via a bundled `go/types`
bridge, with taint resolved interprocedurally through helper
functions, value/pointer receiver methods, and across packages.
Requires the `go` toolchain on the runner — GitHub-hosted runners
include it; see [Go support](#go-support).

> **Not on GitHub Actions?** heatcheck also ships as a container
> (`ghcr.io/nchantarotwong/heatcheck`) and as a standalone binary —
> see [docs/non-github-actions.md](docs/non-github-actions.md) for
> GitLab CI, Jenkins, generic Docker, and pre-commit setups.

## Quick start

```yaml
name: heatcheck
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: nchantarotwong/heatcheck-action@v1
```

That's it. No config file, no rule selection, no annotations to add
to your code. heatcheck infers source tags (`@user_input`,
`@network_input`, `@untrusted_storage`, etc.) from the imports and
call sites it recognizes — Flask, FastAPI, Django, SQLAlchemy,
requests, MCP server decorators, and more.

Violations show up as:

- **Inline annotations** on the PR Files tab, one per violation.
- **A workflow summary** at the bottom of the run, grouped by sink code.
- **Job failure** (rc=1) by default — set `fail-on-violations: false`
  to make heatcheck advisory.

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `paths` | `.` | Space-separated paths to scan. Heatcheck skips dotdirs (`.git`, `.venv`, `__pycache__`, ...) automatically. Paths cannot contain spaces. |
| `fail-on-violations` | `true` | Set to `false` to make the action advisory (always rc=0). |
| `heatcheck-version` | (action ref) | Release tag whose binary to download. Defaults to the action's own ref — `uses: ...@v1.3.4` downloads the `v1.3.4` binary. Override only to pin the binary independently of the wrapper. |
| `python-version` | `3.11` | Python version on PATH (heatcheck calls CPython's `ast` module). |
| `upload-report` | `false` | Upload `.heatcheck/report.html` as a workflow artifact for browsing. |
| `timeout-seconds` | `600` | Per-run timeout for the heatcheck binary. |

## Outputs

| Output | Description |
|--------|-------------|
| `violations` | Number of violations across all scanned files. `-1` on internal failure (no JSON produced). |
| `json-path` | Path to the raw JSON report on the runner filesystem. Use it in downstream steps that need to parse violations programmatically. |

The JSON report has `healthy` (bool), `files_analyzed`, `violations`,
`parse_errors`, and `skipped` (Go inputs excluded from the active
build — build tag / cgo). **An empty `violations` array only means
"clean" when `healthy` is `true`** — check `healthy`, not just the
count: a run that failed to analyze inputs, or where every input was
build-excluded, reports `healthy: false` with empty `violations`
(and the action exits non-zero).

## What heatcheck catches

| Code | Sink | Example |
|------|------|---------|
| HC-001 | Path traversal | `open(f"/cfg/{user_name}.cfg")` |
| HC-002 | Command injection | `subprocess.run(cmd, shell=True)` |
| HC-003 | Code injection (eval / exec) | `eval(user_expr)` |
| HC-004 | Unsafe deserialize | `pickle.loads(payload)`, `yaml.load(s)` |
| HC-005 | SQL injection | `cursor.execute(f"... {user_id}")` |
| HC-006 | SSRF | `requests.get(user_url)` without allowlist |
| HC-007 | Template injection | `Template(user_html).render()` |
| HC-008 | NoSQL injection | `db.users.find({"$where": user_q})` |
| HC-009 | XPath injection | `tree.xpath(f"//user[name='{name}']")` |
| HC-010 | LDAP injection | `conn.search_s(base, scope, f"(uid={u})")` |
| HC-011 | XXE / billion-laughs | `etree.fromstring(request.body)` |
| HC-012 | TLS verification disabled | `requests.get(url, verify=False)` |
| HC-013 | Weak credential hash | `hashlib.md5(request.form["password"])` |
| HC-014 | Mass assignment | `User(**request.json)` |

The table above is the **Python** catalog. See [Go support](#go-support)
for the Go coverage.

## Go support

The same interprocedural taint engine analyzes Go — not a separate
Go linter, the *same* engine over a shared AST vocabulary (the
substrate property). Go is **type-driven**, not pattern-matched: a
bundled `go/types` bridge resolves real types.

```go
func handler(w http.ResponseWriter, r *http.Request) {
    id := r.URL.Query().Get("id")                       // @user_input
    db.Query("SELECT * FROM users WHERE id = " + id)    // HC-005
}
```

Recognized Go sinks (each CI-guarded by fixtures):

| Code | Sink | Go surface |
|------|------|------------|
| HC-001 | Path traversal | `os.Open` / `os.ReadFile` / `os.WriteFile` / `http.ServeFile` (`filepath.Base` launders) |
| HC-002 | Command injection | `exec.Command` / `exec.CommandContext` (tainted program, or shell `-c` payload) |
| HC-004 | Unsafe deserialize | `encoding/gob` `Decode` |
| HC-005 | SQL injection | `database/sql` `Query` / `QueryRow` / `Exec` + `*Context` + prepared-stmt `Prepare*` |
| HC-006 | SSRF | `net/http` `Get` / `NewRequest` without allowlist |
| HC-007 | Template injection | `html/template` bypass conversions (`template.HTML` casts) |

Source: a parameter typed `*net/http.Request`. Taint resolves
**interprocedurally** through helper functions, **value- and
pointer-receiver methods**, and **across packages** — Go modules
(`go.mod`, via `go list`) and loose multi-file inputs alike, with
violations attributed to the defining file. SQL precision is
type-driven: parameterized queries (`$1` placeholders) are clean,
string-concat / `fmt.Sprintf` queries are flagged.

Directory and whole-repo scans include `.go` automatically — point
the action at a path and Go and Python are analyzed in one pass (Go
is type-checked per package via `go list`, so real multi-package
modules scan correctly, not just single files).

Files Go itself excludes from the active build — behind a build tag
or cgo-only — are reported as **skipped**: not analyzed, not a false
failure. Skipped files are visible in text output, in the JSON
`skipped` array, and as SARIF execution notifications, and are never
silently treated as clean — a scan whose inputs were *all*
build-excluded analyzed nothing and exits non-zero (rc 3), so a CI
gate cannot read "everything skipped" as "code is clean".

This is a focused catalog (6 sinks) versus Python's 14 — the same
engine, deliberately scoped to the high-signal Go classes rather
than ported broad-and-shallow.

**Runner requirement:** the Go bridge is built on the runner, so the
`go` toolchain must be on `PATH`. GitHub-hosted `ubuntu-*` and
`macos-*` runners ship Go preinstalled — no setup step needed. On a
self-hosted or minimal runner without Go, add an `actions/setup-go`
step before this action; a `.go` scan with no toolchain fails
**loud** (`could not analyze Go: bridge unavailable`) — it never
silently passes Go code as clean. Python scanning is unaffected
either way.

## Why heatcheck

heatcheck is **taint-gated**: it reports only when provenance analysis
shows untrusted input reaching a sink that requires a sanitized value —
not when a call merely *looks* dangerous. Out of the box, no custom
rule writing:

| Capability | Bandit | Semgrep CE `p/security-audit` | heatcheck |
|---|---|---|---|
| Taint-gated reporting (not pattern/audit) | ✗ | ✗ | ✓ |
| Cross-file taint | ✗ | ✗ ¹ | ✓ ² |
| MCP decorator parameter sources | ✗ | ✗ | ✓ |
| SQLAlchemy Core `.execute()` FP narrowed | ✗ | ✗ | ✓ ³ |

¹ Per Semgrep's docs, Community Edition analysis is single-file.
² Cross-module: request handler → `from app.dao import X; X.create(...)`
→ `%`-formatted `cur.execute()` in the imported module, followed
end-to-end (v1.3.3). ³ `.execute(f"…")` on a SQLAlchemy Core
connection is no longer flagged when the bound value is safe (v1.3.3).

Columns reflect only Bandit and Semgrep CE `p/security-audit` exactly
as run in our internal OSS field campaign — **not** Semgrep Pro,
CodeQL, or Semgrep's taint mode. Reproducible artifacts, exact scope,
and the committed `anxolerd/dvpwa` cross-module SQLi regression test
are in [docs/methodology.md](docs/methodology.md).

## Examples

### Minimal — scan everything, fail the build on violations

```yaml
- uses: actions/checkout@v6
- uses: nchantarotwong/heatcheck-action@v1
```

### Scan specific directories

```yaml
- uses: actions/checkout@v6
- uses: nchantarotwong/heatcheck-action@v1
  with:
    paths: src api/handlers
```

### Advisory mode — surface findings without failing the build

Useful for adopting heatcheck on an existing codebase without
blocking PRs until the backlog is cleaned up.

```yaml
- uses: actions/checkout@v6
- uses: nchantarotwong/heatcheck-action@v1
  with:
    fail-on-violations: 'false'
```

### Reproducible CI — pin to a specific release

```yaml
- uses: actions/checkout@v6
- uses: nchantarotwong/heatcheck-action@v1.3.4   # immutable patch version
```

Pin to the exact patch version (e.g. `@v1.3.4`) instead of the floating
major (`@v1`) when you need byte-identical scan results across re-runs.

### Upload the HTML report as an artifact

```yaml
- uses: actions/checkout@v6
- uses: nchantarotwong/heatcheck-action@v1
  with:
    upload-report: 'true'
```

Then download from the run's Artifacts panel; it opens as a static
HTML page with one section per violation.

### Read the JSON in a downstream step

```yaml
- uses: actions/checkout@v6
- id: heatcheck
  uses: nchantarotwong/heatcheck-action@v1
  with:
    fail-on-violations: 'false'

- name: Post to Slack on violations
  if: steps.heatcheck.outputs.violations != '0'
  run: |
    jq '.violations[] | "\(.code) \(.file):\(.line) — \(.message)"' \
      "${{ steps.heatcheck.outputs.json-path }}"
```

See [examples/](examples/) for complete workflow files you can drop
into `.github/workflows/`.

## Using heatcheck without GitHub Actions

The scanner is a single standalone CLI binary; the GitHub Action is just a
wrapper that adds PR annotations and a workflow summary. Same binary
ships through three channels — pick whichever your CI prefers:

| Channel | Pin like | When to use |
|---------|----------|-------------|
| **Container** | `ghcr.io/nchantarotwong/heatcheck:v1.3.4` | GitLab, Jenkins, Azure DevOps, Buildkite, any container-capable CI. Pinnable by digest for supply-chain review. |
| **Binary release** | `heatcheck-{linux,darwin}-{x86_64,arm64}` from the [Releases page](https://github.com/nchantarotwong/heatcheck-action/releases) | CIs without container support, or air-gapped builds where you mirror the asset to internal storage. |
| **macOS installer** | `heatcheck-darwin-arm64.pkg` from the [Releases page](https://github.com/nchantarotwong/heatcheck-action/releases) | Local use on a Mac — signed, notarized, and stapled, so it installs `heatcheck` to `/usr/local/bin` with no Gatekeeper warning. (The bare `darwin` binary above is fine for `curl`/CI; the `.pkg` is for humans downloading via a browser.) |
| **This Action** | `nchantarotwong/heatcheck-action@v1.3.4` | GitHub Actions (you're reading its docs). |

Quick container example:

```sh
docker run --rm -v "$PWD:/src" ghcr.io/nchantarotwong/heatcheck:v1 --json .
```

Full guide with GitLab CI, Jenkins, generic Docker, pre-commit, and
SARIF setups: [docs/non-github-actions.md](docs/non-github-actions.md).

## Runner support

| Runner | Supported |
|--------|-----------|
| `ubuntu-latest` (x86_64) | ✓ |
| `ubuntu-24.04-arm` (arm64) | ✓ |
| `macos-latest` (arm64) | ✓ |
| `macos-13` (x86_64) | ✗ — no prebuilt binary for Darwin x86_64. Use `macos-14`+. |
| `windows-latest` | ✗ — bootstrap chain assumes a Unix shell. |

## How it runs

On a cache miss (first run for a given release tag on this runner), the
action:

1. Validates inputs + OS / arch.
2. Sets up Python via `actions/setup-python` (heatcheck calls
   CPython's `ast` module to parse Python). Go uses the runner's
   preinstalled `go` toolchain — see [Go support](#go-support); no
   setup step is added for it.
3. Resolves the heatcheck-action release tag from the action's own
   ref (e.g. `@v1.3.4` → `v1.3.4`).
4. Downloads `heatcheck-{linux|darwin}-{x86_64|arm64}` and its
   `.sha256` from the GitHub Release.
5. Verifies the SHA256 checksum.
6. Runs the binary on the configured paths.

Binaries are cached per-runner keyed by `version/os/arch`. Cold-cache
runs take ~10-20s (download + run); cached runs take ~5s.

## Permissions

The action does not need any `permissions:` block — it doesn't post
comments or push commits. Annotations are emitted via stdout
workflow commands, which work with the default token.

If you turn on `upload-report`, the artifact upload step uses
`actions/upload-artifact` which needs the default `actions: write`
permission (granted by default in public repos).

## Versioning

- `v1` — current stable major.
- `main` — bleeding edge, may break without notice. Don't pin to `main` in CI.

When `v2` ships, `v1` continues to receive bug fixes for a transition
window. Major-version bumps cover input/output schema changes only;
internal-only changes ship to `v1`.

## License

Apache 2.0. See [LICENSE](LICENSE).
