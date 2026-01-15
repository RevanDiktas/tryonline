#!/usr/bin/env python3
"""
Fix body pose to neutral A-pose with arms at 45° from vertical
"""

import numpy as np
import torch
import argparse
from pathlib import Path
import trimesh

try:
    import smplx
except ImportError:
    print("❌ Error: smplx not installed. Install with: pip install smplx")
    exit(1)

def fix_pose_to_apose(params_path, output_path, arm_angle_degrees=45):
    """
    Load SMPL parameters and regenerate mesh in A-pose
    
    Args:
        params_path: Path to .npz file with SMPL parameters
        output_path: Path to save the A-pose OBJ
        arm_angle_degrees: Arm angle from vertical (default 45°)
    """
    print("=" * 60)
    print("🎯 FIXING POSE TO A-POSE")
    print("=" * 60)
    
    # Load parameters
    print(f"\n📥 Loading SMPL parameters: {params_path}")
    params = np.load(params_path, allow_pickle=True)
    
    # Extract betas (body shape)
    if 'betas' in params:
        betas = params['betas']
    elif 'shape' in params:
        betas = params['shape']
    else:
        raise ValueError("No 'betas' or 'shape' found in params file")
    
    # Ensure betas is the right shape
    if len(betas.shape) > 1:
        betas = betas.flatten()
    if len(betas) > 10:
        betas = betas[:10]  # SMPL uses 10 shape parameters
    elif len(betas) < 10:
        betas = np.pad(betas, (0, 10 - len(betas)), 'constant')
    
    print(f"   ✓ Betas shape: {betas.shape}")
    
    # Find SMPL model directory compatible with smplx.create
    # smplx expects a directory containing a `smpl` subfolder with
    # files like `SMPL_NEUTRAL.pkl`.
    smpl_models_root = Path(__file__).parent / "4D-Humans-clean" / "data" / "SMPL_python_v.1.1.0"
    if not (smpl_models_root / "smpl" / "SMPL_NEUTRAL.pkl").exists():
        # Fallback: try a simpler `data/smpl` layout if present
        alt_root = Path(__file__).parent / "4D-Humans-clean" / "data"
        if (alt_root / "smpl" / "SMPL_NEUTRAL.pkl").exists():
            smpl_models_root = alt_root
        else:
            raise FileNotFoundError(
                f"SMPL_NEUTRAL.pkl not found. Expected under: {smpl_models_root}/smpl or {alt_root}/smpl"
            )
    
    print(f"   ✓ SMPL models root: {smpl_models_root}")
    
    # Create SMPL model
    print(f"\n🔧 Creating SMPL model...")
    smpl_model = smplx.create(
        str(smpl_models_root),
        model_type='smpl',
        gender='neutral',
        num_betas=10,
        use_face_contour=False
    )
    
    # Convert betas to torch tensor
    betas_tensor = torch.from_numpy(betas).float().unsqueeze(0)
    
    # Create pose
    # Global orientation: upright (all zeros)
    global_orient = torch.zeros(1, 3)
    
    # Body pose: start with all zeros (T-pose in SMPL)
    body_pose = torch.zeros(1, 69)  # 23 joints * 3
    
    # CRITICAL: In SMPL, all zeros = T-pose (arms horizontal/up)
    # arm_angle_degrees: Angle from vertical (0° = straight down, 90° = horizontal)
    # To INVERT from current position (45° up) to desired position (45° down = 315°),
    # we need to NEGATE the rotation
    # Formula: arm_rotation_rad = -np.deg2rad(90 - arm_angle_degrees)
    # This inverts the direction from up to down
    
    arm_angle_rad = -np.deg2rad(90 - arm_angle_degrees)  # NEGATE to invert direction (down instead of up)
    
    # Set arm angles: rotate shoulders to position arms
    # In body_pose array (69 dims = 23 joints * 3, excludes root joint):
    # body_pose index 15 = SMPL joint 16 (left shoulder)
    # body_pose index 16 = SMPL joint 17 (right shoulder)
    # Rotate around Z-axis (axis-angle representation, index 2)
    
    # Left shoulder (body_pose index 15 = SMPL joint 16): rotate Z-axis
    body_pose[0, 15*3 + 2] = arm_angle_rad  # Negative rotation for arms down
    
    # Right shoulder (body_pose index 16 = SMPL joint 17): rotate Z-axis (positive for symmetry)
    body_pose[0, 16*3 + 2] = -arm_angle_rad  # Positive rotation for arms down
    
    print(f"   ✓ Pose configured: arms at {arm_angle_degrees}° from vertical")
    print(f"   ✓ Rotation: {np.rad2deg(arm_angle_rad):.1f}° from horizontal")
    
    # Generate mesh
    print(f"\n🔨 Generating A-pose mesh...")
    with torch.no_grad():
        output = smpl_model(
            betas=betas_tensor,
            body_pose=body_pose,
            global_orient=global_orient
        )
    
    vertices = output.vertices[0].cpu().numpy()
    faces = smpl_model.faces
    
    print(f"   ✓ Generated: {len(vertices)} vertices, {len(faces)} faces")
    
    # Save mesh
    print(f"\n💾 Saving A-pose mesh: {output_path}")
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.export(str(output_path))
    print(f"   ✓ Saved: {output_path}")
    
    print("\n✅ COMPLETE!")
    print("=" * 60)
    
    return output_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fix body pose to A-pose')
    parser.add_argument('--params', type=str, required=True, help='SMPL params .npz file')
    parser.add_argument('--output', type=str, required=True, help='Output OBJ file')
    parser.add_argument('--arm-angle', type=float, default=45, help='Arm angle from vertical (degrees)')
    
    args = parser.parse_args()
    
    fix_pose_to_apose(args.params, args.output, args.arm_angle)

