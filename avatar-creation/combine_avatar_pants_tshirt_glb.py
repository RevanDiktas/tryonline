#!/usr/bin/env python3
"""
Combine Avatar + Pants + T-Shirt and export as GLB
Loads existing files and combines them for all 5 sizes (XS, S, M, L, XL)
Optimized: Loads avatar and pants once, processes sizes in parallel
"""

import os
import sys
import time
import argparse
import trimesh
from concurrent.futures import ProcessPoolExecutor, as_completed

# Default paths
DEFAULT_AVATAR = "output/female_avatar/body_woman_apose_textured.obj"
DEFAULT_PANTS_DIR = "output/pants_both_genders/female"
DEFAULT_TSHIRT_DIR = "output/heatmaps/v1tweaking"
DEFAULT_OUTPUT_DIR = "output/avatar_pants_tshirt_glb"

SIZES = ['XS', 'S', 'M', 'L', 'XL']

def find_files(avatar_path, pants_dir, tshirt_dir, size):
    """Find the files for a given size"""
    size_lower = size.lower()
    
    # Avatar (same for all sizes)
    avatar_file = avatar_path
    if not os.path.exists(avatar_file):
        # Try alternative paths
        alternatives = [
            "output/your_body/body_person0_neutral_textured.obj",
            "output/female_avatar/body_woman_apose.obj",
        ]
        for alt in alternatives:
            if os.path.exists(alt):
                avatar_file = alt
                break
    
    # Pants - try size-specific first, then fallback to single file
    pants_file = None
    pants_patterns = [
        os.path.join(pants_dir, f"pants_{size_lower}.ply"),
        os.path.join(pants_dir, f"pants_female_{size_lower}.ply"),
        os.path.join(pants_dir, f"pants_{size_lower}_female.ply"),
        os.path.join(pants_dir, "pants_female.ply"),  # Fallback: same pants for all
        os.path.join(pants_dir, "pants.ply"),
    ]
    for pattern in pants_patterns:
        if os.path.exists(pattern):
            pants_file = pattern
            break
    
    # T-shirt - try CLO 3D exports first, then heatmap t-shirts
    tshirt_file = None
    tshirt_patterns = [
        # CLO 3D exported files (new naming)
        os.path.join(tshirt_dir, f"tshirt_{size_lower}.obj"),
        os.path.join(tshirt_dir, f"tshirt_{size_lower}.ply"),
        os.path.join(tshirt_dir, f"tshirt_{size_lower}_clo3d.obj"),
        os.path.join(tshirt_dir, f"tshirt_{size_lower}_clo3d.ply"),
        # Original heatmap t-shirts (fallback)
        os.path.join(tshirt_dir, f"playboy_tshirt_{size_lower}_perfect_stress_heatmap_v1.ply"),
        os.path.join(tshirt_dir, f"playboy_tshirt_{size_lower}_perfect.ply"),
        os.path.join(tshirt_dir, f"tshirt_{size_lower}.ply"),
    ]
    for pattern in tshirt_patterns:
        if os.path.exists(pattern):
            tshirt_file = pattern
            break
    
    return avatar_file, pants_file, tshirt_file

def combine_and_export_optimized(avatar_mesh, pants_mesh, tshirt_path, output_path, size):
    """Combine pre-loaded avatar + pants + t-shirt and export as GLB"""
    print(f"📦 Processing {size}...")
    
    # Check t-shirt file exists
    if not os.path.exists(tshirt_path):
        print(f"   ❌ T-shirt not found: {tshirt_path}")
        return False
    
    # Load only t-shirt (avatar and pants already loaded)
    try:
        tshirt = trimesh.load(tshirt_path)
    except Exception as e:
        print(f"   ❌ Error loading t-shirt: {e}")
        return False
    
    # Combine all meshes
    try:
        combined = trimesh.util.concatenate([avatar_mesh, pants_mesh, tshirt])
    except Exception as e:
        print(f"   ❌ Error combining meshes: {e}")
        return False
    
    # Export as GLB
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        combined.export(output_path, file_type='glb')
        return True
    except Exception as e:
        print(f"   ❌ Error exporting GLB: {e}")
        return False

def process_single_size_with_paths(size, avatar_path, pants_path, tshirt_path, output_path):
    """Process a single size - loads meshes in worker process for parallel processing"""
    size_start = time.time()
    
    # Load meshes in this process
    try:
        avatar_mesh = trimesh.load(avatar_path)
        pants_mesh = trimesh.load(pants_path)
        tshirt_mesh = trimesh.load(tshirt_path)
    except Exception as e:
        return {
            'size': size,
            'success': False,
            'time': time.time() - size_start,
            'output': None,
            'file_size': 0,
            'error': str(e)
        }
    
    # Combine and export
    try:
        combined = trimesh.util.concatenate([avatar_mesh, pants_mesh, tshirt_mesh])
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        combined.export(output_path, file_type='glb')
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        return {
            'size': size,
            'success': True,
            'time': time.time() - size_start,
            'output': output_path,
            'file_size': file_size
        }
    except Exception as e:
        return {
            'size': size,
            'success': False,
            'time': time.time() - size_start,
            'output': None,
            'file_size': 0,
            'error': str(e)
        }

def main():
    parser = argparse.ArgumentParser(description="Combine Avatar + Pants + T-Shirt and export as GLB")
    parser.add_argument('--avatar', type=str, default=DEFAULT_AVATAR,
                        help='Path to textured avatar (OBJ or PLY)')
    parser.add_argument('--pants-dir', type=str, default=DEFAULT_PANTS_DIR,
                        help='Directory containing pants files')
    parser.add_argument('--tshirt-dir', type=str, default=DEFAULT_TSHIRT_DIR,
                        help='Directory containing t-shirt files')
    parser.add_argument('--output-dir', type=str, default=DEFAULT_OUTPUT_DIR,
                        help='Output directory for GLB files')
    parser.add_argument('--sizes', nargs='+', default=SIZES,
                        help='Sizes to process (default: XS S M L XL)')
    
    parser.add_argument('--parallel', action='store_true', default=False,
                        help='Process sizes in parallel (slower due to overhead, but useful for many sizes)')
    parser.add_argument('--no-parallel', dest='parallel', action='store_false',
                        help='Process sizes sequentially (default: faster)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("AVATAR + PANTS + T-SHIRT → GLB EXPORT (OPTIMIZED)")
    print("="*60)
    print(f"Avatar: {args.avatar}")
    print(f"Pants dir: {args.pants_dir}")
    print(f"T-shirt dir: {args.tshirt_dir}")
    print(f"Output dir: {args.output_dir}")
    print(f"Sizes: {', '.join(args.sizes)}")
    print(f"Parallel: {args.parallel}")
    print("="*60)
    
    # Load avatar and pants ONCE (they're the same for all sizes)
    print("\n📥 Loading avatar and pants (once for all sizes)...")
    load_start = time.time()
    
    # Find avatar file
    avatar_file = args.avatar
    if not os.path.exists(avatar_file):
        alternatives = [
            "output/your_body/body_person0_neutral_textured.obj",
            "output/female_avatar/body_woman_apose.obj",
        ]
        for alt in alternatives:
            if os.path.exists(alt):
                avatar_file = alt
                break
    
    if not os.path.exists(avatar_file):
        print(f"❌ Avatar not found: {args.avatar}")
        return 1
    
    # Find pants file
    pants_file = None
    pants_patterns = [
        os.path.join(args.pants_dir, "pants_female.ply"),
        os.path.join(args.pants_dir, "pants.ply"),
    ]
    for pattern in pants_patterns:
        if os.path.exists(pattern):
            pants_file = pattern
            break
    
    if not pants_file or not os.path.exists(pants_file):
        print(f"❌ Pants not found in: {args.pants_dir}")
        return 1
    
    # Load meshes
    try:
        avatar_mesh = trimesh.load(avatar_file)
        print(f"   ✓ Avatar loaded: {len(avatar_mesh.vertices)} vertices")
    except Exception as e:
        print(f"   ❌ Error loading avatar: {e}")
        return 1
    
    try:
        pants_mesh = trimesh.load(pants_file)
        print(f"   ✓ Pants loaded: {len(pants_mesh.vertices)} vertices")
    except Exception as e:
        print(f"   ❌ Error loading pants: {e}")
        return 1
    
    load_time = time.time() - load_start
    print(f"   ⏱️  Load time: {load_time:.2f}s")
    
    # Prepare tasks for all sizes
    print(f"\n🔍 Finding t-shirt files for {len(args.sizes)} sizes...")
    tasks = []
    for size in args.sizes:
        size_lower = size.lower()
        tshirt_patterns = [
            os.path.join(args.tshirt_dir, f"playboy_tshirt_{size_lower}_perfect_stress_heatmap_v1.ply"),
            os.path.join(args.tshirt_dir, f"playboy_tshirt_{size_lower}_perfect.ply"),
            os.path.join(args.tshirt_dir, f"tshirt_{size_lower}.ply"),
        ]
        
        tshirt_file = None
        for pattern in tshirt_patterns:
            if os.path.exists(pattern):
                tshirt_file = pattern
                break
        
        if not tshirt_file:
            print(f"   ❌ T-shirt not found for size {size}")
            continue
        
        output_path = os.path.join(args.output_dir, f"avatar_pants_tshirt_{size_lower}.glb")
        tasks.append((size, avatar_mesh, pants_mesh, tshirt_file, output_path))
        print(f"   ✓ {size}: {os.path.basename(tshirt_file)}")
    
    if not tasks:
        print("❌ No valid tasks to process")
        return 1
    
    # Process sizes
    print(f"\n🚀 Processing {len(tasks)} sizes...")
    start_time = time.time()
    results = {}
    
    if args.parallel and len(tasks) > 1:
        # Parallel processing
        with ProcessPoolExecutor(max_workers=min(len(tasks), 5)) as executor:
            # Note: trimesh objects can't be pickled, so we need to reload in each process
            # Instead, pass file paths and reload in worker
            future_to_size = {}
            for size, _, _, tshirt_file, output_path in tasks:
                # Pass file paths instead of mesh objects for parallel processing
                future = executor.submit(process_single_size_with_paths, 
                                       size, avatar_file, pants_file, tshirt_file, output_path)
                future_to_size[future] = size
            
            for future in as_completed(future_to_size):
                result = future.result()
                results[result['size']] = result
                if result['success']:
                    print(f"   ✅ {result['size']}: {result['time']:.2f}s ({result['file_size']:.2f} MB)")
                else:
                    print(f"   ❌ {result['size']}: Failed")
    else:
        # Sequential processing (but still optimized - avatar/pants loaded once)
        for size, avatar_mesh, pants_mesh, tshirt_file, output_path in tasks:
            size_start = time.time()
            success = combine_and_export_optimized(avatar_mesh, pants_mesh, tshirt_file, output_path, size)
            size_time = time.time() - size_start
            file_size = os.path.getsize(output_path) / (1024 * 1024) if success and os.path.exists(output_path) else 0
            results[size] = {
                'success': success,
                'time': size_time,
                'output': output_path if success else None,
                'file_size': file_size
            }
            if success:
                print(f"   ✅ {size}: {size_time:.2f}s ({file_size:.2f} MB)")
            else:
                print(f"   ❌ {size}: Failed")
    
    # Summary
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    successful = [s for s, r in results.items() if r.get('success', False)]
    failed = [s for s, r in results.items() if not r.get('success', False)]
    
    print(f"✅ Successful: {len(successful)}/{len(args.sizes)}")
    if successful:
        for size in successful:
            time_taken = results[size].get('time', 0)
            file_size = results[size].get('file_size', 0)
            print(f"   {size}: {time_taken:.2f}s ({file_size:.2f} MB) → {os.path.basename(results[size]['output'])}")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(args.sizes)}")
        for size in failed:
            print(f"   {size}")
    
    print(f"\n⏱️  Total time: {total_time:.2f} seconds")
    print(f"📁 Output directory: {args.output_dir}")
    print("="*60)
    
    return 0 if len(successful) == len(args.sizes) else 1

if __name__ == '__main__':
    sys.exit(main())

