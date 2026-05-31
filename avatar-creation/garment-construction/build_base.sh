#!/bin/bash
# =============================================================================
# Build & push the garment-construction BASE image.
# RUN THIS ON A GPU POD (needs nvcc + an NVIDIA GPU), not on the Mac.
# =============================================================================
# On a RunPod GPU pod (e.g. an A6000/L40S "PyTorch 2.1" pod with Docker, or a
# bare CUDA box):
#   1. git clone your repo (or scp this folder up)
#   2. cd avatar-creation/garment-construction
#   3. docker login        # so the push works
#   4. bash build_base.sh push
#
# The build compiles the Warp fork + (maybe) flash-attn — expect 30-60 min the
# first time. There is NO 30-min cap here (that cap is only RunPod's GitHub
# auto-build farm, which we are deliberately avoiding for this image).
# =============================================================================
set -e

IMAGE="revandiktas/tryon-garment-base"
TAG="${TAG:-latest}"
FULL="${IMAGE}:${TAG}"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  Building garment-construction BASE image"
echo "  Image:   ${FULL}"
echo "  Context: ${DIR}"
echo "============================================"

docker build -f "${DIR}/Dockerfile.base" -t "${FULL}" "${DIR}"

if [ "$1" = "push" ]; then
  echo ">> pushing ${FULL}"
  docker push "${FULL}"
  echo ">> done. Use this as FROM in the serverless Dockerfile."
fi
