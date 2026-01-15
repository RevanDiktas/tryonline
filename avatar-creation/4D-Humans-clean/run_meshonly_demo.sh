#!/bin/bash

echo "============================================================"
echo "Running 4D-Humans Demo (Mesh Generation Only)"
echo "============================================================"
echo ""
echo "This demo generates 3D meshes without rendering"
echo "Perfect for macOS (bypasses OpenGL issues)"
echo ""

python demo_meshonly.py \
    --img_folder example_data/images \
    --out_folder demo_out \
    --batch_size=1

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✓ Demo completed successfully!"
    echo "Check the 'demo_out/' folder for .obj mesh files!"
    echo "============================================================"
else
    echo ""
    echo "============================================================"
    echo "⚠ Demo encountered issues"
    echo "Please check the error messages above."
    echo "============================================================"
fi

