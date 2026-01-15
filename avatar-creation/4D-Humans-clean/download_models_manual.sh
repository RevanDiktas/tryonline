#!/bin/bash
# Manual model download script for 4D-Humans

set -e

echo "============================================================"
echo "Downloading 4D-Humans Models"
echo "============================================================"

# Create directories
mkdir -p data/checkpoints
mkdir -p outputs

# Download HMR2 checkpoint (using gdown from Google Drive)
echo ""
echo "Downloading HMR2 model checkpoint..."
cd data/checkpoints

# HMR2 checkpoint ID from the official repo
gdown --fuzzy "https://people.eecs.berkeley.edu/~jathushan/projects/4D-Humans/hmr2.ckpt" -O hmr2.ckpt

if [ -f "hmr2.ckpt" ]; then
    echo "✓ HMR2 checkpoint downloaded successfully!"
else
    echo "⚠ Failed to download HMR2 checkpoint"
    echo "Try manually downloading from: https://github.com/shubham-goel/4D-Humans"
fi

cd ../..

echo ""
echo "============================================================"
echo "Model Files Status"
echo "============================================================"
ls -lh data/checkpoints/ 2>/dev/null || echo "No checkpoints found"

echo ""
echo "============================================================"
echo "NEXT STEP: Download SMPL Body Model"
echo "============================================================"
echo ""
echo "The SMPL model requires registration and cannot be auto-downloaded."
echo ""
echo "Steps:"
echo "1. Visit: https://smpl.is.tue.mpg.de/"
echo "2. Register for an account (it's free)"
echo "3. Download: SMPL for Python (version 1.0.0)"
echo "4. Extract and find: basicModel_neutral_lbs_10_207_0_v1.0.0.pkl"
echo "5. Place it in: $(pwd)/data/"
echo ""
echo "Alternative: Download from SMPL-X website"
echo "   https://smpl-x.is.tue.mpg.de/"
echo ""
echo "Without SMPL model, the demo will not work!"
echo "============================================================"

