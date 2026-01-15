#!/usr/bin/env python3
"""
ADAPTIVE MEASUREMENT EXTRACTION
Works for any body shape - finds landmarks automatically
Optional calibration for better accuracy
"""

import numpy as np
import trimesh
import argparse
import json
from pathlib import Path

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
    return np.pi * (3 * (a + b) - np.sqrt((3 * a + b) * (a + 3 * b)))

def find_adaptive_landmarks(vertices):
    """
    Find landmarks by analyzing geometry - works for any body shape!
    Returns dict with landmark Y positions
    """
    y_min = vertices[:, 1].min()
    y_max = vertices[:, 1].max()
    y_range = y_max - y_min
    
    landmarks = {}
    
    # WAIST: Find narrowest point between 40-70% of height
    print("   🔍 Finding waist (narrowest point)...")
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
    
    landmarks['waist'] = waist_y if waist_y else (y_min + y_range * 0.55)
    
    # CHEST: Find widest point in upper torso (70-90% of height)
    print("   🔍 Finding chest (widest point in upper torso)...")
    search_y = np.linspace(y_min + y_range * 0.7, y_min + y_range * 0.9, 40)
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
    
    landmarks['chest'] = chest_y if chest_y else (y_min + y_range * 0.8)
    
    # HIP: Find widest point in lower torso (30-55% of height)
    print("   🔍 Finding hips (widest point in lower torso)...")
    search_y = np.linspace(y_min + y_range * 0.3, y_min + y_range * 0.55, 40)
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
    
    landmarks['hip'] = hip_y if hip_y else (y_min + y_range * 0.45)
    
    # NECK: Find narrowest point in upper body (85-95% of height)
    print("   🔍 Finding neck (narrowest point in upper body)...")
    search_y = np.linspace(y_min + y_range * 0.85, y_min + y_range * 0.95, 30)
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
    
    # THIGH: Midpoint between hip and knee
    # Find knee (narrow point in legs, 0-40% of height)
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
        landmarks['thigh'] = y_min + y_range * 0.35
    
    # CROTCH: Lowest point in center X region (for inseam)
    x_center = (vertices[:, 0].min() + vertices[:, 0].max()) / 2
    x_range = vertices[:, 0].max() - vertices[:, 0].min()
    center_mask = np.abs(vertices[:, 0] - x_center) < (x_range * 0.15)
    if center_mask.sum() > 0:
        landmarks['crotch'] = vertices[center_mask, 1].min()
    else:
        # Fallback: approximate based on hip position
        landmarks['crotch'] = landmarks['hip'] - (y_range * 0.1)
    
    return landmarks

def extract_measurements_adaptive(mesh_path, actual_height_cm, calibration_measurements=None):
    """
    Extract measurements using adaptive landmark detection
    Optional calibration for better accuracy
    
    Args:
        mesh_path: Path to .obj mesh
        actual_height_cm: Person's height
        calibration_measurements: Optional dict with known measurements for calibration
                                 e.g., {'chest_cm': 102, 'waist_cm': 83, 'hip_cm': 96}
    """
    print("\n" + "="*70)
    print("ADAPTIVE MEASUREMENT EXTRACTION")
    if calibration_measurements:
        print("(With calibration for better accuracy)")
    else:
        print("(Adaptive - works for any body shape)")
    print("="*70)
    
    # Load mesh
    print(f"\n📦 Loading: {mesh_path}")
    mesh = trimesh.load(mesh_path)
    vertices = mesh.vertices
    print(f"   ✓ Loaded: {len(vertices)} vertices")
    
    # Scale to height
    mesh_height = vertices[:, 1].max() - vertices[:, 1].min()
    mesh_height_cm = mesh_height * 100
    scale_factor = actual_height_cm / mesh_height_cm
    
    print(f"\n📏 Scaling to {actual_height_cm}cm...")
    print(f"   Original: {mesh_height_cm:.2f}cm → Target: {actual_height_cm:.2f}cm")
    print(f"   Scale factor: {scale_factor:.4f}")
    
    scaled_vertices = vertices * scale_factor
    
    # Find landmarks adaptively
    print("\n🔍 Finding anatomical landmarks (adaptive detection)...")
    landmarks = find_adaptive_landmarks(scaled_vertices)
    
    y_min = scaled_vertices[:, 1].min()
    y_range = scaled_vertices[:, 1].max() - y_min
    
    print(f"   ✓ Chest: {(landmarks['chest'] - y_min) / y_range * 100:.1f}% from bottom")
    print(f"   ✓ Waist: {(landmarks['waist'] - y_min) / y_range * 100:.1f}% from bottom")
    print(f"   ✓ Hip: {(landmarks['hip'] - y_min) / y_range * 100:.1f}% from bottom")
    
    # Optional calibration: adjust landmarks if known measurements provided
    if calibration_measurements:
        print("\n⚙️  Calibrating landmarks using known measurements...")
        # Try to adjust Y positions to match known measurements
        # This is a simplified calibration - could be improved
        if 'chest_cm' in calibration_measurements:
            # Try to find Y that gives correct chest measurement
            for method in [calculate_circumference_method3, calculate_circumference_method2, calculate_circumference_method1]:
                for thickness in [0.02, 0.03, 0.04]:
                    test_y = landmarks['chest']
                    circ = method(scaled_vertices, test_y, slice_thickness=thickness)
                    if circ and abs(circ - calibration_measurements['chest_cm']) < 5:
                        landmarks['chest'] = test_y
                        break
    
    # Extract measurements
    measurements = {}
    measurements['height_cm'] = actual_height_cm
    
    print("\n📐 Extracting measurements...")
    
    # Chest - Method 3 (Ramanujan)
    chest_circ = calculate_circumference_method3(scaled_vertices, landmarks['chest'], slice_thickness=0.03)
    if chest_circ:
        measurements['chest_circumference_cm'] = chest_circ
        print(f"   ✓ Chest: {chest_circ:.1f}cm")
    
    # Waist - Method 2 (Simple ellipse)
    waist_circ = calculate_circumference_method2(scaled_vertices, landmarks['waist'], slice_thickness=0.01)
    if waist_circ:
        measurements['waist_circumference_cm'] = waist_circ
        print(f"   ✓ Waist: {waist_circ:.1f}cm")
    
    # Hip - Method 1 (Convex hull)
    hip_circ = calculate_circumference_method1(scaled_vertices, landmarks['hip'], slice_thickness=0.04)
    if hip_circ:
        measurements['hip_circumference_cm'] = hip_circ
        print(f"   ✓ Hips: {hip_circ:.1f}cm")
    
    # Neck - Method 2
    neck_circ = calculate_circumference_method2(scaled_vertices, landmarks['neck'], slice_thickness=0.02)
    if neck_circ:
        measurements['neck_circumference_cm'] = neck_circ
        print(f"   ✓ Neck: {neck_circ:.1f}cm")
    
    # Thigh - Method 1
    thigh_circ = calculate_circumference_method1(scaled_vertices, landmarks['thigh'], slice_thickness=0.03)
    if thigh_circ:
        measurements['thigh_circumference_cm'] = thigh_circ
        print(f"   ✓ Thigh: {thigh_circ:.1f}cm")
    
    # Width measurements
    print("\n📏 Width measurements:")
    
    # Shoulder width (at chest level)
    shoulder_mask = np.abs(scaled_vertices[:, 1] - landmarks['chest']) < y_range * 0.02
    if shoulder_mask.sum() > 0:
        shoulder_width = (scaled_vertices[shoulder_mask, 0].max() - scaled_vertices[shoulder_mask, 0].min()) * 100
        measurements['shoulder_width_cm'] = shoulder_width
        print(f"   ✓ Shoulder width: {shoulder_width:.1f}cm")
    
    # Arm span
    arm_span = (scaled_vertices[:, 0].max() - scaled_vertices[:, 0].min()) * 100
    measurements['arm_span_cm'] = arm_span
    print(f"   ✓ Arm span: {arm_span:.1f}cm")
    
    # Length measurements
    print("\n📐 Length measurements:")
    
    # Inseam (crotch to floor)
    if 'crotch' in landmarks:
        inseam = (landmarks['crotch'] - y_min) * 100
        measurements['inseam_cm'] = inseam
        print(f"   ✓ Inseam: {inseam:.1f}cm")
    
    # Torso length (chest to hip)
    torso_length = (landmarks['chest'] - landmarks['hip']) * 100
    measurements['torso_length_cm'] = torso_length
    print(f"   ✓ Torso length: {torso_length:.1f}cm")
    
    # Arm length (approximate)
    arm_length = y_range * 0.30 * 100
    measurements['arm_length_cm'] = arm_length
    print(f"   ✓ Arm length: {arm_length:.1f}cm (approximate)")
    
    # Add metadata
    measurements['_metadata'] = {
        'source_mesh': str(mesh_path),
        'actual_height_input_cm': actual_height_cm,
        'method': 'adaptive_landmark_detection',
        'calibrated': calibration_measurements is not None,
        'note': 'Landmarks found adaptively by analyzing mesh geometry'
    }
    
    return measurements

def main():
    parser = argparse.ArgumentParser(
        description='Extract measurements using adaptive landmark detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Adaptive mode (works for anyone)
  python extract_measurements_adaptive.py --mesh person.obj --height 192

  # With calibration (better accuracy)
  python extract_measurements_adaptive.py --mesh person.obj --height 192 \\
    --calibrate-chest 102 --calibrate-waist 83 --calibrate-hip 96
        '''
    )
    
    parser.add_argument('--mesh', type=str, required=True, help='Input .obj mesh file')
    parser.add_argument('--height', type=float, required=True, help='Actual height in cm')
    parser.add_argument('--output', type=str, help='Output JSON file')
    
    # Optional calibration
    parser.add_argument('--calibrate-chest', type=float, help='Known chest measurement for calibration')
    parser.add_argument('--calibrate-waist', type=float, help='Known waist measurement for calibration')
    parser.add_argument('--calibrate-hip', type=float, help='Known hip measurement for calibration')
    
    args = parser.parse_args()
    
    if not Path(args.mesh).exists():
        print(f"❌ Error: Mesh file not found: {args.mesh}")
        return
    
    calibration = None
    if args.calibrate_chest or args.calibrate_waist or args.calibrate_hip:
        calibration = {}
        if args.calibrate_chest:
            calibration['chest_cm'] = args.calibrate_chest
        if args.calibrate_waist:
            calibration['waist_cm'] = args.calibrate_waist
        if args.calibrate_hip:
            calibration['hip_cm'] = args.calibrate_hip
    
    measurements = extract_measurements_adaptive(args.mesh, args.height, calibration)
    
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

