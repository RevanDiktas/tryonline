"""
Test shoulder drop on different axes to find the right one
Arms stay neutral, only shoulders move
"""
import numpy as np
import torch
import trimesh
import argparse
from pathlib import Path
import os
os.environ['PYOPENGL_PLATFORM'] = ''

def axis_angle_to_rotation_matrix(axis_angle):
    """Convert axis-angle to rotation matrix"""
    batch_shape = axis_angle.shape[:-1]
    axis_angle_flat = axis_angle.reshape(-1, 3)
    
    angle = torch.norm(axis_angle_flat + 1e-8, dim=1, keepdim=True)
    axis = axis_angle_flat / angle
    
    cos = torch.cos(angle)
    sin = torch.sin(angle)
    one_minus_cos = 1.0 - cos
    
    x, y, z = axis[:, 0:1], axis[:, 1:2], axis[:, 2:3]
    
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

def test_shoulder_drop(params_file, output_obj, target_height_cm=192, axis='x', angle_deg=20):
    """
    Test shoulder drop on different axes
    
    Args:
        axis: 'x', 'y', or 'z' to test
        angle_deg: how much to drop (degrees)
    """
    
    print(f"\n{'='*70}")
    print(f"TESTING SHOULDER DROP ON {axis.upper()}-AXIS ({angle_deg}°)")
    print(f"{'='*70}\n")
    
    # Load parameters
    print(f"📦 Loading: {params_file}")
    data = np.load(params_file)
    betas = data['betas']
    
    # Load SMPL
    print("🎨 Loading SMPL model...")
    from hmr2.models.smpl_wrapper import SMPL
    from hmr2.configs import CACHE_DIR_4DHUMANS
    
    smpl = SMPL(f'{CACHE_DIR_4DHUMANS}/data/smpl', batch_size=1)
    betas_tensor = torch.from_numpy(betas).float().unsqueeze(0)
    
    print(f"\n🧍 Testing shoulder drop:")
    print(f"   Axis: {axis.upper()}")
    print(f"   Angle: {angle_deg}°")
    print(f"   Arms: NEUTRAL (no rotation)")
    
    # Body pose: ALL ZEROS except shoulder drop
    body_pose_aa = torch.zeros(1, 23, 3)
    
    # Apply shoulder drop on specified axis
    shoulder_drop = np.deg2rad(angle_deg)
    
    axis_idx = {'x': 0, 'y': 1, 'z': 2}[axis.lower()]
    
    # Left shoulder (joint 15)
    body_pose_aa[0, 15, axis_idx] = shoulder_drop
    
    # Right shoulder (joint 16)
    if axis.lower() == 'x':
        body_pose_aa[0, 16, axis_idx] = -shoulder_drop  # Mirror for X
    else:
        body_pose_aa[0, 16, axis_idx] = shoulder_drop   # Same for Y/Z
    
    print(f"   ✓ Left shoulder [{axis}]: {angle_deg}°")
    print(f"   ✓ Right shoulder [{axis}]: {'-' if axis.lower() == 'x' else ''}{angle_deg}°")
    
    # Convert to rotation matrices
    body_pose_rotmat = axis_angle_to_rotation_matrix(body_pose_aa).reshape(1, 23, 3, 3)
    
    # Global orient (standing upright)
    global_orient_aa = torch.zeros(1, 3)
    global_orient_rotmat = axis_angle_to_rotation_matrix(global_orient_aa.unsqueeze(1)).reshape(1, 1, 3, 3)
    
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
    
    # Scale to target height
    current_height_m = vertices[:, 1].max() - vertices[:, 1].min()
    scale_factor = (target_height_cm / 100) / current_height_m
    vertices = vertices * scale_factor
    
    final_height_cm = (vertices[:, 1].max() - vertices[:, 1].min()) * 100
    print(f"   Final height: {final_height_cm:.1f}cm ✅")
    
    # Save
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    mesh.export(str(output_obj))
    print(f"\n💾 Saved: {output_obj}")
    
    # Measurements
    arm_span = (vertices[:, 0].max() - vertices[:, 0].min()) * 100
    shoulder_height_left = vertices[:, 1][vertices[:, 0] < -0.1].max() if (vertices[:, 0] < -0.1).any() else 0
    shoulder_height_right = vertices[:, 1][vertices[:, 0] > 0.1].max() if (vertices[:, 0] > 0.1).any() else 0
    
    print(f"\n📐 Results:")
    print(f"   Arm span: {arm_span:.1f}cm")
    print(f"   (Should be ~60-80cm for arms at sides)")
    
    print(f"\n{'='*70}")
    print(f"✅ TEST COMPLETE - {axis.upper()}-AXIS")
    print(f"{'='*70}")
    print(f"\n💡 Check in Blender to see if shoulders dropped!")
    print(f"   open -a Blender {output_obj}")
    print()

def main():
    parser = argparse.ArgumentParser(
        description='Test shoulder drop on different axes',
        epilog='''
Examples:
  # Test X-axis
  python test_shoulder_drop.py --params params.npz --output test_x.obj --axis x --angle 20
  
  # Test Y-axis
  python test_shoulder_drop.py --params params.npz --output test_y.obj --axis y --angle 20
  
  # Test Z-axis
  python test_shoulder_drop.py --params params.npz --output test_z.obj --axis z --angle 20
        '''
    )
    parser.add_argument('--params', required=True, help='Input .npz parameters')
    parser.add_argument('--output', required=True, help='Output .obj file')
    parser.add_argument('--height', type=float, default=192, help='Height in cm')
    parser.add_argument('--axis', choices=['x', 'y', 'z', 'X', 'Y', 'Z'], required=True, help='Axis to test')
    parser.add_argument('--angle', type=float, default=20, help='Drop angle in degrees')
    
    args = parser.parse_args()
    
    test_shoulder_drop(args.params, args.output, args.height, args.axis, args.angle)

if __name__ == '__main__':
    main()


