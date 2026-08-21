#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE="$PWD"

echo "▶ Starting container..."
# The private NuGet feed authenticates with a GitHub token taken from the host's
# gh login. Passing it inline as -e means it never becomes an environment
# variable on the host and never reaches a container volume. NuGet reads
# NuGetPackageSourceCredentials_<source key> and expects a plaintext Password=
# there — ClearTextPassword= is only recognised inside NuGet.Config.
docker compose -f "$REPO_ROOT/docker-compose.yml" run --rm \
  -e "NuGetPackageSourceCredentials_galaxus_github=Username=ai-buddy;Password=$(gh auth token 2>/dev/null)" \
  -v "$WORKSPACE:/workspace" \
  agent
