# Security Policy

## Reporting a Vulnerability

If you've discovered a security issue in heatcheck, the heatcheck-action
wrapper, or any related component, please report it through one of the
private channels below — in preference order:

1. **GitHub Security Advisory** (preferred):
   https://github.com/nchantarotwong/heatcheck-action/security/advisories/new
   — guided form, encrypted, automatically loops in the maintainer.
2. **Email**: **security@heatcheck.dev** — for reporters who can't or
   don't want to use GitHub.

Include:

- A description of the vulnerability and its potential impact
- A minimal reproduction (Python source, action input, expected vs. actual
  behavior — whichever applies)
- The version of heatcheck-action and the underlying heatcheck binary
  (visible in the action's CI log output)

Please do **not** report security issues in public GitHub issues, pull
requests, or Discussions. Public disclosure before a fix is shipped puts
heatcheck users at risk.

## Response Expectations

- Initial acknowledgement within **3 business days**
- Triage and severity assessment within **7 business days**
- Coordinated disclosure: we aim to ship a fix within **90 days** of report,
  or sooner for high-severity issues
- Reporters are credited in the fix's release notes unless they request
  anonymity

## In Scope

- False negatives in heatcheck's sink detection (a real vulnerability
  pattern that heatcheck silently passes)
- Crashes, infinite loops, or denial-of-service triggered by malicious
  input files
- Issues in the GitHub Action wrapper (action.yml, post-process scripts)
- Issues in the release-build supply chain (compromise of CI, asset
  tampering, etc.)

## Out of Scope

- False positives in heatcheck's sink detection (file an Issue instead —
  these are correctness bugs, not security bugs)
- Issues in third-party dependencies used by the runtime, unless they are
  exploitable through heatcheck's specific use of them
- Scanning your own deliberately-vulnerable code with heatcheck and
  reporting that heatcheck flagged it (working as intended)
