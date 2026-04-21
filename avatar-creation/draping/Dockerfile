# RunPod Serverless — Cloth Draping Service (v18: PyGarment only, Newton nuked)
# ==============================================================================
# Sole GPU backend: NvidiaWarp-GarmentCode + PyGarment — a fork of NVIDIA Warp
# with XPBD extensions engineered for garment simulation: particle_max_velocity
# clamp, global viscous damping, zero-gravity warmup, body-part panel drag,
# attachment constraints, body smoothing, auto-terminate on equilibrium.
#
# Newton Style3D was removed in v18 after v4–v16 of NaN fights. Geometric drape
# stays as the deterministic safety net in handler.py (no GPU, ~1s).

FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

WORKDIR /workspace

# Build deps for NvidiaWarp-GarmentCode (builds Warp from source) + runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential cmake \
    libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

# Core runtime deps — no `newton` pip package, we use NvidiaWarp-GarmentCode
# directly (installed in a separate step below).
RUN pip install --no-cache-dir \
    runpod \
    trimesh \
    pygltflib \
    scipy \
    httpx \
    Pillow \
    numpy \
    pyyaml \
    libigl

# --- NvidiaWarp-GarmentCode ---
# Fork of NVIDIA Warp (v1.0.0-beta.6) with cloth-simulation extensions
# specifically for garments: body-cloth drag constraint, attachment constraints,
# point-triangle + edge-edge self-collisions, body-smoothing initialization.
#
# Built from source (they don't publish a wheel):
#   --no_standalone : skip the standalone Clang/LLVM backend build. That
#     backend is ONLY for CPU-side kernel codegen; our path is GPU-only and
#     NVRTC handles CUDA codegen. Skipping it avoids a 15+ min LLVM compile
#     AND the packman permission-denied error we hit in the first v18 build.
#   --no_verify_fp : skip per-kernel finite-value checks (runtime overhead).
#   chmod on tools/packman/ : belt-and-suspenders so any future build step
#     that does touch packman can exec it.
RUN git clone --depth 1 https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode.git /workspace/warp-gc \
    && cd /workspace/warp-gc \
    && (chmod -R +x ./tools/packman/ 2>/dev/null || true) \
    && python build_lib.py --no_standalone --no_verify_fp \
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
