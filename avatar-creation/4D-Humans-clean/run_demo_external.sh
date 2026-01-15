#!/bin/bash
# Run 4D-Humans with cache on external drive

# Set cache directory to external drive
export HMR2_CACHE_DIR=/Volumes/Expansion/avatar-creation/4D-Humans-clean/.cache
export PYOPENGL_PLATFORM=

echo "============================================================"
echo "Running 4D-Humans Demo (External Drive Cache)"
echo "============================================================"
echo "Cache directory: $HMR2_CACHE_DIR"
echo ""

# Create cache directory
mkdir -p $HMR2_CACHE_DIR

python demo.py \
    --img_folder example_data/images \
    --out_folder demo_out \
    --batch_size=1 \
    --save_mesh \
    --full_frame

echo ""
echo "============================================================"
if [ -d "demo_out" ]; then
    echo "✓ Demo completed! Results in demo_out/"
    echo ""
    echo "Generated files:"
    find demo_out -type f | head -20
else
    echo "⚠ Demo encountered issues"
fi
echo "============================================================"

