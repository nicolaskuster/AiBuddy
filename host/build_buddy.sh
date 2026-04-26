#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="ai-buddy"

echo "⚙ Building AI Buddy with UID=$(id -u) and GID=$(id -g)..."
docker build \
  -f "$REPO_ROOT/docker/Dockerfile" \
  --build-arg USER_UID="$(id -u)" \
  --build-arg USER_GID="$(id -g)" \
  --no-cache \
  -t "$IMAGE_NAME" \
  "$REPO_ROOT"
