# Heatmap worker (Phase 0.5): NVIDIA Warp fork from GarmentCode + GPU smoke.
# Build context: repository root with heatmap-worker/ (see README).
#
# First build can take a long time (compiles Warp native libs + optional LLVM stack).

FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    git-lfs \
    build-essential \
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
COPY heatmap-worker/requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r /workspace/requirements.txt

COPY heatmap-worker/scripts/ /workspace/scripts/
COPY heatmap-worker/handler.py /workspace/handler.py

ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "/workspace/handler.py"]
