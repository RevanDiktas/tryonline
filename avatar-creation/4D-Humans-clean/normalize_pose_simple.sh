#!/bin/bash
# Simple script to normalize pose using Blender
# Usage: bash normalize_pose_simple.sh input.obj output.obj [t-pose|a-pose]

INPUT_MESH="$1"
OUTPUT_MESH="$2"
POSE_TYPE="${3:-a-pose}"

if [ -z "$INPUT_MESH" ] || [ -z "$OUTPUT_MESH" ]; then
    echo "Usage: bash normalize_pose_simple.sh input.obj output.obj [t-pose|a-pose]"
    exit 1
fi

echo "================================"
echo "Normalizing Pose in Blender"
echo "================================"
echo "Input: $INPUT_MESH"
echo "Output: $OUTPUT_MESH"
echo "Pose: $POSE_TYPE"
echo ""

# Create temporary Python script
cat > /tmp/blender_normalize_temp.py << 'PYTHON_SCRIPT'
import bpy
import sys
import os

# Get arguments
argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []

if len(argv) < 2:
    print("Error: Need input and output paths")
    sys.exit(1)

input_path = argv[0]
output_path = argv[1]
pose_type = argv[2] if len(argv) > 2 else 'a-pose'

print(f"Processing: {input_path}")
print(f"Output: {output_path}")
print(f"Pose: {pose_type}")

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Import mesh (Blender 4.0+ uses wm.obj_import)
try:
    bpy.ops.wm.obj_import(filepath=input_path)
except AttributeError:
    bpy.ops.import_scene.obj(filepath=input_path)
obj = bpy.context.selected_objects[0]
mesh = obj.data
vertices = mesh.vertices

# Get dimensions
verts = [(v.co.x, v.co.y, v.co.z) for v in vertices]
min_y = min(v[1] for v in verts)
max_y = max(v[1] for v in verts)
height = max_y - min_y
center_x = sum(v[0] for v in verts) / len(verts)
center_z = sum(v[2] for v in verts) / len(verts)

# Normalize pose - straighten and center
for v in vertices:
    # Center horizontally
    v.co.x -= center_x
    v.co.z -= center_z
    
    y_ratio = (v.co.y - min_y) / height
    
    # Straighten arms (A-pose or T-pose)
    if abs(v.co.x) > 0.25:  # Arm vertices
        if 0.65 < y_ratio < 0.90:  # Upper arm/shoulder
            if pose_type == 't-pose':
                # T-pose: arms horizontal
                v.co.y = min_y + (height * 0.78)
            else:
                # A-pose: arms at 45 degrees down
                angle_factor = 0.15
                v.co.y = min_y + (height * (0.75 - y_ratio * angle_factor))

mesh.update()

# Add material
mat = bpy.data.materials.new(name="Skin")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs['Base Color'].default_value = (0.76, 0.57, 0.45, 1.0)
    try:
        # Blender 4.0+
        if 'Subsurface Weight' in bsdf.inputs:
            bsdf.inputs['Subsurface Weight'].default_value = 0.15
        else:
            bsdf.inputs['Subsurface'].default_value = 0.15
    except:
        pass
    bsdf.inputs['Roughness'].default_value = 0.4

if obj.data.materials:
    obj.data.materials[0] = mat
else:
    obj.data.materials.append(mat)

# Export (Blender 4.0+ uses wm.obj_export)
try:
    bpy.ops.wm.obj_export(
        filepath=output_path,
        export_selected_objects=True,
        export_materials=True
    )
except AttributeError:
    bpy.ops.export_scene.obj(
        filepath=output_path,
        use_selection=True,
        use_materials=True
    )

# Save blend file too
blend_path = output_path.replace('.obj', '.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend_path)

print(f"✓ Saved: {output_path}")
print(f"✓ Saved: {blend_path}")
PYTHON_SCRIPT

# Run Blender
blender --background --python /tmp/blender_normalize_temp.py -- "$INPUT_MESH" "$OUTPUT_MESH" "$POSE_TYPE"

echo ""
echo "✓ Complete!"

