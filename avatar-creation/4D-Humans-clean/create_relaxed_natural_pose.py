"""
Create truly relaxed natural pose - like standing casually
Arms hang naturally with slight elbow bend
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

def create_relaxed_pose(params_file, output_obj, target_height_cm=192):
    """Create relaxed natural standing pose"""
    
    print(f"\n{'='*70}")
    print("CREATING RELAXED NATURAL POSE")
    print("(Like standing casually - arms hanging naturally)")
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
    betas_tensor = torch.from_numpy(betas).float().unsqueeze(0)
    
    print(f"\n🧍 Setting up relaxed pose...")
    print("   - Arms hanging naturally at sides")
    print("   - Slight elbow bend")
    print("   - Natural shoulder position")
    
    # Body pose: 23 joints in axis-angle
    # SMPL joint indices:
    # 15 = Left shoulder, 16 = Right shoulder
    # 18 = Left elbow, 19 = Right elbow
    # 20 = Left wrist, 21 = Right wrist
    
    body_pose_aa = torch.zeros(1, 23, 3)
    
    # Shoulders: arms mostly down + shoulder drop for relaxed look
    shoulder_angle = np.deg2rad(-75)  # Negative = arms down
    shoulder_drop = np.deg2rad(15)    # Drop shoulders down (Y rotation - roll forward)
    
    # Left shoulder
    body_pose_aa[0, 15, 2] = shoulder_angle   # Arm down (Z rotation)
    body_pose_aa[0, 15, 1] = shoulder_drop    # Shoulder drop (Y rotation)
    
    # Right shoulder
    body_pose_aa[0, 16, 2] = -shoulder_angle  # Arm down (Z rotation)
    body_pose_aa[0, 16, 1] = shoulder_drop    # Shoulder drop (Y rotation)
    
    # Elbows: slight bend (natural relaxed bend ~15-20 degrees)
    elbow_bend = np.deg2rad(15)  # Slight bend
    body_pose_aa[0, 18, 1] = elbow_bend   # Left elbow (bend inward)
    body_pose_aa[0, 19, 1] = elbow_bend   # Right elbow
    
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
    arm_span = (vertices[:, 0].max() - vertices[:, 0].min()) * 100
    print(f"   Arm span: {arm_span:.1f}cm")
    print(f"   (Should be ~60-80cm for relaxed arms at sides)")
    
    print(f"\n{'='*70}")
    print("✅ RELAXED NATURAL POSE CREATED!")
    print(f"{'='*70}")
    print(f"\n💡 This pose mimics:")
    print("   - Standing casually")
    print("   - Arms hanging naturally")
    print("   - Slight elbow bend (not stiff)")
    print("   - Natural, relaxed stance")
    print(f"\n🚀 View it:")
    print(f"   open -a Blender {output_obj}")
    print()
    
    return output_obj

def main():
    parser = argparse.ArgumentParser(description='Create relaxed natural standing pose')
    parser.add_argument('--params', required=True, help='Input .npz parameters')
    parser.add_argument('--output', required=True, help='Output .obj file')
    parser.add_argument('--height', type=float, default=192, help='Height in cm')
    
    args = parser.parse_args()
    
    create_relaxed_pose(args.params, args.output, args.height)

if __name__ == '__main__':
    main()

