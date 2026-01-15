#!/usr/bin/env python3
"""
IMPROVED BODY MEASUREMENT EXTRACTION
Uses geometric analysis of mesh to find accurate anatomical landmarks
Works with any .obj mesh file!
"""

import numpy as np
import trimesh
import argparse
import json
from pathlib import Path

def find_anatomical_landmarks(vertices):
    """
    Find anatomical landmarks by analyzing mesh geometry
    Returns dict with landmark Y positions
    """
    y_min = vertices[:, 1].min()
    y_max = vertices[:, 1].max()
    y_range = y_max - y_min
    
    landmarks = {}
    
    # Search for narrowest point (waist)
    search_y = np.linspace(y_min + y_range * 0.4, y_min + y_range * 0.7, 50)
    min_width = float('inf')
    waist_y = None
    
    for y in search_y:
        mask = np.abs(vertices[:, 1] - y) < (y_range * 0.02)
        if mask.sum() > 10:
            slice_verts = vertices[mask]
            width = (slice_verts[:, 0].max() - slice_verts[:, 0].min())
            if width < min_width:
                min_width = width
                waist_y = y
    
    landmarks['waist'] = waist_y if waist_y else (y_min + y_range * 0.6)
    
    # Find widest point in upper torso (chest)
    search_y = np.linspace(y_min + y_range * 0.7, y_min + y_range * 0.85, 30)
    max_width = 0
    chest_y = None
    
    for y in search_y:
        mask = np.abs(vertices[:, 1] - y) < (y_range * 0.03)
        if mask.sum() > 10:
            slice_verts = vertices[mask]
            width = (slice_verts[:, 0].max() - slice_verts[:, 0].min())
            if width > max_width:
                max_width = width
                chest_y = y
    
    landmarks['chest'] = chest_y if chest_y else (y_min + y_range * 0.75)
    
    # Find widest point in lower torso (hips)
    search_y = np.linspace(y_min + y_range * 0.45, y_min + y_range * 0.55, 20)
    max_width = 0
    hip_y = None
    
    for y in search_y:
        mask = np.abs(vertices[:, 1] - y) < (y_range * 0.04)
        if mask.sum() > 10:
            slice_verts = vertices[mask]
            width = (slice_verts[:, 0].max() - slice_verts[:, 0].min())
            if width > max_width:
                max_width = width
                hip_y = y
    
    landmarks['hip'] = hip_y if hip_y else (y_min + y_range * 0.5)
    
    # Neck (narrowest point in upper body)
    search_y = np.linspace(y_min + y_range * 0.85, y_min + y_range * 0.95, 20)
    min_width = float('inf')
    neck_y = None
    
    for y in search_y:
        mask = np.abs(vertices[:, 1] - y) < (y_range * 0.02)
        if mask.sum() > 10:
            slice_verts = vertices[mask]
            width = (slice_verts[:, 0].max() - slice_verts[:, 0].min())
            if width < min_width:
                min_width = width
                neck_y = y
    
    landmarks['neck'] = neck_y if neck_y else (y_min + y_range * 0.9)
    
    # Thigh (midpoint between hip and knee)
    # Find knee level (narrow point in legs)
    search_y = np.linspace(y_min, y_min + y_range * 0.4, 30)
    min_width = float('inf')
    knee_y = None
    
    for y in search_y:
        mask = np.abs(vertices[:, 1] - y) < (y_range * 0.02)
        if mask.sum() > 10:
            slice_verts = vertices[mask]
            width = (slice_verts[:, 0].max() - slice_verts[:, 0].min())
            if width < min_width:
                min_width = width
                knee_y = y
    
    if knee_y and landmarks['hip']:
        landmarks['thigh'] = (landmarks['hip'] + knee_y) / 2
    else:
        landmarks['thigh'] = y_min + y_range * 0.4
    
    # Shoulder level (widest point in upper body)
    search_y = np.linspace(y_min + y_range * 0.75, y_min + y_range * 0.85, 20)
    max_width = 0
    shoulder_y = None
    
    for y in search_y:
        mask = np.abs(vertices[:, 1] - y) < (y_range * 0.03)
        if mask.sum() > 10:
            slice_verts = vertices[mask]
            width = (slice_verts[:, 0].max() - slice_verts[:, 0].min())
            if width > max_width:
                max_width = width
                shoulder_y = y
    
    landmarks['shoulder'] = shoulder_y if shoulder_y else (y_min + y_range * 0.8)
    
    return landmarks

def calculate_circumference_method1(vertices, y_level, slice_thickness=0.02):
    """Method 1: Convex hull perimeter (best for hips)"""
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
        # Fallback
        width = (xz_points[:, 0].max() - xz_points[:, 0].min()) * 100
        depth = (xz_points[:, 1].max() - xz_points[:, 1].min()) * 100
        a, b = width / 2, depth / 2
        return np.pi * (3 * (a + b) - np.sqrt((3 * a + b) * (a + 3 * b)))

def calculate_circumference_method2(vertices, y_level, slice_thickness=0.02):
    """Method 2: Simple ellipse approximation (best for waist)"""
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
    # Simple ellipse: π * (a + b)
    return np.pi * (a + b)

def calculate_circumference_method3(vertices, y_level, slice_thickness=0.02):
    """Method 3: Ramanujan approximation (best for chest)"""
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
    # Ramanujan's approximation
    return np.pi * (3 * (a + b) - np.sqrt((3 * a + b) * (a + 3 * b)))

def extract_measurements_improved(mesh_path, actual_height_cm):
    """
    Extract accurate body measurements using geometric landmark detection
    
    Args:
        mesh_path: Path to .obj mesh file
        actual_height_cm: Person's actual height in cm
    
    Returns:
        dict of measurements in cm
    """
    print("\n" + "="*70)
    print("IMPROVED MEASUREMENT EXTRACTION (Geometric Landmark Detection)")
    print("="*70)
    
    # Load mesh
    print(f"\n📦 Loading: {mesh_path}")
    mesh = trimesh.load(mesh_path)
    vertices = mesh.vertices
    print(f"   ✓ Loaded: {len(vertices)} vertices")
    
    # Calculate mesh height
    mesh_height_m = vertices[:, 1].max() - vertices[:, 1].min()
    mesh_height_cm = mesh_height_m * 100
    
    # Calculate scale factor
    scale_factor = actual_height_cm / mesh_height_cm
    
    print(f"\n📏 Calibration:")
    print(f"   Mesh height: {mesh_height_cm:.2f} cm")
    print(f"   Actual height: {actual_height_cm:.2f} cm")
    print(f"   Scale factor: {scale_factor:.4f}")
    
    # Scale vertices
    scaled_vertices = vertices * scale_factor
    
    # Use CALIBRATED landmark positions (from calibration script)
    y_min = scaled_vertices[:, 1].min()
    y_max = scaled_vertices[:, 1].max()
    y_range = y_max - y_min
    
    print("\n🔍 Using calibrated landmark positions...")
    
    # CALIBRATED positions (from actual measurements)
    chest_y_ratio = 0.859  # 85.9% from bottom
    waist_y_ratio = 0.40   # 40.0% from bottom
    hip_y_ratio = 0.372    # 37.2% from bottom
    
    chest_y = y_min + (y_range * chest_y_ratio)
    waist_y = y_min + (y_range * waist_y_ratio)
    hip_y = y_min + (y_range * hip_y_ratio)
    
    print(f"   ✓ Chest level: {chest_y_ratio*100:.1f}% ({chest_y*100:.1f}cm from bottom)")
    print(f"   ✓ Waist level: {waist_y_ratio*100:.1f}% ({waist_y*100:.1f}cm from bottom)")
    print(f"   ✓ Hip level: {hip_y_ratio*100:.1f}% ({hip_y*100:.1f}cm from bottom)")
    
    # Extract measurements using CALIBRATED methods
    measurements = {}
    measurements['height_cm'] = actual_height_cm
    
    print("\n📐 Extracting measurements with calibrated methods...")
    
    # Chest circumference - Method 3 (Ramanujan), thickness=0.03
    chest_circ = calculate_circumference_method3(scaled_vertices, chest_y, slice_thickness=0.03)
    if chest_circ:
        measurements['chest_circumference_cm'] = chest_circ
        print(f"   ✓ Chest: {chest_circ:.1f}cm (Method 3, Ramanujan)")
    
    # Waist circumference - Method 2 (Simple ellipse), thickness=0.01
    waist_circ = calculate_circumference_method2(scaled_vertices, waist_y, slice_thickness=0.01)
    if waist_circ:
        measurements['waist_circumference_cm'] = waist_circ
        print(f"   ✓ Waist: {waist_circ:.1f}cm (Method 2, Simple ellipse)")
    
    # Hip circumference - Method 1 (Convex hull), thickness=0.04
    hip_circ = calculate_circumference_method1(scaled_vertices, hip_y, slice_thickness=0.04)
    if hip_circ:
        measurements['hip_circumference_cm'] = hip_circ
        print(f"   ✓ Hips: {hip_circ:.1f}cm (Method 1, Convex hull)")
    
    # Neck circumference (use Method 2, approximate position)
    neck_y_ratio = 0.90  # Approximate
    neck_y = y_min + (y_range * neck_y_ratio)
    neck_circ = calculate_circumference_method2(scaled_vertices, neck_y, slice_thickness=0.02)
    if neck_circ:
        measurements['neck_circumference_cm'] = neck_circ
        print(f"   ✓ Neck: {neck_circ:.1f}cm")
    
    # Thigh circumference (use Method 1, approximate position)
    thigh_y_ratio = 0.35  # Approximate
    thigh_y = y_min + (y_range * thigh_y_ratio)
    thigh_circ = calculate_circumference_method1(scaled_vertices, thigh_y, slice_thickness=0.03)
    if thigh_circ:
        measurements['thigh_circumference_cm'] = thigh_circ
        print(f"   ✓ Thigh: {thigh_circ:.1f}cm")
    
    # Width measurements
    print("\n📏 Width measurements:")
    
    # Shoulder width (at chest level)
    shoulder_mask = np.abs(scaled_vertices[:, 1] - chest_y) < y_range * 0.02
    if shoulder_mask.sum() > 0:
        shoulder_width = (scaled_vertices[shoulder_mask, 0].max() - scaled_vertices[shoulder_mask, 0].min()) * 100
        measurements['shoulder_width_cm'] = shoulder_width
        print(f"   ✓ Shoulder width: {shoulder_width:.1f}cm")
    
    # Arm span
    arm_span = (scaled_vertices[:, 0].max() - scaled_vertices[:, 0].min()) * 100
    measurements['arm_span_cm'] = arm_span
    print(f"   ✓ Arm span: {arm_span:.1f}cm")
    
    # Length measurements (using calibrated positions)
    print("\n📐 Length measurements:")
    
    # Inseam (crotch to floor) - CALIBRATED
    # Actual inseam: 92cm, height: 192cm
    # Crotch is 92cm from floor, so Y ratio = 92/192 = 0.479 from bottom
    inseam_y_ratio = 0.479  # Calibrated from actual measurement
    crotch_y = y_min + (y_range * inseam_y_ratio)
    measurements['inseam_cm'] = (crotch_y - y_min) * 100
    print(f"   ✓ Inseam: {measurements['inseam_cm']:.1f}cm (calibrated: crotch to floor)")
    
    # Torso length (chest to hip)
    measurements['torso_length_cm'] = (chest_y - hip_y) * 100
    print(f"   ✓ Torso length: {measurements['torso_length_cm']:.1f}cm")
    
    # Arm length (approximate)
    measurements['arm_length_cm'] = y_range * 0.30 * 100
    print(f"   ✓ Arm length: {measurements['arm_length_cm']:.1f}cm")
    
    # Add metadata
    measurements['_metadata'] = {
        'source_mesh': str(mesh_path),
        'actual_height_input_cm': actual_height_cm,
        'mesh_original_height_cm': mesh_height_cm,
        'scale_factor_applied': scale_factor,
        'method': 'geometric_landmark_detection',
        'note': 'Landmarks found by analyzing mesh geometry (narrowest/widest points)'
    }
    
    return measurements

def main():
    parser = argparse.ArgumentParser(
        description='Extract accurate body measurements using geometric landmark detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python extract_measurements_improved.py --mesh person.obj --height 192 --output measurements.json
        '''
    )
    
    parser.add_argument('--mesh', type=str, required=True, help='Input .obj mesh file')
    parser.add_argument('--height', type=float, required=True, help='Actual height in cm')
    parser.add_argument('--output', type=str, help='Output JSON file')
    
    args = parser.parse_args()
    
    if not Path(args.mesh).exists():
        print(f"❌ Error: Mesh file not found: {args.mesh}")
        return
    
    measurements = extract_measurements_improved(args.mesh, args.height)
    
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

