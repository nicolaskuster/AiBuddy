#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE="$PWD"

COMPOSE=(docker compose -f "$REPO_ROOT/docker-compose.yml")

if [ ! -f "$REPO_ROOT/.env" ]; then
  echo "⚠ No .env found at $REPO_ROOT/.env - copy .env.example to .env and add your secrets." >&2
  echo "  Continuing without it; Claude Code will start but real API calls will fail." >&2
fi

echo "▶ Ensuring proxy is running..."
"${COMPOSE[@]}" up -d proxy

echo "▶ Starting container..."
"${COMPOSE[@]}" run --rm \
  -v "$WORKSPACE:/workspace" \
  -v "$HOME/.gitconfig:/home/buddy/.gitconfig:ro" \
  agent
