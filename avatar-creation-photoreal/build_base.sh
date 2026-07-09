#!/bin/bash
# =============================================================================
# Build & push the photoreal-avatar BASE image.
# RUN THIS ON A GPU POD (needs nvcc + an NVIDIA GPU), not on the Mac.
# =============================================================================
# On a RunPod GPU pod (an A6000 / L40S "PyTorch 2.3" pod with Docker, or a bare
# CUDA 12.1 box):
#   1. git clone the repo (or scp this folder up)
#   2. cd avatar-creation-photoreal
#   3. docker login                 # so the push works
#   4. bash build_base.sh push
#
# The build compiles three small CUDA exts (pointops, diff-gaussian-
# rasterization, simple-knn) and installs prebuilt wheels for the rest. Expect
# ~15-25 min the first time. There is NO 30-min cap here (that cap is only
# RunPod's GitHub auto-build farm, which we deliberately avoid for this image).
#
# Verify BEFORE a long build (cheap, catches the two known-risky URLs):
#   docker pull pytorch/pytorch:2.3.0-cuda12.1-cudnn8-devel   # base tag exists
#   # gsplat pt23cu121 find-links + torch_scatter find-links resolve (the
#   # Dockerfile already falls back to PyPI/JIT for gsplat if the wheel 404s).
# =============================================================================
set -e

IMAGE="revandiktas/tryon-photoreal-base"
TAG="${TAG:-latest}"
FULL="${IMAGE}:${TAG}"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  Building photoreal-avatar BASE image"
echo "  Image:   ${FULL}"
echo "  Context: ${DIR}"
echo "============================================"

docker build -f "${DIR}/Dockerfile.base" -t "${FULL}" "${DIR}"

if [ "$1" = "push" ]; then
  echo ">> pushing ${FULL}"
  docker push "${FULL}"
  echo ">> done. Use this as FROM in the serverless Dockerfile."
fi
