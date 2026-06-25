#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="$PWD"
IMAGE_NAME="ai-buddy"

echo "▶ Starting container..."
docker run --rm -it \
  -v "$WORKSPACE:/workspace" \
  -v "ai-buddy-shared:/home/buddy/.ai-buddy" \
  -v "$HOME/.gitconfig:/home/buddy/.gitconfig:ro" \
  "$IMAGE_NAME"
