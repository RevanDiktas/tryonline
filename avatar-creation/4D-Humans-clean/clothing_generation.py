#!/usr/bin/env python3
"""
Clothing Generation Pipeline using Blender Python SDK (bpy)
Run with: blender --background --python clothing_generation.py -- <args>
"""

import bpy
import bmesh
import json
import sys
import argparse
from pathlib import Path
from mathutils import Vector, Matrix

def clear_scene():
    """Remove all objects from scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def load_mesh(mesh_path):
    """Load OBJ mesh into Blender"""
    try:
        bpy.ops.wm.obj_import(filepath=str(mesh_path))
    except:
        # Fallback for older Blender versions
        bpy.ops.import_scene.obj(filepath=str(mesh_path))
    
    obj = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = obj
    return obj

def load_avatar_and_garment(avatar_path, garment_path):
    """Load avatar mesh and garment template"""
    clear_scene()
    
    # Load avatar
    print(f"   Loading avatar: {avatar_path}")
    avatar = load_mesh(avatar_path)
    avatar.name = "Avatar"
    
    # Load garment
    print(f"   Loading garment: {garment_path}")
    garment = load_mesh(garment_path)
    garment.name = "Garment"
    
    return avatar, garment

def get_bounding_box(obj):
    """Get bounding box dimensions of object"""
    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    
    x_coords = [v.x for v in bbox_corners]
    y_coords = [v.y for v in bbox_corners]
    z_coords = [v.z for v in bbox_corners]
    
    return {
        'width': max(x_coords) - min(x_coords),
        'depth': max(y_coords) - min(y_coords),
        'height': max(z_coords) - min(z_coords),
        'center': Vector((
            sum(x_coords) / 8,
            sum(y_coords) / 8,
            sum(z_coords) / 8
        ))
    }

def scale_garment_to_measurements(garment, measurements):
    """
    Scale garment based on body measurements
    
    Uses chest, waist, and hip measurements to scale appropriately
    """
    print("   Scaling garment to measurements...")
    
    # Get current garment dimensions
    garment_bbox = get_bounding_box(garment)
    current_width = garment_bbox['width']
    
    # Use chest measurement as primary scale reference
    if 'chest_circumference_cm' in measurements:
        target_chest = measurements['chest_circumference_cm'] / 100  # Convert cm to meters
        
        # Approximate: chest circumference ≈ 2 * width (for simple shapes)
        # More accurate would use actual garment template measurements
        target_width = target_chest / 2
        
        scale_factor = target_width / current_width if current_width > 0 else 1.0
        
        # Apply scale
        garment.scale = (scale_factor, scale_factor, scale_factor)
        
        print(f"      Chest: {measurements['chest_circumference_cm']:.1f}cm")
        print(f"      Scale factor: {scale_factor:.3f}")
    
    return garment

def position_garment_on_avatar(garment, avatar):
    """Position garment over avatar body"""
    print("   Positioning garment on avatar...")
    
    # Get centers
    avatar_bbox = get_bounding_box(avatar)
    garment_bbox = get_bounding_box(garment)
    
    # Align centers (X and Y)
    offset = Vector((
        avatar_bbox['center'].x - garment_bbox['center'].x,
        avatar_bbox['center'].y - garment_bbox['center'].y,
        0  # Z will be adjusted separately
    ))
    
    garment.location += offset
    
    # Position garment at chest level (approximately)
    # This is a simplified approach - real implementation would use measurements
    chest_height = avatar_bbox['center'].z + (avatar_bbox['height'] * 0.3)
    garment.location.z = chest_height
    
    print(f"      Positioned at Z: {chest_height:.3f}m")
    
    return garment

def setup_cloth_simulation(garment, avatar):
    """
    Setup cloth physics for garment draping
    """
    print("   Setting up cloth simulation...")
    
    # Select garment
    bpy.context.view_layer.objects.active = garment
    garment.select_set(True)
    
    # Add Cloth modifier
    cloth_mod = garment.modifiers.new(name="Cloth", type='CLOTH')
    
    # Cloth physics settings
    cloth_mod.settings.quality = 5
    cloth_mod.settings.time_scale = 1.0
    cloth_mod.settings.mass = 0.3
    cloth_mod.settings.air_damping = 0.5
    cloth_mod.settings.bending_model = 'ANGULAR'
    
    # Collision settings
    cloth_mod.collision_settings.collision_quality = 3
    cloth_mod.collision_settings.distance_min = 0.01
    cloth_mod.collision_settings.self_distance_min = 0.01
    
    # Setup avatar as collision object
    bpy.context.view_layer.objects.active = avatar
    avatar.select_set(True)
    
    # Add Collision modifier to avatar
    collision_mod = avatar.modifiers.new(name="Collision", type='COLLISION')
    collision_mod.settings.distance = 0.01
    collision_mod.settings.thickness_outer = 0.02
    collision_mod.settings.thickness_inner = 0.01
    
    print("      ✓ Cloth modifier added")
    print("      ✓ Collision modifier added")
    
    return cloth_mod, collision_mod

def run_simulation(garment, frame_count=100):
    """Run cloth simulation for specified frames"""
    print(f"   Running simulation ({frame_count} frames)...")
    
    # Set animation range
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_count
    
    # Run simulation frame by frame
    for frame in range(1, frame_count + 1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        
        if frame % 20 == 0:
            print(f"      Frame {frame}/{frame_count}")
    
    print("      ✓ Simulation complete")

def apply_cloth_modifier(garment):
    """Apply cloth modifier to bake result into mesh"""
    print("   Applying cloth modifier...")
    
    bpy.context.view_layer.objects.active = garment
    garment.select_set(True)
    
    # Apply modifier
    for mod in garment.modifiers:
        if mod.type == 'CLOTH':
            bpy.ops.object.modifier_apply(modifier=mod.name)
            break
    
    print("      ✓ Modifier applied")

def export_result(output_path, export_format='obj'):
    """Export final result"""
    print(f"   Exporting to: {output_path}")
    
    if export_format.lower() == 'obj':
        bpy.ops.export_scene.obj(
            filepath=str(output_path),
            use_selection=True,
            use_materials=True
        )
    elif export_format.lower() == 'fbx':
        bpy.ops.export_scene.fbx(
            filepath=str(output_path),
            use_selection=True
        )
    elif export_format.lower() == 'glb':
        bpy.ops.export_scene.gltf(
            filepath=str(output_path),
            use_selection=True,
            export_format='GLB'
        )
    
    print(f"      ✓ Exported: {output_path}")

def generate_clothing(avatar_path, garment_path, measurements_path, output_path, 
                     run_sim=True, sim_frames=100, export_format='obj'):
    """
    Complete clothing generation pipeline
    """
    print("\n" + "="*70)
    print("CLOTHING GENERATION PIPELINE")
    print("="*70)
    
    # Load measurements
    print("\n📦 Loading measurements...")
    with open(measurements_path) as f:
        measurements = json.load(f)
    print(f"   ✓ Measurements loaded")
    
    # Load meshes
    print("\n📦 Loading meshes...")
    avatar, garment = load_avatar_and_garment(avatar_path, garment_path)
    print(f"   ✓ Avatar: {avatar.name}")
    print(f"   ✓ Garment: {garment.name}")
    
    # Scale garment
    print("\n📏 Scaling garment...")
    scale_garment_to_measurements(garment, measurements)
    
    # Position garment
    print("\n📍 Positioning garment...")
    position_garment_on_avatar(garment, avatar)
    
    # Setup simulation
    print("\n🎨 Setting up simulation...")
    setup_cloth_simulation(garment, avatar)
    
    # Run simulation (optional)
    if run_sim:
        print("\n🎬 Running simulation...")
        run_simulation(garment, sim_frames)
        apply_cloth_modifier(garment)
    
    # Export result
    print("\n💾 Exporting result...")
    export_result(output_path, export_format)
    
    print("\n" + "="*70)
    print("✅ CLOTHING GENERATION COMPLETE!")
    print("="*70)
    print(f"\n📁 Output: {output_path}")

def main():
    """Main entry point - handles command line arguments"""
    # When run from Blender, sys.argv includes Blender's args
    # We need to find our arguments after '--'
    
    if '--' in sys.argv:
        args = sys.argv[sys.argv.index('--') + 1:]
    else:
        # If not run from Blender, use argparse
        parser = argparse.ArgumentParser(description='Generate clothing on avatar')
        parser.add_argument('--avatar', required=True, help='Avatar mesh path')
        parser.add_argument('--garment', required=True, help='Garment template path')
        parser.add_argument('--measurements', required=True, help='Measurements JSON')
        parser.add_argument('--output', required=True, help='Output path')
        parser.add_argument('--no-sim', action='store_true', help='Skip simulation')
        parser.add_argument('--frames', type=int, default=100, help='Simulation frames')
        parser.add_argument('--format', default='obj', choices=['obj', 'fbx', 'glb'], help='Export format')
        
        args = parser.parse_args()
        args = [args.avatar, args.garment, args.measurements, args.output, 
                '--no-sim' if args.no_sim else '', str(args.frames), args.format]
    
    if len(args) < 4:
        print("Usage: blender --background --python clothing_generation.py -- <avatar.obj> <garment.obj> <measurements.json> <output.obj> [--no-sim] [frames] [format]")
        return
    
    avatar_path = Path(args[0])
    garment_path = Path(args[1])
    measurements_path = Path(args[2])
    output_path = Path(args[3])
    
    run_sim = '--no-sim' not in args
    sim_frames = int(args[5]) if len(args) > 5 else 100
    export_format = args[6] if len(args) > 6 else 'obj'
    
    # Validate paths
    if not avatar_path.exists():
        print(f"❌ Error: Avatar file not found: {avatar_path}")
        return
    
    if not garment_path.exists():
        print(f"❌ Error: Garment file not found: {garment_path}")
        return
    
    if not measurements_path.exists():
        print(f"❌ Error: Measurements file not found: {measurements_path}")
        return
    
    # Run pipeline
    generate_clothing(
        avatar_path, 
        garment_path, 
        measurements_path, 
        output_path,
        run_sim=run_sim,
        sim_frames=sim_frames,
        export_format=export_format
    )

if __name__ == '__main__':
    main()

