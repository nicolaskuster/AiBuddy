#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export USER_UID="$(id -u)"
export USER_GID="$(id -g)"

echo "⚙ Building AI Buddy (agent + proxy) with UID=$USER_UID and GID=$USER_GID..."
docker compose -f "$REPO_ROOT/docker-compose.yml" build --no-cache
