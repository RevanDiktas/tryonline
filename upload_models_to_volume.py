#!/usr/bin/env python3
"""
Upload models to RunPod Network Volume via S3 API

This script uploads all required model files to your RunPod Network Volume.
Make sure you've downloaded all files locally first!

Usage:
    export RUNPOD_API_KEY="your-api-key"
    python upload_models_to_volume.py --models-dir ~/models_4dhumans
"""

import os
import sys
import argparse
from pathlib import Path
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

# RunPod S3 API Configuration
BUCKET_NAME = "btb36084y0"  # Your volume ID from RunPod
ENDPOINT_URL = "https://s3api-eu-cz-1.runpod.io"
REGION = "eu-cz-1"

# Required files and their destination paths
# local_path is relative to models_dir
REQUIRED_FILES = {
    # Checkpoint (2.5GB)
    "checkpoints/epoch=35-step=1000000.ckpt": {
        "local_path": "checkpoints/epoch=35-step=1000000.ckpt",
        "description": "HMR2 Checkpoint",
        "expected_size_mb": 2500,
        "required": True
    },
    # SMPL Models (~247MB each)
    "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl": {
        "local_path": "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl",
        "description": "SMPL Neutral Model",
        "expected_size_mb": 247,
        "required": True
    },
    "data/basicmodel_m_lbs_10_207_0_v1.1.0.pkl": {
        "local_path": "data/basicmodel_m_lbs_10_207_0_v1.1.0.pkl",
        "description": "SMPL Male Model",
        "expected_size_mb": 247,
        "required": True
    },
    "data/basicmodel_f_lbs_10_207_0_v1.1.0.pkl": {
        "local_path": "data/basicmodel_f_lbs_10_207_0_v1.1.0.pkl",
        "description": "SMPL Female Model",
        "expected_size_mb": 247,
        "required": True
    },
    # Supporting files
    "data/smpl_mean_params.npz": {
        "local_path": "data/smpl_mean_params.npz",
        "description": "SMPL Mean Params",
        "expected_size_mb": 1,
        "required": True
    },
    "data/SMPL_to_J19.pkl": {
        "local_path": "data/SMPL_to_J19.pkl",
        "description": "SMPL Joint Regressor",
        "expected_size_mb": 1,
        "required": True
    }
}

def get_s3_client():
    """Create S3 client using RunPod S3 API credentials"""
    # RunPod S3 API requires:
    # - AWS_ACCESS_KEY_ID = Your RunPod User ID (e.g., user_XXXXX)
    # - AWS_SECRET_ACCESS_KEY = S3 API Key Secret (generated in Settings > S3 API Keys)
    
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("RUNPOD_USER_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY") or os.environ.get("RUNPOD_S3_SECRET")
    
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        print("❌ ERROR: S3 API credentials not set!")
        print()
        print("RunPod S3 API requires SEPARATE credentials from REST API:")
        print("1. Go to: https://www.runpod.io/console/user/settings")
        print("2. Find 'S3 API Keys' section")
        print("3. Generate new S3 API key (or use existing)")
        print("4. Get your User ID (usually shown as 'user_XXXXX')")
        print()
        print("Then set these environment variables:")
        print("   export AWS_ACCESS_KEY_ID='your-user-id'  # e.g., user_XXXXX")
        print("   export AWS_SECRET_ACCESS_KEY='your-s3-api-secret'")
        print()
        print("OR use these variable names:")
        print("   export RUNPOD_USER_ID='your-user-id'")
        print("   export RUNPOD_S3_SECRET='your-s3-api-secret'")
        sys.exit(1)
    
    s3_client = boto3.client(
        's3',
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}  # Use path-style addressing
        )
    )
    return s3_client

def check_file_exists(s3_client, s3_key):
    """Check if file already exists in S3"""
    try:
        s3_client.head_object(Bucket=BUCKET_NAME, Key=s3_key)
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '404':
            return False
        elif error_code == '403':
            # 403 might mean file doesn't exist or no permission to check
            # We'll try to upload anyway - if it exists, upload will fail gracefully
            return False
        else:
            # For other errors, log but don't fail - try upload anyway
            print(f"   ⚠️  Could not check if file exists: {error_code}, will attempt upload")
            return False

def upload_file(s3_client, local_path, s3_key, description, expected_size_mb):
    """Upload a single file to S3 with progress"""
    local_path = Path(local_path)
    
    if not local_path.exists():
        print(f"❌ File not found: {local_path}")
        return False
    
    # Check file size
    file_size_mb = local_path.stat().st_size / (1024 * 1024)
    if file_size_mb < expected_size_mb * 0.9:  # Allow 10% tolerance
        print(f"⚠️  Warning: {description} size seems small ({file_size_mb:.1f}MB, expected ~{expected_size_mb}MB)")
        response = input("   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return False
    
    # Check if already exists
    if check_file_exists(s3_client, s3_key):
        print(f"⏭️  {description} already exists in volume, skipping...")
        return True
    
    print(f"⬆️  Uploading {description} ({file_size_mb:.1f}MB)...")
    print(f"   From: {local_path}")
    print(f"   To: s3://{BUCKET_NAME}/{s3_key}")
    
    try:
        # Upload with optimized settings for speed
        # Use larger multipart chunk size (64MB instead of default 8MB) for faster uploads
        from boto3.s3.transfer import TransferConfig
        
        config = TransferConfig(
            multipart_threshold=1024 * 25,  # Use multipart for files > 25MB
            multipart_chunksize=1024 * 1024 * 64,  # 64MB chunks (larger = faster)
            max_concurrency=10,  # Upload 10 parts concurrently
            use_threads=True
        )
        
        # Progress callback
        class ProgressTracker:
            def __init__(self, total_size):
                self.total_size = total_size
                self.transferred = 0
                self.last_reported = 0
            
            def __call__(self, bytes_transferred):
                self.transferred = bytes_transferred
                # Report every 200MB or at completion
                if bytes_transferred - self.last_reported >= 200 * 1024 * 1024 or bytes_transferred == self.total_size:
                    mb_transferred = bytes_transferred / (1024 * 1024)
                    mb_total = self.total_size / (1024 * 1024)
                    percent = (bytes_transferred / self.total_size) * 100
                    print(f"   Progress: {mb_transferred:.1f}MB / {mb_total:.1f}MB ({percent:.1f}%)")
                    self.last_reported = bytes_transferred
        
        progress = ProgressTracker(local_path.stat().st_size)
        
        # Use upload_file with optimized config for better performance
        s3_client.upload_file(
            str(local_path),
            BUCKET_NAME,
            s3_key,
            Config=config,
            Callback=progress
        )
        
        print(f"✅ {description} uploaded successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to upload {description}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Upload models to RunPod Network Volume')
    parser.add_argument(
        '--models-dir',
        type=str,
        default=os.path.expanduser('~/models_4dhumans'),
        help='Directory containing downloaded model files (default: ~/models_4dhumans)'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip files that already exist in volume'
    )
    
    args = parser.parse_args()
    
    models_dir = Path(args.models_dir)
    
    print("=" * 70)
    print("UPLOAD MODELS TO RUNPOD NETWORK VOLUME")
    print("=" * 70)
    print()
    print(f"Models directory: {models_dir}")
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Endpoint: {ENDPOINT_URL}")
    print()
    
    # Check if models directory exists
    if not models_dir.exists():
        print(f"❌ ERROR: Models directory not found: {models_dir}")
        print()
        print("Please download models first:")
        print("1. Download files from browser (see QUICK_UPLOAD_GUIDE.md)")
        print("2. Organize them in this structure:")
        print(f"   {models_dir}/")
        print("   ├── checkpoints/")
        print("   │   └── epoch=35-step=1000000.ckpt")
        print("   └── data/")
        print("       ├── basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl")
        print("       ├── basicmodel_m_lbs_10_207_0_v1.1.0.pkl")
        print("       ├── basicmodel_f_lbs_10_207_0_v1.1.0.pkl")
        print("       ├── smpl_mean_params.npz")
        print("       └── SMPL_to_J19.pkl")
        sys.exit(1)
    
    # Create S3 client
    try:
        s3_client = get_s3_client()
        print("✅ Connected to RunPod S3 API")
    except Exception as e:
        print(f"❌ Failed to connect to S3: {e}")
        sys.exit(1)
    
    print()
    print("=" * 70)
    print("CHECKING FILES...")
    print("=" * 70)
    
    # Check which files exist locally
    files_to_upload = []
    for s3_key, file_info in REQUIRED_FILES.items():
        local_file = models_dir / file_info["local_path"]
        if local_file.exists():
            files_to_upload.append((s3_key, file_info, local_file))
        else:
            if file_info["required"]:
                print(f"❌ Required file missing: {local_file}")
            else:
                print(f"⚠️  Optional file missing: {local_file}")
    
    if not files_to_upload:
        print("❌ No files found to upload!")
        sys.exit(1)
    
    print(f"✅ Found {len(files_to_upload)} files to upload")
    print()
    
    # Calculate total size
    total_size_mb = sum(f.stat().st_size / (1024 * 1024) for _, _, f in files_to_upload)
    print(f"Total size: {total_size_mb:.1f}MB (~{total_size_mb/1024:.2f}GB)")
    print(f"Estimated upload time: ~{int(total_size_mb / 10)} minutes (at 10MB/s)")
    print()
    
    response = input("Continue with upload? (y/n): ")
    if response.lower() != 'y':
        print("Upload cancelled.")
        sys.exit(0)
    
    print()
    print("=" * 70)
    print("UPLOADING FILES...")
    print("=" * 70)
    print()
    
    # Upload files
    # Note: S3 key needs to be prefixed with "4DHumans/" to match expected structure
    success_count = 0
    failed_count = 0
    
    for s3_key, file_info, local_file in files_to_upload:
        # Prepend "4DHumans/" to match the expected cache structure
        full_s3_key = f"4DHumans/{s3_key}"
        
        # For checkpoint, need full path
        if "checkpoints" in s3_key:
            full_s3_key = f"4DHumans/logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"
        
        if upload_file(s3_client, local_file, full_s3_key, file_info["description"], file_info["expected_size_mb"]):
            success_count += 1
        else:
            failed_count += 1
            if file_info["required"]:
                print(f"⚠️  Required file failed to upload - pipeline may not work!")
        print()
    
    print()
    print("=" * 70)
    print("UPLOAD SUMMARY")
    print("=" * 70)
    print(f"✅ Successfully uploaded: {success_count} files")
    if failed_count > 0:
        print(f"❌ Failed: {failed_count} files")
    
    if success_count == len(files_to_upload):
        print()
        print("🎉 All files uploaded successfully!")
        print()
        print("Next steps:")
        print("1. Run a test avatar creation job")
        print("2. Check logs - should see:")
        print("   [Config] Using RunPod Network Volume cache: /runpod-volume/4DHumans")
        print("   ✅ Checkpoint found in cache (volume working!)")
    else:
        print()
        print("⚠️  Some files failed to upload. Please check errors above and retry.")

if __name__ == "__main__":
    main()
