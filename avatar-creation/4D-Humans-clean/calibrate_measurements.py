#!/usr/bin/env python3
"""
Calibration script to back-engineer correct measurement extraction
Uses actual measurements to find the right algorithm parameters
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
    """Method 2: Direct perimeter from mesh edges"""
    y_min = vertices[:, 1].min()
    y_max = vertices[:, 1].max()
    y_range = y_max - y_min
    thickness = y_range * slice_thickness
    
    mask = np.abs(vertices[:, 1] - y_level) < thickness
    slice_verts = vertices[mask]
    
    if len(slice_verts) < 10:
        return None
    
    xz_points = slice_verts[:, [0, 2]]
    
    # Simple ellipse approximation
    width = (xz_points[:, 0].max() - xz_points[:, 0].min()) * 100
    depth = (xz_points[:, 1].max() - xz_points[:, 1].min()) * 100
    a, b = width / 2, depth / 2
    # Simple ellipse: π * (a + b)
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
    # Ramanujan's approximation
    return np.pi * (3 * (a + b) - np.sqrt((3 * a + b) * (a + 3 * b)))

def find_best_landmarks_and_method(mesh_path, actual_measurements):
    """Try different methods and landmark positions to find what matches actual measurements"""
    
    print("\n" + "="*70)
    print("CALIBRATING MEASUREMENT EXTRACTION")
    print("="*70)
    
    # Load mesh
    mesh = trimesh.load(mesh_path)
    vertices = mesh.vertices
    
    # Scale to actual height
    mesh_height = vertices[:, 1].max() - vertices[:, 1].min()
    mesh_height_cm = mesh_height * 100
    scale_factor = actual_measurements['height_cm'] / mesh_height_cm
    scaled_vertices = vertices * scale_factor
    
    y_min = scaled_vertices[:, 1].min()
    y_max = scaled_vertices[:, 1].max()
    y_range = y_max - y_min
    
    print(f"\n📏 Mesh scaled to {actual_measurements['height_cm']}cm")
    print(f"   Y range: {y_min*100:.1f} to {y_max*100:.1f} cm")
    
    # Try different Y levels for each measurement
    print("\n🔍 Testing different landmark positions and methods...")
    
    best_results = {}
    
    # Test CHEST
    print("\n📐 CHEST (target: {:.1f}cm):".format(actual_measurements['chest_cm']))
    best_chest_error = float('inf')
    best_chest = None
    
    for y_ratio in np.linspace(0.6, 0.9, 30):
        y_level = y_min + (y_range * y_ratio)
        for method_num, method in enumerate([calculate_circumference_method1, 
                                             calculate_circumference_method2, 
                                             calculate_circumference_method3], 1):
            for thickness in [0.01, 0.02, 0.03, 0.04]:
                circ = method(scaled_vertices, y_level, slice_thickness=thickness)
                if circ:
                    error = abs(circ - actual_measurements['chest_cm'])
                    if error < best_chest_error:
                        best_chest_error = error
                        best_chest = {
                            'y_ratio': y_ratio,
                            'y_level': y_level,
                            'method': method_num,
                            'thickness': thickness,
                            'circumference': circ,
                            'error': error
                        }
    
    if best_chest:
        print(f"   ✓ Best: Method {best_chest['method']}, Y={best_chest['y_ratio']*100:.1f}%, "
              f"Thickness={best_chest['thickness']:.3f}")
        print(f"      Result: {best_chest['circumference']:.1f}cm (error: {best_chest['error']:.1f}cm)")
        best_results['chest'] = best_chest
    
    # Test WAIST
    print("\n📐 WAIST (target: {:.1f}cm):".format(actual_measurements['waist_cm']))
    best_waist_error = float('inf')
    best_waist = None
    
    for y_ratio in np.linspace(0.4, 0.7, 30):
        y_level = y_min + (y_range * y_ratio)
        for method_num, method in enumerate([calculate_circumference_method1, 
                                             calculate_circumference_method2, 
                                             calculate_circumference_method3], 1):
            for thickness in [0.01, 0.02, 0.03, 0.04]:
                circ = method(scaled_vertices, y_level, slice_thickness=thickness)
                if circ:
                    error = abs(circ - actual_measurements['waist_cm'])
                    if error < best_waist_error:
                        best_waist_error = error
                        best_waist = {
                            'y_ratio': y_ratio,
                            'y_level': y_level,
                            'method': method_num,
                            'thickness': thickness,
                            'circumference': circ,
                            'error': error
                        }
    
    if best_waist:
        print(f"   ✓ Best: Method {best_waist['method']}, Y={best_waist['y_ratio']*100:.1f}%, "
              f"Thickness={best_waist['thickness']:.3f}")
        print(f"      Result: {best_waist['circumference']:.1f}cm (error: {best_waist['error']:.1f}cm)")
        best_results['waist'] = best_waist
    
    # Test HIP
    print("\n📐 HIP (target: {:.1f}cm):".format(actual_measurements['hip_cm']))
    best_hip_error = float('inf')
    best_hip = None
    
    for y_ratio in np.linspace(0.3, 0.6, 30):
        y_level = y_min + (y_range * y_ratio)
        for method_num, method in enumerate([calculate_circumference_method1, 
                                             calculate_circumference_method2, 
                                             calculate_circumference_method3], 1):
            for thickness in [0.01, 0.02, 0.03, 0.04, 0.05]:
                circ = method(scaled_vertices, y_level, slice_thickness=thickness)
                if circ:
                    error = abs(circ - actual_measurements['hip_cm'])
                    if error < best_hip_error:
                        best_hip_error = error
                        best_hip = {
                            'y_ratio': y_ratio,
                            'y_level': y_level,
                            'method': method_num,
                            'thickness': thickness,
                            'circumference': circ,
                            'error': error
                        }
    
    if best_hip:
        print(f"   ✓ Best: Method {best_hip['method']}, Y={best_hip['y_ratio']*100:.1f}%, "
              f"Thickness={best_hip['thickness']:.3f}")
        print(f"      Result: {best_hip['circumference']:.1f}cm (error: {best_hip['error']:.1f}cm)")
        best_results['hip'] = best_hip
    
    return best_results

def main():
    mesh_path = 'FINAL_RELAXED_RIG.obj'
    
    if not Path(mesh_path).exists():
        print(f"❌ Error: Mesh file not found: {mesh_path}")
        return
    
    results = find_best_landmarks_and_method(mesh_path, ACTUAL_MEASUREMENTS)
    
    print("\n" + "="*70)
    print("CALIBRATION RESULTS")
    print("="*70)
    print("\n📋 Best parameters found:")
    print(json.dumps(results, indent=2, default=str))
    
    # Save results
    with open('calibration_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\n✅ Saved to: calibration_results.json")
    print("\n💡 Use these parameters to update extract_measurements_improved.py")

if __name__ == '__main__':
    main()

