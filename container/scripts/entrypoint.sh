#!/usr/bin/env bash
set -euo pipefail

# ── Trust the egress proxy's CA certificate (system-wide) ──────────────────
#
# The proxy (see docker-compose.yml / container/proxy) terminates TLS for
# selected hosts to inject secrets that this container never holds itself.
# For that to work without every tool throwing certificate errors, this
# container needs to trust the proxy's CA. The public certificate is shared
# read-only via the `ai-buddy-proxy-ca` volume - the private key never
# leaves the proxy container.
#
# Debian's update-ca-certificates already scans this exact directory for
# custom CAs, so no copying is required here.
CA_CERT_FILE="/usr/local/share/ca-certificates/ai-buddy/ai-buddy-ca.crt"

if [ -f "$CA_CERT_FILE" ]; then
  update-ca-certificates >/dev/null || echo "⚠ ai-buddy: update-ca-certificates failed" >&2
else
  echo "⚠ ai-buddy: proxy CA certificate not found at $CA_CERT_FILE - HTTPS calls through the proxy will fail." >&2
  echo "  Make sure the 'proxy' service is up (docker compose up -d proxy) before starting the agent." >&2
fi

# ── Drop privileges and continue as the non-root user ───────────────────────
# This container starts as root only for the update-ca-certificates step
# above. Everything else runs as ${USER_NAME} (see entrypoint-user.sh).
exec gosu "${USER_NAME:-buddy}" /usr/local/bin/entrypoint-user.sh "$@"
