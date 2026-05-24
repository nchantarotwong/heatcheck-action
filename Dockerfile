# Container image for running heatcheck outside GitHub Actions.
# Built and pushed by .github/workflows/release.yml on tag push.
# Consumers should pull a tagged digest from
#   ghcr.io/nchantarotwong/heatcheck:<tag>
# rather than building this Dockerfile themselves.
#
# Multi-arch (linux/amd64 + linux/arm64). The binary is downloaded
# from the heatcheck-action release matching HEATCHECK_VERSION and
# its companion .sha256 is verified before install.
#
# Base: debian:bookworm-slim ships glibc 2.36 + Python 3.11, which
# matches what the action.yml-managed runner provides. heatcheck
# shells out to CPython's `ast` module for parsing, so `python3` must
# be on PATH at runtime.

FROM debian:bookworm-slim

ARG TARGETARCH
ARG HEATCHECK_VERSION

# Runtime deps. The binary is dynamically linked against libxml2 and
# libsqlite3 (release.yml builds against libxml2-dev / libsqlite3-dev);
# the slim base doesn't ship either, so the binary fails to load
# without them. libcurl4 and zlib1g come in via `curl` / base.
# `python3` is required at scan time — heatcheck shells out to
# CPython's ast module for parsing.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      libsqlite3-0 \
      libxml2 \
      python3 \
 && rm -rf /var/lib/apt/lists/* \
 && ln -s /usr/bin/python3 /usr/local/bin/python

RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64) ASSET=heatcheck-linux-x86_64 ;; \
      arm64) ASSET=heatcheck-linux-arm64 ;; \
      *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    if [ -z "${HEATCHECK_VERSION:-}" ]; then \
      echo "HEATCHECK_VERSION build-arg is required (e.g. v1.0.2)" >&2; exit 1; \
    fi; \
    BASE="https://github.com/nchantarotwong/heatcheck-action/releases/download/${HEATCHECK_VERSION}"; \
    cd /tmp; \
    curl --fail --silent --show-error --location --retry 3 --retry-delay 2 \
         -o "${ASSET}"        "${BASE}/${ASSET}"; \
    curl --fail --silent --show-error --location --retry 3 --retry-delay 2 \
         -o "${ASSET}.sha256" "${BASE}/${ASSET}.sha256"; \
    sha256sum -c "${ASSET}.sha256"; \
    install -m 0755 "${ASSET}" /usr/local/bin/heatcheck; \
    rm "${ASSET}" "${ASSET}.sha256"; \
    /usr/local/bin/heatcheck --version

WORKDIR /src

LABEL org.opencontainers.image.title="heatcheck" \
      org.opencontainers.image.description="Static taint analysis for AI-generated Python — SQLi, command/code injection, SSRF, path traversal, XXE, template injection; incl. untrusted model/LLM output flowing to a sink." \
      org.opencontainers.image.source="https://github.com/nchantarotwong/heatcheck-action" \
      org.opencontainers.image.documentation="https://github.com/nchantarotwong/heatcheck-action/blob/main/docs/non-github-actions.md" \
      org.opencontainers.image.licenses="Apache-2.0"

ENTRYPOINT ["/usr/local/bin/heatcheck"]
CMD ["--help"]
