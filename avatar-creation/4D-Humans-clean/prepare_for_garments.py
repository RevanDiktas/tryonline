"""
Complete pipeline: Extract measurements + Normalize pose for garment draping
This is your one-stop script to prepare meshes for garment work
"""
import subprocess
import argparse
import json
from pathlib import Path
import sys

def run_measurement_extraction(mesh_path, output_json):
    """Extract body measurements"""
    print("\n" + "="*60)
    print("STEP 1: Extracting Body Measurements")
    print("="*60)
    
    cmd = [
        sys.executable,
        'extract_measurements.py',
        '--mesh', str(mesh_path),
        '--output', str(output_json)
    ]
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print("✓ Measurements extracted successfully")
        
        # Load and display measurements
        with open(output_json, 'r') as f:
            measurements = json.load(f)
        
        return measurements
    else:
        print("✗ Failed to extract measurements")
        return None

def run_pose_normalization(mesh_path, output_path, pose_type='a-pose'):
    """Normalize pose using Blender"""
    print("\n" + "="*60)
    print(f"STEP 2: Normalizing Pose to {pose_type.upper()}")
    print("="*60)
    
    # Check if Blender is installed
    blender_paths = [
        '/Applications/Blender.app/Contents/MacOS/Blender',
        '/usr/local/bin/blender',
        'blender'
    ]
    
    blender_cmd = None
    for path in blender_paths:
        if Path(path).exists() or subprocess.run(['which', path], capture_output=True).returncode == 0:
            blender_cmd = path
            break
    
    if not blender_cmd:
        print("\n⚠️  Blender not found!")
        print("Please install Blender:")
        print("  brew install --cask blender")
        print("\nOr download from: https://www.blender.org/download/")
        return None
    
    print(f"Using Blender: {blender_cmd}")
    
    cmd = [
        blender_cmd,
        '--background',
        '--python', 'blender_normalize_pose.py',
        '--',
        '--input', str(mesh_path),
        '--output', str(output_path),
        '--pose', pose_type
    ]
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print(f"✓ Pose normalized and saved to: {output_path}")
        return output_path
    else:
        print("✗ Failed to normalize pose")
        return None

def create_summary_report(measurements, normalized_mesh, output_dir):
    """Create a summary report"""
    report = {
        'measurements': measurements,
        'normalized_mesh': str(normalized_mesh),
        'ready_for_garments': True
    }
    
    report_path = output_dir / 'garment_ready_summary.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\n" + "="*60)
    print("SUMMARY REPORT")
    print("="*60)
    print(f"\n📏 Measurements:")
    for key, value in measurements.items():
        if key != 'smpl_betas' and isinstance(value, (int, float)):
            print(f"  {key:30s}: {value:7.2f}")
    
    print(f"\n📦 Outputs:")
    print(f"  Normalized mesh: {normalized_mesh}")
    print(f"  Measurements JSON: {output_dir / 'measurements.json'}")
    print(f"  Blender file: {Path(normalized_mesh).with_suffix('.blend')}")
    print(f"  Summary: {report_path}")
    
    print("\n" + "="*60)
    print("✓ READY FOR GARMENT DRAPING!")
    print("="*60)
    
    return report_path

def main():
    parser = argparse.ArgumentParser(
        description='Prepare SMPL mesh for garment draping',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Process single mesh
  python prepare_for_garments.py --mesh my_mesh.obj --output-dir garment_ready

  # Process with T-pose instead of A-pose
  python prepare_for_garments.py --mesh my_mesh.obj --pose t-pose

  # Process all meshes in a folder
  python prepare_for_garments.py --batch multiple_meshes/*.obj --output-dir batch_ready
        '''
    )
    
    parser.add_argument('--mesh', type=str, help='Input .obj mesh file')
    parser.add_argument('--batch', nargs='+', help='Process multiple meshes')
    parser.add_argument('--output-dir', type=str, default='garment_ready', 
                        help='Output directory')
    parser.add_argument('--pose', type=str, default='a-pose', 
                        choices=['t-pose', 'a-pose'],
                        help='Target pose (a-pose recommended for garments)')
    
    args = parser.parse_args()
    
    # Determine which meshes to process
    if args.batch:
        meshes = [Path(m) for m in args.batch]
    elif args.mesh:
        meshes = [Path(args.mesh)]
    else:
        print("Error: Specify either --mesh or --batch")
        return
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    print("\n" + "="*70)
    print("GARMENT PREPARATION PIPELINE")
    print("="*70)
    print(f"\nProcessing {len(meshes)} mesh(es)")
    print(f"Output directory: {output_dir}")
    print(f"Target pose: {args.pose.upper()}")
    
    # Process each mesh
    for i, mesh_path in enumerate(meshes, 1):
        print(f"\n\n{'#'*70}")
        print(f"# MESH {i}/{len(meshes)}: {mesh_path.name}")
        print(f"{'#'*70}")
        
        if not mesh_path.exists():
            print(f"✗ File not found: {mesh_path}")
            continue
        
        # Create subfolder for this mesh
        mesh_output_dir = output_dir / mesh_path.stem
        mesh_output_dir.mkdir(exist_ok=True)
        
        # Step 1: Extract measurements
        measurements_json = mesh_output_dir / 'measurements.json'
        measurements = run_measurement_extraction(mesh_path, measurements_json)
        
        if not measurements:
            print("Skipping pose normalization due to measurement extraction failure")
            continue
        
        # Step 2: Normalize pose
        normalized_mesh = mesh_output_dir / f"{mesh_path.stem}_normalized.obj"
        result = run_pose_normalization(mesh_path, normalized_mesh, args.pose)
        
        if not result:
            print("Pose normalization failed, but measurements are available")
            continue
        
        # Step 3: Create summary
        create_summary_report(measurements, normalized_mesh, mesh_output_dir)
    
    print("\n\n" + "="*70)
    print("🎉 PIPELINE COMPLETE!")
    print("="*70)
    print(f"\nAll outputs saved to: {output_dir}/")
    print("\nNext steps:")
    print("  1. Open normalized mesh in Blender")
    print("  2. Load garment templates")
    print("  3. Use measurements for sizing")
    print("  4. Drape garments on the rig")
    print("\n" + "="*70)

if __name__ == '__main__':
    main()


