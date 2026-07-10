#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE=(docker compose -f "$REPO_ROOT/docker-compose.yml")
WORKSPACE="$PWD"

echo "▶ Starting container..."
"${COMPOSE[@]}" run --rm \
  -v "$WORKSPACE:/workspace" \
  -v "$HOME/.gitconfig:/home/buddy/.gitconfig:ro" \
  agent
