# Methodology & evidence

This document backs the comparative claims in the README. It records
exactly what was run, what is independently reproducible, and — just
as important — what is **not** claimed.

## Scope and honesty

The figures referenced in the README ("OSS field campaign", precision
vs. advisory volume) come from an **internal** scanning campaign over
a set of open-source Python projects. That campaign's running
scoreboard is a hand-maintained internal artifact (it interleaves
pre- and post-disclosure context for filed advisories) and is **not**
published wholesale. What *is* published here is the methodology plus
a fully public, self-contained reproduction of the headline claim.

We measured heatcheck against exactly one external ruleset:
**Semgrep Community Edition `p/security-audit`**. That is an *audit*
ruleset — broad, pattern-oriented, deliberately high-recall. It is
**not** Semgrep's taint mode, and **not** Semgrep Pro (whose
cross-file/interfile dataflow is a paid capability; Semgrep's own
documentation notes Community Edition analysis is single-file). We
did **not** benchmark Semgrep taint mode, Semgrep Pro, CodeQL, Snyk,
Sonar, or Bearer. No claim in the README should be read as covering
tools or modes we did not run.

## Tools and versions

| Tool | Version / ruleset |
|---|---|
| heatcheck | container `ghcr.io/nchantarotwong/heatcheck` (≥ `v1.3.2` for the cross-module claim) |
| Semgrep | Community Edition, `--config p/security-audit`, default settings |
| Target | `anxolerd/dvpwa` (Damn Vulnerable Python Web App) — a deliberately-vulnerable training app |

## Publicly reproducible: the cross-module claim

Anyone can verify the headline differentiator end-to-end with public
artifacts only (the published heatcheck container + Semgrep CE).
`anxolerd/dvpwa` contains a request-handler → imported-DAO →
`%`-formatted `cur.execute()` SQL-injection that crosses files
(`sqli/views.py` → `sqli/dao/student.py`).

```sh
git clone --depth 1 https://github.com/anxolerd/dvpwa.git

# heatcheck (>= v1.3.2): reports the cross-module SQLi
docker run --rm -v "$PWD/dvpwa:/src" \
  ghcr.io/nchantarotwong/heatcheck:v1.3.2 --json /src \
  | python3 -c 'import json,sys; v=json.load(sys.stdin)["violations"]; print([f"{x[\"code\"]} {x[\"file\"].split(\"/\")[-1]}:{x[\"line\"]}" for x in v])'
# → ['HC-005 student.py:45']

# Semgrep Community Edition, p/security-audit: no findings on the same code
docker run --rm -v "$PWD/dvpwa:/src" returntocorp/semgrep:latest \
  semgrep --config=p/security-audit --json --quiet /src/sqli \
  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["results"]), "findings")'
# → 0 findings
```

heatcheck reaches this only with the full v1.3.0–v1.3.2 chain
(request-bag aliasing → `ClassName.staticmethod` resolution →
absolute-package-import resolution). Semgrep CE returns zero because
its analysis is single-file. This is the only cross-tool claim the
README makes, and it is the one fully reproducible above.

> dvpwa is intentionally vulnerable and documents its own bugs — it
> is a *validation* target, not an undisclosed finding. Nothing here
> is being responsibly disclosed; the only real-world true positives
> from the campaign were filed as GHSAs (Gradio
> `GHSA-fr87-3xv6-8vg8`, Open Interpreter `GHSA-xfh8-8242-vfv3`).

## Internal CI assurance

Beyond the public reproduction, the scanner's own test suite carries
a regression corpus that pins this behavior so it cannot silently
regress: a hard GUARD for the dvpwa cross-module SQLi, plus
false-negative guards proving the SQLAlchemy-session narrowing does
**not** suppress real raw-SQL injection (`cursor.execute("..."+u)`
and `session.execute(text(f"...{u}"))` still fire). That corpus lives
with the scanner source, not in this action repo.

## What is NOT claimed

- No benchmark numbers are presented as a peer-reviewable result.
  "Precision over advisory volume" is a qualitative observation from
  the internal campaign, scoped to Semgrep CE `p/security-audit`.
- No claim about Semgrep taint mode, Semgrep Pro, CodeQL, Snyk,
  Sonar, Bearer, or any tool/mode we did not run.
- "MCP source modeling": we state only that we found no MCP
  tool-parameter source modeling in Bandit, CodeQL's documented
  Python built-in queries, or Semgrep CE `p/security-audit` during
  the campaign — not that no SAST tool anywhere models it.
