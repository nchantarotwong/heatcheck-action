---
name: Bug report
about: heatcheck flagged the wrong thing, missed a real issue, or didn't run
title: ''
labels: bug
assignees: nchantarotwong

---

**Bug type** (pick the closest)
- [ ] False positive — heatcheck flagged code that is actually safe
- [ ] False negative — heatcheck missed a real vulnerability
- [ ] Wrong location — finding points at the wrong file / line / snippet
- [ ] Crash / scan error — heatcheck exited non-zero, panicked, or hung
- [ ] Framework awareness — incorrect routing of sources/sinks for a specific framework (FastAPI / Flask / Django / etc.)
- [ ] CI integration — the GitHub Action itself misbehaved (install, exit code, SARIF upload, comment, etc.)
- [ ] Other (describe below)

**Minimal repro**
The smallest Python snippet (or repo URL) that triggers the bug. Trim imports and unrelated helpers — the smaller the repro, the faster the fix.

```python
# Paste the code here. Mark the line you think heatcheck should/shouldn't flag.
```

If applicable, the config you ran with (`.heatcheck.json` contents) — heatcheck respects opt-in framework hints, severity filters, and ignore-paths from this file, and behavior changes meaningfully with config.

**Command + output**
What you ran (CLI flags, Action `with:` block) and the full output. For False Positive / False Negative / Wrong Location, paste the relevant finding verbatim — the rule ID (e.g. `HC-SQL-001`), the highlighted snippet, the location heatcheck printed. For Crash / Scan error, paste stderr and the exit code.

```
$ heatcheck scan path/to/code
... paste output here ...
```

**Expected behavior**
What heatcheck *should* have done. For False Positive: why the flagged code is safe (which sanitizer / framework guarantee / type discipline makes it OK). For False Negative: what the real vulnerability is and where you'd expect it flagged. For Wrong Location: where the finding should have pointed.

**Environment**
- heatcheck version: [output of `heatcheck --version`, or the Action ref you used like `nchantarotwong/heatcheck-action@v1`]
- Install method: [release binary | `bash scripts/install.sh` (source) | GitHub Action | Docker]
- OS: [macOS Sonoma 14.4 | Ubuntu 22.04 GH-hosted | Alpine 3.19 Docker | etc.]
- Python version of the code being scanned: [output of `python3 --version`]
- Framework (if relevant): [FastAPI 0.104 | Django 4.2 | Flask 3.0 | no framework | etc.]

**Additional context**
Anything else that helps:
- What you tried already (different config flags, scanning subsets, downgrading version)
- Whether this used to work (commit / version where it did)
- If it's framework-specific, the route definition or model that triggers it
- Cross-reference to a CVE, CWE, or similar tool's finding if the comparison is useful
- Whether the code was LLM-authored, and which model (helps us tune detections to the patterns LLMs ship)
