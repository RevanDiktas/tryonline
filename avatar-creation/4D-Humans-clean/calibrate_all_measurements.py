#!/usr/bin/env python3
"""
Calibrate ALL measurements, not just chest/waist/hips
"""

import numpy as np
import trimesh
import json
from pathlib import Path

# Your actual measurements
ACTUAL_MEASUREMENTS = {
    'height_cm': 192,
    'chest_cm': 102,
    'waist_cm': 83,
    'hip_cm': 96,
    'inseam_cm': 92,  # You provided this
    # Add more as you provide them:
    # 'neck_cm': ?,
    # 'thigh_cm': ?,
    # 'torso_length_cm': ?,
    # 'arm_length_cm': ?,
    # 'shoulder_width_cm': ?,
}

def calculate_circumference_method1(vertices, y_level, slice_thickness=0.02):
    """Method 1: Convex hull perimeter"""
    y_min = vertices[:, 1].min()
    y_max = vertices[:, 1].max()
    y_range = y_max - y_min
    thickness = y_range * slice_thickness
    
    mask = np.abs(vertices[:, 1] - y_level) < thickness
    slice_verts = vertices[mask]
    
    if len(slice_verts) < 10:
        return None
    
    xz_points = slice_verts[:, [0, 2]]
    
    try:
        from scipy.spatial import ConvexHull
        hull = ConvexHull(xz_points)
        perimeter = 0.0
        for i in range(len(hull.vertices)):
            p1 = xz_points[hull.vertices[i]]
            p2 = xz_points[hull.vertices[(i + 1) % len(hull.vertices)]]
            perimeter += np.linalg.norm(p2 - p1)
        return perimeter * 100
    except:
        width = (xz_points[:, 0].max() - xz_points[:, 0].min()) * 100
        depth = (xz_points[:, 1].max() - xz_points[:, 1].min()) * 100
        a, b = width / 2, depth / 2
        return np.pi * (3 * (a + b) - np.sqrt((3 * a + b) * (a + 3 * b)))

def calculate_circumference_method2(vertices, y_level, slice_thickness=0.02):
    """Method 2: Simple ellipse approximation"""
    y_min = vertices[:, 1].min()
    y_max = vertices[:, 1].max()
    y_range = y_max - y_min
    thickness = y_range * slice_thickness
    
    mask = np.abs(vertices[:, 1] - y_level) < thickness
    slice_verts = vertices[mask]
    
    if len(slice_verts) < 10:
        return None
    
    xz_points = slice_verts[:, [0, 2]]
    width = (xz_points[:, 0].max() - xz_points[:, 0].min()) * 100
    depth = (xz_points[:, 1].max() - xz_points[:, 1].min()) * 100
    a, b = width / 2, depth / 2
    return np.pi * (a + b)

def calculate_circumference_method3(vertices, y_level, slice_thickness=0.02):
    """Method 3: Ramanujan approximation"""
    y_min = vertices[:, 1].min()
    y_max = vertices[:, 1].max()
    y_range = y_max - y_min
    thickness = y_range * slice_thickness
    
    mask = np.abs(vertices[:, 1] - y_level) < thickness
    slice_verts = vertices[mask]
    
    if len(slice_verts) < 10:
        return None
    
    xz_points = slice_verts[:, [0, 2]]
    width = (xz_points[:, 0].max() - xz_points[:, 0].min()) * 100
    depth = (xz_points[:, 1].max() - xz_points[:, 1].min()) * 100
    a, b = width / 2, depth / 2
    return np.pi * (3 * (a + b) - np.sqrt((3 * a + b) * (a + 3 * b)))

def calibrate_inseam(vertices, actual_inseam_cm):
    """Find the correct Y position for inseam measurement"""
    y_min = vertices[:, 1].min()
    y_max = vertices[:, 1].max()
    
    # Inseam is from hip to ankle (or floor)
    # Try different hip positions and see which gives correct inseam
    best_error = float('inf')
    best_hip_y = None
    
    # Known hip Y ratio from previous calibration
    hip_y_ratio = 0.372
    hip_y = y_min + ((y_max - y_min) * hip_y_ratio)
    
    # Inseam should be: hip_y to y_min (floor)
    calculated_inseam = (hip_y - y_min) * 100
    
    print(f"\n📐 INSEAM Calibration:")
    print(f"   Current calculation: {calculated_inseam:.1f}cm")
    print(f"   Actual: {actual_inseam_cm:.1f}cm")
    print(f"   Error: {abs(calculated_inseam - actual_inseam_cm):.1f}cm")
    
    # The issue is likely that we need to measure from a different point
    # Inseam is typically from crotch to floor, not hip to floor
    # Let's find the crotch position (lowest point between legs)
    
    # Search for lowest point in the middle X region (between legs)
    x_center = (vertices[:, 0].min() + vertices[:, 0].max()) / 2
    x_range = vertices[:, 0].max() - vertices[:, 0].min()
    
    # Look for lowest Y in center X region (crotch area)
    center_mask = np.abs(vertices[:, 0] - x_center) < (x_range * 0.2)
    if center_mask.sum() > 0:
        crotch_y = vertices[center_mask, 1].min()
        crotch_inseam = (crotch_y - y_min) * 100
        
        print(f"   Crotch Y: {crotch_y*100:.1f}cm from bottom")
        print(f"   Inseam from crotch: {crotch_inseam:.1f}cm")
        
        if abs(crotch_inseam - actual_inseam_cm) < abs(calculated_inseam - actual_inseam_cm):
            return {
                'method': 'crotch_to_floor',
                'crotch_y': crotch_y,
                'inseam': crotch_inseam,
                'error': abs(crotch_inseam - actual_inseam_cm)
            }
    
    # If crotch doesn't work, try adjusting hip position
    # Maybe inseam should be measured differently
    return {
        'method': 'hip_to_floor',
        'hip_y': hip_y,
        'inseam': calculated_inseam,
        'error': abs(calculated_inseam - actual_inseam_cm),
        'note': 'Need to find correct measurement point'
    }

def main():
    mesh_path = 'FINAL_RELAXED_RIG.obj'
    
    if not Path(mesh_path).exists():
        print(f"❌ Error: Mesh file not found: {mesh_path}")
        return
    
    # Load mesh
    mesh = trimesh.load(mesh_path)
    vertices = mesh.vertices
    
    # Scale to actual height
    mesh_height = vertices[:, 1].max() - vertices[:, 1].min()
    mesh_height_cm = mesh_height * 100
    scale_factor = ACTUAL_MEASUREMENTS['height_cm'] / mesh_height_cm
    scaled_vertices = vertices * scale_factor
    
    print("\n" + "="*70)
    print("CALIBRATING ALL MEASUREMENTS")
    print("="*70)
    
    results = {}
    
    # Calibrate inseam
    if 'inseam_cm' in ACTUAL_MEASUREMENTS:
        inseam_result = calibrate_inseam(scaled_vertices, ACTUAL_MEASUREMENTS['inseam_cm'])
        results['inseam'] = inseam_result
    
    print("\n" + "="*70)
    print("CALIBRATION RESULTS")
    print("="*70)
    print(json.dumps(results, indent=2, default=str))
    
    print("\n💡 Please provide your actual measurements for:")
    print("   - Neck circumference")
    print("   - Thigh circumference")
    print("   - Torso length")
    print("   - Arm length")
    print("   - Shoulder width")
    print("\n   Then I can calibrate those too!")

if __name__ == '__main__':
    main()

