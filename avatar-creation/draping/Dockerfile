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

# CUDA env vars — set BEFORE any build step so build_lib.py's find_cuda() finds
# the toolkit. Without these, the first v18 build produced a Warp binary with
# WP_ENABLE_CUDA=0 (CPU-only) which made the whole GPU path unreachable.
ENV CUDA_HOME=/usr/local/cuda
ENV CUDA_PATH=/usr/local/cuda
ENV PATH=/usr/local/cuda/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Core runtime deps. pygarment's install_requires (setup.cfg) pulls in a bunch
# of things we don't need (pyrender, CairoSVG, nicegui, cgal). We install only
# the subset actually used by the simulation path — render/ui modules get
# stubbed at runtime in handler.py.
RUN pip install --no-cache-dir \
    runpod \
    trimesh \
    pygltflib \
    scipy \
    httpx \
    Pillow \
    numpy \
    pyyaml \
    libigl \
    svgwrite \
    svgpathtools \
    psutil \
    matplotlib

# --- NvidiaWarp-GarmentCode ---
# Fork of NVIDIA Warp (v1.0.0-beta.6) with cloth-simulation extensions
# specifically for garments: body-cloth drag constraint, attachment constraints,
# point-triangle + edge-edge self-collisions, body-smoothing initialization.
#
# Flags:
#   --cuda_path /usr/local/cuda : explicit CUDA location (also in env for
#     belt-and-suspenders). Without this, find_cuda() may return None and
#     build WITHOUT CUDA support — which we saw in the first build attempt.
#   --no_standalone : skip the standalone Clang/LLVM backend build. That
#     backend is ONLY for CPU-side kernel codegen; our path is GPU-only and
#     NVRTC (in the CUDA toolkit) handles CUDA codegen. Saves 15+ min of
#     compile and dodges the packman permission bug.
#   --no_verify_fp : skip per-kernel finite-value checks (runtime overhead).
RUN git clone --depth 1 https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode.git /workspace/warp-gc \
    && cd /workspace/warp-gc \
    && (chmod -R +x ./tools/packman/ 2>/dev/null || true) \
    && python build_lib.py --cuda_path /usr/local/cuda --no_standalone --no_verify_fp \
    && pip install --no-cache-dir -e .

# --- GarmentCode / PyGarment ---
# The repo's setup.cfg has `package_dir = =pygarment` which, when pip-installed,
# exposes sub-packages as top-level (meshgen, pattern, etc.) — but the repo's
# own code uses `from pygarment.meshgen.X import Y`. That mismatch is why
# `pip install -e .` left `pygarment` itself unimportable in the first build.
# Workaround: skip pip install entirely and put the repo dir on PYTHONPATH.
# Python then finds /workspace/garmentcode/pygarment/ as a normal package.
RUN git clone --depth 1 https://github.com/maria-korosteleva/GarmentCode.git /workspace/garmentcode
ENV PYTHONPATH=/workspace/garmentcode:$PYTHONPATH

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
