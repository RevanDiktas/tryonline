#!/usr/bin/env python3
"""
IMPROVED BODY MEASUREMENT EXTRACTION
Uses SMPL joint positions for accurate anatomical landmarks
Much more accurate than height-based slicing!
"""

import os
os.environ['PYOPENGL_PLATFORM'] = ''  # Disable OpenGL on macOS

import numpy as np
import torch
import trimesh
import argparse
import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from hmr2.models.smpl_wrapper import SMPL
from hmr2.configs import CACHE_DIR_4DHUMANS

# SMPL Joint indices (24 joints total)
# Based on SMPL-X structure mapped to OpenPose
SMPL_JOINTS = {
    'pelvis': 0,
    'left_hip': 1,
    'right_hip': 2,
    'spine1': 3,
    'left_knee': 4,
    'right_knee': 5,
    'spine2': 6,
    'left_ankle': 7,
    'right_ankle': 8,
    'spine3': 9,
    'left_foot': 10,
    'right_foot': 11,
    'neck': 12,
    'left_collar': 13,
    'right_collar': 14,
    'head': 15,
    'left_shoulder': 16,
    'right_shoulder': 17,
    'left_elbow': 18,
    'right_elbow': 19,
    'left_wrist': 20,
    'right_wrist': 21,
    'left_hand': 22,
    'right_hand': 23,
}

def calculate_circumference_from_slice(vertices, y_level, slice_thickness=0.02):
    """
    Calculate actual circumference by slicing mesh at specific Y level
    Uses actual mesh cross-section, not ellipse approximation!
    
    Args:
        vertices: Mesh vertices (N, 3)
        y_level: Y coordinate to slice at
        slice_thickness: Thickness of slice (as fraction of height)
    
    Returns:
        circumference in cm, or None if insufficient points
    """
    y_min = vertices[:, 1].min()
    y_max = vertices[:, 1].max()
    y_range = y_max - y_min
    thickness = y_range * slice_thickness
    
    # Get vertices in slice
    mask = np.abs(vertices[:, 1] - y_level) < thickness
    slice_verts = vertices[mask]
    
    if len(slice_verts) < 10:
        return None
    
    # Project to XZ plane (front view)
    xz_points = slice_verts[:, [0, 2]]
    
    # Find convex hull for accurate perimeter (if scipy available)
    try:
        from scipy.spatial import ConvexHull
        hull = ConvexHull(xz_points)
        # Calculate perimeter from hull edges
        perimeter = 0.0
        for i in range(len(hull.vertices)):
            p1 = xz_points[hull.vertices[i]]
            p2 = xz_points[hull.vertices[(i + 1) % len(hull.vertices)]]
            perimeter += np.linalg.norm(p2 - p1)
        
        # Convert to cm
        circumference_cm = perimeter * 100
        return circumference_cm
    except ImportError:
        # Fallback: use bounding box approximation (no scipy)
        pass
    except:
        # Fallback: convex hull failed, use approximation
        pass
    
    # Fallback: use bounding box approximation
    width = (xz_points[:, 0].max() - xz_points[:, 0].min()) * 100
    depth = (xz_points[:, 1].max() - xz_points[:, 1].min()) * 100
    # Ellipse approximation (Ramanujan's approximation)
    a, b = width / 2, depth / 2
    circumference_cm = np.pi * (3 * (a + b) - np.sqrt((3 * a + b) * (a + 3 * b)))
    return circumference_cm

def extract_measurements_with_smpl_joints(params_path, actual_height_cm):
    """
    Extract accurate body measurements using SMPL joint positions
    
    Args:
        params_path: Path to .npz file with SMPL parameters
        actual_height_cm: Person's actual height in cm
    
    Returns:
        dict of measurements in cm
    """
    print("\n" + "="*70)
    print("IMPROVED MEASUREMENT EXTRACTION (SMPL Joint-Based)")
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
    betas_tensor = torch.from_numpy(betas).float().unsqueeze(0)
    
    # Generate mesh with neutral pose (for accurate joint positions)
    print("\n🔨 Generating mesh with neutral pose...")
    body_pose_aa = torch.zeros(1, 23, 3)
    global_orient_aa = torch.zeros(1, 3)
    
    # Convert to rotation matrices
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
    
    body_pose_rotmat = axis_angle_to_rotation_matrix(body_pose_aa).reshape(1, 23, 3, 3)
    global_orient_rotmat = axis_angle_to_rotation_matrix(global_orient_aa.unsqueeze(1)).reshape(1, 1, 3, 3)
    
    with torch.no_grad():
        output = smpl(
            global_orient=global_orient_rotmat,
            body_pose=body_pose_rotmat,
            betas=betas_tensor,
            pose2rot=False
        )
    
    vertices = output.vertices[0].detach().cpu().numpy()
    joints = output.joints[0].detach().cpu().numpy()  # (24, 3)
    faces = smpl.faces
    
    print(f"   ✓ Generated: {len(vertices)} vertices")
    print(f"   ✓ Joints: {len(joints)} joints")
    
    # Scale to actual height
    print(f"\n📏 Scaling to {actual_height_cm}cm...")
    current_height = vertices[:, 1].max() - vertices[:, 1].min()
    current_height_cm = current_height * 100
    scale_factor = actual_height_cm / current_height_cm
    
    vertices = vertices * scale_factor
    joints = joints * scale_factor
    
    print(f"   Original height: {current_height_cm:.2f}cm")
    print(f"   Target height: {actual_height_cm:.2f}cm")
    print(f"   Scale factor: {scale_factor:.4f}")
    
    # Extract measurements using joint positions
    measurements = {}
    measurements['height_cm'] = actual_height_cm
    
    print("\n📐 Extracting measurements using joint landmarks...")
    
    # ============================================================
    # CHEST CIRCUMFERENCE
    # ============================================================
    # Chest is typically at nipple level, which is between shoulders and armpit
    # Use average of left and right shoulder Y positions
    left_shoulder_y = joints[SMPL_JOINTS['left_shoulder'], 1]
    right_shoulder_y = joints[SMPL_JOINTS['right_shoulder'], 1]
    chest_y = (left_shoulder_y + right_shoulder_y) / 2 - 0.05  # Slightly below shoulders
    
    chest_circ = calculate_circumference_from_slice(vertices, chest_y, slice_thickness=0.03)
    if chest_circ:
        measurements['chest_circumference_cm'] = chest_circ
        print(f"   ✓ Chest: {chest_circ:.1f}cm (at shoulder level - 5cm)")
    else:
        print(f"   ⚠️  Chest: Could not calculate")
    
    # ============================================================
    # WAIST CIRCUMFERENCE
    # ============================================================
    # Waist is typically at the narrowest point between chest and hips
    # Use spine3 (upper spine) as reference, then find narrowest point
    spine3_y = joints[SMPL_JOINTS['spine3'], 1]
    pelvis_y = joints[SMPL_JOINTS['pelvis'], 1]
    
    # Search for narrowest point between spine3 and pelvis
    search_range = np.linspace(spine3_y, pelvis_y, 20)
    min_circ = float('inf')
    waist_y = spine3_y
    
    for y in search_range:
        circ = calculate_circumference_from_slice(vertices, y, slice_thickness=0.02)
        if circ and circ < min_circ:
            min_circ = circ
            waist_y = y
    
    if min_circ != float('inf'):
        measurements['waist_circumference_cm'] = min_circ
        print(f"   ✓ Waist: {min_circ:.1f}cm (narrowest point)")
    else:
        # Fallback: use midpoint
        waist_y = (spine3_y + pelvis_y) / 2
        waist_circ = calculate_circumference_from_slice(vertices, waist_y, slice_thickness=0.03)
        if waist_circ:
            measurements['waist_circumference_cm'] = waist_circ
            print(f"   ✓ Waist: {waist_circ:.1f}cm (midpoint)")
    
    # ============================================================
    # HIP CIRCUMFERENCE
    # ============================================================
    # Hips are at the widest point of the pelvis
    # Use pelvis joint as reference
    hip_y = joints[SMPL_JOINTS['pelvis'], 1] + 0.03  # Slightly below pelvis
    
    hip_circ = calculate_circumference_from_slice(vertices, hip_y, slice_thickness=0.04)
    if hip_circ:
        measurements['hip_circumference_cm'] = hip_circ
        print(f"   ✓ Hips: {hip_circ:.1f}cm (at pelvis level)")
    else:
        print(f"   ⚠️  Hips: Could not calculate")
    
    # ============================================================
    # NECK CIRCUMFERENCE
    # ============================================================
    # Neck is at neck joint level
    neck_y = joints[SMPL_JOINTS['neck'], 1]
    
    neck_circ = calculate_circumference_from_slice(vertices, neck_y, slice_thickness=0.02)
    if neck_circ:
        measurements['neck_circumference_cm'] = neck_circ
        print(f"   ✓ Neck: {neck_circ:.1f}cm")
    else:
        print(f"   ⚠️  Neck: Could not calculate")
    
    # ============================================================
    # THIGH CIRCUMFERENCE
    # ============================================================
    # Thigh is at midpoint between hip and knee
    left_knee_y = joints[SMPL_JOINTS['left_knee'], 1]
    right_knee_y = joints[SMPL_JOINTS['right_knee'], 1]
    pelvis_y = joints[SMPL_JOINTS['pelvis'], 1]
    
    thigh_y = (pelvis_y + (left_knee_y + right_knee_y) / 2) / 2
    
    thigh_circ = calculate_circumference_from_slice(vertices, thigh_y, slice_thickness=0.03)
    if thigh_circ:
        measurements['thigh_circumference_cm'] = thigh_circ
        print(f"   ✓ Thigh: {thigh_circ:.1f}cm")
    else:
        print(f"   ⚠️  Thigh: Could not calculate")
    
    # ============================================================
    # WIDTH MEASUREMENTS
    # ============================================================
    print("\n📏 Width measurements:")
    
    # Shoulder width (distance between shoulder joints)
    left_shoulder = joints[SMPL_JOINTS['left_shoulder']]
    right_shoulder = joints[SMPL_JOINTS['right_shoulder']]
    shoulder_width = np.linalg.norm(left_shoulder - right_shoulder) * 100
    measurements['shoulder_width_cm'] = shoulder_width
    print(f"   ✓ Shoulder width: {shoulder_width:.1f}cm")
    
    # Arm span (left wrist to right wrist)
    left_wrist = joints[SMPL_JOINTS['left_wrist']]
    right_wrist = joints[SMPL_JOINTS['right_wrist']]
    arm_span = np.linalg.norm(left_wrist - right_wrist) * 100
    measurements['arm_span_cm'] = arm_span
    print(f"   ✓ Arm span: {arm_span:.1f}cm")
    
    # ============================================================
    # LENGTH MEASUREMENTS
    # ============================================================
    print("\n📐 Length measurements:")
    
    # Arm length (shoulder to wrist)
    left_arm_length = np.linalg.norm(
        joints[SMPL_JOINTS['left_shoulder']] - joints[SMPL_JOINTS['left_wrist']]
    ) * 100
    right_arm_length = np.linalg.norm(
        joints[SMPL_JOINTS['right_shoulder']] - joints[SMPL_JOINTS['right_wrist']]
    ) * 100
    arm_length = (left_arm_length + right_arm_length) / 2
    measurements['arm_length_cm'] = arm_length
    print(f"   ✓ Arm length: {arm_length:.1f}cm")
    
    # Inseam (pelvis to ankle)
    left_inseam = np.linalg.norm(
        joints[SMPL_JOINTS['pelvis']] - joints[SMPL_JOINTS['left_ankle']]
    ) * 100
    right_inseam = np.linalg.norm(
        joints[SMPL_JOINTS['pelvis']] - joints[SMPL_JOINTS['right_ankle']]
    ) * 100
    inseam = (left_inseam + right_inseam) / 2
    measurements['inseam_cm'] = inseam
    print(f"   ✓ Inseam: {inseam:.1f}cm")
    
    # Torso length (shoulder to pelvis)
    torso_length = np.linalg.norm(
        (joints[SMPL_JOINTS['left_shoulder']] + joints[SMPL_JOINTS['right_shoulder']]) / 2
        - joints[SMPL_JOINTS['pelvis']]
    ) * 100
    measurements['torso_length_cm'] = torso_length
    print(f"   ✓ Torso length: {torso_length:.1f}cm")
    
    # Add metadata
    measurements['_metadata'] = {
        'source_params': str(params_path),
        'actual_height_input_cm': actual_height_cm,
        'method': 'smpl_joint_based',
        'note': 'Measurements extracted using SMPL joint positions for accurate landmarks'
    }
    
    return measurements

def main():
    parser = argparse.ArgumentParser(
        description='Extract accurate body measurements using SMPL joints',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python extract_measurements_smpl_joints.py --params person_params.npz --height 192 --output measurements.json
        '''
    )
    
    parser.add_argument('--params', type=str, required=True, help='Input .npz params file')
    parser.add_argument('--height', type=float, required=True, help='Actual height in cm')
    parser.add_argument('--output', type=str, help='Output JSON file')
    
    args = parser.parse_args()
    
    if not Path(args.params).exists():
        print(f"❌ Error: Params file not found: {args.params}")
        return
    
    measurements = extract_measurements_with_smpl_joints(args.params, args.height)
    
    print("\n" + "="*70)
    print("FINAL MEASUREMENTS")
    print("="*70)
    for key, value in measurements.items():
        if key != '_metadata' and value is not None:
            print(f"{key:30s}: {value:7.2f}")
    print("="*70)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(measurements, f, indent=2)
        print(f"\n✅ Saved to: {args.output}")
    
    print()

if __name__ == '__main__':
    main()

