#!/usr/bin/env python3
"""
Quick script to check RunPod Network Volume contents via S3 API
Note: RunPod S3 API requires authentication via RunPod API key
"""
import os
import boto3
from botocore.client import Config

# Your volume details
BUCKET_NAME = "btb36084y0"  # Your volume ID
ENDPOINT_URL = "https://s3api-eu-cz-1.runpod.io"
REGION = "eu-cz-1"

# Get RunPod API key from environment or prompt
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
if not RUNPOD_API_KEY:
    print("⚠️  RUNPOD_API_KEY not found in environment variables")
    print("   Set it with: export RUNPOD_API_KEY='your_key_here'")
    print("   Or check volume contents via job logs instead (recommended)")
    print()
    print("   The easiest way is to run a job and check logs for:")
    print("   - '[RunPod] Network Volume detected'")
    print("   - '[DEBUG download_models] ✓ Found checkpoint in Network Volume'")
    exit(1)

# Create S3 client with RunPod API key
# RunPod uses API key as both access key and secret
s3_client = boto3.client(
    's3',
    endpoint_url=ENDPOINT_URL,
    region_name=REGION,
    aws_access_key_id=RUNPOD_API_KEY,
    aws_secret_access_key=RUNPOD_API_KEY,
    config=Config(signature_version='s3v4')
)

print(f"Checking RunPod Network Volume: {BUCKET_NAME}")
print(f"Endpoint: {ENDPOINT_URL}")
print("-" * 60)

try:
    # List all objects in the bucket
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
    
    if 'Contents' in response:
        print(f"✓ Volume has {len(response['Contents'])} files/folders:")
        print()
        
        # Group by prefix (folder structure)
        folders = {}
        files = []
        
        for obj in response['Contents']:
            key = obj['Key']
            size = obj['Size']
            
            if '/' in key:
                folder = key.split('/')[0]
                if folder not in folders:
                    folders[folder] = []
                folders[folder].append((key, size))
            else:
                files.append((key, size))
        
        # Show folder structure
        for folder, items in sorted(folders.items()):
            total_size_mb = sum(s for _, s in items) / (1024 * 1024)
            print(f"📁 {folder}/ ({len(items)} items, {total_size_mb:.1f} MB)")
            # Show first few items in each folder
            for key, size in items[:5]:
                size_mb = size / (1024 * 1024)
                print(f"   - {key} ({size_mb:.1f} MB)")
            if len(items) > 5:
                print(f"   ... and {len(items) - 5} more items")
        
        # Show root files
        if files:
            print("\n📄 Root files:")
            for key, size in files:
                size_mb = size / (1024 * 1024)
                print(f"   - {key} ({size_mb:.1f} MB)")
        
        # Check specifically for models
        has_checkpoint = any('epoch=35-step=1000000.ckpt' in obj['Key'] for obj in response['Contents'])
        has_smpl = any('SMPL' in obj['Key'] or 'basicmodel' in obj['Key'].lower() for obj in response['Contents'])
        
        print()
        print("Model Status:")
        print(f"  Checkpoint: {'✓ Found' if has_checkpoint else '✗ Not found'}")
        print(f"  SMPL models: {'✓ Found' if has_smpl else '✗ Not found'}")
        
        if has_checkpoint and has_smpl:
            print("\n✅ Volume has cached models! Jobs should use them instead of downloading.")
        else:
            print("\n⚠️  Volume is empty or incomplete. First job will download models.")
    else:
        print("✗ Volume is empty (no files found)")
        print("\nThe first successful job will download models and save them here.")
        
except Exception as e:
    print(f"Error checking volume: {e}")
    print("\nThis might mean:")
    print("1. Volume is empty (first time use)")
    print("2. S3 API access issue")
    print("3. Volume not properly configured")
    print("\nBest to check via job logs instead.")
