"""
Create natural standing pose with arms at sides (zero rotation)
"""
import numpy as np
import torch
import trimesh
import argparse
from pathlib import Path
import os
os.environ['PYOPENGL_PLATFORM'] = ''

def create_natural_pose(params_file, output_obj, target_height_cm=192):
    """Create natural standing pose - SMPL default with zero rotations"""
    
    print(f"\n{'='*70}")
    print("CREATING NATURAL STANDING POSE (Arms at sides)")
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
    
    # ZERO ROTATION = Natural pose
    print(f"\n🧍 Using default SMPL pose (zero rotations)...")
    body_pose = torch.zeros(1, 23, 3, 3)  # Identity matrices
    body_pose[:, :, 0, 0] = 1
    body_pose[:, :, 1, 1] = 1
    body_pose[:, :, 2, 2] = 1
    
    global_orient = torch.zeros(1, 1, 3, 3)
    global_orient[:, :, 0, 0] = 1
    global_orient[:, :, 1, 1] = 1
    global_orient[:, :, 2, 2] = 1
    
    print("   ✓ Pose configured (identity/zero rotation)")
    
    # Generate mesh
    print("\n🔨 Generating mesh...")
    with torch.no_grad():
        output = smpl(
            betas=betas_tensor,
            body_pose=body_pose,
            global_orient=global_orient,
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
    print(f"   (Smaller arm span = arms closer to body)")
    
    print(f"\n{'='*70}")
    print("✅ NATURAL POSE CREATED!")
    print(f"{'='*70}")
    print(f"\n🚀 View it:")
    print(f"   open -a Blender {output_obj}")
    print()
    
    return output_obj

def main():
    parser = argparse.ArgumentParser(description='Create natural standing pose')
    parser.add_argument('--params', required=True, help='Input .npz parameters')
    parser.add_argument('--output', required=True, help='Output .obj file')
    parser.add_argument('--height', type=float, default=192, help='Height in cm')
    
    args = parser.parse_args()
    
    create_natural_pose(args.params, args.output, args.height)

if __name__ == '__main__':
    main()


