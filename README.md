# heatcheck-action

[![test](https://github.com/nchantarotwong/heatcheck-action/actions/workflows/test.yml/badge.svg)](https://github.com/nchantarotwong/heatcheck-action/actions/workflows/test.yml)
[![release](https://img.shields.io/github/v/release/nchantarotwong/heatcheck-action)](https://github.com/nchantarotwong/heatcheck-action/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

> Block the injection bugs LLMs ship past green tests — static taint
> analysis for Python, covering SQLi, command injection, SSRF, path
> traversal, XXE, and template injection.

heatcheck walks a Python project's AST, traces provenance through
assignments, returns, and tuple-unpacks, and reports cases where
attacker-controlled input reaches a sink that requires a sanitized
value. Built around how LLMs actually fail — not generic Python lint.

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
| `heatcheck-version` | (action ref) | Release tag whose binary to download. Defaults to the action's own ref — `uses: ...@v1.1.0` downloads the `v1.1.0` binary. Override only to pin the binary independently of the wrapper. |
| `python-version` | `3.11` | Python version on PATH (heatcheck calls CPython's `ast` module). |
| `upload-report` | `false` | Upload `.heatcheck/report.html` as a workflow artifact for browsing. |
| `timeout-seconds` | `600` | Per-run timeout for the heatcheck binary. |

## Outputs

| Output | Description |
|--------|-------------|
| `violations` | Number of violations across all scanned files. `-1` on internal failure (no JSON produced). |
| `json-path` | Path to the raw JSON report on the runner filesystem. Use it in downstream steps that need to parse violations programmatically. |

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
- uses: nchantarotwong/heatcheck-action@v1.1.0   # immutable patch version
```

Pin to the exact patch version (e.g. `@v1.1.0`) instead of the floating
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

The scanner is a single static binary; the GitHub Action is just a
wrapper that adds PR annotations and a workflow summary. Same binary
ships through three channels — pick whichever your CI prefers:

| Channel | Pin like | When to use |
|---------|----------|-------------|
| **Container** | `ghcr.io/nchantarotwong/heatcheck:v1.1.0` | GitLab, Jenkins, Azure DevOps, Buildkite, any container-capable CI. Pinnable by digest for supply-chain review. |
| **Binary release** | `heatcheck-{linux,darwin}-{x86_64,arm64}` from the [Releases page](https://github.com/nchantarotwong/heatcheck-action/releases) | CIs without container support, or air-gapped builds where you mirror the asset to internal storage. |
| **This Action** | `nchantarotwong/heatcheck-action@v1.1.0` | GitHub Actions (you're reading its docs). |

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
   CPython's `ast` module for parsing).
3. Resolves the heatcheck-action release tag from the action's own
   ref (e.g. `@v1.1.0` → `v1.1.0`).
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
