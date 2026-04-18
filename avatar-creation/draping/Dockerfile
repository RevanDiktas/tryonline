# RunPod Serverless — Cloth Draping Service
# ===========================================
# Same base as the avatar pipeline (proven, GPU-ready).
# This is a NEW serverless endpoint — does NOT touch the avatar endpoint.

FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN pip install --no-cache-dir \
    runpod \
    trimesh \
    pygltflib \
    scipy \
    httpx \
    Pillow \
    numpy

COPY handler.py /workspace/handler.py
COPY convert.py /workspace/convert.py
COPY configs/ /workspace/configs/

CMD ["python3", "/workspace/handler.py"]
