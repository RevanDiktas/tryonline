# Clothing Generation Using Blender Python SDK (bpy)

## 🎯 Overview

We're using **Blender's Python API (`bpy`)** - this is Blender's SDK for programmatic 3D operations!

**What we can do:**
- ✅ Load avatar meshes
- ✅ Import garment templates
- ✅ Scale garments to measurements
- ✅ Apply cloth simulation (draping)
- ✅ Export final results
- ✅ All programmatically (no manual Blender work!)

## 📚 Blender Python API (bpy) Reference

**Official Docs**: https://docs.blender.org/api/current/

**Key Modules:**
- `bpy` - Main Blender API
- `bmesh` - Mesh editing
- `mathutils` - Vector/matrix math
- `bpy.ops` - Operators (import, export, etc.)

## 🛠️ Our Existing bpy Scripts

We already have scripts using bpy:

1. **`blender_normalize_pose.py`** - Normalize mesh pose
2. **`normalize_pose_simple.sh`** - Wrapper script
3. **`create_mesh_animation.py`** - Animation setup

## 👕 Clothing Generation Pipeline

### Step 1: Load Avatar + Garment Template

```python
import bpy
import bmesh
from pathlib import Path

def load_avatar_and_garment(avatar_path, garment_path):
    """Load avatar mesh and garment template"""
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Load avatar
    bpy.ops.import_scene.obj(filepath=str(avatar_path))
    avatar = bpy.context.selected_objects[0]
    avatar.name = "Avatar"
    
    # Load garment
    bpy.ops.import_scene.obj(filepath=str(garment_path))
    garment = bpy.context.selected_objects[0]
    garment.name = "Garment"
    
    return avatar, garment
```

### Step 2: Scale Garment to Measurements

```python
def scale_garment_to_measurements(garment, measurements):
    """
    Scale garment based on body measurements
    
    Args:
        garment: Blender object (garment mesh)
        measurements: dict with chest, waist, hip, etc.
    """
    # Get garment bounding box
    bbox = [garment.matrix_world @ Vector(corner) 
            for corner in garment.bound_box]
    
    # Calculate current dimensions
    x_dim = max(v.x for v in bbox) - min(v.x for v in bbox)
    y_dim = max(v.y for v in bbox) - min(v.y for v in bbox)
    z_dim = max(v.z for v in bbox) - min(v.z for v in bbox)
    
    # Scale based on chest measurement (example)
    if 'chest_circumference_cm' in measurements:
        target_chest = measurements['chest_circumference_cm'] / 100  # Convert to meters
        current_chest = x_dim  # Approximate
        scale_factor = target_chest / current_chest
        
        garment.scale = (scale_factor, scale_factor, scale_factor)
    
    return garment
```

### Step 3: Position Garment on Avatar

```python
def position_garment_on_avatar(garment, avatar):
    """Position garment over avatar body"""
    # Get avatar center
    avatar_center = sum((Vector(b) for b in avatar.bound_box), Vector()) / 8
    
    # Get garment center
    garment_center = sum((Vector(b) for b in garment.bound_box), Vector()) / 8
    
    # Calculate offset
    offset = avatar_center - garment_center
    garment.location += offset
    
    # Adjust height (garment should start at chest level)
    # This is simplified - real implementation would use measurements
    garment.location.z += 0.1  # Slight offset above body
    
    return garment
```

### Step 4: Apply Cloth Simulation

```python
def setup_cloth_simulation(garment, avatar):
    """
    Setup cloth physics for garment draping
    
    Args:
        garment: Garment mesh object
        avatar: Avatar body mesh object
    """
    # Select garment
    bpy.context.view_layer.objects.active = garment
    garment.select_set(True)
    
    # Add Cloth modifier
    cloth_mod = garment.modifiers.new(name="Cloth", type='CLOTH')
    
    # Cloth settings
    cloth_mod.settings.quality = 5  # Higher = more accurate
    cloth_mod.settings.time_scale = 1.0
    cloth_mod.settings.mass = 0.3  # Fabric weight
    cloth_mod.settings.air_damping = 0.5
    
    # Collision settings
    cloth_mod.collision_settings.collision_quality = 3
    cloth_mod.collision_settings.distance_min = 0.01
    cloth_mod.collision_settings.self_distance_min = 0.01
    
    # Setup avatar as collision object
    avatar.select_set(True)
    bpy.context.view_layer.objects.active = avatar
    
    # Add Collision modifier to avatar
    collision_mod = avatar.modifiers.new(name="Collision", type='COLLISION')
    collision_mod.settings.distance = 0.01
    collision_mod.settings.thickness_outer = 0.02
    
    return cloth_mod, collision_mod
```

### Step 5: Run Simulation & Export

```python
def run_simulation_and_export(garment, output_path, frame_count=100):
    """
    Run cloth simulation and export result
    
    Args:
        garment: Garment object
        output_path: Path to save final mesh
        frame_count: Number of simulation frames
    """
    # Set up animation
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_count
    
    # Run simulation frame by frame
    for frame in range(1, frame_count + 1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
    
    # Apply cloth modifier (bake to mesh)
    bpy.context.view_layer.objects.active = garment
    bpy.ops.object.modifier_apply(modifier="Cloth")
    
    # Export result
    bpy.ops.export_scene.obj(
        filepath=str(output_path),
        use_selection=True,
        use_materials=True
    )
    
    print(f"✅ Exported draped garment to: {output_path}")
```

## 🚀 Complete Pipeline Script

```python
#!/usr/bin/env python3
"""
Complete clothing generation pipeline using Blender Python SDK
"""

import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

def generate_clothing(avatar_path, garment_template_path, measurements_path, output_path):
    """
    Complete pipeline: Load → Scale → Position → Simulate → Export
    """
    print("="*70)
    print("CLOTHING GENERATION PIPELINE")
    print("="*70)
    
    # Load measurements
    print("\n📦 Loading measurements...")
    with open(measurements_path) as f:
        measurements = json.load(f)
    print(f"   ✓ Loaded measurements")
    
    # Load meshes
    print("\n📦 Loading avatar and garment...")
    avatar, garment = load_avatar_and_garment(avatar_path, garment_template_path)
    print(f"   ✓ Avatar: {avatar.name}")
    print(f"   ✓ Garment: {garment.name}")
    
    # Scale garment
    print("\n📏 Scaling garment to measurements...")
    scale_garment_to_measurements(garment, measurements)
    print("   ✓ Garment scaled")
    
    # Position garment
    print("\n📍 Positioning garment on avatar...")
    position_garment_on_avatar(garment, avatar)
    print("   ✓ Garment positioned")
    
    # Setup simulation
    print("\n🎨 Setting up cloth simulation...")
    setup_cloth_simulation(garment, avatar)
    print("   ✓ Simulation ready")
    
    # Run simulation
    print("\n🎬 Running cloth simulation...")
    run_simulation_and_export(garment, output_path, frame_count=100)
    print("   ✓ Simulation complete")
    
    print("\n✅ Clothing generation complete!")
    print(f"   Output: {output_path}")

if __name__ == '__main__':
    # Run from command line
    if len(sys.argv) < 5:
        print("Usage: blender --background --python clothing_generation.py -- <avatar.obj> <garment.obj> <measurements.json> <output.obj>")
        sys.exit(1)
    
    avatar_path = Path(sys.argv[4])
    garment_path = Path(sys.argv[5])
    measurements_path = Path(sys.argv[6])
    output_path = Path(sys.argv[7])
    
    generate_clothing(avatar_path, garment_path, measurements_path, output_path)
```

## 📋 Usage

### Command Line

```bash
# Run in Blender (background mode)
blender --background --python clothing_generation.py -- \
  FINAL_RELAXED_RIG.obj \
  templates/tshirt_template.obj \
  all_measurements.json \
  output/avatar_with_shirt.obj
```

### From Python

```python
import bpy

# Run script inside Blender
exec(open('clothing_generation.py').read())
```

## 🎯 Next Steps

1. **Create garment templates** - Basic shapes (t-shirt, pants, etc.)
2. **Improve scaling algorithm** - Use all measurements (chest, waist, hip)
3. **Add texture support** - Apply fabric textures
4. **Batch processing** - Process multiple garments
5. **API wrapper** - FastAPI endpoint for web service

## 📚 Resources

- **Blender Python API Docs**: https://docs.blender.org/api/current/
- **Cloth Simulation**: https://docs.blender.org/manual/en/latest/physics/cloth.html
- **bpy Examples**: https://docs.blender.org/api/current/bpy_examples.html

---

**Status**: Ready to implement! We have all the pieces:
- ✅ Avatar meshes (FINAL_RELAXED_RIG.obj)
- ✅ Measurements (calibrated)
- ✅ Blender Python SDK (bpy)
- ⏳ Garment templates (need to create/download)

