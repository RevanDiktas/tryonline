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
