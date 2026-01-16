#!/usr/bin/env python3
"""
TryOn MVP Avatar Pipeline
=========================

Complete pipeline for avatar creation from body photo:
1. 4D-Humans: Extract SMPL parameters from body image
2. T-Pose: Generate T-pose mesh for measurements
3. SMPL-Anthropometry: Extract body measurements
4. A-Pose: Generate A-pose mesh for visualization
5. Skin Extraction: Extract skin color from body image
6. Texture Mapping: Apply skin to avatar and export GLB

Usage:
    python run_avatar_pipeline.py --image body.jpg --height 175 --gender male --output ./output
"""

# ============================================================
# COMPATIBILITY FIXES FOR PYTHON 3.11+ AND NUMPY 2.0+
# Must be applied BEFORE any imports that use chumpy/smplx
# ============================================================
import inspect
if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = inspect.getfullargspec

import numpy as np
if not hasattr(np, 'bool'):
    np.bool = np.bool_
if not hasattr(np, 'int'):
    np.int = np.int_
if not hasattr(np, 'float'):
    np.float = np.float64
if not hasattr(np, 'complex'):
    np.complex = np.complex128
if not hasattr(np, 'object'):
    np.object = np.object_
if not hasattr(np, 'str'):
    np.str = np.str_
if not hasattr(np, 'unicode'):
    np.unicode = np.str_
# ============================================================

import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple

# Add parent directories to path for imports
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "4D-Humans-clean"))
sys.path.insert(0, str(PROJECT_ROOT.parent / "avatar-creation-measurements"))


def log_step(step_num: int, title: str, status: str = "start"):
    """Print formatted step header."""
    if status == "start":
        print(f"\n{'='*60}")
        print(f"STEP {step_num}: {title}")
        print(f"{'='*60}")
    elif status == "done":
        print(f"[OK] Step {step_num} complete: {title}")
    elif status == "error":
        print(f"[ERROR] Step {step_num} failed: {title}")


def step1_extract_body(
    image_path: Path,
    output_dir: Path,
    four_d_humans_dir: Path
) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Step 1: Run 4D-Humans to extract SMPL parameters from body image.
    
    Returns:
        Tuple of (mesh_path, params_path) or (None, None) on failure
    """
    log_step(1, "4D-Humans Body Extraction")
    
    # Create temp input folder (demo_yolo.py expects a folder)
    import tempfile
    import shutil
    
    temp_input = Path(tempfile.mkdtemp())
    shutil.copy(image_path, temp_input / image_path.name)
    
    print(f"  Input image: {image_path}")
    print(f"  Output dir: {output_dir}")
    
    # Run demo_yolo.py
    demo_script = four_d_humans_dir / "demo_yolo.py"
    if not demo_script.exists():
        print(f"  [ERROR] demo_yolo.py not found at {demo_script}")
        return None, None
    
    cmd = [
        sys.executable,
        str(demo_script),
        "--img_folder", str(temp_input),
        "--out_folder", str(output_dir),
        "--batch_size", "1"
    ]
    
    print(f"  Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(four_d_humans_dir),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            print(f"  [ERROR] 4D-Humans failed:")
            print(result.stderr)
            return None, None
            
    except subprocess.TimeoutExpired:
        print("  [ERROR] 4D-Humans timed out")
        return None, None
    finally:
        # Cleanup temp folder
        shutil.rmtree(temp_input, ignore_errors=True)
    
    # Find output files
    mesh_files = list(output_dir.glob("*person0.obj"))
    params_files = list(output_dir.glob("*person0_params.npz"))
    
    if not mesh_files or not params_files:
        # Try alternative naming
        mesh_files = list(output_dir.glob("*.obj"))
        params_files = list(output_dir.glob("*params.npz"))
    
    if not mesh_files or not params_files:
        print("  [ERROR] Output files not found")
        return None, None
    
    mesh_path = mesh_files[0]
    params_path = params_files[0]
    
    print(f"  [OK] Mesh: {mesh_path.name}")
    print(f"  [OK] Params: {params_path.name}")
    
    log_step(1, "4D-Humans Body Extraction", "done")
    return mesh_path, params_path


def step2_create_tpose(
    params_path: Path,
    output_path: Path,
    smpl_model_path: Path
) -> Optional[Path]:
    """
    Step 2: Generate T-pose mesh for measurements.
    
    T-pose = arms horizontal (90 degrees from vertical)
    """
    log_step(2, "T-Pose Generation (for measurements)")
    
    try:
        import torch
        import trimesh
        import smplx
    except ImportError as e:
        print(f"  [ERROR] Missing dependency: {e}")
        return None
    
    print(f"  Loading params: {params_path}")
    params = np.load(params_path, allow_pickle=True)
    
    # Extract betas
    if 'betas' in params:
        betas = params['betas']
    elif 'shape' in params:
        betas = params['shape']
    else:
        print("  [ERROR] No betas/shape found in params")
        return None
    
    # Ensure correct shape
    betas = betas.flatten()
    if len(betas) > 10:
        betas = betas[:10]
    elif len(betas) < 10:
        betas = np.pad(betas, (0, 10 - len(betas)), 'constant')
    
    print(f"  Betas shape: {betas.shape}")
    
    # Create SMPL model
    print(f"  Loading SMPL model from: {smpl_model_path}")
    
    smpl_model = smplx.create(
        str(smpl_model_path),
        model_type='smpl',
        gender='neutral',
        num_betas=10
    )
    
    # T-pose = all zeros (arms horizontal in SMPL)
    betas_tensor = torch.from_numpy(betas).float().unsqueeze(0)
    body_pose = torch.zeros(1, 69)  # 23 joints * 3
    global_orient = torch.zeros(1, 3)
    
    print("  Generating T-pose mesh (arms horizontal)...")
    
    with torch.no_grad():
        output = smpl_model(
            betas=betas_tensor,
            body_pose=body_pose,
            global_orient=global_orient
        )
    
    vertices = output.vertices[0].cpu().numpy()
    faces = smpl_model.faces
    
    # Save mesh
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.export(str(output_path))
    
    print(f"  [OK] T-pose mesh saved: {output_path.name}")
    print(f"       Vertices: {len(vertices)}, Faces: {len(faces)}")
    
    log_step(2, "T-Pose Generation", "done")
    return output_path


def step3_extract_measurements(
    params_path: Path,
    height_cm: float,
    gender: str,
    measurements_dir: Path
) -> Optional[Dict[str, float]]:
    """
    Step 3: Extract body measurements using SMPL-Anthropometry.
    
    Uses the body branch measurement extraction code.
    """
    log_step(3, "SMPL-Anthropometry Measurement Extraction")
    
    try:
        import torch
        
        # Add measurements module to path
        sys.path.insert(0, str(measurements_dir))
        from measure import MeasureBody
        from measurement_definitions import STANDARD_LABELS
    except ImportError as e:
        print(f"  [ERROR] Missing dependency: {e}")
        print(f"  Make sure avatar-creation-measurements is available")
        return None
    
    print(f"  Height: {height_cm} cm")
    print(f"  Gender: {gender}")
    
    # Load betas from params
    params = np.load(params_path, allow_pickle=True)
    if 'betas' in params:
        betas = params['betas']
    elif 'shape' in params:
        betas = params['shape']
    else:
        print("  [ERROR] No betas found in params")
        return None
    
    betas = betas.flatten()[:10]
    betas_tensor = torch.from_numpy(betas).float().unsqueeze(0)
    
    print("  Creating SMPL measurer...")
    measurer = MeasureBody("smpl")
    
    # Set body model with betas
    gender_upper = gender.upper() if gender.lower() in ['male', 'female'] else 'NEUTRAL'
    measurer.from_body_model(gender=gender_upper, shape=betas_tensor)
    
    # Get all possible measurements
    measurement_names = measurer.all_possible_measurements
    print(f"  Measuring {len(measurement_names)} body dimensions...")
    
    measurer.measure(measurement_names)
    
    # Normalize to actual height
    measurer.height_normalize_measurements(height_cm)
    
    # Get normalized measurements
    measurements = measurer.height_normalized_measurements
    
    print(f"\n  Measurements (height-normalized to {height_cm}cm):")
    for name, value in sorted(measurements.items()):
        print(f"    {name}: {value:.1f} cm")
    
    log_step(3, "Measurement Extraction", "done")
    return measurements


def step4_create_apose(
    params_path: Path,
    output_path: Path,
    smpl_model_path: Path,
    arm_angle: float = 45.0
) -> Optional[Path]:
    """
    Step 4: Generate A-pose mesh for visualization.
    
    A-pose = arms at 45 degrees from vertical
    """
    log_step(4, f"A-Pose Generation (arms at {arm_angle} deg)")
    
    try:
        import torch
        import trimesh
        import smplx
    except ImportError as e:
        print(f"  [ERROR] Missing dependency: {e}")
        return None
    
    print(f"  Loading params: {params_path}")
    params = np.load(params_path, allow_pickle=True)
    
    # Extract betas
    if 'betas' in params:
        betas = params['betas']
    elif 'shape' in params:
        betas = params['shape']
    else:
        print("  [ERROR] No betas/shape found in params")
        return None
    
    betas = betas.flatten()[:10]
    if len(betas) < 10:
        betas = np.pad(betas, (0, 10 - len(betas)), 'constant')
    
    # Create SMPL model
    smpl_model = smplx.create(
        str(smpl_model_path),
        model_type='smpl',
        gender='neutral',
        num_betas=10
    )
    
    betas_tensor = torch.from_numpy(betas).float().unsqueeze(0)
    global_orient = torch.zeros(1, 3)
    body_pose = torch.zeros(1, 69)
    
    # Set arm angle (45 degrees from vertical = 45 degrees down from horizontal)
    # In SMPL: 0 = T-pose (horizontal), we rotate down
    arm_angle_rad = -np.deg2rad(90 - arm_angle)
    
    # Left shoulder (joint 16, body_pose index 15)
    body_pose[0, 15*3 + 2] = arm_angle_rad
    # Right shoulder (joint 17, body_pose index 16)
    body_pose[0, 16*3 + 2] = -arm_angle_rad
    
    print(f"  Generating A-pose mesh (arms at {arm_angle} deg from vertical)...")
    
    with torch.no_grad():
        output = smpl_model(
            betas=betas_tensor,
            body_pose=body_pose,
            global_orient=global_orient
        )
    
    vertices = output.vertices[0].cpu().numpy()
    faces = smpl_model.faces
    
    # Save mesh
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.export(str(output_path))
    
    print(f"  [OK] A-pose mesh saved: {output_path.name}")
    
    log_step(4, "A-Pose Generation", "done")
    return output_path


def step5_extract_skin(
    body_image_path: Path,
    output_dir: Path
) -> Optional[Tuple[Path, np.ndarray]]:
    """
    Step 5: Extract skin color from BODY image (not face).
    """
    log_step(5, "Skin Color Extraction from Body Image")
    
    try:
        import cv2
        from PIL import Image
    except ImportError as e:
        print(f"  [ERROR] Missing dependency: {e}")
        return None
    
    print(f"  Loading body image: {body_image_path}")
    
    image = cv2.imread(str(body_image_path))
    if image is None:
        print(f"  [ERROR] Could not load image")
        return None
    
    print(f"  Image size: {image.shape[1]}x{image.shape[0]}")
    
    # Convert to HSV for skin detection
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Skin detection ranges (works for various skin tones)
    lower_skin1 = np.array([0, 20, 70], dtype=np.uint8)
    upper_skin1 = np.array([20, 255, 255], dtype=np.uint8)
    lower_skin2 = np.array([170, 20, 70], dtype=np.uint8)
    upper_skin2 = np.array([180, 255, 255], dtype=np.uint8)
    
    mask1 = cv2.inRange(hsv, lower_skin1, upper_skin1)
    mask2 = cv2.inRange(hsv, lower_skin2, upper_skin2)
    skin_mask = cv2.bitwise_or(mask1, mask2)
    
    # For body images: use more of the image (not just center like face)
    # Focus on upper body area where skin is likely visible
    h, w = image.shape[:2]
    
    # Create region of interest mask (upper 2/3 of image, center 60%)
    roi_mask = np.zeros((h, w), dtype=np.uint8)
    roi_y_start = int(h * 0.1)
    roi_y_end = int(h * 0.7)
    roi_x_start = int(w * 0.2)
    roi_x_end = int(w * 0.8)
    roi_mask[roi_y_start:roi_y_end, roi_x_start:roi_x_end] = 255
    
    skin_mask = cv2.bitwise_and(skin_mask, roi_mask)
    
    # Get skin pixels
    skin_pixels = image[skin_mask > 0]
    
    if len(skin_pixels) < 100:
        print("  [WARNING] Few skin pixels detected, using image center")
        center_region = image[h//3:2*h//3, w//3:2*w//3]
        skin_color = np.median(center_region.reshape(-1, 3), axis=0)
    else:
        skin_color = np.median(skin_pixels, axis=0)
    
    skin_color = skin_color.astype(np.uint8)
    
    print(f"  Skin pixels detected: {np.sum(skin_mask > 0)}")
    print(f"  Skin color (BGR): {skin_color}")
    print(f"  Skin color (RGB): {skin_color[::-1]}")
    
    # Save skin texture PNG (solid color)
    texture_path = output_dir / "skin_texture.png"
    skin_color_rgb = skin_color[::-1]  # BGR to RGB
    texture_img = np.full((512, 512, 3), skin_color_rgb, dtype=np.uint8)
    Image.fromarray(texture_img, 'RGB').save(str(texture_path))
    
    print(f"  [OK] Skin texture saved: {texture_path.name}")
    
    # Save mask visualization
    mask_vis_path = output_dir / "skin_detection_mask.png"
    vis = image.copy()
    vis[skin_mask > 0] = [0, 255, 0]  # Green overlay
    cv2.imwrite(str(mask_vis_path), vis)
    print(f"  [OK] Mask visualization: {mask_vis_path.name}")
    
    log_step(5, "Skin Color Extraction", "done")
    return texture_path, skin_color


def step6_create_textured_glb(
    mesh_path: Path,
    skin_color: np.ndarray,
    output_path: Path,
    texture_path: Optional[Path] = None
) -> Optional[Path]:
    """
    Step 6: Apply skin texture to mesh using UV mapping and export as GLB.
    
    Uses proper UV texture mapping instead of vertex colors for better
    rendering in web viewers (Three.js, etc.)
    """
    log_step(6, "UV Texture Mapping & GLB Export")
    
    try:
        import trimesh
        from PIL import Image
    except ImportError as e:
        print(f"  [ERROR] Missing dependency: {e}")
        return None
    
    print(f"  Loading mesh: {mesh_path}")
    
    mesh = trimesh.load(str(mesh_path), process=False)
    if not isinstance(mesh, trimesh.Trimesh):
        mesh = list(mesh.geometry.values())[0]
    
    # Convert BGR to RGB
    skin_color_rgb = skin_color[::-1].astype(np.uint8)
    
    print(f"  Skin color (RGB): {skin_color_rgb}")
    print(f"  Vertices: {len(mesh.vertices)}, Faces: {len(mesh.faces)}")
    
    # Create UV coordinates for the mesh
    # Simple cylindrical UV projection for SMPL body
    vertices = mesh.vertices
    
    # Normalize vertices for UV mapping
    v_min = vertices.min(axis=0)
    v_max = vertices.max(axis=0)
    v_range = v_max - v_min
    
    # Cylindrical UV projection: 
    # U = atan2(x, z) normalized to [0,1]
    # V = y normalized to [0,1]
    x = vertices[:, 0]
    y = vertices[:, 1]
    z = vertices[:, 2]
    
    # Calculate U coordinate from angle around Y axis
    u = (np.arctan2(x, z) / (2 * np.pi)) + 0.5
    
    # Calculate V coordinate from height
    v = (y - v_min[1]) / v_range[1]
    
    uv = np.column_stack([u, v])
    
    print(f"  Generated UV coordinates: shape {uv.shape}")
    
    # Create skin texture image (512x512 solid color)
    texture_size = 512
    texture_img = Image.new('RGB', (texture_size, texture_size), 
                            tuple(skin_color_rgb.tolist()))
    
    # Save texture to file
    if texture_path is None:
        texture_path = output_path.parent / "avatar_texture.png"
    texture_img.save(str(texture_path))
    print(f"  Saved texture: {texture_path.name}")
    
    # Create a textured visual for the mesh with actual texture image
    from trimesh.visual.material import PBRMaterial
    from trimesh.visual import TextureVisuals
    
    # Load texture as numpy array for PBR material
    texture_array = np.array(texture_img)
    
    # Create PBR material with the actual texture image
    material = PBRMaterial(
        baseColorTexture=Image.fromarray(texture_array),
        baseColorFactor=[1.0, 1.0, 1.0, 1.0],  # No tint, use texture as-is
        metallicFactor=0.0,
        roughnessFactor=0.7
    )
    
    # Apply texture visual with UV coordinates and material
    mesh.visual = TextureVisuals(uv=uv, material=material)
    
    print(f"  Applied texture: {texture_path.name} with PBR material")
    
    # Export as GLB (binary glTF)
    mesh.export(str(output_path), file_type='glb')
    
    file_size = output_path.stat().st_size / 1024
    print(f"  [OK] GLB exported: {output_path.name} ({file_size:.1f} KB)")
    
    # Verify the export contains proper data
    try:
        test_load = trimesh.load(str(output_path))
        if hasattr(test_load, 'geometry'):
            for name, geom in test_load.geometry.items():
                print(f"  Verified geometry '{name}': {len(geom.vertices)} vertices")
        else:
            print(f"  Verified: {len(test_load.vertices)} vertices")
    except Exception as e:
        print(f"  [WARNING] Verification failed: {e}")
    
    log_step(6, "UV Texture Mapping & GLB Export", "done")
    return output_path


def save_measurements_json(
    measurements: Dict[str, float],
    output_path: Path,
    height_cm: float,
    gender: str
):
    """Save measurements to JSON file."""
    output_data = {
        "input": {
            "height_cm": height_cm,
            "gender": gender
        },
        "measurements_cm": {
            name: round(float(value), 1)  # Convert numpy float32 to Python float
            for name, value in sorted(measurements.items())
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"  [OK] Measurements saved: {output_path.name}")


def run_pipeline(
    image_path: str,
    height_cm: float,
    gender: str,
    output_dir: str
) -> Dict:
    """
    Run the complete avatar pipeline.
    
    Args:
        image_path: Path to body image
        height_cm: User's height in centimeters
        gender: 'male', 'female', or 'neutral'
        output_dir: Directory for output files
        
    Returns:
        Dict with paths to output files and measurements
    """
    print("\n" + "="*60)
    print("TRYON MVP AVATAR PIPELINE")
    print("="*60)
    
    # Setup paths
    image_path = Path(image_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    four_d_humans_dir = PROJECT_ROOT / "4D-Humans-clean"
    smpl_model_path = four_d_humans_dir / "data"
    measurements_dir = PROJECT_ROOT.parent / "avatar-creation-measurements"
    
    print(f"\nInput:")
    print(f"  Image: {image_path}")
    print(f"  Height: {height_cm} cm")
    print(f"  Gender: {gender}")
    print(f"  Output: {output_dir}")
    
    results = {
        "success": False,
        "error": None,
        "outputs": {}
    }
    
    try:
        # Step 1: 4D-Humans body extraction
        mesh_path, params_path = step1_extract_body(
            image_path, output_dir, four_d_humans_dir
        )
        if not params_path:
            results["error"] = "Step 1 failed: Body extraction"
            return results
        
        results["outputs"]["original_mesh"] = str(mesh_path)
        results["outputs"]["smpl_params"] = str(params_path)
        
        # Step 2: T-pose for measurements
        tpose_path = output_dir / "body_tpose.obj"
        tpose_result = step2_create_tpose(params_path, tpose_path, smpl_model_path)
        if not tpose_result:
            results["error"] = "Step 2 failed: T-pose generation"
            return results
        
        results["outputs"]["tpose_mesh"] = str(tpose_path)
        
        # Step 3: Extract measurements
        measurements = step3_extract_measurements(
            params_path, height_cm, gender, measurements_dir
        )
        if not measurements:
            print("  [WARNING] Measurement extraction failed, using defaults")
            measurements = {
                "height": height_cm,
                "chest circumference": height_cm * 0.53,
                "waist circumference": height_cm * 0.43,
                "hip circumference": height_cm * 0.50,
                "inside leg height": height_cm * 0.45,
            }
        
        measurements_path = output_dir / "measurements.json"
        save_measurements_json(measurements, measurements_path, height_cm, gender)
        results["outputs"]["measurements"] = str(measurements_path)
        results["measurements"] = measurements
        
        # Step 4: A-pose for visualization
        apose_path = output_dir / "body_apose.obj"
        apose_result = step4_create_apose(params_path, apose_path, smpl_model_path)
        if not apose_result:
            results["error"] = "Step 4 failed: A-pose generation"
            return results
        
        results["outputs"]["apose_mesh"] = str(apose_path)
        
        # Step 5: Extract skin from body image
        skin_result = step5_extract_skin(image_path, output_dir)
        if not skin_result:
            print("  [WARNING] Skin extraction failed, using default color")
            skin_color = np.array([180, 140, 120], dtype=np.uint8)  # Default skin tone
        else:
            _, skin_color = skin_result
        
        results["outputs"]["skin_texture"] = str(output_dir / "skin_texture.png")
        
        # Step 6: Create textured GLB
        glb_path = output_dir / "avatar_textured.glb"
        glb_result = step6_create_textured_glb(apose_path, skin_color, glb_path)
        if not glb_result:
            results["error"] = "Step 6 failed: GLB export"
            return results
        
        results["outputs"]["avatar_glb"] = str(glb_path)
        
        # Success!
        results["success"] = True
        
        print("\n" + "="*60)
        print("PIPELINE COMPLETE!")
        print("="*60)
        print(f"\nOutput files in: {output_dir}")
        for name, path in results["outputs"].items():
            print(f"  {name}: {Path(path).name}")
        
        return results
        
    except Exception as e:
        import traceback
        results["error"] = f"Pipeline error: {str(e)}"
        print(f"\n[ERROR] Pipeline failed: {e}")
        traceback.print_exc()
        return results


def main():
    parser = argparse.ArgumentParser(
        description='TryOn MVP Avatar Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_avatar_pipeline.py --image body.jpg --height 175 --gender male
    python run_avatar_pipeline.py --image photo.png --height 165 --gender female --output ./my_avatar
        """
    )
    
    parser.add_argument(
        '--image', '-i',
        type=str,
        required=True,
        help='Path to body image (full body photo)'
    )
    parser.add_argument(
        '--height', '-H',
        type=float,
        required=True,
        help='Height in centimeters'
    )
    parser.add_argument(
        '--gender', '-g',
        type=str,
        choices=['male', 'female', 'neutral'],
        default='neutral',
        help='Gender for body model (default: neutral)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='./output/avatar',
        help='Output directory (default: ./output/avatar)'
    )
    
    args = parser.parse_args()
    
    # Validate image exists
    if not Path(args.image).exists():
        print(f"Error: Image not found: {args.image}")
        sys.exit(1)
    
    # Validate height
    if args.height < 100 or args.height > 250:
        print(f"Warning: Unusual height value: {args.height} cm")
    
    # Run pipeline
    results = run_pipeline(
        image_path=args.image,
        height_cm=args.height,
        gender=args.gender,
        output_dir=args.output
    )
    
    if not results["success"]:
        print(f"\nPipeline failed: {results.get('error', 'Unknown error')}")
        sys.exit(1)
    
    # Output results as JSON for programmatic use
    # Convert numpy types to Python types for JSON serialization
    def convert_numpy(obj):
        if isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert_numpy(v) for v in obj]
        elif isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    print(f"\n--- RESULTS JSON ---")
    print(json.dumps(convert_numpy(results), indent=2))


if __name__ == "__main__":
    main()
