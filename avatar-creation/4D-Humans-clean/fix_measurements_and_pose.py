"""
Fix measurements and create proper A-pose using SMPL model
This regenerates the mesh with correct body shape but neutral pose
"""
import numpy as np
import torch
import trimesh
import argparse
from pathlib import Path
import json
import sys

# Add SMPL path
sys.path.append('data/SMPL_python_v.1.1.0/smpl')

def load_smpl_params(params_path):
    """Load SMPL parameters from .npz file"""
    params = np.load(params_path, allow_pickle=True)
    return params

def calculate_measurements_from_vertices(vertices, actual_height_cm=None):
    """
    Calculate body measurements from mesh vertices
    If actual_height_cm is provided, scale all measurements accordingly
    """
    # Calculate mesh height
    mesh_height = (vertices[:, 1].max() - vertices[:, 1].min())
    
    # If actual height provided, calculate scale factor
    if actual_height_cm:
        mesh_height_cm = mesh_height * 100
        scale_factor = actual_height_cm / mesh_height_cm
        print(f"\n📏 Scaling mesh to match actual height:")
        print(f"   Mesh height: {mesh_height_cm:.2f} cm")
        print(f"   Actual height: {actual_height_cm:.2f} cm")
        print(f"   Scale factor: {scale_factor:.4f}")
    else:
        scale_factor = 1.0
    
    measurements = {}
    y_range = vertices[:, 1].max() - vertices[:, 1].min()
    
    # HEIGHT
    measurements['height_cm'] = (actual_height_cm if actual_height_cm else mesh_height * 100)
    
    # Helper function to measure circumference at a given height
    def measure_circumference_at_height(height_ratio, thickness_ratio=0.05):
        target_y = vertices[:, 1].min() + (y_range * height_ratio)
        slice_verts = vertices[np.abs(vertices[:, 1] - target_y) < (y_range * thickness_ratio)]
        
        if len(slice_verts) > 0:
            width = slice_verts[:, 0].max() - slice_verts[:, 0].min()
            depth = slice_verts[:, 2].max() - slice_verts[:, 2].min()
            # Circumference of ellipse approximation
            circumference = np.pi * (width + depth) / 2 * 100 * scale_factor
            return circumference
        return None
    
    # CHEST (75% up from ground)
    measurements['chest_circumference_cm'] = measure_circumference_at_height(0.75, 0.05)
    
    # WAIST (60% up)
    measurements['waist_circumference_cm'] = measure_circumference_at_height(0.60, 0.03)
    
    # HIP (50% up)
    measurements['hip_circumference_cm'] = measure_circumference_at_height(0.50, 0.05)
    
    # NECK (88% up)
    measurements['neck_circumference_cm'] = measure_circumference_at_height(0.88, 0.02)
    
    # SHOULDER WIDTH (85% up)
    shoulder_y = vertices[:, 1].min() + (y_range * 0.85)
    shoulder_verts = vertices[np.abs(vertices[:, 1] - shoulder_y) < (y_range * 0.02)]
    if len(shoulder_verts) > 0:
        measurements['shoulder_width_cm'] = (shoulder_verts[:, 0].max() - 
                                             shoulder_verts[:, 0].min()) * 100 * scale_factor
    
    # ARM LENGTH / SPAN
    measurements['arm_span_cm'] = (vertices[:, 0].max() - vertices[:, 0].min()) * 100 * scale_factor
    
    # INSEAM (approximate as 45% of height)
    measurements['inseam_cm'] = measurements['height_cm'] * 0.45
    
    # TORSO LENGTH (shoulder to hip)
    measurements['torso_length_cm'] = (y_range * 0.35) * 100 * scale_factor
    
    return measurements, scale_factor

def create_neutral_pose_smpl(betas, actual_height_cm=None):
    """
    Create SMPL mesh with neutral pose but same body shape
    
    Args:
        betas: SMPL shape parameters (body shape)
        actual_height_cm: Target height in cm (for scaling)
    
    Returns:
        vertices, faces, scale_factor
    """
    try:
        # Try to use the SMPL model from the hmr2 package
        from hmr2.models.smpl_wrapper import SMPL
        from hmr2.configs import CACHE_DIR_4DHUMANS
        
        # Initialize SMPL model
        smpl = SMPL(
            CACHE_DIR_4DHUMANS,
            batch_size=1,
            create_transl=False
        )
        
        # Convert betas to torch tensor
        if isinstance(betas, np.ndarray):
            betas_tensor = torch.from_numpy(betas).float().unsqueeze(0)
        else:
            betas_tensor = betas
        
        # Create neutral pose (all zeros)
        body_pose = torch.zeros(1, 69)  # 23 joints * 3 params each
        global_orient = torch.zeros(1, 3)
        
        # Generate mesh with neutral pose but input body shape
        output = smpl(
            betas=betas_tensor,
            body_pose=body_pose,
            global_orient=global_orient
        )
        
        vertices = output.vertices.detach().cpu().numpy()[0]
        faces = smpl.faces
        
        # Scale to match actual height if provided
        scale_factor = 1.0
        if actual_height_cm:
            mesh_height = (vertices[:, 1].max() - vertices[:, 1].min())
            mesh_height_cm = mesh_height * 100
            scale_factor = actual_height_cm / mesh_height_cm
            vertices = vertices * scale_factor
        
        return vertices, faces, scale_factor
        
    except Exception as e:
        print(f"Error using SMPL model: {e}")
        print("Falling back to manual pose normalization...")
        return None, None, 1.0

def main():
    parser = argparse.ArgumentParser(description='Fix measurements and create proper A-pose')
    parser.add_argument('--params', type=str, required=True, help='Path to .npz parameters file')
    parser.add_argument('--mesh', type=str, help='Path to original .obj mesh (optional)')
    parser.add_argument('--height', type=float, help='Your actual height in cm (e.g., 192)')
    parser.add_argument('--output', type=str, default='corrected_mesh.obj', help='Output mesh file')
    parser.add_argument('--measurements-output', type=str, default='corrected_measurements.json',
                        help='Output measurements JSON')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("FIXING MEASUREMENTS AND POSE")
    print("="*70)
    
    # Load SMPL parameters
    print(f"\n📦 Loading parameters from: {args.params}")
    params = load_smpl_params(args.params)
    
    # Extract betas (body shape parameters)
    if 'betas' not in params:
        print("❌ No betas found in parameters file!")
        return
    
    betas = params['betas']
    print(f"✓ Found body shape parameters (betas): {betas.shape}")
    
    # Try to create neutral pose mesh using SMPL
    print(f"\n🎨 Creating neutral A-pose with your body shape...")
    vertices, faces, scale_factor = create_neutral_pose_smpl(betas, args.height)
    
    if vertices is None:
        # Fallback: load original mesh and scale it
        if not args.mesh:
            print("❌ Need either SMPL to work or --mesh parameter!")
            return
        
        print(f"📦 Loading original mesh: {args.mesh}")
        mesh = trimesh.load(args.mesh)
        vertices = mesh.vertices
        faces = mesh.faces
        
        # Scale if height provided
        if args.height:
            mesh_height_cm = (vertices[:, 1].max() - vertices[:, 1].min()) * 100
            scale_factor = args.height / mesh_height_cm
            vertices = vertices * scale_factor
            print(f"✓ Scaled mesh by {scale_factor:.4f}")
    
    print(f"✓ Mesh created with {len(vertices)} vertices")
    
    # Calculate corrected measurements
    print(f"\n📏 Calculating corrected measurements...")
    measurements, _ = calculate_measurements_from_vertices(vertices, args.height)
    
    # Print measurements
    print("\n" + "="*70)
    print("CORRECTED BODY MEASUREMENTS")
    print("="*70)
    for key, value in measurements.items():
        if value is not None:
            print(f"{key:30s}: {value:7.2f}")
    print("="*70)
    
    # Save mesh
    print(f"\n💾 Saving corrected mesh to: {args.output}")
    corrected_mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    corrected_mesh.export(args.output)
    print(f"✓ Saved: {args.output}")
    
    # Save measurements
    measurements_dict = {k: float(v) if v is not None else None for k, v in measurements.items()}
    measurements_dict['scale_factor'] = float(scale_factor)
    measurements_dict['actual_height_cm'] = args.height if args.height else None
    
    with open(args.measurements_output, 'w') as f:
        json.dump(measurements_dict, f, indent=2)
    print(f"✓ Saved measurements: {args.measurements_output}")
    
    print("\n" + "="*70)
    print("✓ COMPLETE! Measurements and pose corrected")
    print("="*70)
    print(f"\nNext steps:")
    print(f"1. Open {args.output} in Blender")
    print(f"2. Verify measurements in {args.measurements_output}")
    print(f"3. Use for garment draping!")
    print()

if __name__ == '__main__':
    main()


