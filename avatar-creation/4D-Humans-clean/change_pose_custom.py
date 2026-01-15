"""
Create custom pose with specified arm angles
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

def create_custom_pose(params_file, output_obj, target_height_cm=192, arm_angle_degrees=70):
    """
    Create pose with custom arm angle
    
    Args:
        arm_angle_degrees: Angle from vertical (0° = straight down, 90° = horizontal)
                          70° = arms mostly down, slightly out
    """
    
    print(f"\n{'='*70}")
    print(f"CREATING CUSTOM POSE (Arms at {arm_angle_degrees}° from vertical)")
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
    
    # Calculate arm rotation in radians
    # For SMPL, we rotate around Z-axis (lateral rotation)
    # Positive for left arm (out), negative for right arm (out)
    arm_angle_rad = np.deg2rad(90 - arm_angle_degrees)  # Convert from vertical to horizontal reference
    
    print(f"\n🧍 Setting arm angle: {arm_angle_degrees}° from vertical")
    print(f"   = {90 - arm_angle_degrees}° from horizontal")
    print(f"   = {arm_angle_rad:.3f} radians")
    
    # Body pose: 23 joints in axis-angle
    body_pose_aa = torch.zeros(1, 23, 3)
    
    # Shoulder joints (15 = left shoulder, 16 = right shoulder)
    # Rotate around Z-axis (axis_angle[..., 2])
    body_pose_aa[0, 15, 2] = arm_angle_rad   # Left arm
    body_pose_aa[0, 16, 2] = -arm_angle_rad  # Right arm (negative for symmetry)
    
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
            pose2rot=False
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
    
    # Quick measurements
    print(f"\n📐 Quick measurements:")
    y_min = vertices[:, 1].min()
    y_max = vertices[:, 1].max()
    y_range = y_max - y_min
    
    chest_y = y_min + (y_range * 0.75)
    chest_mask = np.abs(vertices[:, 1] - chest_y) < (y_range * 0.04)
    if chest_mask.sum() > 0:
        chest_verts = vertices[chest_mask]
        width = chest_verts[:, 0].max() - chest_verts[:, 0].min()
        depth = chest_verts[:, 2].max() - chest_verts[:, 2].min()
        chest_circ = np.pi * (width + depth) / 2 * 100
        print(f"   Chest: {chest_circ:.1f}cm")
    
    # Arm span
    arm_span = (vertices[:, 0].max() - vertices[:, 0].min()) * 100
    print(f"   Arm span: {arm_span:.1f}cm")
    
    print(f"\n{'='*70}")
    print(f"✅ CUSTOM POSE CREATED!")
    print(f"{'='*70}")
    print(f"\n💡 Arm angle reference:")
    print(f"   0° = Arms straight down (hanging)")
    print(f"   20° = Very slight angle (relaxed)")
    print(f"   45° = Standard A-pose")
    print(f"   70° = Your current pose (arms mostly down) ✅")
    print(f"   90° = T-pose (arms horizontal)")
    print(f"\n🚀 View it:")
    print(f"   open -a Blender {output_obj}")
    print()
    
    return output_obj

def main():
    parser = argparse.ArgumentParser(
        description='Create mesh with custom arm angle',
        epilog='''
Examples:
  # Arms at 70° from vertical (mostly down, slightly out)
  python change_pose_custom.py --params params.npz --output mesh.obj --arm-angle 70
  
  # Arms at 20° (very relaxed, almost straight down)
  python change_pose_custom.py --params params.npz --output mesh.obj --arm-angle 20
  
  # Standard A-pose (45°)
  python change_pose_custom.py --params params.npz --output mesh.obj --arm-angle 45
  
  # T-pose (90° horizontal)
  python change_pose_custom.py --params params.npz --output mesh.obj --arm-angle 90
        '''
    )
    parser.add_argument('--params', required=True, help='Input .npz parameters file')
    parser.add_argument('--output', required=True, help='Output .obj mesh file')
    parser.add_argument('--height', type=float, default=192, help='Target height in cm (default: 192)')
    parser.add_argument('--arm-angle', type=float, default=70, 
                       help='Arm angle from vertical in degrees (0=down, 90=horizontal, default: 70)')
    
    args = parser.parse_args()
    
    # Validate arm angle
    if not 0 <= args.arm_angle <= 90:
        print(f"⚠️  Warning: Arm angle {args.arm_angle}° is outside normal range (0-90°)")
        print("   Continuing anyway...")
    
    create_custom_pose(args.params, args.output, args.height, args.arm_angle)

if __name__ == '__main__':
    main()


