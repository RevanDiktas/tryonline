#!/bin/bash
# macOS-compatible demo script for 4D-Humans

# Set PyOpenGL to use OSMesa (software rendering) instead of EGL
export PYOPENGL_PLATFORM=osmesa

# Alternative: disable rendering entirely (faster, no visualizations)
# export PYOPENGL_PLATFORM=

echo "============================================================"
echo "Running 4D-Humans Demo (macOS compatible)"
echo "============================================================"
echo ""

python demo.py \
    --img_folder example_data/images \
    --out_folder demo_out \
    --batch_size=1 \
    --full_frame

echo ""
echo "============================================================"
if [ -d "demo_out" ]; then
    echo "✓ Demo completed! Results in demo_out/"
    echo ""
    echo "Generated files:"
    ls -lh demo_out/
else
    echo "⚠ Demo may have encountered issues"
fi
echo "============================================================"

