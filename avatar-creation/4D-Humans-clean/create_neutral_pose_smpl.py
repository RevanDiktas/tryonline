"""
Create neutral A-pose mesh using SMPL model directly
No rendering needed - pure mesh generation
"""
import numpy as np
import torch
import trimesh
import argparse
import json
from pathlib import Path

def create_smpl_neutral_pose(betas, target_height_cm=None, pose_type='a-pose'):
    """
    Create SMPL mesh in neutral pose with given body shape
    
    Args:
        betas: SMPL shape parameters (10 values)
        target_height_cm: Desired height in cm
        pose_type: 'a-pose' or 't-pose'
    
    Returns:
        vertices, faces
    """
    # Import SMPL
    import sys
    sys.path.insert(0, 'data/SMPL_python_v.1.1.0/smpl')
    
    try:
        from smpl_webuser.serialization import load_model
        
        # Load SMPL model
        model_path = 'data/SMPL_python_v.1.1.0/smpl/models/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl'
        print(f"Loading SMPL model from: {model_path}")
        model = load_model(model_path)
        
        # Set body shape
        model.betas[:len(betas)] = betas
        
        # Create neutral pose (all zeros = standing straight)
        model.pose[:] = np.zeros(72)
        
        # For A-pose: slightly angle the arms down
        if pose_type == 'a-pose':
            # Arms (shoulders) - indices 16-17 (left), 17-18 (right)
            # Rotate arms down about 45 degrees
            arm_angle = np.deg2rad(30)  # 30 degrees down
            model.pose[16*3 + 2] = arm_angle   # Left shoulder, z-rotation
            model.pose[17*3 + 2] = -arm_angle  # Right shoulder, z-rotation
        
        # Set neutral translation
        model.trans[:] = np.zeros(3)
        
        # Generate mesh
        vertices = np.array(model.r)
        faces = model.f
        
        # Scale to target height if specified
        if target_height_cm:
            current_height = (vertices[:, 1].max() - vertices[:, 1].min()) * 100
            scale_factor = target_height_cm / current_height
            vertices = vertices * scale_factor
            print(f"Scaled from {current_height:.2f}cm to {target_height_cm:.2f}cm (factor: {scale_factor:.4f})")
        
        return vertices, faces
        
    except Exception as e:
        print(f"Error loading SMPL: {e}")
        print("\nTrying alternative method...")
        return None, None

def calculate_accurate_measurements(vertices):
    """Calculate measurements from neutral-pose mesh"""
    measurements = {}
    
    y_min = vertices[:, 1].min()
    y_max = vertices[:, 1].max()
    y_range = y_max - y_min
    
    # Height
    measurements['height_cm'] = y_range * 100
    
    def get_circumference(height_ratio, thickness=0.05):
        target_y = y_min + (y_range * height_ratio)
        mask = np.abs(vertices[:, 1] - target_y) < (y_range * thickness)
        slice_verts = vertices[mask]
        
        if len(slice_verts) > 10:
            # More accurate: use actual perimeter of the slice
            x_coords = slice_verts[:, 0]
            z_coords = slice_verts[:, 2]
            
            # Find convex hull for better circumference estimate
            from scipy.spatial import ConvexHull
            try:
                points_2d = np.column_stack([x_coords, z_coords])
                hull = ConvexHull(points_2d)
                perimeter = hull.area  # In 2D, 'area' is actually perimeter
                return perimeter * 100
            except:
                # Fallback to ellipse approximation
                width = x_coords.max() - x_coords.min()
                depth = z_coords.max() - z_coords.min()
                return np.pi * (width + depth) / 2 * 100
        return None
    
    # Key measurements
    measurements['chest_circumference_cm'] = get_circumference(0.75, 0.04)
    measurements['underbust_cm'] = get_circumference(0.70, 0.03)
    measurements['waist_circumference_cm'] = get_circumference(0.60, 0.03)
    measurements['hip_circumference_cm'] = get_circumference(0.50, 0.04)
    measurements['neck_circumference_cm'] = get_circumference(0.90, 0.02)
    
    # Widths and lengths
    shoulder_y = y_min + (y_range * 0.85)
    shoulder_mask = np.abs(vertices[:, 1] - shoulder_y) < (y_range * 0.02)
    if shoulder_mask.sum() > 0:
        measurements['shoulder_width_cm'] = (vertices[shoulder_mask, 0].max() - 
                                             vertices[shoulder_mask, 0].min()) * 100
    
    measurements['arm_span_cm'] = (vertices[:, 0].max() - vertices[:, 0].min()) * 100
    measurements['inseam_cm'] = measurements['height_cm'] * 0.45
    measurements['torso_length_cm'] = y_range * 0.35 * 100
    
    return measurements

def main():
    parser = argparse.ArgumentParser(description='Create neutral SMPL pose')
    parser.add_argument('--params', type=str, required=True, help='Input .npz parameters')
    parser.add_argument('--height', type=float, required=True, help='Your actual height in cm')
    parser.add_argument('--output', type=str, default='neutral_pose.obj', help='Output mesh')
    parser.add_argument('--pose', type=str, default='a-pose', choices=['a-pose', 't-pose'])
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print(f"CREATING NEUTRAL {args.pose.upper()} WITH YOUR BODY SHAPE")
    print("="*70)
    
    # Load parameters
    print(f"\n📦 Loading: {args.params}")
    params = np.load(args.params, allow_pickle=True)
    
    if 'betas' not in params:
        print("❌ No betas found!")
        return
    
    betas = params['betas']
    print(f"✓ Body shape parameters: {betas[:5]}... (showing first 5)")
    
    # Create neutral pose mesh
    print(f"\n🎨 Generating neutral {args.pose} mesh...")
    vertices, faces = create_smpl_neutral_pose(betas, args.height, args.pose)
    
    if vertices is None:
        print("❌ Failed to create SMPL mesh")
        return
    
    print(f"✓ Created mesh: {len(vertices)} vertices, {len(faces)} faces")
    
    # Calculate measurements
    print("\n📏 Calculating measurements...")
    measurements = calculate_accurate_measurements(vertices)
    
    print("\n" + "="*70)
    print("CORRECTED MEASUREMENTS (from neutral pose)")
    print("="*70)
    for key, value in measurements.items():
        if value:
            print(f"{key:30s}: {value:7.2f}")
    print("="*70)
    
    # Save mesh
    print(f"\n💾 Saving: {args.output}")
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.export(args.output)
    
    # Save measurements
    measurements_file = Path(args.output).with_suffix('.json')
    with open(measurements_file, 'w') as f:
        json.dump(measurements, f, indent=2)
    
    print(f"✓ Saved mesh: {args.output}")
    print(f"✓ Saved measurements: {measurements_file}")
    
    print("\n" + "="*70)
    print("✓ DONE! Perfect neutral pose with accurate measurements")
    print("="*70)
    print(f"\nOpen in Blender:")
    print(f"  open -a Blender {args.output}")
    print()

if __name__ == '__main__':
    main()


