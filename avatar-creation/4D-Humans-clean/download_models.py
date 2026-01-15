#!/usr/bin/env python3
"""
Script to download pretrained models for 4D-Humans
"""

import os
import sys

# Create necessary directories
os.makedirs('data', exist_ok=True)
os.makedirs('outputs', exist_ok=True)

print("=" * 60)
print("Downloading 4D-Humans pretrained models...")
print("=" * 60)

try:
    from hmr2.utils.download import download_models
    download_models()
    print("\n✓ Models downloaded successfully!")
except Exception as e:
    print(f"\n⚠ Could not auto-download models: {e}")
    print("\nManual download instructions:")
    print("1. Download checkpoint from: https://github.com/shubham-goel/4D-Humans")
    print("2. Place in the appropriate directory")

print("\n" + "=" * 60)
print("IMPORTANT: Download SMPL Body Model")
print("=" * 60)
print("\n1. Visit: https://smpl.is.tue.mpg.de/")
print("2. Register for an account")
print("3. Download: SMPL for Python (version 1.0.0)")
print("4. Extract and find: basicModel_neutral_lbs_10_207_0_v1.0.0.pkl")
print("5. Place it in: ./data/")
print("\nWithout SMPL model, the demo will not work!")
print("=" * 60)

