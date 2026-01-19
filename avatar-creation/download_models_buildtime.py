#!/usr/bin/env python3
"""
Build-time model download script for Docker builds.
Downloads models during Docker build to avoid runtime quota issues.

This script:
1. Downloads checkpoint and SMPL models from Google Drive
2. Places them in the expected cache directory structure
3. Handles quota errors gracefully (warns but doesn't fail build)
4. Validates file sizes to ensure correct downloads
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Import at top level for Dropbox URLs
import urllib.request as urlrequest

# File IDs from Google Drive (fallback)
GOOGLE_DRIVE_CHECKPOINT_ID = "1ISfMrpiiwoSzLoQXsXsX5FUcOxZY5Bzu"
GOOGLE_DRIVE_SMPL_NEUTRAL_ID = "1A2qaP3xWZRuBOPaNx0-tovBBhtftxuSv"
GOOGLE_DRIVE_SMPL_MALE_ID = "1MYc-Qduvki8xcvEGQSwmCiEhg3Ehs0o5"
GOOGLE_DRIVE_SMPL_FEMALE_ID = "1Xr4UaC8job6f0UPMnwwzWRi3pxf8znoE"
GOOGLE_DRIVE_MEAN_PARAMS_ID = "1cqbspPE9LM2ysB_YvBcRZR3JGVb3ve_I"
GOOGLE_DRIVE_JOINT_REGRESSOR_ID = "1hoGaaioCh9bo3jNY84N3A5VB51DRqnQE"

# Dropbox URLs (set via environment variables - PREFERRED if available)
# Format: https://www.dropbox.com/s/XXXXX/filename?dl=1
# OR: https://dl.dropboxusercontent.com/s/XXXXX/filename
DROPBOX_CHECKPOINT_URL = os.environ.get("DROPBOX_CHECKPOINT_URL")
DROPBOX_SMPL_NEUTRAL_URL = os.environ.get("DROPBOX_SMPL_NEUTRAL_URL")
DROPBOX_SMPL_MALE_URL = os.environ.get("DROPBOX_SMPL_MALE_URL")
DROPBOX_SMPL_FEMALE_URL = os.environ.get("DROPBOX_SMPL_FEMALE_URL")
DROPBOX_MEAN_PARAMS_URL = os.environ.get("DROPBOX_MEAN_PARAMS_URL")
DROPBOX_JOINT_REGRESSOR_URL = os.environ.get("DROPBOX_JOINT_REGRESSOR_URL")

# Cache directory (matches what the code expects)
CACHE_DIR = Path("/root/.cache/4DHumans")
CHECKPOINT_PATH = CACHE_DIR / "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"
DATA_DIR = CACHE_DIR / "data"
SMPL_DIR = DATA_DIR / "smpl"

def install_gdown():
    """Install gdown if not available"""
    try:
        import gdown
        return gdown
    except ImportError:
        print("[Build] Installing gdown...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "gdown"])
        import gdown
        return gdown

def download_from_url(url, output_path, expected_size_mb_min=None, expected_size_mb_max=None, description=""):
    """
    Download a file from any URL (Dropbox, direct HTTP, etc.)
    
    Args:
        url: Direct download URL
        output_path: Where to save the file
        expected_size_mb_min: Minimum expected size in MB (for validation)
        expected_size_mb_max: Maximum expected size in MB (for validation)
        description: Human-readable description of the file
    
    Returns:
        bool: True if download succeeded, False otherwise
    """
    import urllib.request as urlrequest
    
    output_path = Path(output_path)
    
    # Skip if already exists
    if output_path.exists():
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        if expected_size_mb_min and file_size_mb < expected_size_mb_min:
            print(f"[Build] ⚠️  Existing file {output_path.name} is too small ({file_size_mb:.1f}MB), re-downloading...")
            output_path.unlink()
        elif expected_size_mb_max and file_size_mb > expected_size_mb_max:
            print(f"[Build] ⚠️  Existing file {output_path.name} is too large ({file_size_mb:.1f}MB), re-downloading...")
            output_path.unlink()
        else:
            print(f"[Build] ✓ {description or output_path.name} already exists ({file_size_mb:.1f}MB)")
            return True
    
    # Create parent directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Ensure Dropbox URL has dl=1 for direct download
    if "dropbox.com" in url and "?dl=" not in url:
        url = url + "?dl=1" if "?" not in url else url.replace("?dl=0", "?dl=1")
    
    print(f"[Build] Downloading {description or output_path.name} from URL...")
    print(f"[Build]   URL: {url}")
    print(f"[Build]   Destination: {output_path}")
    
    try:
        # Download with progress
        req = urlrequest.Request(url)
        response = urlrequest.urlopen(req)
        total_size = int(response.info().get("Content-Length", 0))
        
        if total_size == 0:
            print(f"[Build] ⚠️  Warning: Could not determine file size")
        
        temp_file = output_path.parent / f"temp_{output_path.name}"
        bytes_so_far = 0
        chunk_size = 8192 * 1024  # 8MB chunks
        
        with open(temp_file, "wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                bytes_so_far += len(chunk)
                
                # Progress every 200MB
                if total_size > 0 and bytes_so_far % (200 * 1024 * 1024) < chunk_size:
                    percent = (bytes_so_far / total_size) * 100
                    mb_transferred = bytes_so_far / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    print(f"[Build]   Progress: {mb_transferred:.1f}MB / {mb_total:.1f}MB ({percent:.1f}%)")
        
        # Validate size
        if temp_file.exists():
            file_size_mb = temp_file.stat().st_size / (1024 * 1024)
            
            if expected_size_mb_min and file_size_mb < expected_size_mb_min:
                print(f"[Build] ✗ Downloaded file is too small: {file_size_mb:.1f}MB (expected at least {expected_size_mb_min}MB)")
                temp_file.unlink()
                return False
            
            if expected_size_mb_max and file_size_mb > expected_size_mb_max:
                print(f"[Build] ✗ Downloaded file is too large: {file_size_mb:.1f}MB (expected at most {expected_size_mb_max}MB)")
                temp_file.unlink()
                return False
            
            # Move to final location
            if output_path.exists():
                output_path.unlink()
            shutil.move(str(temp_file), str(output_path))
            print(f"[Build] ✓ Downloaded {description or output_path.name} ({file_size_mb:.1f}MB)")
            return True
        else:
            print(f"[Build] ✗ Download failed: temp file not found")
            return False
            
    except Exception as e:
        print(f"[Build] ✗ Download error for {description or output_path.name}: {e}")
        return False

def download_file(gdown, file_id, output_path, expected_size_mb_min=None, expected_size_mb_max=None, description="", dropbox_url=None):
    """
    Download a file from Google Drive or Dropbox.
    
    Args:
        gdown: gdown module (for Google Drive)
        file_id: Google Drive file ID (fallback)
        output_path: Where to save the file
        expected_size_mb_min: Minimum expected size in MB (for validation)
        expected_size_mb_max: Maximum expected size in MB (for validation)
        description: Human-readable description of the file
        dropbox_url: Dropbox URL (preferred if provided)
    
    Returns:
        bool: True if download succeeded, False otherwise
    """
    # Prefer Dropbox if available
    if dropbox_url:
        return download_from_url(dropbox_url, output_path, expected_size_mb_min, expected_size_mb_max, description)
    
    # Fallback to Google Drive
    output_path = Path(output_path)
    
    # Skip if already exists
    if output_path.exists():
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        if expected_size_mb_min and file_size_mb < expected_size_mb_min:
            print(f"[Build] ⚠️  Existing file {output_path.name} is too small ({file_size_mb:.1f}MB), re-downloading...")
            output_path.unlink()
        elif expected_size_mb_max and file_size_mb > expected_size_mb_max:
            print(f"[Build] ⚠️  Existing file {output_path.name} is too large ({file_size_mb:.1f}MB), re-downloading...")
            output_path.unlink()
        else:
            print(f"[Build] ✓ {description or output_path.name} already exists ({file_size_mb:.1f}MB)")
            return True
    
    # Create parent directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Download from Google Drive
    gdrive_url = f"https://drive.google.com/uc?id={file_id}"
    print(f"[Build] Downloading {description or output_path.name} from Google Drive...")
    print(f"[Build]   URL: {gdrive_url}")
    print(f"[Build]   Destination: {output_path}")
    
    try:
        # Download to temp file first
        temp_file = output_path.parent / f"temp_{output_path.name}"
        gdown.download(gdrive_url, output=str(temp_file), quiet=False)
        
        # Validate size
        if temp_file.exists():
            file_size_mb = temp_file.stat().st_size / (1024 * 1024)
            
            if expected_size_mb_min and file_size_mb < expected_size_mb_min:
                print(f"[Build] ✗ Downloaded file is too small: {file_size_mb:.1f}MB (expected at least {expected_size_mb_min}MB)")
                temp_file.unlink()
                return False
            
            if expected_size_mb_max and file_size_mb > expected_size_mb_max:
                print(f"[Build] ✗ Downloaded file is too large: {file_size_mb:.1f}MB (expected at most {expected_size_mb_max}MB)")
                temp_file.unlink()
                return False
            
            # Move to final location
            if output_path.exists():
                output_path.unlink()
            shutil.move(str(temp_file), str(output_path))
            print(f"[Build] ✓ Downloaded {description or output_path.name} ({file_size_mb:.1f}MB)")
            return True
        else:
            print(f"[Build] ✗ Download failed: temp file not found")
            return False
            
    except Exception as e:
        error_str = str(e)
        if "Too many users" in error_str or "quota" in error_str.lower() or "FileURLRetrievalError" in error_str:
            print(f"[Build] ⚠️  Google Drive quota exceeded for {description or output_path.name}")
            print(f"[Build]    This is expected during high-traffic periods.")
            print(f"[Build]    Models will be downloaded at runtime if volume is empty.")
            print(f"[Build]    Build will continue without this file.")
            return False
        else:
            print(f"[Build] ✗ Download error for {description or output_path.name}: {e}")
            return False

def main():
    """Main download function"""
    print("=" * 70)
    print("BUILD-TIME MODEL DOWNLOAD")
    print("=" * 70)
    print()
    print("This script downloads models during Docker build to avoid")
    print("runtime quota issues. If downloads fail due to quota, the")
    print("build will continue and models will be downloaded at runtime.")
    print()
    
    # Install gdown
    gdown = install_gdown()
    
    # Create directories
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SMPL_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    print()
    print("=" * 70)
    print("DOWNLOADING CHECKPOINT (2.5GB)")
    print("=" * 70)
    checkpoint_success = download_file(
        gdown,
        GOOGLE_DRIVE_CHECKPOINT_ID,
        CHECKPOINT_PATH,
        expected_size_mb_min=2000,  # At least 2GB
        expected_size_mb_max=3000,   # At most 3GB
        description="HMR2 Checkpoint",
        dropbox_url=DROPBOX_CHECKPOINT_URL
    )
    
    print()
    print("=" * 70)
    print("DOWNLOADING SMPL MODELS (~247MB each)")
    print("=" * 70)
    
    smpl_neutral_path = DATA_DIR / "basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl"
    smpl_male_path = DATA_DIR / "basicmodel_m_lbs_10_207_0_v1.1.0.pkl"
    smpl_female_path = DATA_DIR / "basicmodel_f_lbs_10_207_0_v1.1.0.pkl"
    
    smpl_neutral_success = download_file(
        gdown,
        GOOGLE_DRIVE_SMPL_NEUTRAL_ID,
        smpl_neutral_path,
        expected_size_mb_min=200,   # At least 200MB
        expected_size_mb_max=300,    # At most 300MB
        description="SMPL Neutral Model",
        dropbox_url=DROPBOX_SMPL_NEUTRAL_URL
    )
    
    smpl_male_success = download_file(
        gdown,
        GOOGLE_DRIVE_SMPL_MALE_ID,
        smpl_male_path,
        expected_size_mb_min=200,
        expected_size_mb_max=300,
        description="SMPL Male Model",
        dropbox_url=DROPBOX_SMPL_MALE_URL
    )
    
    smpl_female_success = download_file(
        gdown,
        GOOGLE_DRIVE_SMPL_FEMALE_ID,
        smpl_female_path,
        expected_size_mb_min=200,
        expected_size_mb_max=300,
        description="SMPL Female Model",
        dropbox_url=DROPBOX_SMPL_FEMALE_URL
    )
    
    print()
    print("=" * 70)
    print("DOWNLOADING SUPPORTING FILES")
    print("=" * 70)
    
    mean_params_success = download_file(
        gdown,
        GOOGLE_DRIVE_MEAN_PARAMS_ID,
        DATA_DIR / "smpl_mean_params.npz",
        expected_size_mb_min=0.1,   # Small file
        expected_size_mb_max=50,    # But not huge
        description="SMPL Mean Params",
        dropbox_url=DROPBOX_MEAN_PARAMS_URL
    )
    
    joint_regressor_success = download_file(
        gdown,
        GOOGLE_DRIVE_JOINT_REGRESSOR_ID,
        DATA_DIR / "SMPL_to_J19.pkl",
        expected_size_mb_min=0.1,
        expected_size_mb_max=50,
        description="SMPL Joint Regressor",
        dropbox_url=DROPBOX_JOINT_REGRESSOR_URL
    )
    
    print()
    print("=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)
    
    results = {
        "Checkpoint": checkpoint_success,
        "SMPL Neutral": smpl_neutral_success,
        "SMPL Male": smpl_male_success,
        "SMPL Female": smpl_female_success,
        "Mean Params": mean_params_success,
        "Joint Regressor": joint_regressor_success,
    }
    
    for name, success in results.items():
        status = "✓" if success else "⚠️"
        print(f"{status} {name}: {'Downloaded' if success else 'Skipped (quota or error)'}")
    
    print()
    
    # Check if critical files are present
    critical_files = [
        ("Checkpoint", CHECKPOINT_PATH),
        ("SMPL Neutral", smpl_neutral_path),
    ]
    
    all_critical_present = True
    for name, path in critical_files:
        if not path.exists():
            print(f"⚠️  WARNING: Critical file missing: {name} ({path})")
            all_critical_present = False
    
    if all_critical_present:
        print("✓ All critical files downloaded successfully!")
        print("  Models are baked into the Docker image.")
        print("  Runtime downloads will be skipped if these files exist.")
    else:
        print("⚠️  Some critical files are missing.")
        print("  Models will be downloaded at runtime (may hit quota).")
        print("  Consider re-running build when quota resets.")
    
    print()
    print("=" * 70)
    print("BUILD CONTINUES...")
    print("=" * 70)
    print()
    
    # Don't fail the build - let runtime handle missing files
    # Exit with 0 so Docker build continues
    sys.exit(0)

if __name__ == "__main__":
    main()
