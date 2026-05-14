#!/usr/bin/env bash
set -euo pipefail

# ── Claude: link persistent config from volume ────────────────────────────────
CLAUDE_CONFIG_SOURCE="$HOME/.ai-buddy/.claude.json"
CLAUDE_CONFIG_TARGET="$HOME/.claude.json"

mkdir -p "$(dirname "$CLAUDE_CONFIG_SOURCE")"
mkdir -p "$(dirname "$CLAUDE_CONFIG_TARGET")"
if [ ! -f "$CLAUDE_CONFIG_SOURCE" ]; then
  printf '{}\n' > "$CLAUDE_CONFIG_SOURCE"
fi

ln -sfn "$CLAUDE_CONFIG_SOURCE" "$CLAUDE_CONFIG_TARGET"

CLAUDE_CREDENTIALS_SOURCE="$HOME/.ai-buddy/.claude/.credentials.json"
CLAUDE_CREDENTIALS_TARGET="$HOME/.claude/.credentials.json"

mkdir -p "$(dirname "$CLAUDE_CREDENTIALS_SOURCE")"
mkdir -p "$(dirname "$CLAUDE_CREDENTIALS_TARGET")"
if [ ! -f "$CLAUDE_CREDENTIALS_SOURCE" ]; then
  printf '{}\n' > "$CLAUDE_CREDENTIALS_SOURCE"
  chmod 600 $CLAUDE_CREDENTIALS_SOURCE 
fi

ln -sfn "$CLAUDE_CREDENTIALS_SOURCE" "$CLAUDE_CREDENTIALS_TARGET"

# ── Opencode: link persistent auth from volume ────────────────────────────────
OPENCODE_AUTH_SOURCE="$HOME/.ai-buddy/opencode-auth.json"
OPENCODE_AUTH_TARGET="$HOME/.local/share/opencode/auth.json"

mkdir -p "$(dirname "$OPENCODE_AUTH_SOURCE")"
mkdir -p "$(dirname "$OPENCODE_AUTH_TARGET")"
if [ ! -f "$OPENCODE_AUTH_SOURCE" ]; then
  printf '{}\n' > "$OPENCODE_AUTH_SOURCE"
fi

ln -sfn "$OPENCODE_AUTH_SOURCE" "$OPENCODE_AUTH_TARGET"

# ── Handoff: run the container command ────────────────────────────────────────
exec "$@"
