# =============================================================================
# Measurement-only worker: photos + height + weight -> body measurements
# =============================================================================
# Small and self-contained: every model file is baked in at build time, so a cold
# start downloads nothing. Built by RunPod's GitHub integration.
#
#   Dockerfile path (endpoint field):  avatar-creation-measure/Dockerfile
#   Build context   (endpoint field):  avatar-creation-measure
#
# Baked in:
#   DeepLabV3-R101 person segmenter   233 MB  download.pytorch.org (public)
#   SMPL-X male / female / neutral    3 x 104 MB  HuggingFace 3DAIGC/LHMPP-Prior (public; non-commercial licence)
#   Measurement CNN                   10 MB   weights/measure_cnn.pt from this folder (or CNN_URL)
# =============================================================================
# Runtime (not devel) image: nothing here is compiled. Same torch 2.3.0 / cu121 / py3.10 line
# as the photoreal endpoint; it already carries torch and torchvision.
FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

WORKDIR /workspace/measure

# Bump to force a clean rebuild of every layer below.
ARG CACHEBUST=2026-11-20a

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

# numpy stays below 2: the base image's torch 2.3.0 was built against numpy 1.x.
RUN pip install --no-cache-dir "numpy<2" pillow opencv-python-headless smplx httpx runpod

ENV TORCH_HOME=/workspace/torch_home
ENV MEASURE_HUMAN_MODELS=/workspace/measure/human_model_files
ENV PYTHONUNBUFFERED=1

# --- model files, checked against known SHA-256 so a changed upstream file fails the build ---
RUN mkdir -p $TORCH_HOME/hub/checkpoints $MEASURE_HUMAN_MODELS/smplx \
    && curl -fL --retry 3 -o $TORCH_HOME/hub/checkpoints/deeplabv3_resnet101_coco-586e9e4e.pth \
         https://download.pytorch.org/models/deeplabv3_resnet101_coco-586e9e4e.pth \
    && for g in MALE FEMALE NEUTRAL; do \
         curl -fL --retry 3 -o $MEASURE_HUMAN_MODELS/smplx/SMPLX_$g.npz \
           https://huggingface.co/3DAIGC/LHMPP-Prior/resolve/main/human_model_files/smplx/SMPLX_$g.npz || exit 1; \
       done \
    && printf '%s  %s\n' \
         586e9e4e203fcbf17e1ad45533d8d33ab133fc762bf03101c5dd743995c08c0d $TORCH_HOME/hub/checkpoints/deeplabv3_resnet101_coco-586e9e4e.pth \
         ab318e3f37d2bfaae26abf4e6fab445c2a610e1d63714794d60379cc263bc2a5 $MEASURE_HUMAN_MODELS/smplx/SMPLX_MALE.npz \
         b2a3686c9d6d218ff6822fba411c607a3c8125a70af340f384ce68bebecabe0e $MEASURE_HUMAN_MODELS/smplx/SMPLX_FEMALE.npz \
         376021446ddc86e99acacd795182bbef903e61d33b76b9d8b359c2b0865bd992 $MEASURE_HUMAN_MODELS/smplx/SMPLX_NEUTRAL.npz \
       | sha256sum -c -

# --- code and the measurement CNN (last, so a handler edit rebuilds only from here) ---
COPY preprocess.py fit.py model.py handler.py test_preprocess.py ./
COPY weights/ ./weights/

# Optional: take the CNN from a URL instead of the folder (leave empty to use weights/measure_cnn.pt).
# The matching weights/measure_cnn.json (version + sha256) must still be in the folder.
ARG CNN_URL=""
RUN if [ -n "$CNN_URL" ]; then curl -fL --retry 3 -o weights/measure_cnn.pt "$CNN_URL"; fi \
    && test -s weights/measure_cnn.pt || (echo "weights/measure_cnn.pt is missing: commit it or pass CNN_URL" && exit 1)

# --- the build fails here if anything is broken ---
# 1. gate tests on drawn figures; 2. imports; 3. the worker's own selftest (loads every model and runs
# each once on the build host's CPU); 4. refuses a wiring-test checkpoint unless explicitly allowed.
ARG ALLOW_WIRING_MODEL=0
RUN python test_preprocess.py \
    && python -c "import runpod; from runpod.serverless import start; print('runpod', runpod.__version__)" \
    && python -c "import json, sys, handler; r = handler.selftest(); print(json.dumps(r, indent=1)); \
v = r.get('cnn', {}).get('version', '') if isinstance(r.get('cnn'), dict) else ''; \
bad = v.startswith('wiring') and '$ALLOW_WIRING_MODEL' != '1'; \
print('REFUSED: wiring-test checkpoint; put the real model in weights/ or build with ALLOW_WIRING_MODEL=1') if bad else None; \
sys.exit(0 if r['ok'] and not bad else 1)"

ENV MEASURE_BUILD=v0.1
CMD ["python", "/workspace/measure/handler.py"]
