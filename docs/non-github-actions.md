# Using heatcheck without GitHub Actions

heatcheck is a single standalone binary. The [GitHub Action wrapper](../README.md)
exists to make it pleasant in GHA — PR annotations, workflow summary,
artifact upload — but the binary works the same everywhere. If you're
on GitLab CI, Jenkins, Buildkite, Azure DevOps, a custom CI, or just
want to run it locally, you have two distribution channels:

- **Container image** (recommended) — `ghcr.io/nchantarotwong/heatcheck`,
  pinnable by tag or digest, no install script, works under any
  container-capable CI.
- **Direct binary download** — fetch the release asset, verify the
  sha256, run it.

Both come from the same release pipeline as the action wrapper, so
versions are byte-identical across channels.

## Container image

```sh
docker run --rm -v "$PWD:/src" \
  ghcr.io/nchantarotwong/heatcheck:v1 \
  --json . > heatcheck.json
```

- Image tags mirror the wrapper's releases: `v1.0.3` (immutable),
  `v1` (floating major), `latest` (latest stable, skips prereleases).
- Mount your repo at `/src` (the image's `WORKDIR`).
- Pass any flag the binary accepts — `--help` is the default `CMD`.
- Pin by digest in enterprise / supply-chain-sensitive environments:

  ```sh
  docker run --rm -v "$PWD:/src" \
    ghcr.io/nchantarotwong/heatcheck@sha256:<digest> \
    --json .
  ```

The image is `linux/amd64` + `linux/arm64`. Base is `debian:bookworm-slim`
(glibc 2.36, Python 3.11).

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Clean scan, no violations |
| `1` | Violations found |
| `2` | Usage / argument error |
| `64` | Internal scanner error |

Most CIs fail the job on any non-zero exit — that's the default
behavior. To make heatcheck advisory, run with `|| true` or check
exit code 0/1 explicitly.

## Direct binary download

If your CI doesn't do containers (or pulling from `ghcr.io` is
blocked), grab the binary from a release:

```sh
VERSION=v1.0.3
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64)  ASSET=heatcheck-linux-x86_64 ;;
  Linux/aarch64) ASSET=heatcheck-linux-arm64 ;;
  Darwin/arm64)  ASSET=heatcheck-darwin-arm64 ;;
  *) echo "unsupported platform" >&2; exit 1 ;;
esac

BASE="https://github.com/nchantarotwong/heatcheck-action/releases/download/${VERSION}"
curl -fsSL -o heatcheck       "${BASE}/${ASSET}"
curl -fsSL -o heatcheck.sha256 "${BASE}/${ASSET}.sha256"

# The .sha256 file references the asset name; rename so sha256sum -c
# can find the file it expects.
sed -i.bak "s|${ASSET}|heatcheck|" heatcheck.sha256
sha256sum -c heatcheck.sha256

chmod +x heatcheck
./heatcheck --version
```

heatcheck needs **Python 3.x on PATH** at runtime — it shells out to
CPython's `ast` module for parsing. Any 3.x will do (3.11 matches the
action wrapper's pin).

## SARIF output

> **Status:** SARIF emission lands in **heatcheck v1.1.0** (not yet
> released). The snippets below show how to wire it up; the
> `--sarif` flag will exit `2` on earlier versions. Track progress
> on the [releases page](https://github.com/nchantarotwong/heatcheck-action/releases).

[SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
is the OASIS-standard format for static-analysis results. Once
heatcheck v1.1.0 ships, the binary will emit SARIF that surfaces
natively in:

- GitLab Ultimate's SAST widget (MR pipeline reports)
- Azure DevOps SARIF SAST tasks
- SonarQube / SonarCloud external-issue ingestion
- GitHub Code Scanning (via `github/codeql-action/upload-sarif@v3`)
- Any tool that consumes SARIF (Defectdojo, Semgrep AppSec Platform,
  etc.)

Usage will look like:

```sh
heatcheck --sarif . > heatcheck.sarif
```

Each violation maps to a SARIF `result` with the heatcheck sink code
(`HC-005` etc.) as the `ruleId` and source/sink expressions in the
`message` and `locations` fields.

## GitLab CI

### Basic — fail the pipeline on violations

```yaml
heatcheck:
  stage: test
  image: ghcr.io/nchantarotwong/heatcheck:v1
  script:
    - heatcheck --json . > heatcheck.json
  artifacts:
    when: always
    paths:
      - heatcheck.json
    expire_in: 1 week
```

The image's entrypoint is the binary, so `image:` + `script: heatcheck ...`
works. Non-zero exit fails the job; the JSON report is uploaded as a
job artifact you can grab from the pipeline page.

### With SARIF — surface findings in the MR widget *(requires heatcheck v1.1.0+)*

GitLab Ultimate ingests SARIF as a `sast` report and renders findings
inline on the MR:

```yaml
heatcheck:
  stage: test
  image: ghcr.io/nchantarotwong/heatcheck:v1
  script:
    - heatcheck --sarif . > heatcheck.sarif
  artifacts:
    when: always
    reports:
      sast: heatcheck.sarif
    paths:
      - heatcheck.sarif
    expire_in: 1 week
```

Requires GitLab Ultimate (the `reports: sast:` keyword is gated to the
Ultimate tier). On Free / Premium, upload SARIF as a regular artifact
and use the GitLab REST API or a dashboard to surface it.

### Advisory mode

To run heatcheck without failing the pipeline:

```yaml
heatcheck:
  stage: test
  image: ghcr.io/nchantarotwong/heatcheck:v1
  script:
    - heatcheck --json . > heatcheck.json || true
  allow_failure: true   # belt + suspenders
  artifacts:
    when: always
    paths: [heatcheck.json]
```

## Jenkins

Declarative pipeline using the official `docker.image()` step:

```groovy
pipeline {
  agent any
  stages {
    stage('heatcheck') {
      steps {
        script {
          docker.image('ghcr.io/nchantarotwong/heatcheck:v1').inside('-v ${WORKSPACE}:/src') {
            sh 'heatcheck --json /src > heatcheck.json'
          }
        }
      }
      post {
        always {
          archiveArtifacts artifacts: 'heatcheck.json', allowEmptyArchive: true
        }
      }
    }
  }
}
```

If your Jenkins agents don't have Docker, fall back to the direct
binary download snippet above — drop it into a `sh` step at the start
of the stage.

For agents behind a corporate proxy or air-gapped from GHCR, mirror
the image to your internal registry once per release tag and pull
from there.

## Generic Docker / any other CI

The pattern is the same on Azure DevOps, CircleCI, Buildkite,
TeamCity, custom CIs — anywhere you can run a container:

```sh
docker run --rm \
  -v "${CI_WORKSPACE:-$PWD}:/src" \
  ghcr.io/nchantarotwong/heatcheck:v1 \
  --json . > heatcheck.json
```

For CIs without container support, use the direct binary download
snippet. Cache the binary keyed by `${VERSION}-${OS}-${ARCH}` so
re-runs don't re-download — the file is ~20–30 MB.

## Pre-commit / local development

Add heatcheck to [`pre-commit`](https://pre-commit.com/) so it runs on
every commit alongside your linters:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: heatcheck
        name: heatcheck (taint analysis)
        language: docker_image
        entry: ghcr.io/nchantarotwong/heatcheck:v1
        types: [python]
        pass_filenames: false
        args: ['--json', '.']
```

`pass_filenames: false` is intentional — heatcheck reasons across
files (provenance tracking) so it needs the whole tree, not just the
staged subset. The `types: [python]` clause skips the hook entirely
when no Python files changed.

For one-shot local runs without pre-commit:

```sh
docker run --rm -v "$PWD:/src" ghcr.io/nchantarotwong/heatcheck:v1 .
```

Drop `--json` for human-readable output.

## Troubleshooting

**`exec format error` on arm64 macOS via Docker Desktop.** You pulled
the amd64 image on Apple Silicon. Force the platform:
`docker pull --platform=linux/arm64 ghcr.io/nchantarotwong/heatcheck:v1`.

**`python: command not found` from heatcheck.** Only happens with the
direct binary, not the container. Install Python 3.x and ensure
`python3` is on PATH.

**Exit code 64 with no output.** Internal scanner error. File an
issue with the heatcheck version (`heatcheck --version`) and a
minimal reproducer.

**GHCR pull blocked by enterprise policy.** Mirror the image to your
internal registry:

```sh
docker pull   ghcr.io/nchantarotwong/heatcheck:v1.0.3
docker tag    ghcr.io/nchantarotwong/heatcheck:v1.0.3  internal.registry/security/heatcheck:v1.0.3
docker push   internal.registry/security/heatcheck:v1.0.3
```

Then point your CI at the internal mirror.
