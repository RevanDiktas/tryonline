# =============================================================================
# Photoreal Avatar - SERVERLESS image (self-contained, built on RunPod's farm)
# =============================================================================
# Multi-photo -> photoreal, drape-ready, clothing-stripped avatar. Built as ONE
# self-contained image on RunPod's CPU GitHub auto-build farm (30-min cap),
# exactly like the proven tryonline-garment and tryonline-lhm images. Our
# compiled deps (pointops + diff-gaussian-rasterization + simple-knn) are
# LIGHTER than garment's Warp fork (~8 min) and LHM's source pytorch3d
# (~14 min), and pytorch3d/gsplat/torch_scatter/spconv are prebuilt wheels here,
# so this should sit comfortably under the cap.
#
# Recipe grounded line-for-line in LHM++'s INSTALL.md (torch 2.3.0 / cu121 /
# py3.10). LHM++ provides BOTH the SMPL-X PoseEstimator (hidden betas +
# measurements) AND the multi-image Gaussian splat export (to_gs_ply.py).
#
# Model weights (LHMPP-700M-*, human_model_files, SCHP ckpt) are NOT baked -
# they are runtime-downloaded by the handler to the Network Volume (the
# _ensure_lhm_data pattern), keeping the image lean so export fits the cap.
#
# Dockerfile path (RunPod endpoint field):  avatar-creation-photoreal/Dockerfile
# =============================================================================

# Same known-good base the live LHM image ships on (torch 2.3.0 + cu121 + py3.10,
# exactly what LHM++'s INSTALL.md pins). It already carries torch, so we do NOT
# reinstall it.
FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-devel

WORKDIR /workspace

# Bump CACHEBUST to force a full clean rebuild (per "always push RunPod clean":
# guarantees no stale layer hides as CACHED). Leave unchanged for cheap
# handler-only iteration, when only the final COPY layer rebuilds.
ARG CACHEBUST=2026-07-09a

# --- system build deps ---------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs build-essential cmake ninja-build wget curl aria2 \
    libgl1-mesa-glx libglib2.0-0 libegl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

# --- CUDA env (MUST precede any source build so find_cuda() sees the toolkit) --
# Without these, pointops / diff-gaussian-rasterization / simple-knn build
# CPU-only or crash with the empty-arch-list IndexError on the farm build host.
ENV CUDA_HOME=/usr/local/cuda
ENV CUDA_PATH=/usr/local/cuda
ENV PATH=/usr/local/cuda/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
# Arch list so compiled CUDA extensions target real GPUs, not the build host.
# 8.0 A100 / 8.6 A40,A6000,3090 / 8.9 L40S,4090 / 9.0 H100.
ENV TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"
ENV FORCE_CUDA=1

# --- xformers ------------------------------------------------------------------
# Base already has torch 2.3.0 + cu121; only add the matching xformers wheel.
# NOTE: the runpod serverless SDK is installed LAST (near the end of this file),
# not here. If installed first, LHM++'s requirements.txt then DOWNGRADES
# fastapi/requests/tomlkit below what runpod 1.10.x needs, which breaks
# runpod.serverless.start() at worker boot. Installing it last lets its deps win.
RUN pip install --no-cache-dir -U xformers==0.0.26.post1 \
       --index-url https://download.pytorch.org/whl/cu121

# --- clone LHM++ ---------------------------------------------------------------
# TODO before prod: pin a commit SHA for reproducibility. Floating for bring-up.
RUN git clone --depth 1 https://github.com/aigc3d/LHM-plusplus.git /workspace/LHM-plusplus

# --- LHM++ base python deps (its own requirements.txt) -------------------------
# Pins torch==2.3.0 (already satisfied) + gsplat/xatlas/open3d/smplx/plyfile/etc.
# numpy==1.23.0 pin downgrades the base image numpy (expected). rembg[cpu] is
# used only for sparse-view input extraction.
RUN cd /workspace/LHM-plusplus \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "rembg[cpu]"

# --- pointops (INSTALL.md step 4, from-source CUDA ext for the point encoder) ---
RUN cd /workspace/LHM-plusplus/lib/pointops \
    && python setup.py install

# --- spconv + torch_scatter (INSTALL.md step 5, prebuilt wheels) ---------------
RUN pip install --no-cache-dir spconv-cu121 \
    && pip install --no-cache-dir torch_scatter \
       -f https://data.pyg.org/whl/torch-2.3.0+cu121.html

# --- pytorch3d (INSTALL.md step 6, prebuilt wheel; our UV bake needs it too) ----
# pytorch3d depends on fvcore + iopath, which live on PyPI (NOT on the wheel
# find-links page). Install them first WITHOUT --no-index, then pull the
# pytorch3d wheel itself with --no-index so we get the prebuilt binary (not a
# ~10-min source compile). Base image is py3.10, so the py310 wheel matches.
RUN pip install --no-cache-dir fvcore iopath \
    && pip install --no-index --no-cache-dir pytorch3d \
      -f https://dl.fbaipublicfiles.com/pytorch3d/packaging/wheels/py310_cu121_pyt230/download.html

# --- diff-gaussian-rasterization + simple-knn (INSTALL.md 7-8, source, small) ---
RUN pip install --no-cache-dir "git+https://github.com/ashawkey/diff-gaussian-rasterization/" \
    && pip install --no-cache-dir "git+https://github.com/camenduru/simple-knn/"

# --- gsplat (INSTALL.md step 9, prebuilt wheel; PyPI/JIT fallback) --------------
RUN pip install --no-cache-dir gsplat==1.4.0 \
      -f https://docs.gsplat.studio/whl/pt23cu121.html \
    || pip install --no-cache-dir gsplat==1.4.0

# --- SMPL-Anthropometry (DavidBoja) for the 16-key measurement bundle ----------
# Same package the live LHM image uses; loader patched to load the .npz SMPL-X
# models we ship (we have no .pkl models). measure.py references the ext two
# ways: `.pkl` path literals AND `ext="pkl"` kwargs on smplx.SMPLX(...). The
# first sed catches the literals; the second catches the kwargs (which the
# original .pkl->.npz sed missed, causing MeasureSMPLX to assert a missing
# SMPLX_NEUTRAL.pkl). The handler also normalizes this at runtime as a fallback
# (the repo is cloned unpinned).
RUN git clone --depth 1 https://github.com/DavidBoja/SMPL-Anthropometry.git /workspace/SMPL-Anthropometry \
    && sed -i 's/\.pkl/\.npz/g' /workspace/SMPL-Anthropometry/measure.py \
    && sed -i -E "s/ext=['\"]pkl['\"]/ext='npz'/g" /workspace/SMPL-Anthropometry/measure.py \
    && echo "patched SMPL-Anthropometry to load ext=npz" \
    && grep -n "ext=" /workspace/SMPL-Anthropometry/measure.py

# --- SCHP (MIT) human parsing for the clothing-strip stage ---------------------
# Weights runtime-downloaded by the handler.
RUN git clone --depth 1 https://github.com/GoGoDuck912/Self-Correction-Human-Parsing.git /workspace/SCHP

# --- runpod SDK (installed LAST so its fastapi/requests/tomlkit deps win over
#     LHM++ requirements.txt's older pins; our handler path never uses gradio) --
# hf_transfer: Rust parallel downloader for huggingface_hub. The handler pulls
# the ~2.15 GB LHM++ prior at cold start (no Network Volume attached), and plain
# single-threaded HTTP (~6.7 MB/s observed) blew past the endpoint's 600 s
# execution cap. With HF_HUB_ENABLE_HF_TRANSFER=1 the same pull saturates the
# worker link (~200+ MB/s) and finishes in seconds, so every cold avatar request
# fits comfortably under the cap WITHOUT a volume.
RUN pip install --no-cache-dir runpod hf_transfer

# --- PYTHONPATH so LHM++ / SMPL-Anthropometry / SCHP import cleanly -------------
# Extra entries verified against the LHM++ tree (2026-07-11 selftest):
#  - lib/                     : pointops setup.py installs only the compiled
#                               `pointops_cuda` ext (no packages=), so the python
#                               wrapper package `pointops` (lib/pointops/) must be
#                               on the path for `import pointops` to resolve.
#  - engine/pose_estimation/  : pose_estimation/model.py does `from blocks import`
#                               where `blocks` is a package under that dir.
ENV PYTHONPATH=/workspace/LHM-plusplus:/workspace/LHM-plusplus/lib:/workspace/LHM-plusplus/engine/pose_estimation:/workspace/SMPL-Anthropometry:/workspace/SCHP:$PYTHONPATH

# --- build-time smoke imports (fail fast if a wheel/dep is broken) -------------
# CPU-safe imports only. The CUDA-kernel exts (diff_gaussian_rasterization,
# simple-knn, pointops, gsplat) init on a GPU, so their real check runs in the
# handler cold-start self-test, not here on the farm build host.
RUN python -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda)" \
    && python -c "import runpod; print('runpod SDK', runpod.__version__)" \
    && python -c "from runpod.serverless import start; print('runpod.serverless import OK')" \
    && python -c "import pytorch3d; print('pytorch3d', pytorch3d.__version__)" \
    && python -c "import xformers, smplx, trimesh, xatlas, open3d, cv2, plyfile; print('core deps OK')" \
    && python -c "import measure; print('SMPL-Anthropometry OK')"

# --- handler (COPYed last so handler edits rebuild only this tiny layer) --------
# Unbuffered so a boot-time traceback flushes to the worker log before exit(1),
# instead of being lost (which is what produced the bare "worker exited with exit
# code 1" with no cause on the first deploy).
ENV PYTHONUNBUFFERED=1
# Turn on the Rust parallel downloader for the cold-start prior fetch (no volume).
ENV HF_HUB_ENABLE_HF_TRANSFER=1
ENV PHOTOREAL_BUILD=v0.9-stage2b
COPY handler.py /workspace/handler.py

CMD ["python", "/workspace/handler.py"]
