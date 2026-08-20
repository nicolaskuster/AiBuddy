#!/bin/bash
set -euo pipefail

# Runs as root so it can update the system trust store, then drops to the
# non-root buddy user for the actual session (see docker-compose.yml and the
# Dockerfile for how the CA cert gets here).
CA_SRC=/run/ai-buddy-ca/ai-buddy-ca.crt
CA_DST=/usr/local/share/ca-certificates/ai-buddy-ca.crt

if [ ! -s "$CA_SRC" ]; then
  echo "error: ai-buddy proxy CA not found at $CA_SRC" >&2
  exit 1
fi

if ! cmp -s "$CA_SRC" "$CA_DST" 2>/dev/null; then
  cp "$CA_SRC" "$CA_DST"
  update-ca-certificates >/dev/null
fi

exec runuser -u buddy -- "$@"
