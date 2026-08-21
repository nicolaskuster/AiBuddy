#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE="$PWD"
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"

echo "▶ Starting container..."
HOST_UID="$HOST_UID" HOST_GID="$HOST_GID" \
docker compose -f "$REPO_ROOT/docker-compose.yml" run --rm \
  -e "NuGetPackageSourceCredentials_galaxus_github=Username=ai-buddy;Password=$(gh auth token 2>/dev/null)" \
  -v "$WORKSPACE:/workspace" \
  agent
