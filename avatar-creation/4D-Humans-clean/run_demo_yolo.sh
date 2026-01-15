#!/bin/bash
# Run 4D-Humans with YOLOv8 detection (macOS compatible, no detectron2 required!)

echo "============================================================"
echo "4D-Humans Demo with YOLOv8 Detection"
echo "No detectron2 required - works on macOS!"
echo "============================================================"
echo ""

cd /Volumes/Expansion/avatar-creation/4D-Humans-clean

# Activate conda environment
source /Volumes/Expansion/miniconda3/etc/profile.d/conda.sh
conda activate 4D-humans

# Run the demo
python demo_yolo.py \
    --img_folder example_data/images \
    --out_folder demo_out \
    --batch_size=1

echo ""
echo "============================================================"
if [ -d "demo_out" ] && [ "$(ls -A demo_out/*.obj 2>/dev/null)" ]; then
    echo "✓ Demo completed successfully!"
    echo ""
    echo "Generated 3D meshes:"
    ls -lh demo_out/*.obj | awk '{print "  - " $9 " (" $5 ")"}'
    echo ""
    echo "You can open these .obj files in:"
    echo "  - Blender"
    echo "  - MeshLab"
    echo "  - Any 3D viewer"
else
    echo "⚠ Demo encountered issues"
fi
echo "============================================================"


