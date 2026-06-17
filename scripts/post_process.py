#!/usr/bin/env python3
"""Post-process heatcheck --json output for GitHub Actions.

Emits:
  - ::error file=...,line=...,col=...,title=...::message annotations
    (one per violation; show up inline on the PR Files tab).
  - A markdown summary appended to $GITHUB_STEP_SUMMARY.

heatcheck reports absolute paths (the runner-side path inside the
checked-out workspace); annotations need workspace-relative paths so
GitHub can map them to the PR diff. We strip the workspace prefix
before printing.

Exits 0 always — the action's own gating logic decides whether to
fail the workflow.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def workspace_relative(path: str, workspace: str) -> str:
    """Return path as a workspace-relative POSIX path, or the original on mismatch."""
    if not workspace:
        return path
    try:
        rel = Path(path).resolve().relative_to(Path(workspace).resolve())
        return str(rel)
    except (ValueError, OSError):
        return path


def escape_annotation(text: str) -> str:
    """GitHub Workflow Command escaping for `::error::` body.

    Newlines must be %0A; %, CR, NL all encoded so multi-line bodies
    render correctly in the annotation panel.
    """
    return (
        text.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
    )


def emit_annotations(violations: list, workspace: str) -> None:
    for v in violations:
        if not isinstance(v, dict):
            continue
        file = workspace_relative(str(v.get("file", "?")), workspace)
        line = v.get("line", 1)
        col = v.get("column", 1)
        code = v.get("code", "HC-???")
        msg = v.get("message", "violation")
        fix = v.get("fix", "")
        source = v.get("source", {}) if isinstance(v.get("source"), dict) else {}
        sink = v.get("sink", {}) if isinstance(v.get("sink"), dict) else {}

        body_parts = [msg]
        if source.get("expr") or source.get("tag"):
            s_expr = source.get("expr", "")
            s_line = source.get("line", "")
            s_tag = source.get("tag", "")
            body_parts.append(f"source: {s_expr}  (line {s_line})  {s_tag}".rstrip())
        if sink.get("expr") or sink.get("required_tag"):
            k_expr = sink.get("expr", "")
            k_tag = sink.get("required_tag", "")
            body_parts.append(f"sink: {k_expr}  requires {k_tag}".rstrip())
        if fix:
            body_parts.append(f"fix: {fix}")

        body = escape_annotation("\n".join(body_parts))
        title = escape_annotation(str(code))
        print(f"::error file={file},line={line},col={col},title={title}::{body}")


def write_summary(path: str, data: dict, workspace: str) -> None:
    """Append a markdown summary to $GITHUB_STEP_SUMMARY."""
    if not isinstance(data, dict):
        data = {}
    violations = data.get("violations") or []
    parse_errors = data.get("parse_errors") or []
    files_analyzed = data.get("files_analyzed", 0)
    decision = data.get("decision")

    lines: list[str] = []
    lines.append("## heatcheck")
    lines.append("")
    if isinstance(decision, str) and decision:
        risk = data.get("risk_score", 0)
        new_findings = data.get("new_findings", len(violations))
        existing = data.get("existing_findings", 0)
        summary = data.get("summary", "")
        lines.append(f"Decision: **{decision}**")
        lines.append("")
        lines.append(f"Risk score: **{risk}**")
        lines.append("")
        lines.append(f"New findings: **{new_findings}**")
        lines.append("")
        lines.append(f"Existing baseline findings: **{existing}**")
        lines.append("")
        if summary:
            lines.append(str(summary))
            lines.append("")
    elif not violations and not parse_errors:
        lines.append(
            f"No violations across **{files_analyzed}** Python file(s) scanned."
        )
        lines.append("")
    elif not violations and parse_errors:
        lines.append(
            f"No violations across **{files_analyzed}** Python file(s) scanned. "
            f"**{len(parse_errors)}** file(s) failed to analyze (see below)."
        )
        lines.append("")
    else:
        lines.append(
            f"**{len(violations)}** violation(s) across **{files_analyzed}** Python file(s) scanned."
        )
        lines.append("")

    if violations:
        # Group by sink code.
        by_code: dict[str, int] = {}
        for v in violations:
            if not isinstance(v, dict):
                continue
            code = str(v.get("code", "HC-???"))
            by_code[code] = by_code.get(code, 0) + 1

        lines.append("### Violations by sink")
        lines.append("")
        lines.append("| Code | Count |")
        lines.append("|------|-------|")
        for code in sorted(by_code):
            lines.append(f"| `{code}` | {by_code[code]} |")
        lines.append("")

        lines.append("### Details")
        lines.append("")
        lines.append("| File | Line | Code | Message |")
        lines.append("|------|------|------|---------|")
        for v in violations:
            if not isinstance(v, dict):
                continue
            file = workspace_relative(str(v.get("file", "?")), workspace)
            line = v.get("line", "")
            code = v.get("code", "")
            msg = str(v.get("message", "")).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| `{file}` | {line} | `{code}` | {msg} |")
        lines.append("")

    if parse_errors:
        lines.append("### Files that failed to analyze")
        lines.append("")
        for e in parse_errors:
            if isinstance(e, dict):
                file = workspace_relative(str(e.get("file", "?")), workspace)
                reason = e.get("reason", "")
            else:
                file = workspace_relative(str(e), workspace)
                reason = ""
            if reason:
                lines.append(f"- `{file}` — {reason}")
            else:
                lines.append(f"- `{file}`")
        lines.append("")

    if path and path != "/dev/null":
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", required=True, help="Path to heatcheck JSON output.")
    ap.add_argument("--workspace", default="", help="$GITHUB_WORKSPACE for relative-path rewriting.")
    ap.add_argument("--summary", default="", help="Path to $GITHUB_STEP_SUMMARY (append target).")
    args = ap.parse_args()

    try:
        with open(args.json, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"::error::heatcheck output at {args.json} was not valid JSON: {e}", file=sys.stderr)
        return 0  # action gating handles the failure path

    violations = data.get("violations", [])
    emit_annotations(violations, args.workspace)
    write_summary(args.summary, data, args.workspace)
    return 0


if __name__ == "__main__":
    sys.exit(main())
