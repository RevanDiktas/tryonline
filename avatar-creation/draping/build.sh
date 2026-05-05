#!/bin/bash
# =============================================================
# Build & Push Draping Service Docker Image
# =============================================================
# Usage:
#   ./build.sh                    # build only (local test)
#   ./build.sh push               # build + push to DockerHub
#   ./build.sh push ghcr          # build + push to GitHub Container Registry
#
# Prerequisites:
#   - Docker Desktop running
#   - For push: docker login (DockerHub) or docker login ghcr.io (GitHub)
#
# RunPod Setup:
#   After pushing, create a new Serverless Endpoint in RunPod:
#   1. Go to runpod.io → Serverless → New Endpoint
#   2. Container Image: revandiktas/tryon-draping:latest (or ghcr.io/...)
#   3. GPU: Any (even 16GB is enough for geometric fallback)
#   4. Min Workers: 0, Max Workers: 3
#   5. Idle Timeout: 5s (fast scale-down, pay-per-use)
#   6. Copy the Endpoint ID → set RUNPOD_DRAPING_ENDPOINT_ID on Railway
# =============================================================

set -e

IMAGE_NAME="revandiktas/tryon-draping"
TAG="latest"
FULL_TAG="${IMAGE_NAME}:${TAG}"
GHCR_TAG="ghcr.io/revandiktas/tryon-draping:${TAG}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  Building Draping Service Docker Image"
echo "============================================"
echo "  Image:   ${FULL_TAG}"
echo "  Context: ${SCRIPT_DIR}"
echo "============================================"

docker build -t "${FULL_TAG}" "${SCRIPT_DIR}"

echo ""
echo "Build complete: ${FULL_TAG}"
echo ""

if [ "$1" = "push" ]; then
    if [ "$2" = "ghcr" ]; then
        echo "Tagging for GitHub Container Registry..."
        docker tag "${FULL_TAG}" "${GHCR_TAG}"
        echo "Pushing to ghcr.io..."
        docker push "${GHCR_TAG}"
        echo ""
        echo "Pushed: ${GHCR_TAG}"
        echo "Use this in RunPod: ${GHCR_TAG}"
    else
        echo "Pushing to DockerHub..."
        docker push "${FULL_TAG}"
        echo ""
        echo "Pushed: ${FULL_TAG}"
        echo "Use this in RunPod: ${FULL_TAG}"
    fi
    echo ""
    echo "Next: Create RunPod Serverless Endpoint with this image."
fi
