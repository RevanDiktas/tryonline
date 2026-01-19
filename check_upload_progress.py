#!/usr/bin/env python3
"""
Monitor upload progress to RunPod Network Volume

Run this in a separate terminal to check what's been uploaded so far.
"""

import os
import sys
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

# RunPod S3 API Configuration
BUCKET_NAME = "btb36084y0"
ENDPOINT_URL = "https://s3api-eu-cz-1.runpod.io"
REGION = "eu-cz-1"

# Expected files
EXPECTED_FILES = {
    "4DHumans/logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt": {
        "name": "Checkpoint",
        "expected_size_mb": 2500
    },
    "4DHumans/data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl": {
        "name": "SMPL Neutral",
        "expected_size_mb": 247
    },
    "4DHumans/data/basicmodel_m_lbs_10_207_0_v1.1.0.pkl": {
        "name": "SMPL Male",
        "expected_size_mb": 247
    },
    "4DHumans/data/basicmodel_f_lbs_10_207_0_v1.1.0.pkl": {
        "name": "SMPL Female",
        "expected_size_mb": 247
    },
    "4DHumans/data/smpl_mean_params.npz": {
        "name": "Mean Params",
        "expected_size_mb": 1
    },
    "4DHumans/data/SMPL_to_J19.pkl": {
        "name": "Joint Regressor",
        "expected_size_mb": 1
    }
}

def get_s3_client():
    """Create S3 client"""
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("RUNPOD_USER_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY") or os.environ.get("RUNPOD_S3_SECRET")
    
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        print("❌ ERROR: S3 API credentials not set!")
        print("   Set: export AWS_ACCESS_KEY_ID='your-user-id'")
        print("   Set: export AWS_SECRET_ACCESS_KEY='your-s3-secret'")
        sys.exit(1)
    
    return boto3.client(
        's3',
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}
        )
    )

def check_file_status(s3_client, s3_key, file_info):
    """Check if file exists and get its size"""
    try:
        response = s3_client.head_object(Bucket=BUCKET_NAME, Key=s3_key)
        size_bytes = response['ContentLength']
        size_mb = size_bytes / (1024 * 1024)
        return True, size_mb
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '404':
            return False, 0
        elif error_code == '403':
            # Might be uploading - try to list to see if it exists
            return None, 0
        else:
            return None, 0

def main():
    print("=" * 70)
    print("UPLOAD PROGRESS MONITOR")
    print("=" * 70)
    print()
    
    try:
        s3_client = get_s3_client()
        print("✅ Connected to RunPod S3 API")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        sys.exit(1)
    
    print()
    print("Checking uploaded files...")
    print()
    
    uploaded_count = 0
    total_size_mb = 0
    expected_total_mb = sum(f["expected_size_mb"] for f in EXPECTED_FILES.values())
    
    for s3_key, file_info in EXPECTED_FILES.items():
        exists, size_mb = check_file_status(s3_client, s3_key, file_info)
        
        if exists:
            status = "✅"
            uploaded_count += 1
            total_size_mb += size_mb
            percent = (size_mb / file_info["expected_size_mb"]) * 100
            if percent >= 95:
                print(f"{status} {file_info['name']:20} {size_mb:7.1f}MB / {file_info['expected_size_mb']:4.0f}MB (100%)")
            else:
                print(f"{status} {file_info['name']:20} {size_mb:7.1f}MB / {file_info['expected_size_mb']:4.0f}MB ({percent:.1f}%)")
        elif exists is None:
            print(f"⏳ {file_info['name']:20} Checking...")
        else:
            print(f"⏳ {file_info['name']:20} Not uploaded yet")
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Uploaded: {uploaded_count}/{len(EXPECTED_FILES)} files")
    print(f"Progress: {total_size_mb:.1f}MB / {expected_total_mb:.1f}MB ({total_size_mb/expected_total_mb*100:.1f}%)")
    
    if uploaded_count == len(EXPECTED_FILES):
        print()
        print("🎉 All files uploaded successfully!")
    elif uploaded_count > 0:
        print()
        print("⏳ Upload in progress... Run this script again to check progress.")
    else:
        print()
        print("⏳ Upload hasn't started yet or files not found.")

if __name__ == "__main__":
    main()
