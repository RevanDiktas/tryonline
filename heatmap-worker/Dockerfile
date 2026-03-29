# Heatmap worker (Phase 0.5): NVIDIA Warp fork from GarmentCode + GPU smoke.
# Build context: THIS DIRECTORY ONLY (heatmap-worker/) — keeps RunPod context small.
# Local:  docker build -f heatmap-worker/Dockerfile heatmap-worker/
# RunPod: use heatmap-runpod/Dockerfile + repo-root context (see docs/research/RUNPOD_HEATMAP_BUILD_RESEARCH.md).
#
# First build can take a long time (compiles Warp native libs + optional LLVM stack).

FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-devel

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    git-lfs \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV CUDA_HOME=/usr/local/cuda
ENV CUDA_PATH=/usr/local/cuda

# Pin the fork to a commit for reproducible builds (update intentionally).
ARG GARMENT_WARP_REF=main

WORKDIR /opt
RUN git lfs install \
    && git clone https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode.git \
    && cd NvidiaWarp-GarmentCode \
    && git checkout ${GARMENT_WARP_REF} \
    && git lfs pull \
    && python build_lib.py --cuda_path=/usr/local/cuda \
    && pip install --no-cache-dir -e .

WORKDIR /workspace
COPY requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r /workspace/requirements.txt

COPY scripts/ /workspace/scripts/
COPY handler.py /workspace/handler.py

ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "/workspace/handler.py"]
