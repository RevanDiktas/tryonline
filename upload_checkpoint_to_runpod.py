#!/usr/bin/env python3
"""
Upload HMR2 checkpoint to RunPod S3 storage
"""
import boto3
import os
import time
from pathlib import Path

# RunPod S3 credentials - GET THESE FROM RUNPOD DASHBOARD
# Go to: Storage > Your Volume > "S3 API Access" or "Access Keys"
RUNPOD_ACCESS_KEY = "user_38Lv6qFBoOX38DBNIc1vS9UVI58"  # Replace this
RUNPOD_SECRET_KEY = "rps_6OGZ805GBQUQXO7RXOZMOUDZL9YSXSWK2IN5DT3U1h54t3"  # Replace this

# Volume details from the screenshot
BUCKET_NAME = "btb36084y0"
ENDPOINT_URL = "https://s3api-eu-cz-1.runpod.io"
REGION = "eu-cz-1"

# Local checkpoint file
LOCAL_CHECKPOINT = Path("/Volumes/Expansion/mvp_pipeline/avatar-creation/4D-Humans-clean/.cache/4DHumans/logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")

# S3 destination path
S3_KEY = "checkpoints/epoch=35-step=1000000.ckpt"

def upload_checkpoint():
    """Upload checkpoint file to RunPod S3 storage"""
    
    if not LOCAL_CHECKPOINT.exists():
        print(f"ERROR: Checkpoint file not found: {LOCAL_CHECKPOINT}")
        return False
    
    if RUNPOD_ACCESS_KEY == "YOUR_ACCESS_KEY_HERE" or RUNPOD_SECRET_KEY == "YOUR_SECRET_KEY_HERE":
        print("ERROR: Please set RUNPOD_ACCESS_KEY and RUNPOD_SECRET_KEY")
        print("\nTo get your S3 credentials:")
        print("1. Go to RunPod Dashboard > Storage > hmr2-models")
        print("2. Look for 'S3 API Access' or 'Access Keys' section")
        print("3. Copy your Access Key and Secret Key")
        print("4. Edit this script and replace the placeholder values")
        return False
    
    # Create S3 client
    s3_client = boto3.client(
        's3',
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=RUNPOD_ACCESS_KEY,
        aws_secret_access_key=RUNPOD_SECRET_KEY,
        region_name=REGION
    )
    
    # Test connection first
    print("Testing S3 connection...")
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        print("✅ Connection successful!\n")
    except Exception as e:
        print(f"⚠️  Connection test failed: {e}")
        print("Continuing anyway...\n")
    
    file_size = LOCAL_CHECKPOINT.stat().st_size / (1024 * 1024 * 1024)  # GB
    print(f"Uploading checkpoint file...")
    print(f"  Source: {LOCAL_CHECKPOINT}")
    print(f"  Destination: s3://{BUCKET_NAME}/{S3_KEY}")
    print(f"  Size: {file_size:.2f} GB")
    print(f"  This may take a while...\n")
    
    try:
        # Use multipart upload for large files (better for 2.5GB)
        from boto3.s3.transfer import TransferConfig
        
        # Configure multipart upload (smaller chunks to avoid timeout)
        # 524 error = gateway timeout, so we need smaller chunks
        config = TransferConfig(
            multipart_threshold=10 * 1024 * 1024,  # 10MB threshold (start multipart for files > 10MB)
            max_concurrency=2,  # Fewer concurrent uploads to avoid overwhelming connection
            multipart_chunksize=5 * 1024 * 1024,  # 5MB chunks (smaller = less likely to timeout)
            use_threads=True,
            max_bandwidth=None  # No bandwidth limit
        )
        
        # Progress tracker
        class ProgressTracker:
            def __init__(self, total_size):
                self.total_size = total_size
                self.uploaded = 0
                self.last_update = 0
                self.start_time = time.time()
                self.last_print_time = self.start_time
                
            def __call__(self, bytes_transferred):
                self.uploaded = bytes_transferred
                mb_uploaded = bytes_transferred / (1024 * 1024)
                mb_total = self.total_size / (1024 * 1024)
                percent = (bytes_transferred / self.total_size) * 100
                current_time = time.time()
                
                # Update every 2 seconds OR every 1 MB (more frequent), whichever comes first
                time_since_last = current_time - self.last_print_time
                mb_since_last = mb_uploaded - self.last_update
                
                # Always print on first call or if enough time/data has passed
                if self.last_update == 0 or time_since_last >= 2.0 or mb_since_last >= 1.0:
                    elapsed = current_time - self.start_time
                    if mb_uploaded > 0 and elapsed > 0:
                        speed = mb_uploaded / elapsed  # MB/s
                        remaining_mb = mb_total - mb_uploaded
                        remaining_sec = remaining_mb / speed if speed > 0 else 0
                        print(f"\r  Progress: {mb_uploaded:.1f} MB / {mb_total:.1f} MB ({percent:.1f}%) | Speed: {speed:.2f} MB/s | ETA: {remaining_sec:.0f}s", end="", flush=True)
                    else:
                        print(f"\r  Progress: {mb_uploaded:.1f} MB / {mb_total:.1f} MB ({percent:.1f}%)", end="", flush=True)
                    self.last_update = mb_uploaded
                    self.last_print_time = current_time
        
        file_size_bytes = LOCAL_CHECKPOINT.stat().st_size
        progress = ProgressTracker(file_size_bytes)
        
        print("Starting multipart upload with 5MB chunks...")
        print("(Smaller chunks to avoid timeout - this may take longer but more reliable)")
        print("Progress will update every 2 seconds or every 1 MB...\n")
        
        # Retry logic for timeout errors
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                s3_client.upload_file(
                    str(LOCAL_CHECKPOINT),
                    BUCKET_NAME,
                    S3_KEY,
                    Config=config,
                    Callback=progress
                )
                break  # Success!
            except Exception as e:
                error_str = str(e)
                if "524" in error_str or "timeout" in error_str.lower() or "Timeout" in error_str:
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"\n\n⚠️  Upload timed out (524 error). Retry {retry_count}/{max_retries}...")
                        print("This usually means the connection is slow or unstable.")
                        print("Trying again with smaller chunks...\n")
                        
                        # Reduce chunk size even more on retry
                        config.multipart_chunksize = max(1 * 1024 * 1024, config.multipart_chunksize // 2)  # Half the chunk size, min 1MB
                        config.max_concurrency = 1  # Single connection
                        
                        # Reset progress tracker
                        progress = ProgressTracker(file_size_bytes)
                    else:
                        raise
                else:
                    raise  # Not a timeout error, raise immediately
        print(f"\n\n✅ Upload complete!")
        print(f"File is now at: s3://{BUCKET_NAME}/{S3_KEY}")
        return True
    except Exception as e:
        print(f"\n\n❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    upload_checkpoint()