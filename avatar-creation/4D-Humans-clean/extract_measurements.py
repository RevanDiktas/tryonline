"""
Extract body measurements from SMPL mesh parameters
Outputs: height, chest, waist, hip, inseam, arm length, etc.
"""
import numpy as np
import trimesh
import argparse
from pathlib import Path
import json

def extract_measurements(mesh_path, params_path):
    """
    Extract key body measurements from SMPL mesh
    Returns measurements in centimeters
    """
    # Load mesh
    mesh = trimesh.load(mesh_path)
    vertices = mesh.vertices
    
    # Load SMPL parameters
    params = np.load(params_path)
    
    measurements = {}
    
    # HEIGHT (head to floor)
    measurements['height_cm'] = (vertices[:, 1].max() - vertices[:, 1].min()) * 100
    
    # Get torso vertices (approximate body regions)
    y_range = vertices[:, 1].max() - vertices[:, 1].min()
    
    # Chest level (approximately 75% up from ground)
    chest_y = vertices[:, 1].min() + (y_range * 0.75)
    chest_vertices = vertices[np.abs(vertices[:, 1] - chest_y) < (y_range * 0.05)]
    if len(chest_vertices) > 0:
        chest_width = chest_vertices[:, 0].max() - chest_vertices[:, 0].min()
        chest_depth = chest_vertices[:, 2].max() - chest_vertices[:, 2].min()
        measurements['chest_circumference_cm'] = np.pi * (chest_width + chest_depth) / 2 * 100
    
    # Waist level (approximately 60% up from ground)
    waist_y = vertices[:, 1].min() + (y_range * 0.60)
    waist_vertices = vertices[np.abs(vertices[:, 1] - waist_y) < (y_range * 0.03)]
    if len(waist_vertices) > 0:
        waist_width = waist_vertices[:, 0].max() - waist_vertices[:, 0].min()
        waist_depth = waist_vertices[:, 2].max() - waist_vertices[:, 2].min()
        measurements['waist_circumference_cm'] = np.pi * (waist_width + waist_depth) / 2 * 100
    
    # Hip level (approximately 50% up from ground)
    hip_y = vertices[:, 1].min() + (y_range * 0.50)
    hip_vertices = vertices[np.abs(vertices[:, 1] - hip_y) < (y_range * 0.05)]
    if len(hip_vertices) > 0:
        hip_width = hip_vertices[:, 0].max() - hip_vertices[:, 0].min()
        hip_depth = hip_vertices[:, 2].max() - hip_vertices[:, 2].min()
        measurements['hip_circumference_cm'] = np.pi * (hip_width + hip_depth) / 2 * 100
    
    # Shoulder width (at shoulder height)
    shoulder_y = vertices[:, 1].min() + (y_range * 0.85)
    shoulder_vertices = vertices[np.abs(vertices[:, 1] - shoulder_y) < (y_range * 0.02)]
    if len(shoulder_vertices) > 0:
        measurements['shoulder_width_cm'] = (shoulder_vertices[:, 0].max() - shoulder_vertices[:, 0].min()) * 100
    
    # Arm length (approximate from shoulder to wrist)
    # Find leftmost and rightmost points (extended arms)
    measurements['arm_span_cm'] = (vertices[:, 0].max() - vertices[:, 0].min()) * 100
    
    # Inseam (crotch to floor - approximate as 45% of height)
    measurements['inseam_cm'] = measurements['height_cm'] * 0.45
    
    # Neck circumference (approximate)
    neck_y = vertices[:, 1].min() + (y_range * 0.88)
    neck_vertices = vertices[np.abs(vertices[:, 1] - neck_y) < (y_range * 0.02)]
    if len(neck_vertices) > 0:
        neck_width = neck_vertices[:, 0].max() - neck_vertices[:, 0].min()
        neck_depth = neck_vertices[:, 2].max() - neck_vertices[:, 2].min()
        measurements['neck_circumference_cm'] = np.pi * (neck_width + neck_depth) / 2 * 100
    
    # Add SMPL shape parameters (betas)
    if 'betas' in params:
        measurements['smpl_betas'] = params['betas'].tolist()
    
    return measurements

def main():
    parser = argparse.ArgumentParser(description='Extract body measurements from SMPL mesh')
    parser.add_argument('--mesh', type=str, required=True, help='Path to .obj mesh file')
    parser.add_argument('--params', type=str, help='Path to .npz params file (optional)')
    parser.add_argument('--output', type=str, help='Output JSON file (optional)')
    
    args = parser.parse_args()
    
    # Auto-find params file if not specified
    if not args.params:
        mesh_path = Path(args.mesh)
        params_path = mesh_path.parent / f"{mesh_path.stem}_params.npz"
        if not params_path.exists():
            print(f"Warning: Parameters file not found at {params_path}")
            params_path = None
    else:
        params_path = args.params
    
    print(f"Extracting measurements from: {args.mesh}")
    measurements = extract_measurements(args.mesh, params_path)
    
    # Print measurements
    print("\n" + "="*60)
    print("BODY MEASUREMENTS")
    print("="*60)
    for key, value in measurements.items():
        if key != 'smpl_betas':
            print(f"{key:30s}: {value:7.2f}")
    print("="*60)
    
    # Save to JSON if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(measurements, f, indent=2)
        print(f"\n✓ Saved measurements to: {args.output}")
    
    return measurements

if __name__ == '__main__':
    main()


