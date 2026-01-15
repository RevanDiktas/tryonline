"""
Simple script to change mesh pose to neutral standing position
"""
import numpy as np
import torch
import trimesh
import argparse
from pathlib import Path
import os
os.environ['PYOPENGL_PLATFORM'] = ''

def create_standing_pose(params_file, output_obj, target_height_cm=192, pose_type='a-pose'):
    """Create a standing pose from SMPL parameters"""
    
    print(f"\n{'='*70}")
    print(f"CHANGING POSE TO {pose_type.upper()}")
    print(f"{'='*70}\n")
    
    # Load parameters
    print(f"📦 Loading parameters: {params_file}")
    data = np.load(params_file)
    betas = data['betas']  # Body shape (10 values)
    print(f"   ✓ Body shape loaded: {betas.shape}")
    
    # Load SMPL model
    print("\n🎨 Loading SMPL model...")
    from hmr2.models.smpl_wrapper import SMPL
    from hmr2.configs import CACHE_DIR_4DHUMANS
    
    smpl = SMPL(f'{CACHE_DIR_4DHUMANS}/data/smpl', batch_size=1)
    print("   ✓ SMPL loaded")
    
    # Prepare betas
    betas_tensor = torch.from_numpy(betas).float().unsqueeze(0)  # (1, 10)
    
    # Create neutral pose
    print(f"\n🧍 Creating {pose_type}...")
    
    if pose_type == 'a-pose':
        # A-pose: arms at 45 degrees
        body_pose = torch.zeros(1, 23, 3)  # 23 joints, axis-angle (not rotation matrix!)
        body_pose[0, 15, 2] = 0.4  # Left arm out
        body_pose[0, 16, 2] = -0.4  # Right arm out
    else:  # t-pose
        # T-pose: arms straight out
        body_pose = torch.zeros(1, 23, 3)
        body_pose[0, 15, 2] = 1.5  # Left arm 90 degrees
        body_pose[0, 16, 2] = -1.5  # Right arm 90 degrees
    
    # Global orientation (standing upright)
    global_orient = torch.zeros(1, 3)
    
    print("   ✓ Pose configured")
    
    # Generate mesh
    print("\n🔨 Generating mesh...")
    with torch.no_grad():
        output = smpl(
            betas=betas_tensor,
            body_pose=body_pose,
            global_orient=global_orient,
            pose2rot=True  # Convert axis-angle to rotation matrices
        )
    
    vertices = output.vertices[0].cpu().numpy()
    faces = smpl.faces
    
    print(f"   ✓ Mesh generated: {vertices.shape[0]} vertices")
    
    # Scale to target height
    print(f"\n📏 Scaling to {target_height_cm}cm...")
    current_height = vertices[:, 1].max() - vertices[:, 1].min()
    scale_factor = (target_height_cm / 100) / current_height
    vertices = vertices * scale_factor
    
    final_height = (vertices[:, 1].max() - vertices[:, 1].min()) * 100
    print(f"   Original height: {current_height*100:.1f}cm")
    print(f"   Scale factor: {scale_factor:.4f}")
    print(f"   Final height: {final_height:.1f}cm")
    
    # Save mesh
    print(f"\n💾 Saving mesh...")
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    mesh.export(str(output_obj))
    
    print(f"   ✓ Saved: {output_obj}")
    
    # Calculate measurements
    print(f"\n📐 Quick measurements:")
    y_min = vertices[:, 1].min()
    y_max = vertices[:, 1].max()
    y_range = y_max - y_min
    
    # Chest (75% of height)
    chest_y = y_min + (y_range * 0.75)
    chest_mask = np.abs(vertices[:, 1] - chest_y) < (y_range * 0.04)
    if chest_mask.sum() > 0:
        chest_verts = vertices[chest_mask]
        width = chest_verts[:, 0].max() - chest_verts[:, 0].min()
        depth = chest_verts[:, 2].max() - chest_verts[:, 2].min()
        chest_circ = np.pi * (width + depth) / 2 * 100
        print(f"   Chest: {chest_circ:.1f}cm")
    
    # Waist (60% of height)
    waist_y = y_min + (y_range * 0.60)
    waist_mask = np.abs(vertices[:, 1] - waist_y) < (y_range * 0.03)
    if waist_mask.sum() > 0:
        waist_verts = vertices[waist_mask]
        width = waist_verts[:, 0].max() - waist_verts[:, 0].min()
        depth = waist_verts[:, 2].max() - waist_verts[:, 2].min()
        waist_circ = np.pi * (width + depth) / 2 * 100
        print(f"   Waist: {waist_circ:.1f}cm")
    
    # Hips (50% of height)
    hip_y = y_min + (y_range * 0.50)
    hip_mask = np.abs(vertices[:, 1] - hip_y) < (y_range * 0.04)
    if hip_mask.sum() > 0:
        hip_verts = vertices[hip_mask]
        width = hip_verts[:, 0].max() - hip_verts[:, 0].min()
        depth = hip_verts[:, 2].max() - hip_verts[:, 2].min()
        hip_circ = np.pi * (width + depth) / 2 * 100
        print(f"   Hips: {hip_circ:.1f}cm")
    
    print(f"\n{'='*70}")
    print("✅ POSE CHANGED SUCCESSFULLY!")
    print(f"{'='*70}")
    print(f"\n💡 View in Blender:")
    print(f"   open -a Blender {output_obj}")
    print()
    
    return str(output_obj)

def main():
    parser = argparse.ArgumentParser(description='Change mesh pose to neutral standing position')
    parser.add_argument('--params', required=True, help='Input .npz parameters file')
    parser.add_argument('--output', required=True, help='Output .obj mesh file')
    parser.add_argument('--height', type=float, default=192, help='Target height in cm')
    parser.add_argument('--pose', choices=['a-pose', 't-pose'], default='a-pose', help='Target pose type')
    
    args = parser.parse_args()
    
    create_standing_pose(args.params, args.output, args.height, args.pose)

if __name__ == '__main__':
    main()


