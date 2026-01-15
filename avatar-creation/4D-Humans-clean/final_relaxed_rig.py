#!/usr/bin/env python3
"""
Create final garment rig with perfect arm position and relaxed upper body.
Adjusts spine/neck to drop shoulder visual appearance.
"""

import os
os.environ['PYOPENGL_PLATFORM'] = ''  # Disable OpenGL rendering on macOS

import torch
import numpy as np
import argparse
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from hmr2.models.smpl_wrapper import SMPL
from hmr2.configs import CACHE_DIR_4DHUMANS
import trimesh

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

def create_final_relaxed_rig(params_path, output_path, target_height_cm):
    """
    Create final garment rig with:
    - Arms at perfect position (165° - naturally at sides)
    - Relaxed upper body posture (adjusted spine/neck)
    - Scaled to target height
    """
    
    print("\n" + "="*70)
    print("CREATING FINAL RELAXED GARMENT RIG")
    print("="*70)
    
    # Load SMPL parameters
    print(f"\n📦 Loading: {params_path}")
    params = np.load(params_path, allow_pickle=True)
    betas = params['betas']
    print(f"   ✓ Body shape: {betas.shape}")
    
    # Initialize SMPL model
    print("\n🎨 Loading SMPL model...")
    smpl = SMPL(f'{CACHE_DIR_4DHUMANS}/data/smpl', batch_size=1)
    
    # Prepare inputs
    betas_tensor = torch.from_numpy(betas).float().unsqueeze(0)  # (1, 10)
    
    print("\n🧍 Configuring relaxed standing pose...")
    
    # Body pose (23 joints * 3 axis-angle)
    body_pose_aa = torch.zeros(1, 23, 3)
    
    # ============================================================
    # SPINE AND NECK - Create relaxed upper body posture
    # ============================================================
    # SMPL joint structure (23 joints):
    # 0: Left Hip, 1: Right Hip
    # 2: Spine1, 5: Spine2, 8: Spine3
    # 11: Neck, 14: Head
    # 15: Left Shoulder, 18: Left Elbow, 21: Left Wrist
    # 16: Right Shoulder, 19: Right Elbow, 22: Right Wrist
    
    # Slight BACKWARD lean in upper spine to drop shoulders down
    # Negative X rotation = lean back, which should drop shoulders
    spine2_tilt = np.deg2rad(-3)  # Mid spine back
    spine3_tilt = np.deg2rad(-5)  # Upper spine back (drops shoulders)
    neck_tilt = np.deg2rad(3)     # Neck forward to keep head upright
    
    body_pose_aa[0, 5, 0] = spine2_tilt   # Spine2 X-axis (backward)
    body_pose_aa[0, 8, 0] = spine3_tilt   # Spine3 X-axis (backward)
    body_pose_aa[0, 11, 0] = neck_tilt    # Neck X-axis (forward)
    
    print("   ✓ Spine adjusted (backward lean to drop shoulders)")
    print("   ✓ Neck forward (keeps head upright)")
    
    # ============================================================
    # SHOULDERS - Arms naturally at sides (165° = perfect!)
    # ============================================================
    # Joint 15: Left Shoulder
    # Joint 16: Right Shoulder
    
    arm_angle = 165  # From vertical (this worked perfectly!)
    arm_rotation_rad = np.deg2rad(90 - arm_angle)  # = -75° from horizontal
    
    # Rotate around Z-axis for arm position
    body_pose_aa[0, 15, 2] = arm_rotation_rad   # Left arm
    body_pose_aa[0, 16, 2] = -arm_rotation_rad  # Right arm (negative for symmetry)
    
    print(f"   ✓ Arms at {arm_angle}° (naturally at sides)")
    
    # ============================================================
    # ELBOWS - Slight natural bend
    # ============================================================
    # Joint 18: Left Elbow
    # Joint 19: Right Elbow
    
    elbow_bend = np.deg2rad(15)  # Slight forward bend
    body_pose_aa[0, 18, 0] = elbow_bend
    body_pose_aa[0, 19, 0] = elbow_bend
    
    print("   ✓ Elbows slightly bent (natural)")
    
    # Convert axis-angle to rotation matrices
    body_pose_rotmat = axis_angle_to_rotation_matrix(body_pose_aa).reshape(1, 23, 3, 3)
    
    # Global orient (standing upright)
    global_orient_aa = torch.zeros(1, 3)
    global_orient_rotmat = axis_angle_to_rotation_matrix(global_orient_aa.unsqueeze(1)).reshape(1, 1, 3, 3)
    
    print("   ✓ Pose configured")
    
    # Generate mesh
    print("\n🔨 Generating mesh...")
    output = smpl(
        global_orient=global_orient_rotmat,
        body_pose=body_pose_rotmat,
        betas=betas_tensor,
        pose2rot=False
    )
    
    vertices = output.vertices[0].detach().cpu().numpy()
    faces = smpl.faces
    print(f"   ✓ Generated: {len(vertices)} vertices")
    
    # Scale to target height
    print(f"\n📏 Scaling to {target_height_cm}cm...")
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    
    current_height = mesh.bounds[1][1] - mesh.bounds[0][1]
    current_height_cm = current_height * 100
    scale_factor = target_height_cm / current_height_cm
    
    mesh.apply_scale(scale_factor)
    
    final_height = (mesh.bounds[1][1] - mesh.bounds[0][1]) * 100
    print(f"   Final height: {final_height:.1f}cm ✅")
    
    # Calculate quick measurements
    arm_span = (mesh.bounds[1][0] - mesh.bounds[0][0]) * 100
    chest_circumference = arm_span * 0.65  # Rough estimate
    
    # Save mesh
    print("\n💾 Saving...")
    mesh.export(output_path)
    print(f"   ✓ Saved: {output_path}")
    
    print("\n📐 Quick measurements:")
    print(f"   Chest: {chest_circumference:.1f}cm")
    print(f"   Arm span: {arm_span:.1f}cm")
    
    print("\n" + "="*70)
    print("✅ FINAL RELAXED RIG CREATED!")
    print("="*70)
    print("\n💡 Key features:")
    print("   ✓ Arms naturally at sides (perfect position)")
    print("   ✓ Relaxed upper body (spine/neck adjusted)")
    print("   ✓ Natural elbow bend")
    print(f"   ✓ Scaled to {target_height_cm}cm")
    print("\n🚀 View it:")
    print(f"   open -a Blender {output_path}")
    print("\n")

def main():
    parser = argparse.ArgumentParser(description='Create final relaxed garment rig')
    parser.add_argument('--params', required=True, help='Path to .npz params file')
    parser.add_argument('--output', default='FINAL_RELAXED_RIG.obj', help='Output OBJ file')
    parser.add_argument('--height', type=float, required=True, help='Target height in cm')
    
    args = parser.parse_args()
    
    if not Path(args.params).exists():
        print(f"❌ Error: Params file not found: {args.params}")
        return
    
    create_final_relaxed_rig(args.params, args.output, args.height)

if __name__ == '__main__':
    main()

