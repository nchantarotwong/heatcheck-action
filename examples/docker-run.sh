#!/usr/bin/env bash
# Run heatcheck on the current directory via the official container.
# Works in any CI with a docker daemon — Azure DevOps, CircleCI,
# Buildkite, TeamCity, custom CI. Also fine for one-shot local runs.
#
# Exit codes:
#   0  - clean scan
#   1  - violations found
#   2  - usage / argument error
#   64 - internal scanner error
#
# Most CIs fail the job on any non-zero exit; replace `:v1` with a
# specific patch tag (e.g. `:v1.3.4`) or digest for reproducible runs.

set -euo pipefail

docker run --rm \
  -v "${CI_WORKSPACE:-$PWD}:/src" \
  ghcr.io/nchantarotwong/heatcheck:v1 \
  --json . > heatcheck.json
