#!/usr/bin/env bash
set -euo pipefail

# This script runs as the non-root user (see entrypoint.sh, which drops
# privileges via gosu before exec'ing this).

# ── Trust the egress proxy's CA for tools with their own trust store ───────
# update-ca-certificates (run as root in entrypoint.sh) covers system-wide
# consumers (curl, git, .NET/NuGet via OpenSSL). Node-based tools (Claude
# Code, OpenCode) and a few others need to be told explicitly.
CA_CERT_FILE="/usr/local/share/ca-certificates/ai-buddy/ai-buddy-ca.crt"
if [ -f "$CA_CERT_FILE" ]; then
  export NODE_EXTRA_CA_CERTS="$CA_CERT_FILE"
  export SSL_CERT_FILE="$CA_CERT_FILE"
  export REQUESTS_CA_BUNDLE="$CA_CERT_FILE"
  export CURL_CA_BUNDLE="$CA_CERT_FILE"
  export GIT_SSL_CAINFO="$CA_CERT_FILE"
fi

# ── Claude: placeholder credential, never a real secret ─────────────────────
# Claude Code needs *some* ANTHROPIC_API_KEY to skip the interactive login
# prompt. This container never holds the real key - the egress proxy
# (container/proxy) injects it into requests to api.anthropic.com. Whatever
# value ends up here is irrelevant and is never sent upstream unmodified.
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-proxy-managed-placeholder}"

# ── Claude: link persistent (non-secret) config from volume ─────────────────
CLAUDE_CONFIG_SOURCE="$HOME/.ai-buddy/.claude.json"
CLAUDE_CONFIG_TARGET="$HOME/.claude.json"

mkdir -p "$(dirname "$CLAUDE_CONFIG_SOURCE")"
mkdir -p "$(dirname "$CLAUDE_CONFIG_TARGET")"
if [ ! -f "$CLAUDE_CONFIG_SOURCE" ]; then
  printf '{}\n' > "$CLAUDE_CONFIG_SOURCE"
fi

ln -sfn "$CLAUDE_CONFIG_SOURCE" "$CLAUDE_CONFIG_TARGET"

CLAUDE_DIR_SOURCE="$HOME/.ai-buddy/.claude"
CLAUDE_DIR_TARGET="$HOME/.claude"

# On first run (empty volume), seed from the image's initial .claude directory
if [ ! -d "$CLAUDE_DIR_SOURCE" ] || [ -z "$(ls -A "$CLAUDE_DIR_SOURCE" 2>/dev/null)" ]; then
  mkdir -p "$CLAUDE_DIR_SOURCE"
  if [ -d "$CLAUDE_DIR_TARGET" ] && [ ! -L "$CLAUDE_DIR_TARGET" ]; then
    cp -a "$CLAUDE_DIR_TARGET/." "$CLAUDE_DIR_SOURCE/"
  fi
fi

# Replace the real directory (from the image layer) with a symlink to the volume
if [ -d "$CLAUDE_DIR_TARGET" ] && [ ! -L "$CLAUDE_DIR_TARGET" ]; then
  rm -rf "$CLAUDE_DIR_TARGET"
fi
ln -sfn "$CLAUDE_DIR_SOURCE" "$CLAUDE_DIR_TARGET"

# NOTE: Claude Code runs in API-key mode (ANTHROPIC_API_KEY above), so it
# never writes real OAuth credentials into .claude/ - only non-secret state
# (settings, project trust decisions, etc.) ends up in this volume. If this
# is ever switched back to an interactive `claude /login` (Pro/Max OAuth)
# flow, .claude/ would hold a real secret again and this needs revisiting.

# ── Opencode: link persistent auth from volume ──────────────────────────────
# NOT YET covered by the egress proxy - this can still be a real secret
# (e.g. GitHub Copilot). See README "Security & network architecture".
OPENCODE_AUTH_SOURCE="$HOME/.ai-buddy/opencode-auth.json"
OPENCODE_AUTH_TARGET="$HOME/.local/share/opencode/auth.json"

mkdir -p "$(dirname "$OPENCODE_AUTH_SOURCE")"
mkdir -p "$(dirname "$OPENCODE_AUTH_TARGET")"
if [ ! -f "$OPENCODE_AUTH_SOURCE" ]; then
  printf '{}\n' > "$OPENCODE_AUTH_SOURCE"
fi

ln -sfn "$OPENCODE_AUTH_SOURCE" "$OPENCODE_AUTH_TARGET"

# ── Handoff: run the container command ──────────────────────────────────────
exec "$@"
