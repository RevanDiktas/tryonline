# TryOn Avatar Pipeline - Google Colab Setup Guide

**Last verified:** January 15, 2026  
**Runtime:** Google Colab Pro (T4 GPU)  
**Repository:** https://github.com/RevanDiktas/tryonline

---

## Prerequisites

Before running in Colab, make sure you have these files in your **Google Drive** under `mvp_pipeline/`:

```
Google Drive/
└── mvp_pipeline/
    ├── logs/                          # HMR2 checkpoint (~2.7GB)
    │   └── train/multiruns/hmr2/0/
    │       ├── checkpoints/
    │       │   └── epoch=35-step=1000000.ckpt
    │       ├── model_config.yaml
    │       └── dataset_config.yaml
    └── data/                          # SMPL model files
        ├── smpl/
        │   └── SMPL_NEUTRAL.pkl
        ├── SMPL_to_J19.pkl
        └── smpl_mean_params.npz
```

---

## Colab Notebook Cells

### Cell 1: Check GPU & Clone Repository

```python
# Check GPU
!nvidia-smi
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# Clone the repository
!git clone https://github.com/RevanDiktas/tryonline.git
%cd tryonline/avatar-creation

print("\n✓ Repository cloned!")
```

---

### Cell 2: Install Dependencies

```python
# Install dependencies (order matters!)
!pip install -q numpy==1.23.5  # Pin numpy for chumpy compatibility

# Core packages
!pip install -q smplx chumpy trimesh opencv-python pillow
!pip install -q torch torchvision --index-url https://download.pytorch.org/whl/cu118
!pip install -q timm einops pytorch-lightning hydra-core yacs omegaconf
!pip install -q ultralytics  # YOLO
!pip install -q webdataset braceexpand gdown scikit-image joblib pandas tqdm matplotlib av iopath

# Detectron2 (for CUDA 12.x)
!pip install -q 'git+https://github.com/facebookresearch/detectron2.git'

# Pyrender for visualization
!pip install -q pyrender PyOpenGL PyOpenGL_accelerate
!apt-get install -qq libegl1-mesa-dev libgles2-mesa-dev

print("\n✓ Dependencies installed!")
```

---

### Cell 3: Upload SMPL Model Files

```python
# Upload SMPL .pkl files from your local machine
# Location: /Volumes/Expansion/avatar-creation/4D-Humans-clean/data/SMPL_python_v.1.1.0/smpl/models/
from google.colab import files
print("Upload SMPL .pkl files (basicmodel_neutral, basicmodel_m, basicmodel_f):")
uploaded = files.upload()

# Move to correct location
!mkdir -p 4D-Humans-clean/data/smpl
!mv *.pkl 4D-Humans-clean/data/smpl/ 2>/dev/null || echo "Files moved or already in place"

# Rename to expected names
!cd 4D-Humans-clean/data/smpl && mv basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl SMPL_NEUTRAL.pkl 2>/dev/null || true
!cd 4D-Humans-clean/data/smpl && mv basicmodel_m_lbs_10_207_0_v1.1.0.pkl SMPL_MALE.pkl 2>/dev/null || true
!cd 4D-Humans-clean/data/smpl && mv basicmodel_f_lbs_10_207_0_v1.1.0.pkl SMPL_FEMALE.pkl 2>/dev/null || true

print("\n✓ SMPL files uploaded!")
!ls -la 4D-Humans-clean/data/smpl/
```

---

### Cell 4: Setup HMR2 Model Files from Google Drive

```python
# Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

# Define paths
CACHE_DIR = "/root/.cache/4DHumans"
DRIVE_DIR = "/content/drive/MyDrive/mvp_pipeline"

# Create directory structure
!mkdir -p {CACHE_DIR}/logs/train/multiruns/hmr2/0/checkpoints
!mkdir -p {CACHE_DIR}/data/smpl

# Copy HMR2 checkpoint and configs from Drive
print("Copying HMR2 model files from Google Drive...")
!cp -rv {DRIVE_DIR}/logs/* {CACHE_DIR}/logs/

# Copy SMPL data files from Drive
print("\nCopying SMPL data files...")
!cp -rv {DRIVE_DIR}/data/* {CACHE_DIR}/data/

# Copy SMPL models from Colab upload
!cp /content/tryonline/avatar-creation/4D-Humans-clean/data/smpl/*.pkl {CACHE_DIR}/data/smpl/

# Create dummy tar.gz to skip download check
!touch {CACHE_DIR}/hmr2_data.tar.gz

# Verify all files
print("\n" + "="*60)
print("VERIFICATION")
print("="*60)
import os
required = {
    f"{CACHE_DIR}/hmr2_data.tar.gz": "Dummy tar (skip download)",
    f"{CACHE_DIR}/logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt": "HMR2 Checkpoint (2.7GB)",
    f"{CACHE_DIR}/logs/train/multiruns/hmr2/0/model_config.yaml": "Model config",
    f"{CACHE_DIR}/data/smpl/SMPL_NEUTRAL.pkl": "SMPL Neutral model",
    f"{CACHE_DIR}/data/SMPL_to_J19.pkl": "Joint regressor",
    f"{CACHE_DIR}/data/smpl_mean_params.npz": "Mean params",
}

all_good = True
for path, desc in required.items():
    exists = os.path.exists(path)
    if exists:
        size = os.path.getsize(path)
        status = "✓" if size > 0 or "tar.gz" in path else "✗ EMPTY"
        print(f"{status} {desc}: {size:,} bytes")
    else:
        print(f"✗ {desc}: MISSING!")
        all_good = False

print("="*60)
print("✓ ALL FILES READY!" if all_good else "✗ MISSING FILES!")
```

---

### Cell 5: Upload Test Image

```python
# Upload a full-body photo
from google.colab import files
print("Upload a full-body photo (JPG/PNG):")
uploaded = files.upload()

# Get filename
test_image = list(uploaded.keys())[0]
print(f"\n✓ Uploaded: {test_image}")
```

---

### Cell 6: Run the Avatar Pipeline

```python
import os
os.environ['PYOPENGL_PLATFORM'] = 'egl'

# Set your parameters
HEIGHT_CM = 192  # CHANGE THIS to actual height
GENDER = "male"  # "male", "female", or "neutral"

# Run the pipeline
!python pipelines/run_avatar_pipeline.py \
    --image {test_image} \
    --height {HEIGHT_CM} \
    --gender {GENDER} \
    --output output
```

---

### Cell 7: View Results

```python
# List output files
!ls -la output/

# Show measurements
!cat output/measurements.json

# Display the avatar (if you have a 3D viewer)
from IPython.display import HTML
HTML(f'''
<p>Output files:</p>
<ul>
<li>avatar_textured.glb - 3D Avatar</li>
<li>measurements.json - Body measurements</li>
<li>body_apose.obj - A-pose mesh</li>
<li>skin_texture.png - Skin color</li>
</ul>
''')
```

---

### Cell 8: Download Results

```python
from google.colab import files

# Download the GLB avatar
files.download('output/avatar_textured.glb')

# Download measurements
files.download('output/measurements.json')

# Download all outputs as zip (optional)
!cd output && zip -r ../avatar_output.zip .
files.download('avatar_output.zip')
```

---

## Troubleshooting

### Error: `weights_only` / `omegaconf.DictConfig`
- **Cause:** PyTorch 2.6+ changed defaults
- **Fix:** Already patched in `demo_yolo.py` - just `git pull origin main`

### Error: `inspect.getargspec`
- **Cause:** Python 3.11+ removed deprecated function
- **Fix:** Already patched in all files - just `git pull origin main`

### Error: `numpy.bool` / `numpy.int`
- **Cause:** NumPy 2.0+ removed deprecated types
- **Fix:** Already patched in all files - just `git pull origin main`

### Error: 403 Forbidden (download)
- **Cause:** Berkeley server blocks downloads
- **Fix:** Use Google Drive for model files (this guide)

### Runtime Disconnects
- **Cause:** Long uploads/idle time
- **Fix:** Use Google Drive instead of direct uploads

---

## File Locations (Local Mac)

If you need to re-upload files, they're located at:

```
# SMPL Models (.pkl files)
/Volumes/Expansion/avatar-creation/4D-Humans-clean/data/SMPL_python_v.1.1.0/smpl/models/

# HMR2 Checkpoint and configs
/Volumes/Expansion/avatar-creation/4D-Humans-clean/.cache/4DHumans/logs/

# SMPL data files (SMPL_to_J19.pkl, smpl_mean_params.npz)
/Volumes/Expansion/avatar-creation/4D-Humans-clean/.cache/4DHumans/data/
```

---

## Expected Output

```
PIPELINE COMPLETE!

Output files in: output/
  original_mesh: user_001_person0.obj
  smpl_params: user_001_person0_params.npz
  tpose_mesh: body_tpose.obj
  measurements: measurements.json
  apose_mesh: body_apose.obj
  skin_texture: skin_texture.png
  avatar_glb: avatar_textured.glb

Measurements:
  height: 192.0 cm
  chest circumference: ~102 cm
  waist circumference: ~83 cm
  hip circumference: ~96 cm
  inside leg height: ~86 cm
```

---

## Next Steps After Verification

1. **Deploy to RunPod** - Create serverless endpoint
2. **Wire Backend** - Connect FastAPI to RunPod
3. **Test E2E** - Frontend → Backend → RunPod → Supabase

---

**Created:** January 15, 2026  
**Author:** TryOn MVP Team
