#!/bin/bash
# Test 4D-Humans setup

echo "============================================================"
echo "Testing 4D-Humans Setup"
echo "============================================================"

# Check if SMPL model exists
echo ""
echo "Checking for SMPL model..."
if [ -f "data/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl" ]; then
    echo "✓ SMPL model found!"
else
    echo "✗ SMPL model NOT found!"
    echo "  Please download from: https://smpl.is.tue.mpg.de/"
    echo "  Place in: $(pwd)/data/"
    exit 1
fi

# Check if HMR2 checkpoint exists
echo ""
echo "Checking for HMR2 checkpoint..."
if [ -f "data/checkpoints/hmr2.ckpt" ]; then
    echo "✓ HMR2 checkpoint found!"
else
    echo "✗ HMR2 checkpoint NOT found!"
    exit 1
fi

# Run demo on example image
echo ""
echo "============================================================"
echo "Running Demo on Example Image"
echo "============================================================"
echo ""

python demo.py \
    --img_folder example_data/images \
    --out_folder demo_out \
    --batch_size=1 \
    --side_view \
    --save_mesh

echo ""
echo "============================================================"
if [ -d "demo_out" ]; then
    echo "✓ Demo completed! Check the 'demo_out' folder for results."
    echo ""
    echo "Output files:"
    ls -lh demo_out/
else
    echo "⚠ Demo may have encountered issues"
fi
echo "============================================================"

