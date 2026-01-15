#!/usr/bin/env python3
"""
Complete Pipeline: Avatar → Measurements → TailorNet → Garment → Blender
Connects all our tools together!
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
tailornet_root = project_root.parent / 'TailorNet'
sys.path.insert(0, str(tailornet_root))

def run_complete_pipeline(image_path, output_dir, height_cm, garment_type='t-shirt', gender='male'):
    """
    Complete pipeline from photo to garment-ready avatar
    
    Steps:
    1. Generate 3D avatar from photo
    2. Create relaxed pose rig
    3. Extract measurements
    4. Generate garment with TailorNet
    5. Export for Blender
    """
    print("\n" + "="*70)
    print("COMPLETE AVATAR TO GARMENT PIPELINE")
    print("="*70)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Generate 3D avatar
    print("\n📸 Step 1: Generating 3D avatar from photo...")
    from demo_yolo import main as demo_main
    import subprocess
    
    avatar_output = output_path / "avatar_mesh"
    avatar_output.mkdir(exist_ok=True)
    
    # Run demo_yolo
    print(f"   Processing: {image_path}")
    result = subprocess.run([
        sys.executable, 
        str(project_root / "demo_yolo.py"),
        "--img_folder", str(image_path),
        "--out_folder", str(avatar_output)
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"   ❌ Error generating avatar: {result.stderr}")
        return None
    
    # Find generated mesh
    mesh_files = list(avatar_output.glob("*person0.obj"))
    params_files = list(avatar_output.glob("*person0_params.npz"))
    
    if not mesh_files:
        print("   ❌ No mesh generated")
        return None
    
    mesh_file = mesh_files[0]
    params_file = params_files[0] if params_files else None
    
    print(f"   ✓ Avatar generated: {mesh_file.name}")
    
    # Step 2: Create relaxed pose rig
    print("\n🧍 Step 2: Creating relaxed pose rig...")
    if params_file:
        relaxed_rig = output_path / "relaxed_rig.obj"
        result = subprocess.run([
            sys.executable,
            str(project_root / "final_relaxed_rig.py"),
            "--params", str(params_file),
            "--height", str(height_cm),
            "--output", str(relaxed_rig)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"   ✓ Relaxed rig created: {relaxed_rig.name}")
        else:
            print(f"   ⚠️  Could not create relaxed rig, using original mesh")
            relaxed_rig = mesh_file
    else:
        relaxed_rig = mesh_file
        print(f"   ⏭️  Using original mesh (no params file)")
    
    # Step 3: Extract measurements
    print("\n📏 Step 3: Extracting body measurements...")
    measurements_file = output_path / "measurements.json"
    result = subprocess.run([
        sys.executable,
        str(project_root / "extract_measurements_improved.py"),
        "--mesh", str(relaxed_rig),
        "--height", str(height_cm),
        "--output", str(measurements_file)
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"   ❌ Error extracting measurements: {result.stderr}")
        return None
    
    # Load measurements
    with open(measurements_file) as f:
        measurements = json.load(f)
    
    print(f"   ✓ Measurements extracted:")
    print(f"      Chest: {measurements.get('chest_circumference_cm', 'N/A'):.1f}cm")
    print(f"      Waist: {measurements.get('waist_circumference_cm', 'N/A'):.1f}cm")
    print(f"      Hip: {measurements.get('hip_circumference_cm', 'N/A'):.1f}cm")
    
    # Step 4: Generate garment with TailorNet
    print(f"\n👕 Step 4: Generating {garment_type} with TailorNet...")
    garment_file = output_path / f"{garment_type}_custom.obj"
    
    # Prepare measurements dict for TailorNet
    tailornet_measurements = {
        'chest': measurements.get('chest_circumference_cm', 96),
        'waist': measurements.get('waist_circumference_cm', 80),
        'hip': measurements.get('hip_circumference_cm', 100),
        'height': height_cm
    }
    
    # Save temp measurements file for TailorNet
    temp_meas = output_path / "temp_measurements.json"
    with open(temp_meas, 'w') as f:
        json.dump(tailornet_measurements, f)
    
    # Run TailorNet
    if params_file:
        result = subprocess.run([
            sys.executable,
            str(tailornet_root / "tailornet_size_recalibration.py"),
            "--garment", garment_type,
            "--gender", gender,
            "--measurements", str(temp_meas),
            "--pose", str(params_file),
            "--output", str(garment_file)
        ], capture_output=True, text=True, cwd=str(tailornet_root))
    else:
        result = subprocess.run([
            sys.executable,
            str(tailornet_root / "tailornet_size_recalibration.py"),
            "--garment", garment_type,
            "--gender", gender,
            "--measurements", str(temp_meas),
            "--output", str(garment_file)
        ], capture_output=True, text=True, cwd=str(tailornet_root))
    
    if result.returncode != 0:
        print(f"   ⚠️  TailorNet error (dataset may not be ready yet):")
        print(f"      {result.stderr[:200]}")
        print(f"   💡 Continue to Step 5 to prepare Blender files anyway")
        garment_file = None
    else:
        print(f"   ✓ Garment generated: {garment_file.name}")
    
    # Step 5: Prepare Blender files
    print("\n🎨 Step 5: Preparing Blender files...")
    blender_dir = output_path / "blender_ready"
    blender_dir.mkdir(exist_ok=True)
    
    # Copy files
    import shutil
    shutil.copy(relaxed_rig, blender_dir / "avatar.obj")
    shutil.copy(measurements_file, blender_dir / "measurements.json")
    
    if garment_file and garment_file.exists():
        shutil.copy(garment_file, blender_dir / "garment.obj")
    
    # Create Blender import script
    blender_script = blender_dir / "import_to_blender.py"
    with open(blender_script, 'w') as f:
        f.write(f'''import bpy
import os

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import avatar
avatar_path = r"{blender_dir / 'avatar.obj'}"
bpy.ops.import_scene.obj(filepath=avatar_path)
avatar = bpy.context.selected_objects[0]
avatar.name = "Avatar"

# Import garment if available
garment_path = r"{blender_dir / 'garment.obj'}"
if os.path.exists(garment_path):
    bpy.ops.import_scene.obj(filepath=garment_path)
    garment = bpy.context.selected_objects[0]
    garment.name = "Garment"
    
    # Setup cloth simulation
    bpy.context.view_layer.objects.active = garment
    cloth_mod = garment.modifiers.new(name="Cloth", type='CLOTH')
    cloth_mod.settings.quality = 5
    
    # Avatar as collision
    bpy.context.view_layer.objects.active = avatar
    collision_mod = avatar.modifiers.new(name="Collision", type='COLLISION')

print("✅ Avatar and garment imported to Blender!")
print("   - Avatar: Ready for garment draping")
print("   - Garment: Cloth simulation ready")
''')
    
    print(f"   ✓ Blender files ready in: {blender_dir.name}/")
    print(f"      - avatar.obj")
    if garment_file:
        print(f"      - garment.obj")
    print(f"      - measurements.json")
    print(f"      - import_to_blender.py (run in Blender)")
    
    # Cleanup
    temp_meas.unlink()
    
    print("\n" + "="*70)
    print("✅ PIPELINE COMPLETE!")
    print("="*70)
    print(f"\n📁 Output directory: {output_path}")
    print(f"🎨 Blender ready: {blender_dir}/")
    print(f"\n🚀 Next: Open Blender and run import_to_blender.py")
    print()
    
    return {
        'avatar': relaxed_rig,
        'garment': garment_file,
        'measurements': measurements_file,
        'blender_dir': blender_dir
    }

def main():
    parser = argparse.ArgumentParser(
        description='Complete pipeline: Photo → Avatar → Garment',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Generate avatar and t-shirt from photo
  python avatar_to_garment_pipeline.py \\
    --image photo.jpg \\
    --height 192 \\
    --output output/ \\
    --garment t-shirt \\
    --gender male
        '''
    )
    
    parser.add_argument('--image', type=str, required=True,
                       help='Input photo path')
    parser.add_argument('--output', type=str, required=True,
                       help='Output directory')
    parser.add_argument('--height', type=float, required=True,
                       help='Person height in cm')
    parser.add_argument('--garment', type=str, default='t-shirt',
                       choices=['t-shirt', 'shirt', 'pant', 'skirt', 'short-pant', 'old-t-shirt'],
                       help='Garment type')
    parser.add_argument('--gender', type=str, default='male',
                       choices=['male', 'female', 'neutral'],
                       help='Gender')
    
    args = parser.parse_args()
    
    if not Path(args.image).exists():
        print(f"❌ Error: Image file not found: {args.image}")
        return 1
    
    result = run_complete_pipeline(
        args.image,
        args.output,
        args.height,
        args.garment,
        args.gender
    )
    
    if result:
        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(main())

