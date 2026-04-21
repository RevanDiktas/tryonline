# RunPod Serverless — Cloth Draping Service (v17: PyGarment / GarmentCode backend)
# ================================================================================
# Replaces the vanilla Newton solver with NvidiaWarp-GarmentCode + PyGarment —
# a fork of Warp with XPBD extensions specifically built for garment simulation:
# particle_max_velocity clamp, global viscous damping, zero-gravity warmup,
# body-part panel drag, attachment constraints, body smoothing, auto-terminate
# on equilibrium. None of these stability features are in the upstream Newton
# Style3D solver we were fighting in v11–v16.
#
# Newton + geometric fallback are kept in handler.py as secondary paths in case
# PyGarment fails on a specific garment.

FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

WORKDIR /workspace

# Build deps for NvidiaWarp-GarmentCode (builds Warp from source) + runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential cmake \
    libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

# Core runtime deps (pin newton as fallback — we still keep the Newton path).
RUN pip install --no-cache-dir \
    runpod \
    newton \
    trimesh \
    pygltflib \
    scipy \
    httpx \
    Pillow \
    numpy \
    pyyaml \
    libigl \
    smplx

# --- NvidiaWarp-GarmentCode ---
# Fork of NVIDIA Warp (v1.0.0-beta.6) with cloth-simulation extensions
# specifically for garments: body-cloth drag constraint, attachment constraints,
# point-triangle + edge-edge self-collisions, body-smoothing initialization.
# These features are what make PyGarment stable on CLO3D-style tight garments
# that explode vanilla Newton.
#
# Built from source (they don't publish a wheel). build_lib.py compiles the
# CUDA kernels; pip install -e wires the Python module into site-packages.
RUN git clone --depth 1 https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode.git /workspace/warp-gc \
    && cd /workspace/warp-gc \
    && python build_lib.py \
    && pip install --no-cache-dir -e .

# --- GarmentCode / PyGarment ---
# High-level pattern/simulation library that drives NvidiaWarp-GarmentCode.
# We use pygarment.meshgen.simulation.run_sim() as our drape entry point.
RUN git clone --depth 1 https://github.com/maria-korosteleva/GarmentCode.git /workspace/garmentcode \
    && cd /workspace/garmentcode \
    && pip install --no-cache-dir -e .

# --- PyGarment assets ---
# SMPL body segmentation (per-vertex body-part labels) shipped with the image
# so PyGarment can use smpl_body=True out of the box. Sim props are our tuned
# config (ground plane ON, velocity clamp 20 m/s, zero-gravity warmup 10f).
RUN mkdir -p /workspace/pygarment_assets
COPY pygarment_assets/smpl_vert_segmentation.json /workspace/pygarment_assets/
COPY pygarment_assets/default_sim_props.yaml /workspace/pygarment_assets/

# system.json for PyGarment — points it at our asset paths.
RUN echo '{"output":"./Logs/","datasets_path":"","datasets_sim":"","sim_configs_path":"/workspace/pygarment_assets","bodies_default_path":"/workspace/pygarment_assets","body_samples_path":""}' > /workspace/system.json

COPY handler.py /workspace/handler.py
COPY convert.py /workspace/convert.py
COPY configs/ /workspace/configs/

CMD ["python3", "/workspace/handler.py"]
