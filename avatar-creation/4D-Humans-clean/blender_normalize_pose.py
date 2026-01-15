"""
Blender script to normalize SMPL mesh pose to T-pose or A-pose
Run this inside Blender or with: blender --background --python blender_normalize_pose.py
"""
import bpy
import bmesh
import numpy as np
import sys
import json
from pathlib import Path
from mathutils import Vector, Matrix, Euler

def clear_scene():
    """Remove all objects from scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def load_mesh(mesh_path):
    """Load OBJ mesh into Blender"""
    bpy.ops.import_scene.obj(filepath=str(mesh_path))
    obj = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = obj
    return obj

def normalize_to_t_pose(obj):
    """
    Normalize mesh to T-pose
    - Straighten spine (vertical)
    - Arms horizontal at sides
    - Legs together and straight
    """
    mesh = obj.data
    vertices = mesh.vertices
    
    # Get current vertex positions
    verts = np.array([v.co for v in vertices])
    
    # Calculate bounding box to understand current pose
    min_y = verts[:, 1].min()
    max_y = verts[:, 1].max()
    height = max_y - min_y
    
    # Straighten vertical axis (remove any lean)
    # Center horizontally
    center_x = verts[:, 0].mean()
    center_z = verts[:, 2].mean()
    
    for v in vertices:
        # Center the mesh
        v.co.x -= center_x
        v.co.z -= center_z
        
        # Straighten spine - vertical adjustment
        y_ratio = (v.co.y - min_y) / height
        
        # Arms should be horizontal (T-pose)
        # Identify arm vertices (far from center in X)
        if abs(v.co.x) > 0.3:  # Likely arm
            # Raise arms to shoulder level
            if y_ratio > 0.7 and y_ratio < 0.9:  # Shoulder height
                # Extend arms horizontally
                target_y = min_y + (height * 0.80)
                v.co.y = target_y
    
    # Update mesh
    mesh.update()
    obj.location = (0, 0, 0)
    
    return obj

def normalize_to_a_pose(obj):
    """
    Normalize mesh to A-pose (arms at 45 degrees)
    Better for garment draping
    """
    mesh = obj.data
    vertices = mesh.vertices
    
    verts = np.array([v.co for v in vertices])
    
    min_y = verts[:, 1].min()
    max_y = verts[:, 1].max()
    height = max_y - min_y
    
    # Center the mesh
    center_x = verts[:, 0].mean()
    center_z = verts[:, 2].mean()
    
    for v in vertices:
        v.co.x -= center_x
        v.co.z -= center_z
        
        y_ratio = (v.co.y - min_y) / height
        
        # A-pose: arms at 45 degrees downward
        if abs(v.co.x) > 0.25:  # Arm vertices
            if y_ratio > 0.6 and y_ratio < 0.9:
                # Slight angle downward (A-pose)
                arm_angle = 0.3  # 30% down from horizontal
                target_y = min_y + (height * (0.80 - (y_ratio - 0.7) * arm_angle))
                v.co.y = target_y
    
    mesh.update()
    obj.location = (0, 0, 0)
    
    return obj

def add_skin_material(obj, skin_color=(0.76, 0.57, 0.45)):
    """Add realistic skin material"""
    mat = bpy.data.materials.new(name="Skin")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    
    if bsdf:
        # Skin color
        bsdf.inputs['Base Color'].default_value = (*skin_color, 1.0)
        
        # Subsurface scattering for realistic skin
        bsdf.inputs['Subsurface'].default_value = 0.15
        bsdf.inputs['Subsurface Color'].default_value = (0.8, 0.4, 0.3, 1.0)
        bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.2, 0.1)
        
        # Surface properties
        bsdf.inputs['Roughness'].default_value = 0.4
        bsdf.inputs['Specular'].default_value = 0.5
    
    # Assign material
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    
    return mat

def setup_camera_and_lights():
    """Setup good camera view and lighting"""
    # Add camera
    bpy.ops.object.camera_add(location=(3, -3, 1.5))
    camera = bpy.context.object
    camera.rotation_euler = (1.1, 0, 0.8)
    bpy.context.scene.camera = camera
    
    # Add key light
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 5))
    key_light = bpy.context.object
    key_light.data.energy = 2.0
    
    # Add fill light
    bpy.ops.object.light_add(type='AREA', location=(-3, -2, 2))
    fill_light = bpy.context.object
    fill_light.data.energy = 100
    
    return camera

def main(mesh_path, output_path, pose_type='a-pose', add_material=True):
    """
    Main function to normalize pose
    
    Args:
        mesh_path: Path to input .obj mesh
        output_path: Path to save normalized mesh
        pose_type: 't-pose' or 'a-pose'
        add_material: Whether to add skin material
    """
    print(f"\n{'='*60}")
    print(f"Normalizing {mesh_path} to {pose_type.upper()}")
    print(f"{'='*60}\n")
    
    # Clear scene
    clear_scene()
    
    # Load mesh
    print("Loading mesh...")
    obj = load_mesh(mesh_path)
    print(f"✓ Loaded: {obj.name}")
    
    # Normalize pose
    print(f"Normalizing to {pose_type}...")
    if pose_type.lower() == 't-pose':
        obj = normalize_to_t_pose(obj)
    else:  # Default to A-pose
        obj = normalize_to_a_pose(obj)
    print(f"✓ Pose normalized")
    
    # Add material
    if add_material:
        print("Adding skin material...")
        add_skin_material(obj)
        print("✓ Material added")
    
    # Setup scene
    print("Setting up scene...")
    setup_camera_and_lights()
    print("✓ Scene ready")
    
    # Export normalized mesh
    print(f"Exporting to {output_path}...")
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    # Export as OBJ
    bpy.ops.export_scene.obj(
        filepath=str(output_path),
        use_selection=True,
        use_materials=add_material,
        use_triangles=True
    )
    print(f"✓ Saved: {output_path}")
    
    # Also save Blender file
    blend_path = Path(output_path).with_suffix('.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"✓ Saved Blender file: {blend_path}")
    
    print(f"\n{'='*60}")
    print("✓ Complete! Mesh ready for garment draping")
    print(f"{'='*60}\n")
    
    return obj

# Command line usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Normalize SMPL mesh pose in Blender')
    parser.add_argument('--input', type=str, required=True, help='Input .obj mesh file')
    parser.add_argument('--output', type=str, required=True, help='Output .obj mesh file')
    parser.add_argument('--pose', type=str, default='a-pose', choices=['t-pose', 'a-pose'], 
                        help='Target pose type')
    parser.add_argument('--no-material', action='store_true', help='Skip adding material')
    
    args = parser.parse_args()
    
    main(
        mesh_path=args.input,
        output_path=args.output,
        pose_type=args.pose,
        add_material=not args.no_material
    )


