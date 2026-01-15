"""
ACCURATE MEASUREMENT EXTRACTION
Requires actual height as calibration reference
Works for any person!
"""
import numpy as np
import trimesh
import argparse
import json
from pathlib import Path

def extract_measurements_with_height(mesh_path, actual_height_cm):
    """
    Extract body measurements from mesh with height calibration
    
    Args:
        mesh_path: Path to .obj mesh file
        actual_height_cm: Person's actual height in centimeters
    
    Returns:
        dict of measurements in cm
    """
    # Load mesh
    print(f"Loading mesh: {mesh_path}")
    mesh = trimesh.load(mesh_path)
    vertices = mesh.vertices
    
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
    
    # Calculate measurements
    measurements = {}
    measurements['height_cm'] = actual_height_cm  # Use actual
    
    y_min = scaled_vertices[:, 1].min()
    y_max = scaled_vertices[:, 1].max()
    y_range = y_max - y_min
    
    def measure_circumference(height_ratio, thickness_ratio=0.05, name=""):
        """Measure circumference at specific body height"""
        target_y = y_min + (y_range * height_ratio)
        mask = np.abs(scaled_vertices[:, 1] - target_y) < (y_range * thickness_ratio)
        slice_verts = scaled_vertices[mask]
        
        if len(slice_verts) > 10:
            # Get width and depth at this height
            x_coords = slice_verts[:, 0]
            z_coords = slice_verts[:, 2]
            
            width = x_coords.max() - x_coords.min()
            depth = z_coords.max() - z_coords.min()
            
            # Ellipse circumference approximation
            # C ≈ π * (3(a+b) - √((3a+b)(a+3b))) / 2
            # Or simpler: π * (a+b) for good approximation
            a = width / 2
            b = depth / 2
            circumference = np.pi * (a + b) * 100  # Convert to cm
            
            print(f"   {name}: width={width*100:.1f}cm, depth={depth*100:.1f}cm → {circumference:.1f}cm")
            return circumference
        return None
    
    print(f"\n📐 Measuring body parts:")
    
    # Standard body measurements
    measurements['chest_circumference_cm'] = measure_circumference(0.75, 0.04, "Chest (75%)")
    measurements['underbust_cm'] = measure_circumference(0.70, 0.03, "Underbust (70%)")
    measurements['waist_circumference_cm'] = measure_circumference(0.60, 0.03, "Waist (60%)")
    measurements['hip_circumference_cm'] = measure_circumference(0.50, 0.04, "Hips (50%)")
    measurements['neck_circumference_cm'] = measure_circumference(0.90, 0.02, "Neck (90%)")
    measurements['thigh_circumference_cm'] = measure_circumference(0.40, 0.03, "Thigh (40%)")
    
    # Width measurements
    print(f"\n📏 Width measurements:")
    
    # Shoulder width
    shoulder_y = y_min + (y_range * 0.85)
    shoulder_mask = np.abs(scaled_vertices[:, 1] - shoulder_y) < (y_range * 0.02)
    if shoulder_mask.sum() > 0:
        shoulder_width = (scaled_vertices[shoulder_mask, 0].max() - 
                         scaled_vertices[shoulder_mask, 0].min()) * 100
        measurements['shoulder_width_cm'] = shoulder_width
        print(f"   Shoulder width: {shoulder_width:.1f}cm")
    
    # Arm span
    arm_span = (scaled_vertices[:, 0].max() - scaled_vertices[:, 0].min()) * 100
    measurements['arm_span_cm'] = arm_span
    print(f"   Arm span: {arm_span:.1f}cm")
    
    # Length measurements
    print(f"\n📐 Length measurements:")
    
    # Inseam (approximate as 45% of height)
    measurements['inseam_cm'] = actual_height_cm * 0.45
    print(f"   Inseam (estimated): {measurements['inseam_cm']:.1f}cm")
    
    # Torso length (shoulder to hip)
    measurements['torso_length_cm'] = y_range * 0.35 * 100
    print(f"   Torso length: {measurements['torso_length_cm']:.1f}cm")
    
    # Arm length (approximate from shoulder to wrist)
    measurements['arm_length_cm'] = y_range * 0.30 * 100
    print(f"   Arm length (estimated): {measurements['arm_length_cm']:.1f}cm")
    
    # Add metadata
    measurements['_metadata'] = {
        'source_mesh': str(mesh_path),
        'actual_height_input_cm': actual_height_cm,
        'mesh_original_height_cm': mesh_height_cm,
        'scale_factor_applied': scale_factor,
        'calibration_method': 'height_based',
        'note': 'All measurements calibrated using actual height'
    }
    
    return measurements

def extract_measurements_from_multiple_heights(mesh_path, height_estimates):
    """
    Extract measurements using multiple height estimates
    Useful when exact height is unknown
    
    Args:
        mesh_path: Path to mesh
        height_estimates: list of possible heights in cm
    
    Returns:
        dict with measurements for each height
    """
    results = {}
    
    for height in height_estimates:
        measurements = extract_measurements_with_height(mesh_path, height)
        results[f'{height}cm'] = measurements
    
    return results

def suggest_height_from_proportions(mesh_path):
    """
    Suggest likely height range based on body proportions
    This is just an estimate - actual height still needed!
    """
    mesh = trimesh.load(mesh_path)
    vertices = mesh.vertices
    
    # Get proportions
    y_range = vertices[:, 1].max() - vertices[:, 1].min()
    x_range = vertices[:, 0].max() - vertices[:, 0].min()
    
    # Head size estimate (top 10%)
    head_start = vertices[:, 1].max() - (y_range * 0.1)
    head_verts = vertices[vertices[:, 1] > head_start]
    head_width = (head_verts[:, 0].max() - head_verts[:, 0].min()) * 100
    
    # Typical head width: 15-18cm for adults
    # Height is typically 7-8 head heights
    estimated_height_range = (head_width * 7, head_width * 8)
    
    print(f"\n🤔 Height Estimation (very approximate!):")
    print(f"   Head width: {head_width:.1f}cm")
    print(f"   Estimated height range: {estimated_height_range[0]:.0f}-{estimated_height_range[1]:.0f}cm")
    print(f"   ⚠️  This is just a guess - ask for actual height!")
    
    return estimated_height_range

def main():
    parser = argparse.ArgumentParser(
        description='Extract accurate body measurements (requires actual height)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # With known height (RECOMMENDED)
  python extract_accurate_measurements.py --mesh person.obj --height 192 --output measurements.json

  # Try multiple heights to see which looks right
  python extract_accurate_measurements.py --mesh person.obj --height-range 170 180 190 200

  # Estimate height from proportions (not recommended - very approximate)
  python extract_accurate_measurements.py --mesh person.obj --estimate-height
        '''
    )
    
    parser.add_argument('--mesh', type=str, required=True, help='Input .obj mesh file')
    parser.add_argument('--height', type=float, help='Actual height in cm (REQUIRED for accuracy)')
    parser.add_argument('--height-range', nargs='+', type=float, 
                       help='Try multiple heights (e.g., --height-range 170 180 190)')
    parser.add_argument('--estimate-height', action='store_true',
                       help='Estimate height from proportions (not accurate!)')
    parser.add_argument('--output', type=str, help='Output JSON file')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("ACCURATE MEASUREMENT EXTRACTION")
    print("="*70)
    
    # Method 1: With known height (BEST)
    if args.height:
        measurements = extract_measurements_with_height(args.mesh, args.height)
        
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
    
    # Method 2: Try multiple heights
    elif args.height_range:
        print("\n📊 Trying multiple heights...")
        results = extract_measurements_from_multiple_heights(args.mesh, args.height_range)
        
        print("\n" + "="*70)
        print("MEASUREMENTS AT DIFFERENT HEIGHTS")
        print("="*70)
        
        for height_key, measurements in results.items():
            print(f"\n### IF HEIGHT = {height_key} ###")
            for key, value in measurements.items():
                if key != '_metadata' and value is not None:
                    print(f"  {key:28s}: {value:7.2f}")
        
        print("\n💡 Pick the height that matches known measurements!")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n✅ Saved all variants to: {args.output}")
    
    # Method 3: Estimate height (NOT RECOMMENDED)
    elif args.estimate_height:
        height_range = suggest_height_from_proportions(args.mesh)
        
        print("\n⚠️  WARNING: Height estimation is not accurate!")
        print("    Please measure actual height for correct results.")
        print(f"\n    Estimated range: {height_range[0]:.0f}-{height_range[1]:.0f}cm")
        print(f"\n    Try:")
        print(f"    python extract_accurate_measurements.py --mesh {args.mesh} --height {(height_range[0]+height_range[1])/2:.0f}")
    
    else:
        print("\n❌ ERROR: Must provide --height, --height-range, or --estimate-height")
        print("\n💡 RECOMMENDED: Always ask the user for their actual height!")
        print("    python extract_accurate_measurements.py --mesh person.obj --height 192")
    
    print()

if __name__ == '__main__':
    main()


