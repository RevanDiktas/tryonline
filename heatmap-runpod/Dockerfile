# RunPod Serverless (GitHub integration): heatmap worker — Garment-Warp + RunPod handler.
#
# Use a NORMAL path/name: heatmap-runpod/Dockerfile  (some RunPod flows choke on odd filenames.)
# Build context: repository root (.)
#
# Local: docker build --platform linux/amd64 -f heatmap-runpod/Dockerfile -t tryonline-heatmap .
#
# Public Docker Hub base (RunPod docs: avoid private registries; runpod/* pulls may fail on builders).

FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-devel

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    git-lfs \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV CUDA_HOME=/usr/local/cuda
ENV CUDA_PATH=/usr/local/cuda

ARG GARMENT_WARP_REF=main

WORKDIR /opt
# Lower peak RAM during native/CUDA compile (helps GH Actions; safe on RunPod builders too).
ENV MAKEFLAGS=-j2
ENV CMAKE_BUILD_PARALLEL_LEVEL=2

RUN git lfs install \
    && git clone https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode.git \
    && cd NvidiaWarp-GarmentCode \
    && git checkout ${GARMENT_WARP_REF} \
    && git lfs pull \
    && if [ -d tools/packman ]; then find tools/packman -type f -exec chmod a+x {} +; fi \
    && python build_lib.py --cuda_path=/usr/local/cuda \
    && pip install --no-cache-dir -e .

WORKDIR /workspace
COPY heatmap-worker/requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r /workspace/requirements.txt

# Flat layout: one process, normal imports (no handler → scripts/ path hack).
COPY heatmap-worker/handler.py heatmap-worker/worker_core.py heatmap-worker/load_assets.py /workspace/

ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "/workspace/handler.py"]
