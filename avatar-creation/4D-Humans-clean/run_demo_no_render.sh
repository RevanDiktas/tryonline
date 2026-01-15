#!/bin/bash
# Run 4D-Humans without rendering (faster, mesh-only output)

# Disable rendering to avoid OpenGL issues on macOS
export PYOPENGL_PLATFORM=

echo "============================================================"
echo "Running 4D-Humans Demo (No Rendering - Mesh Only)"
echo "============================================================"
echo ""

python demo.py \
    --img_folder example_data/images \
    --out_folder demo_out \
    --batch_size=1 \
    --save_mesh

echo ""
echo "============================================================"
if [ -d "demo_out" ]; then
    echo "✓ Demo completed! 3D meshes saved in demo_out/"
    echo ""
    echo "Generated files:"
    find demo_out -name "*.obj" -o -name "*.pkl" | head -20
else
    echo "⚠ Demo encountered issues"
fi
echo "============================================================"

