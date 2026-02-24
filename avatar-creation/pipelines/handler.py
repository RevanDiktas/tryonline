"""
RunPod Serverless Handler for Avatar Pipeline
==============================================

This is the entry point for RunPod serverless GPU processing.
It receives a job request, processes it, and returns results.

Expected input:
{
    "photo_url": "https://...",  # URL of the body photo
    "height": 175,               # Height in cm
    "weight": 70,                # Weight in kg (optional)
    "gender": "male",            # male, female, neutral
    "user_id": "uuid"            # User ID for tracking
}

Output:
{
    "avatar_glb_base64": "...",   # Base64-encoded GLB file
    "measurements": {...},         # Standardized measurements
    "processing_time_seconds": 45.2
}
"""

import os
import sys
import time
import base64
import tempfile
from pathlib import Path

# Set up paths before any other imports
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

# ============================================================
# RUNPOD NETWORK VOLUME SETUP
# ============================================================
# RunPod mounts Network Volumes at /runpod-volume (fixed path)
# But our code expects /root/.cache/4DHumans
# Solution: Create symlink from /root/.cache/4DHumans to /runpod-volume/4DHumans
RUNPOD_VOLUME_PATH = Path("/runpod-volume")
EXPECTED_CACHE_DIR = Path("/root/.cache/4DHumans")
VOLUME_CACHE_DIR = RUNPOD_VOLUME_PATH / "4DHumans"

if RUNPOD_VOLUME_PATH.exists():
    print(f"[RunPod] Network Volume detected at {RUNPOD_VOLUME_PATH}")
    # Ensure the volume cache directory exists
    VOLUME_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create symlink if it doesn't exist
    if not EXPECTED_CACHE_DIR.exists():
        EXPECTED_CACHE_DIR.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(str(VOLUME_CACHE_DIR), str(EXPECTED_CACHE_DIR))
            print(f"[RunPod] ✓ Created symlink: {EXPECTED_CACHE_DIR} -> {VOLUME_CACHE_DIR}")
            print(f"[RunPod] Models will be cached in Network Volume (persistent across jobs)")
        except OSError as e:
            if e.errno != 17:  # File exists (already linked)
                print(f"[RunPod] ⚠️  Could not create symlink: {e}")
                print(f"[RunPod]   Will use local cache instead (not persistent)")
    else:
        # Check if it's already a symlink to the volume
        if EXPECTED_CACHE_DIR.is_symlink():
            try:
                target = EXPECTED_CACHE_DIR.readlink()
                if str(target) == str(VOLUME_CACHE_DIR):
                    print(f"[RunPod] ✓ Symlink already exists: {EXPECTED_CACHE_DIR} -> {VOLUME_CACHE_DIR}")
                else:
                    print(f"[RunPod] ⚠️  Symlink exists but points elsewhere: {EXPECTED_CACHE_DIR} -> {target}")
                    print(f"[RunPod]   Removing old symlink and creating new one...")
                    EXPECTED_CACHE_DIR.unlink()
                    os.symlink(str(VOLUME_CACHE_DIR), str(EXPECTED_CACHE_DIR))
                    print(f"[RunPod] ✓ Recreated symlink: {EXPECTED_CACHE_DIR} -> {VOLUME_CACHE_DIR}")
            except Exception as e:
                print(f"[RunPod] ⚠️  Error checking symlink: {e}")
        else:
            # Directory exists but is not a symlink - might have models from build
            # Defer expensive size check - just note that directory exists
            # Detailed check will happen when config is loaded
            build_checkpoint = EXPECTED_CACHE_DIR / "logs" / "train" / "multiruns" / "hmr2" / "0" / "checkpoints" / "epoch=35-step=1000000.ckpt"
            if build_checkpoint.exists():
                # Quick check only (no size check to avoid slow startup)
                print(f"[RunPod] ✓ Build-time models directory found in {EXPECTED_CACHE_DIR}")
                print(f"[RunPod]   Using build cache (size verification will happen on first use)")
            else:
                print(f"[RunPod] ⚠️  {EXPECTED_CACHE_DIR} exists but is not a symlink and checkpoint not found")
                print(f"[RunPod]   Will check for models on first job")
else:
    print(f"[RunPod] ⚠️  Network Volume not detected at {RUNPOD_VOLUME_PATH}")
    print(f"[RunPod]   Models will be cached locally (not persistent across jobs)")

# Add to Python path
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "4D-Humans-clean"))
# Try both possible locations for avatar-creation-measurements
sys.path.insert(0, str(PROJECT_ROOT / "avatar-creation-measurements"))  # /workspace/avatar-creation-measurements (Docker)
sys.path.insert(0, str(PROJECT_ROOT.parent / "avatar-creation-measurements"))  # Fallback location

# Try to import httpx, fallback to requests
try:
    import httpx
    USE_HTTPX = True
except ImportError:
    import requests
    USE_HTTPX = False

# Don't import pipeline yet - lazy load in handler function to speed up container startup
# This prevents heavy dependencies (PyTorch, models) from loading during container initialization


# Measurement name mapping: pipeline output -> API expected
# Supports variations and partial matches
MEASUREMENT_MAPPING = {
    "height": "height",
    "chest circumference": "chest",
    "waist circumference": "waist",
    "hip circumference": "hips",
    "hip circumference max height": "hips",  # Variation
    "inside leg height": "inseam",
    "shoulder breadth": "shoulder_width",
    "arm left length": "arm_length",
    "arm right length": "arm_length",  # Use either arm
    "arm length (shoulder to elbow)": "arm_length",  # Variation
    "arm length (spine to wrist)": "arm_length",  # Variation
    "neck circumference": "neck",
    "thigh left circumference": "thigh",
    "thigh right circumference": "thigh",  # Use either thigh
    "shoulder to crotch height": "torso_length",
    "crotch height": "crotch_height",
    "bicep right circumference": "bicep",
    "forearm right circumference": "forearm",
    "wrist right circumference": "wrist",
    "calf left circumference": "calf",
    "ankle left circumference": "ankle",
    "head circumference": "head",
}


def download_photo(photo_url: str, output_path: Path) -> bool:
    """Download photo from URL to local file."""
    try:
        # Handle file:// URLs for local testing
        if photo_url.startswith("file://"):
            local_path = photo_url[7:]  # Remove file://
            import shutil
            shutil.copy(local_path, output_path)
            return True
        
        # Download from HTTP/HTTPS
        if USE_HTTPX:
            with httpx.Client(timeout=60.0) as client:
                response = client.get(photo_url)
                response.raise_for_status()
                content = response.content
        else:
            response = requests.get(photo_url, timeout=60)
            response.raise_for_status()
            content = response.content
        
        with open(output_path, 'wb') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"[Handler] Failed to download photo: {e}")
        return False


def standardize_measurements(raw_measurements: dict) -> dict:
    """Convert pipeline measurement names to API-expected names."""
    standardized = {}
    
    for raw_name, value in raw_measurements.items():
        raw_name_lower = raw_name.lower()
        
        # Try exact match first
        mapped_name = MEASUREMENT_MAPPING.get(raw_name_lower)
        
        # If no exact match, try partial matching for variations
        if not mapped_name:
            for key, mapped in MEASUREMENT_MAPPING.items():
                if key in raw_name_lower or raw_name_lower in key:
                    mapped_name = mapped
                    break
        
        if mapped_name:
            # Only set if not already set (prefer first match)
            if mapped_name not in standardized:
                try:
                    standardized[mapped_name] = round(float(value), 1)
                except (ValueError, TypeError):
                    print(f"[Handler] Warning: Could not convert measurement '{raw_name}': {value}")
        else:
            # Log unmapped measurements for debugging
            print(f"[Handler] Unmapped measurement: '{raw_name}' = {value}")
    
    return standardized


def handler(event: dict) -> dict:
    """
    RunPod serverless handler function.
    
    Args:
        event: Job input with photo_url, height, weight, gender, user_id
        
    Returns:
        Dict with avatar_url (base64), measurements, and processing time
    """
    start_time = time.time()
    
    # Extract input
    job_input = event.get("input", {})
    photo_url = job_input.get("photo_url")
    height = job_input.get("height")
    weight = job_input.get("weight")
    gender = job_input.get("gender", "neutral")
    user_id = job_input.get("user_id", "unknown")
    
    # Validate required inputs
    if not photo_url:
        return {"error": "photo_url is required"}
    if not height:
        return {"error": "height is required"}
    
    print(f"[RunPod] Processing avatar for user: {user_id}")
    print(f"[RunPod] Height: {height}cm, Gender: {gender}")
    
    # Create temp directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Download photo
        photo_path = temp_dir / "input_photo.jpg"
        print(f"[RunPod] Downloading photo from: {photo_url[:50]}...")
        
        if not download_photo(photo_url, photo_path):
            return {"error": "Failed to download photo"}
        
        print(f"[RunPod] Photo downloaded: {photo_path.stat().st_size / 1024:.1f} KB")
        
        # Run the pipeline
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        print(f"[RunPod] Running avatar pipeline...")
        
        try:
            # Lazy import - only load heavy dependencies when actually processing a job
            from run_avatar_pipeline import run_pipeline
            
            results = run_pipeline(
                image_path=str(photo_path),
                height_cm=float(height),
                gender=gender,
                output_dir=str(output_dir)
            )
        except Exception as e:
            import traceback
            print(f"[RunPod] Pipeline error: {e}")
            traceback.print_exc()
            return {"error": f"Pipeline failed: {str(e)}"}
        
        if not results.get("success"):
            return {"error": results.get("error", "Pipeline failed")}
        
        # Collect all output files and encode as base64
        files_base64 = {}
        file_sizes = {}
        
        # Map of file keys to paths (from results or by common filenames)
        output_files = {}
        
        # Get paths from results
        if "outputs" in results:
            output_files.update({
                "avatar_glb": results["outputs"].get("avatar_glb"),
                "skin_texture": results["outputs"].get("skin_texture"),
                "original_mesh": results["outputs"].get("original_mesh"),
                "smpl_params": results["outputs"].get("smpl_params"),
                "tpose_mesh": results["outputs"].get("tpose_mesh"),
                "apose_mesh": results["outputs"].get("apose_mesh"),
                "measurements": results["outputs"].get("measurements"),
            })
        
        # Also check for additional files in output_dir by common names
        additional_files = {
            "face_crop": output_dir / "face_crop.png",
            "avatar_texture": output_dir / "avatar_texture.png",
            "skin_detection_mask": output_dir / "skin_detection_mask.png",
            # Also check for common GLB names
            "avatar_glb_alt": output_dir / "avatar_textured.glb",
        }
        
        # Encode all files
        for file_key, file_path in output_files.items():
            if file_path:
                file_path = Path(file_path)
                if file_path.exists():
                    try:
                        with open(file_path, "rb") as f:
                            file_data = f.read()
                        files_base64[file_key] = base64.b64encode(file_data).decode("utf-8")
                        file_sizes[file_key] = len(file_data)
                        print(f"[RunPod] Encoded {file_key}: {len(file_data) / 1024:.1f} KB")
                    except Exception as e:
                        print(f"[RunPod] Warning: Failed to encode {file_key}: {e}")
        
        for file_key, file_path in additional_files.items():
            if file_path.exists():
                try:
                    with open(file_path, "rb") as f:
                        file_data = f.read()
                    files_base64[file_key] = base64.b64encode(file_data).decode("utf-8")
                    file_sizes[file_key] = len(file_data)
                    print(f"[RunPod] Encoded {file_key}: {len(file_data) / 1024:.1f} KB")
                except Exception as e:
                    print(f"[RunPod] Warning: Failed to encode {file_key}: {e}")
        
        # Normalize GLB key (use avatar_glb as standard)
        if "avatar_glb_alt" in files_base64:
            if "avatar_glb" not in files_base64:
                files_base64["avatar_glb"] = files_base64.pop("avatar_glb_alt")
            else:
                del files_base64["avatar_glb_alt"]
        
        # Ensure GLB exists
        if "avatar_glb" not in files_base64:
            # Try to find any GLB file in output_dir
            glb_files = list(output_dir.glob("*.glb"))
            if glb_files:
                glb_path = glb_files[0]
                with open(glb_path, "rb") as f:
                    glb_data = f.read()
                files_base64["avatar_glb"] = base64.b64encode(glb_data).decode("utf-8")
                file_sizes["avatar_glb"] = len(glb_data)
            else:
                return {"error": "GLB file not generated"}
        
        # Standardize measurements
        raw_measurements = results.get("measurements", {})
        standardized_measurements = standardize_measurements(raw_measurements)
        
        # Ensure height is included
        standardized_measurements["height"] = float(height)
        
        print(f"[RunPod] Encoded {len(files_base64)} files")
        print(f"[RunPod] Total size: {sum(file_sizes.values()) / 1024 / 1024:.2f} MB")
        print(f"[RunPod] Measurements: {len(standardized_measurements)} values")
        
        # ============================================
        # VERIFICATION CHECKS
        # ============================================
        print(f"\n{'='*60}")
        print("[VERIFICATION] Post-Pipeline Checks")
        print(f"{'='*60}")
        
        verification_results = {}
        
        # 1. Verify models are downloaded and cached
        try:
            from hmr2.configs import CACHE_DIR_4DHUMANS
            cache_dir = Path(CACHE_DIR_4DHUMANS)
            checkpoint_path = cache_dir / "logs" / "train" / "multiruns" / "hmr2" / "0" / "checkpoints" / "epoch=35-step=1000000.ckpt"
            smpl_path = cache_dir / "data" / "smpl" / "SMPL_NEUTRAL.pkl"
            
            checkpoint_exists = checkpoint_path.exists()
            smpl_exists = smpl_path.exists()
            
            verification_results["models_cached"] = {
                "checkpoint": checkpoint_exists,
                "checkpoint_size_gb": checkpoint_path.stat().st_size / (1024**3) if checkpoint_exists else 0,
                "smpl_model": smpl_exists,
                "cache_dir": str(cache_dir)
            }
            
            if checkpoint_exists and smpl_exists:
                print(f"  ✓ Models cached successfully")
                print(f"    Checkpoint: {verification_results['models_cached']['checkpoint_size_gb']:.2f} GB")
                print(f"    SMPL model: ✓")
            else:
                print(f"  ⚠ Models not fully cached:")
                print(f"    Checkpoint: {'✓' if checkpoint_exists else '✗'}")
                print(f"    SMPL model: {'✓' if smpl_exists else '✗'}")
        except Exception as e:
            verification_results["models_cached"] = {"error": str(e)}
            print(f"  ✗ Model verification failed: {e}")
        
        # 2. Verify all expected files are generated (lazy import here too)
        try:
            from hmr2.configs import CACHE_DIR_4DHUMANS
            expected_files = ["avatar_glb", "measurements"]
            optional_files = ["skin_texture", "original_mesh", "smpl_params", "tpose_mesh", "apose_mesh", "face_crop"]
            
            files_generated = {
                "required": {f: f in files_base64 for f in expected_files},
                "optional": {f: f in files_base64 for f in optional_files}
            }
            
            verification_results["files_generated"] = files_generated
            
            all_required = all(files_generated["required"].values())
            if all_required:
                print(f"  ✓ All required files generated")
            else:
                missing = [f for f, exists in files_generated["required"].items() if not exists]
                print(f"  ✗ Missing required files: {missing}")
            
            optional_count = sum(files_generated["optional"].values())
            print(f"  Optional files: {optional_count}/{len(optional_files)}")
        except ImportError:
            print(f"  ⚠ Could not verify files (import error)")
            verification_results["files_generated"] = {"error": "import_failed"}
        
        # 3. Verify measurements are valid
        measurements_valid = len(standardized_measurements) > 0 and "height" in standardized_measurements
        verification_results["measurements_valid"] = measurements_valid
        
        if measurements_valid:
            print(f"  ✓ Measurements extracted: {len(standardized_measurements)} values")
            print(f"    Height: {standardized_measurements.get('height', 'N/A')} cm")
            print(f"    Chest: {standardized_measurements.get('chest', 'N/A')} cm")
            print(f"    Waist: {standardized_measurements.get('waist', 'N/A')} cm")
        else:
            print(f"  ✗ Measurements invalid or missing")
        
        # 4. Verify file sizes are reasonable
        glb_size_mb = file_sizes.get("avatar_glb", 0) / (1024 * 1024)
        verification_results["file_sizes"] = {
            "avatar_glb_mb": round(glb_size_mb, 2),
            "total_mb": round(sum(file_sizes.values()) / (1024 * 1024), 2)
        }
        
        if 0.1 < glb_size_mb < 50:  # Reasonable GLB size (100KB - 50MB)
            print(f"  ✓ GLB file size reasonable: {glb_size_mb:.2f} MB")
        else:
            print(f"  ⚠ GLB file size unusual: {glb_size_mb:.2f} MB")
        
        print(f"{'='*60}\n")
        
        processing_time = time.time() - start_time
        print(f"[RunPod] Complete in {processing_time:.1f}s")
        
        return {
            "files_base64": files_base64,  # All files as base64 dict
            "file_sizes": file_sizes,      # Original file sizes for reference
            "measurements": standardized_measurements,
            "processing_time_seconds": round(processing_time, 1),
            "user_id": user_id,
            "verification": verification_results,  # Add verification results
        }


# ============================================
# RunPod Serverless Integration
# ============================================

def runpod_handler(event):
    """
    Wrapper for RunPod serverless.
    RunPod expects a function that takes an event dict.
    """
    return handler(event)


# For RunPod serverless - register the handler
# Always try to start (RunPod imports the module)
# Optimize startup: don't import heavy dependencies here
try:
    import runpod
    print("[RunPod] Starting serverless handler...")
    print(f"[RunPod] Python path: {sys.path}")
    print(f"[RunPod] Working directory: {os.getcwd()}")
    print("[RunPod] ✓ Handler ready (heavy imports will load on first job)")
    
    # Start handler - simple call without extra parameters
    # (Some RunPod SDK versions don't support all parameters)
    # Lazy loading ensures container starts quickly
    runpod.serverless.start({"handler": runpod_handler})
except ImportError:
    # RunPod not installed - running locally
    print("[RunPod] RunPod not installed, skipping serverless registration")
    pass
except Exception as e:
    # Print any startup errors
    print(f"[RunPod] ERROR during handler startup: {e}")
    import traceback
    traceback.print_exc()
    # Don't raise - let RunPod handle it
    raise


# For local testing
if __name__ == "__main__":
    import json
    import argparse
    
    parser = argparse.ArgumentParser(description="Test avatar handler locally")
    parser.add_argument("--image", "-i", required=True, help="Path to test image")
    parser.add_argument("--height", "-H", type=float, default=175, help="Height in cm")
    parser.add_argument("--gender", "-g", default="male", help="Gender")
    args = parser.parse_args()
    
    # Test with a local file
    test_event = {
        "input": {
            "photo_url": f"file://{os.path.abspath(args.image)}",
            "height": args.height,
            "gender": args.gender,
            "user_id": "test-user-001"
        }
    }
    
    print("Testing handler locally...")
    print(f"  Image: {args.image}")
    print(f"  Height: {args.height}cm")
    print(f"  Gender: {args.gender}")
    print()
    
    result = handler(test_event)
    
    if "error" in result:
        print(f"\nError: {result['error']}")
    else:
        print(f"\nSuccess!")
        print(f"  GLB size: {len(result.get('avatar_glb_base64', '')) / 1024:.1f} KB (base64)")
        print(f"  Processing time: {result.get('processing_time_seconds')}s")
        print(f"\nMeasurements:")
        for name, value in sorted(result.get('measurements', {}).items()):
            print(f"    {name}: {value} cm")
        
        # Optionally save the GLB
        if result.get('avatar_glb_base64'):
            glb_path = Path("test_avatar_output.glb")
            with open(glb_path, 'wb') as f:
                f.write(base64.b64decode(result['avatar_glb_base64']))
            print(f"\nSaved GLB to: {glb_path}")
