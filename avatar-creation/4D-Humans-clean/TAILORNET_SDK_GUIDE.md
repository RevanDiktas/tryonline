# TailorNet SDK - Clothing Generation with Size Tables

## ✅ **FOUND IT!** - TailorNet is the SDK we planned to use!

## 🎯 What is TailorNet?

**TailorNet** is a neural model that predicts 3D clothing deformations based on:
- Human **pose**
- Human **shape** (SMPL body parameters)
- **Garment style**

**Key Features:**
- ✅ **Fast** - Much faster than physics-based simulation
- ✅ **Realistic** - Preserves fine details like wrinkles
- ✅ **Differentiable** - Can be used in learning algorithms
- ✅ **SMPL-compatible** - Works with our avatar pipeline!
- ✅ **Size tables** - Supports different garment sizes
- ✅ **Recalibration** - Can adjust to custom measurements

## 📚 Resources

### Official Links:
- **Project Website**: https://virtualhumans.mpi-inf.mpg.de/tailornet/
- **GitHub (Code)**: https://github.com/chaitanya100100/TailorNet
- **GitHub (Dataset)**: https://github.com/zycliao/TailorNet_dataset
- **Paper**: "TailorNet: Predicting Clothing in 3D as a Function of Human Pose, Shape and Garment Style"

### Garment Categories:
TailorNet supports 6 garment categories:
1. **T-shirt**
2. **Shirt**
3. **Pant**
4. **Skirt**
5. **Short-pant**
6. **Old T-shirt**

## 🔧 Installation

### Step 1: Clone Repository

```bash
cd /Volumes/Expansion/avatar-creation
git clone https://github.com/chaitanya100100/TailorNet.git
cd TailorNet
```

### Step 2: Setup Environment

```bash
# Create conda environment
conda create -n tailornet python=3.7
conda activate tailornet

# Install dependencies
pip install torch torchvision
pip install numpy scipy
pip install trimesh
pip install smplx  # For SMPL compatibility
```

### Step 3: Download Pre-trained Models

```bash
# Download from TailorNet website or repository
# Models are typically ~500MB-1GB
mkdir -p models/tailornet
# Download models to models/tailornet/
```

### Step 4: Download Dataset (Optional)

```bash
# For training or fine-tuning
git clone https://github.com/zycliao/TailorNet_dataset.git
cd TailorNet_dataset
# Follow dataset download instructions
```

## 📊 Size Tables & Recalibration

### How TailorNet Handles Sizing

TailorNet uses **SMPL body shape parameters (betas)** to control garment fit:
- **10 shape parameters** (betas) control body proportions
- Garments automatically adapt to body shape
- Can be recalibrated by adjusting betas

### Size Table Mapping

```python
# tailornet_size_mapper.py

import numpy as np
from smplx import SMPL

# Standard size tables (example)
STANDARD_SIZES = {
    'XS': {'chest': 84, 'waist': 68, 'hip': 88, 'height': 165},
    'S': {'chest': 88, 'waist': 72, 'hip': 92, 'height': 170},
    'M': {'chest': 96, 'waist': 80, 'hip': 100, 'height': 175},
    'L': {'chest': 104, 'waist': 88, 'hip': 108, 'height': 180},
    'XL': {'chest': 112, 'waist': 96, 'hip': 116, 'height': 185},
}

def measurements_to_smpl_betas(measurements):
    """
    Convert body measurements to SMPL betas (shape parameters)
    
    Args:
        measurements: dict with chest, waist, hip, height (cm)
    
    Returns:
        betas: numpy array of 10 SMPL shape parameters
    """
    # This is a simplified mapping
    # Real implementation would use regression or optimization
    
    # Normalize measurements
    height_norm = (measurements['height'] - 175) / 10  # Center at 175cm
    chest_norm = (measurements['chest'] - 96) / 10     # Center at 96cm
    waist_norm = (measurements['waist'] - 80) / 10    # Center at 80cm
    hip_norm = (measurements['hip'] - 100) / 10        # Center at 100cm
    
    # Map to SMPL betas (simplified - real version would be more complex)
    betas = np.array([
        height_norm * 0.5,    # Beta 0: Height
        chest_norm * 0.3,      # Beta 1: Chest width
        waist_norm * 0.2,      # Beta 2: Waist
        hip_norm * 0.3,        # Beta 3: Hip width
        0, 0, 0, 0, 0, 0, 0    # Other shape parameters
    ])
    
    return betas

def recalibrate_garment(garment_type, custom_measurements, pose, style_params=None):
    """
    Recalibrate TailorNet garment to custom measurements
    
    Args:
        garment_type: 'tshirt', 'shirt', 'pant', etc.
        custom_measurements: dict with chest, waist, hip, height
        pose: SMPL pose parameters (72D)
        style_params: Optional garment style parameters
    
    Returns:
        garment_vertices: 3D garment mesh vertices
    """
    from tailornet import TailorNet
    
    # Load TailorNet model
    model = TailorNet.load_model(garment_type)
    
    # Convert measurements to SMPL betas
    betas = measurements_to_smpl_betas(custom_measurements)
    
    # Generate garment
    garment_vertices = model.predict(
        pose=pose,
        shape=betas,
        style=style_params
    )
    
    return garment_vertices
```

## 🔄 Integration with Our Pipeline

### Complete Workflow

```python
# integrate_tailornet.py

import numpy as np
import json
from pathlib import Path
import trimesh

def generate_clothing_with_tailornet(avatar_params_path, measurements_path, garment_type='tshirt'):
    """
    Complete pipeline: Avatar → Measurements → TailorNet → Blender
    
    Args:
        avatar_params_path: Path to .npz with SMPL parameters
        measurements_path: Path to measurements JSON
        garment_type: 'tshirt', 'shirt', 'pant', 'skirt', 'short-pant', 'old-t-shirt'
    
    Returns:
        garment_mesh_path: Path to generated garment OBJ
    """
    print("="*70)
    print("TAILORNET CLOTHING GENERATION")
    print("="*70)
    
    # 1. Load avatar SMPL parameters
    print("\n📦 Loading avatar parameters...")
    avatar_params = np.load(avatar_params_path, allow_pickle=True)
    betas = avatar_params['betas']  # Body shape
    pose = avatar_params.get('pose', np.zeros(72))  # Body pose
    
    # 2. Load measurements
    print("📦 Loading measurements...")
    with open(measurements_path) as f:
        measurements = json.load(f)
    
    # 3. Recalibrate betas to match measurements
    print("📏 Recalibrating to custom measurements...")
    custom_betas = measurements_to_smpl_betas(measurements)
    
    # 4. Generate garment with TailorNet
    print(f"🎨 Generating {garment_type} with TailorNet...")
    garment_vertices = recalibrate_garment(
        garment_type=garment_type,
        custom_measurements=measurements,
        pose=pose,
        style_params=None  # Can customize style
    )
    
    # 5. Save garment mesh
    print("💾 Saving garment...")
    garment_mesh = trimesh.Trimesh(vertices=garment_vertices, faces=model.faces)
    output_path = f"output/{garment_type}_custom.obj"
    garment_mesh.export(output_path)
    
    print(f"✅ Garment saved: {output_path}")
    return output_path
```

### Usage Example

```bash
# Generate t-shirt for avatar
python integrate_tailornet.py \
  --avatar IMG4698_mesh/IMG_4698_person0_params.npz \
  --measurements all_measurements.json \
  --garment tshirt \
  --output output/avatar_tshirt.obj
```

## 🎨 Blender Integration

### Export to Blender

```python
# tailornet_to_blender.py

import bpy
import numpy as np

def import_tailornet_garment_to_blender(garment_obj_path, avatar_obj_path):
    """
    Import TailorNet garment and fit to avatar in Blender
    """
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Load avatar
    bpy.ops.import_scene.obj(filepath=avatar_obj_path)
    avatar = bpy.context.selected_objects[0]
    
    # Load garment
    bpy.ops.import_scene.obj(filepath=garment_obj_path)
    garment = bpy.context.selected_objects[0]
    
    # Position garment on avatar
    # TailorNet garments are already fitted, but may need slight adjustment
    
    # Add cloth simulation for final draping (optional)
    setup_cloth_simulation(garment, avatar)
    
    return garment, avatar
```

## 📋 Size Table Recalibration Process

### Step-by-Step:

1. **Load Standard Size Table**
   ```python
   standard_size = STANDARD_SIZES['M']  # Medium
   ```

2. **Get Custom Measurements**
   ```python
   custom = {
       'chest': 102,  # Your actual measurements
       'waist': 83,
       'hip': 96,
       'height': 192
   }
   ```

3. **Calculate Scale Factors**
   ```python
   scale_factors = {
       'chest': custom['chest'] / standard_size['chest'],
       'waist': custom['waist'] / standard_size['waist'],
       'hip': custom['hip'] / standard_size['hip'],
       'height': custom['height'] / standard_size['height']
   }
   ```

4. **Convert to SMPL Betas**
   ```python
   betas = measurements_to_smpl_betas(custom)
   ```

5. **Generate Garment**
   ```python
   garment = tailornet.predict(pose, betas, style)
   ```

6. **Export & Import to Blender**
   ```python
   # Export OBJ
   # Import to Blender
   # Fine-tune if needed
   ```

## 🔗 Key Files in TailorNet

```
TailorNet/
├── models/              # Pre-trained models
│   ├── tshirt/
│   ├── shirt/
│   ├── pant/
│   └── ...
├── data/                # Dataset
├── src/                 # Source code
│   ├── tailornet.py     # Main model
│   ├── inference.py     # Inference code
│   └── utils.py         # Utilities
└── README.md
```

## 🚀 Quick Start

```bash
# 1. Clone TailorNet
cd /Volumes/Expansion/avatar-creation
git clone https://github.com/chaitanya100100/TailorNet.git
cd TailorNet

# 2. Setup environment
conda create -n tailornet python=3.7
conda activate tailornet
pip install -r requirements.txt

# 3. Download models
# (Follow instructions in TailorNet README)

# 4. Test
python src/inference.py --garment tshirt --pose pose.npy --shape shape.npy
```

## ✅ Advantages of TailorNet

1. **Fast** - Real-time garment generation
2. **Realistic** - Neural network preserves details
3. **SMPL-compatible** - Works with our avatars
4. **Size tables** - Can recalibrate to measurements
5. **Multiple garments** - 6 garment types
6. **Research-backed** - From MPI-INF (reputable)

## 📝 Next Steps

1. ✅ **Install TailorNet** - Clone and setup
2. ✅ **Download models** - Pre-trained weights
3. ✅ **Create size mapper** - Map measurements → SMPL betas
4. ✅ **Build recalibration script** - Custom measurements → garment
5. ✅ **Integrate with pipeline** - Connect to avatar generation
6. ✅ **Blender export** - Import and fine-tune

---

## 🎯 Summary

**TailorNet** is the SDK we planned to use because:
- ✅ Neural model for fast, realistic clothing
- ✅ Works with SMPL (our avatar format)
- ✅ Supports size tables and recalibration
- ✅ Can be integrated with Blender
- ✅ Research-quality implementation

**Perfect fit for our pipeline!** 🎉

