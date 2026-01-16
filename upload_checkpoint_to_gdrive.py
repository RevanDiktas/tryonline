#!/usr/bin/env python3
"""
Upload HMR2 checkpoint to Google Drive (much faster than RunPod S3)
Then download it in the container at runtime.
"""
import os
from pathlib import Path

LOCAL_CHECKPOINT = Path("/Volumes/Expansion/mvp_pipeline/avatar-creation/4D-Humans-clean/.cache/4DHumans/logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")

print("=" * 60)
print("Upload Checkpoint to Google Drive")
print("=" * 60)
print()
print("Steps:")
print("1. Go to: https://drive.google.com")
print("2. Create a new folder (optional): 'HMR2-Models'")
print("3. Upload the checkpoint file:")
print(f"   {LOCAL_CHECKPOINT.name}")
print(f"   (Size: {LOCAL_CHECKPOINT.stat().st_size / (1024**3):.2f} GB)")
print()
print("4. After upload, right-click the file → 'Get link'")
print("5. Set sharing to 'Anyone with the link'")
print("6. Copy the file ID from the URL")
print("   Example: https://drive.google.com/file/d/FILE_ID_HERE/view")
print()
print("7. Update the handler code with your Google Drive file ID")
print()
print("=" * 60)
print()
print("Alternative: Use gdown CLI to upload (if you have it)")
print("Or use Google Drive web interface (usually fastest)")
