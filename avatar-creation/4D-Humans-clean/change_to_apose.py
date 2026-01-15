"""
Change pose to A-pose - Working version using rotation matrices
"""
import numpy as np
import torch
import trimesh
import argparse
from pathlib import Path
import os
os.environ['PYOPENGL_PLATFORM'] = ''

def axis_angle_to_rotation_matrix(axis_angle):
    """Convert axis-angle to rotation matrix using Rodrigues formula"""
    # axis_angle shape: (batch, n_joints, 3) or (batch, 3)
    
    batch_shape = axis_angle.shape[:-1]
    axis_angle_flat = axis_angle.reshape(-1, 3)
    
    angle = torch.norm(axis_angle_flat + 1e-8, dim=1, keepdim=True)
    axis = axis_angle_flat / angle
    
    cos = torch.cos(angle)
    sin = torch.sin(angle)
    one_minus_cos = 1.0 - cos
    
    x, y, z = axis[:, 0:1], axis[:, 1:2], axis[:, 2:3]
    
    # Rodrigues' rotation formula
    rot_mat = torch.zeros((axis_angle_flat.shape[0], 3, 3), device=axis_angle.device)
    
    rot_mat[:, 0, 0] = (cos + x * x * one_minus_cos).squeeze()
    rot_mat[:, 0, 1] = (x * y * one_minus_cos - z * sin).squeeze()
    rot_mat[:, 0, 2] = (x * z * one_minus_cos + y * sin).squeeze()
    
    rot_mat[:, 1, 0] = (y * x * one_minus_cos + z * sin).squeeze()
    rot_mat[:, 1, 1] = (cos + y * y * one_minus_cos).squeeze()
    rot_mat[:, 1, 2] = (y * z * one_minus_cos - x * sin).squeeze()
    
    rot_mat[:, 2, 0] = (z * x * one_minus_cos - y * sin).squeeze()
    rot_mat[:, 2, 1] = (z * y * one_minus_cos + x * sin).squeeze()
    rot_mat[:, 2, 2] = (cos + z * z * one_minus_cos).squeeze()
    
    return rot_mat.reshape(batch_shape + (3, 3))

def create_apose_mesh(params_file, output_obj, target_height_cm=192):
    """Create A-pose mesh"""
    
    print(f"\n{'='*70}")
    print("CHANGING TO A-POSE (STANDING WITH ARMS OUT)")
    print(f"{'='*70}\n")
    
    # Load parameters
    print(f"📦 Loading: {params_file}")
    data = np.load(params_file)
    betas = data['betas']
    print(f"   ✓ Body shape: {betas.shape}")
    
    # Load SMPL
    print("\n🎨 Loading SMPL model...")
    from hmr2.models.smpl_wrapper import SMPL
    from hmr2.configs import CACHE_DIR_4DHUMANS
    
    smpl = SMPL(f'{CACHE_DIR_4DHUMANS}/data/smpl', batch_size=1)
    
    # Prepare inputs
    betas_tensor = torch.from_numpy(betas).float().unsqueeze(0)  # (1, 10)
    
    # Create A-pose using axis-angle then convert to rotation matrix
    print("\n🧍 Setting up A-pose...")
    
    # Body pose: 23 joints in axis-angle
    body_pose_aa = torch.zeros(1, 23, 3)
    body_pose_aa[0, 15, 2] = 0.4  # Left shoulder - arm out
    body_pose_aa[0, 16, 2] = -0.4  # Right shoulder - arm out
    
    # Convert to rotation matrices
    body_pose_rotmat = axis_angle_to_rotation_matrix(body_pose_aa).reshape(1, 23, 3, 3)
    
    # Global orient (standing upright)
    global_orient_aa = torch.zeros(1, 3)
    global_orient_rotmat = axis_angle_to_rotation_matrix(global_orient_aa.unsqueeze(1)).reshape(1, 1, 3, 3)
    
    print("   ✓ Pose configured")
    
    # Generate mesh
    print("\n🔨 Generating mesh...")
    with torch.no_grad():
        output = smpl(
            betas=betas_tensor,
            body_pose=body_pose_rotmat,
            global_orient=global_orient_rotmat,
            pose2rot=False  # We already have rotation matrices
        )
    
    vertices = output.vertices[0].cpu().numpy()
    faces = smpl.faces
    
    print(f"   ✓ Generated: {vertices.shape[0]} vertices")
    
    # Scale to target height
    print(f"\n📏 Scaling to {target_height_cm}cm...")
    current_height_m = vertices[:, 1].max() - vertices[:, 1].min()
    scale_factor = (target_height_cm / 100) / current_height_m
    vertices = vertices * scale_factor
    
    final_height_cm = (vertices[:, 1].max() - vertices[:, 1].min()) * 100
    print(f"   Final height: {final_height_cm:.1f}cm ✅")
    
    # Save
    print(f"\n💾 Saving...")
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    mesh.export(str(output_obj))
    print(f"   ✓ Saved: {output_obj}")
    
    print(f"\n{'='*70}")
    print("✅ A-POSE MESH CREATED!")
    print(f"{'='*70}")
    print(f"\n🚀 View it:")
    print(f"   open -a Blender {output_obj}")
    print()
    
    return output_obj

def main():
    parser = argparse.ArgumentParser(description='Change mesh to A-pose')
    parser.add_argument('--params', required=True, help='Input .npz parameters')
    parser.add_argument('--output', required=True, help='Output .obj file')
    parser.add_argument('--height', type=float, default=192, help='Height in cm')
    
    args = parser.parse_args()
    
    create_apose_mesh(args.params, args.output, args.height)

if __name__ == '__main__':
    main()

