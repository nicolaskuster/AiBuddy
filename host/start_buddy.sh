#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="$PWD"
IMAGE_NAME="ai-buddy"
CONTAINER_NAME="ai-buddy"

echo "▶ Starting container..."
docker run --rm -it \
  --name "$CONTAINER_NAME" \
  -v "$WORKSPACE:/workspace" \
  -v "ai-buddy-shared:/home/buddy/.ai-buddy" \
  "$IMAGE_NAME"
