#!/usr/bin/env python3
"""Build the request body for GitHub Code Scanning's SARIF upload endpoint.

POST /repos/{owner}/{repo}/code-scanning/sarifs wants a JSON body with the
SARIF gzip+base64-encoded. This script reads a SARIF file, optionally
namespaces it under a Code Scanning category (so heatcheck coexists with other
SAST tools instead of clobbering their alerts), encodes it, and writes the
request body to --out.

Stdlib only. python3 is already required by heatcheck (it shells out to
CPython's `ast` module), so this adds no dependency beyond the scan itself —
and unlike jq it's guaranteed present, with correct JSON escaping.
"""
import argparse
import base64
import gzip
import json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sarif", required=True, help="path to the SARIF file")
    ap.add_argument("--out", required=True, help="path to write the request body JSON")
    ap.add_argument("--commit-sha", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--category", default="", help="Code Scanning category (automationDetails.id)")
    args = ap.parse_args()

    with open(args.sarif, "rb") as f:
        sarif = json.load(f)

    if args.category:
        cat = args.category if args.category.endswith("/") else args.category + "/"
        for run in sarif.get("runs", []):
            details = run.get("automationDetails") or {}
            details["id"] = cat
            run["automationDetails"] = details

    raw = json.dumps(sarif).encode("utf-8")
    encoded = base64.b64encode(gzip.compress(raw)).decode("ascii")
    body = {
        "commit_sha": args.commit_sha,
        "ref": args.ref,
        "sarif": encoded,
        "tool_name": "heatcheck",
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(body, f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
