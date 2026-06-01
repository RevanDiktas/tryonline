# =============================================================================
# Garment Construction — SINGLE self-contained image (RunPod GitHub auto-build)
# =============================================================================
# Photo -> 3D garment OBJ pipeline (ChatGarment -> GarmentCodeRC -> texture).
#
# WHY one file (not base + thin): RunPod GPU *pods* cannot run `docker build`
# (they are containers, no Docker daemon). RunPod's GitHub auto-build farm CAN
# build this — it runs on CPU, which is all we need: the compiled deps
# (NvidiaWarp-GarmentCode, flash-attn) need `nvcc` (baked into the -devel base)
# but NOT a physical GPU at build time (FORCE_CUDA=1 + TORCH_CUDA_ARCH_LIST emit
# device code for the worker GPUs). The serverless *workers* are GPU; the build
# is CPU. So everything builds here in one shot.
#
# RISK being probed: the 30-min auto-build cap covers RUN steps + image/cache
# export. This image is large (flash-attn + transformers + deepspeed + Warp). If
# the build dies at export, fall back to building on a cloud CPU VM via
# Dockerfile.base + build_base.sh (kept in this folder for exactly that).
#
# Model weights (~31 GB) are NOT baked — the handler runtime-downloads / reads
# them from the mounted network volume (the _ensure_* pattern), keeping the
# image lean and the export within the cap.
#
# The Warp build recipe (flags, CUDA env, pygarment __init__ stub) is lifted
# verbatim from the PROVEN avatar-creation/draping/Dockerfile (v18), which ships
# this same fork successfully on the same torch 2.1 / cu118 base.
# =============================================================================

FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

WORKDIR /workspace

# Bump CACHEBUST to force a full clean rebuild (per "always push RunPod clean":
# guarantees no stale layer hides). Leave unchanged for cheap handler-only
# iteration — only the final COPY layer rebuilds then.
ARG CACHEBUST=2026-06-01b

# --- system build deps ---------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs build-essential cmake ninja-build \
    libgl1-mesa-glx libglib2.0-0 libegl1 \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

# --- CUDA env (must precede any source build so find_cuda() sees the toolkit) --
# Without these the Warp fork builds CPU-only (WP_ENABLE_CUDA=0) — the exact
# failure the drape image hit on its first attempt.
ENV CUDA_HOME=/usr/local/cuda
ENV CUDA_PATH=/usr/local/cuda
ENV PATH=/usr/local/cuda/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
# Arch list so compiled CUDA extensions target real GPUs, not the build host.
# 8.0 A100 / 8.6 A40,A6000,3090 / 8.9 L40S,4090 / 9.0 H100.
ENV TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"
ENV FORCE_CUDA=1

# --- pin torch to ChatGarment's tested combo (2.1.2 + cu118) -------------------
# Base ships 2.1.0; ChatGarment's pyproject pins 2.1.2. Install 2.1.2 from the
# cu118 index FIRST so that when `pip install -e .` later sees torch==2.1.2 it is
# already satisfied with the cu118 build (NOT the default cu121 wheel, which
# would mismatch the cu118 toolkit the Warp fork compiles against).
RUN pip install --no-cache-dir \
      torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu118

# --- ChatGarment + its declared deps (the documented install) ------------------
# ChatGarment's pyproject (package name "llava") declares the full, tested dep
# set: transformers==4.37.2, tokenizers==0.15.1, accelerate==0.32.0,
# peft==0.10.0, bitsandbytes, einops, timm, gradio, scikit-learn, opencv-python,
# easydict, sentencepiece ... and the [train] extra adds deepspeed==0.12.6 +
# ninja (the eval launcher uses deepspeed even for inference). Let the repo
# install its OWN pins (docs/Installation.md: `pip install -e ".[train]"`).
RUN git clone --depth 1 https://github.com/biansy000/ChatGarment.git /workspace/ChatGarment \
    && cd /workspace/ChatGarment \
    && pip install --no-cache-dir -e ".[train]"

# --- flash-attn (prebuilt wheel for torch2.1 / cu118 / py310 / cxx11abiFALSE) --
# Building from source takes ~45 min; the matching prebuilt wheel is instant.
# If this exact wheel 404s at build time, fall back to source build.
RUN pip install --no-cache-dir \
      https://github.com/Dao-AILab/flash-attention/releases/download/v2.5.8/flash_attn-2.5.8+cu118torch2.1cxx11abiFALSE-cp310-cp310-linux_x86_64.whl \
    || pip install --no-cache-dir flash-attn==2.5.8 --no-build-isolation

# --- NvidiaWarp-GarmentCode (the compiled Warp fork) ---------------------------
# Recipe verbatim from the proven drape Dockerfile v18:
#   --cuda_path : force CUDA so the binary is GPU-enabled
#   --no_standalone : skip Clang/LLVM CPU codegen backend (NVRTC handles CUDA);
#                     saves 15+ min and dodges the packman permission bug
#   --no_verify_fp : drop per-kernel finite checks (runtime overhead)
RUN git clone --depth 1 https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode.git /workspace/warp-gc \
    && cd /workspace/warp-gc \
    && (chmod -R +x ./tools/packman/ 2>/dev/null || true) \
    && python build_lib.py --cuda_path /usr/local/cuda --no_standalone --no_verify_fp \
    && pip install --no-cache-dir -e .

# --- GarmentCodeRC + pygarment (JSON -> 3D garment decoder + Warp drape) --------
# biansy000's refined GarmentCode fork that ChatGarment's run_garmentcode_sim.py
# imports (pygarment.meshgen.*). Same package_dir quirk + cairosvg-in-__init__
# issue as upstream GarmentCode, so: put repo on PYTHONPATH (no pip install) and
# stub pygarment/__init__.py to the simulation subset only. (Verify at build: if
# run_garmentcode_sim.py needs the full __init__, restore it + add cairosvg.)
RUN git clone --depth 1 https://github.com/biansy000/GarmentCodeRC.git /workspace/GarmentCodeRC

# --- GarmentCodeRC runtime deps (its setup.cfg install_requires) ---------------
# We clone + PYTHONPATH (NOT `pip install -e .`: its package_dir quirk + the CGAL
# bindings make editable install fragile), so install its declared deps here.
# An earlier image BLANKED pygarment/__init__.py to dodge a cairosvg import, but
# ChatGarment's garment programs subclass `pyg.Panel`, so blanking broke STEP-1
# (AttributeError: module 'pygarment' has no attribute 'Panel' -- verified on a
# real GPU run 2026-06-01). Keep the real __init__ and supply its deps.
# Import-time set verified from source: __init__ -> garmentcode/* + pattern/core
# need numpy<2/scipy/svgpathtools/pyyaml; pattern.serialize() -> wrappers.py needs
# cairosvg+svgwrite (libcairo2 system lib); meshgen/* needs igl/trimesh/matplotlib.
RUN apt-get update && apt-get install -y --no-install-recommends libcairo2 \
    && rm -rf /var/lib/apt/lists/* && apt-get clean
# libigl is PINNED to 2.5.1 (last classic-API release). libigl 2.6.x is a
# nanobind rewrite that changed return signatures: igl.facet_components(F) now
# returns a (labels, counts) tuple instead of a flat per-face label array, so
# meshgen/render/texture_utils.py:_uv_connected_components does
# `max(face_components)+1` over a tuple-of-arrays -> "truth value of an array
# with more than one element is ambiguous" (verified on a real GPU run
# 2026-06-01, and reproduced locally: 2.5.1 returns a flat (#F,) array, 2.6.2
# does not). All 5 igl calls the meshgen graph uses (facet_components,
# vertex_components, boundary_loop, read/write_triangle_mesh) exist in 2.5.1.
RUN pip install --no-cache-dir \
      pyyaml scipy svgwrite svgpathtools psutil matplotlib cairosvg trimesh "libigl==2.5.1"
# CGAL bindings: panel triangulation in meshgen/triangulation_utils.py is ON the
# STEP-2 critical path (boxmeshgen.py:337 builds the box mesh with a Constrained
# Delaunay triangulation). The `cgal` PyPI package ships a self-contained cp310
# manylinux wheel (CGAL+GMP+MPFR+Boost bundled), so this is a hard install --
# verified at build below by importing the exact symbols the code uses.
RUN pip install --no-cache-dir cgal

# pyrender is imported (and called) only to render UNUSED preview PNGs of the
# draped garment (simulation.py:28 + :242). The draped OBJ is saved by
# garment.save_frame() BEFORE that render call, so the renders are output we
# never consume -- but the module-level import drags in the whole pyrender/EGL
# GL stack, which is fragile on serverless GPUs and was the STEP-2 crash
# (ModuleNotFoundError: pyrender, real GPU run 2026-06-01). render_images is the
# ONLY name anything imports from pythonrender.py (verified across both repos),
# so replace that module with a no-op stub: removes pyrender/EGL from the
# critical path entirely while keeping the draped-OBJ output identical.
RUN printf '%s\n' \
    'def render_images(*args, **kwargs):' \
    '    """STUB: preview rendering disabled (pyrender/EGL removed from the' \
    '    serverless path). The draped OBJ is saved before this call, so the' \
    '    construction output is unaffected; we do not use the preview PNGs."""' \
    '    return None' \
    > /workspace/GarmentCodeRC/pygarment/meshgen/render/pythonrender.py

# GarmentCodeRC ships the `assets` folder ChatGarment expects symlinked at its root.
RUN ln -sfn /workspace/GarmentCodeRC/assets /workspace/ChatGarment/assets

# --- PYTHONPATH so all three import cleanly ------------------------------------
ENV PYTHONPATH=/workspace/ChatGarment:/workspace/GarmentCodeRC:/workspace/warp-gc:$PYTHONPATH

# --- handler-only runtime deps (pure-python, no compile) -----------------------
# rembg pulls onnxruntime (CPU) — fine. runpod = serverless SDK; requests =
# download/upload helpers. tensorboard: the ChatGarment eval script creates a
# SummaryWriter when launched via deepspeed (local_rank==0), so torch.utils.
# tensorboard needs the tensorboard package present (verified from source).
RUN pip install --no-cache-dir runpod requests rembg tensorboard hf_transfer \
    || pip install --no-cache-dir runpod requests tensorboard hf_transfer

# --- pin numpy<2 LAST (authoritative) ------------------------------------------
# The base image + torch 2.1.2 are compiled against numpy 1.x, and deepspeed
# 0.12.6's autotuning/scheduler.py does `from numpy import BUFSIZE`, which was
# REMOVED in numpy 2.0. One of the installs above (rembg/onnxruntime/tensorboard
# transitive) pulls numpy 2.2.6, which silently breaks torch (UserWarning) and
# HARD-breaks the deepspeed launcher the ChatGarment eval uses
# (ImportError: cannot import name 'BUFSIZE'). Force numpy back to the last 1.x
# release as the FINAL pip step so nothing can re-bump it. Verified from a real
# GPU run log (2026-06-01): numpy 2.2.6 present -> STEP-1 inference failed.
RUN pip install --no-cache-dir "numpy==1.26.4"

# Accelerate the cold-start weight downloads (LLaVA-7B + CLIP + the 14GB
# checkpoint) with the rust multipart transfer backend.
ENV HF_HUB_ENABLE_HF_TRANSFER=1
# Force matplotlib's headless backend: GarmentCodeRC's UV-island texture step
# (texture_utils.create_UV_island_texture -> plt.savefig) runs during STEP-2
# serialize on a worker with no display.
ENV MPLBACKEND=Agg

# Sanity imports at build time (fail fast if any compiled dep is broken).
# NOTE: `import flash_attn` and a real `wp.init()` GPU check only pass on a GPU
# host — those run in the handler's cold-start self-test, not here.
RUN python -c "import numpy; assert numpy.__version__.startswith('1.'), 'numpy got bumped to '+numpy.__version__; print('numpy', numpy.__version__)" \
    && python -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda)" \
    && python -c "import warp as wp; print('warp', wp.__version__)" \
    && python -c "import transformers; print('transformers', transformers.__version__)" \
    && python -c "import deepspeed; print('deepspeed', deepspeed.__version__)" \
    && python -c "import pygarment as pyg; assert hasattr(pyg,'Panel'), 'pygarment __init__ missing Panel'; print('pygarment OK (Panel present)')" \
    && python -c "import CGAL.CGAL_Kernel; from CGAL.CGAL_Mesh_2 import Mesh_2_Constrained_Delaunay_triangulation_2, Delaunay_mesh_size_criteria_2; from CGAL.CGAL_Triangulation_2 import Constrained_Delaunay_triangulation_2; print('CGAL OK (triangulation symbols present)')" \
    && python -c "import importlib.metadata as m, numpy as np, igl; v=m.version('libigl'); assert v=='2.5.1', 'libigl must be 2.5.1 (classic API), got '+v; assert np.asarray(igl.facet_components(np.array([[0,1,2],[3,4,5]],dtype=np.int64))).ndim==1, 'facet_components not flat'; print('libigl', v, '(facet_components flat OK)')" \
    && python -c "import pygarment.meshgen.boxmeshgen; print('STEP-2 boxmeshgen import OK (igl/trimesh/cairosvg/CGAL/texture chain)')" \
    && python -c "import pygarment.meshgen.simulation; print('STEP-2 simulation import OK (warp + stubbed render, no pyrender)')"

# --- handler (COPYed last so handler edits rebuild only this tiny layer) --------
ENV GARMENT_BUILD=v0.1
COPY handler.py /workspace/handler.py

CMD ["python", "/workspace/handler.py"]
