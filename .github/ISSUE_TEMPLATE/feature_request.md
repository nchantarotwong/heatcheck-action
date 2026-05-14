---
name: Feature request
about: Suggest a new detection, framework integration, output format, or workflow improvement
title: ''
labels: enhancement
assignees: nchantarotwong

---

**Request type** (pick the closest)
- [ ] New detection rule (new vulnerability class, new sink/source, new sanitizer)
- [ ] Framework integration (FastAPI / Flask / Django / Starlette / SQLAlchemy / etc.)
- [ ] Output format (SARIF variant, JSON shape, GitHub annotations, custom report)
- [ ] Config option (`.heatcheck.json` field, CLI flag, action input)
- [ ] Performance / scan speed
- [ ] Other (describe below)

**The use case**
Concrete code that motivates the request — the smallest snippet that shows what heatcheck isn't catching, or what it's flagging that you wish it wouldn't, or the workflow shape that's awkward today. For framework or output requests, paste the framework/spec snippet you want supported.

```python
# Or yaml/json/etc. as appropriate
```

**What heatcheck should do**
Describe the desired behavior. For new detections: which sources and sinks, what taint propagation pattern, what severity, the rule ID style (e.g. `HC-SSRF-002`). For frameworks: which routes/decorators/ORM patterns should be recognized. For output: the exact schema or example output you want.

**Alternatives you've tried**
- Existing heatcheck rules that partially cover this
- Other tools (Bandit, Semgrep, CodeQL, custom Semgrep packs) and what they do here
- Manual code review / linter patterns / type-system tricks
- What's insufficient about each — be specific (false positive rate, framework awareness gap, license, ergonomics, etc.)

**Fit + priority**
Briefly address:
- **Detection accuracy**: would this trade false positives for false negatives, or vice versa?
- **LLM patterns**: is this a class of bug LLMs ship more often than human-authored code? (Helps prioritize — closing LLM-pattern gaps is heatcheck's wedge.)
- **Scope**: a single rule, a framework integration, or a broader feature? The smaller the unit, the faster the turnaround.
- **Blocker level**: nice-to-have, important for adoption, or blocking a specific use case?

**Additional context**
Related CVEs, CWEs, PEPs, or framework docs. Links to similar findings in other security tools. Prior art for the proposed rule shape. Whether you're willing to contribute the rule yourself.
