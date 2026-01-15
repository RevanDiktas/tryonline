#!/bin/bash
# MAIN Pipeline: Body Extraction → Pose Fix → Skin Texture → T-shirt Generation → Texture Mapping → GLB

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Input files
BODY_IMAGE="${1:-body.jpg}"
FACE_IMAGE="${2:-face.jpg}"
OUTPUT_DIR="${PROJECT_ROOT}/output/your_body"

echo "============================================================"
echo "🚀 COMPLETE AVATAR PIPELINE"
echo "============================================================"
echo "Body image: ${BODY_IMAGE}"
echo "Face image: ${FACE_IMAGE}"
echo "Output: ${OUTPUT_DIR}"
echo ""

# Step 1: Extract body from image (use venv310 - has cv2 and 4D-Humans deps)
echo "📸 Step 1: Extracting body from ${BODY_IMAGE}..."
echo "🔧 Using venv310 for 4D-Humans (has cv2, torch, etc.)..."

# Create temp folder for image if BODY_IMAGE is a file (demo_yolo.py expects a folder)
TEMP_INPUT_DIR="${PROJECT_ROOT}/temp_input_images"
mkdir -p "${TEMP_INPUT_DIR}"
rm -f "${TEMP_INPUT_DIR}"/*

# Check if BODY_IMAGE is a file or folder
if [ -f "${PROJECT_ROOT}/${BODY_IMAGE}" ]; then
    # It's a file - copy to temp folder
    cp "${PROJECT_ROOT}/${BODY_IMAGE}" "${TEMP_INPUT_DIR}/"
    IMG_FOLDER="${TEMP_INPUT_DIR}"
elif [ -d "${PROJECT_ROOT}/${BODY_IMAGE}" ]; then
    # It's already a folder
    IMG_FOLDER="${PROJECT_ROOT}/${BODY_IMAGE}"
else
    echo "❌ Error: ${BODY_IMAGE} not found!"
    exit 1
fi

source venv310/bin/activate
mkdir -p "${OUTPUT_DIR}"
cd 4D-Humans-clean
python demo_yolo.py \
    --img_folder "${IMG_FOLDER}" \
    --out_folder "${OUTPUT_DIR}" \
    --batch_size 1
cd "${PROJECT_ROOT}"
deactivate

# Clean up temp folder
rm -rf "${TEMP_INPUT_DIR}"

# Find the generated files
BODY_OBJ=$(find "${OUTPUT_DIR}" -name "body_person0.obj" | head -1)
BODY_PARAMS=$(find "${OUTPUT_DIR}" -name "body_person0_params.npz" | head -1)

if [ ! -f "${BODY_OBJ}" ] || [ ! -f "${BODY_PARAMS}" ]; then
    echo "❌ Error: Body extraction failed!"
    exit 1
fi

echo "✓ Body extracted: ${BODY_OBJ}"
echo "✓ Params saved: ${BODY_PARAMS}"

# Step 2: Fix pose to 45 degrees down (use venv310 - has smplx)
echo ""
echo "🎯 Step 2: Fixing pose to 45 degrees down..."
source venv310/bin/activate
python fix_pose_neutral.py \
    --params "${BODY_PARAMS}" \
    --output "${OUTPUT_DIR}/body_person0_neutral.obj" \
    --arm-angle 45
deactivate

if [ ! -f "${OUTPUT_DIR}/body_person0_neutral.obj" ]; then
    echo "❌ Error: Pose fixing failed!"
    exit 1
fi

echo "✓ Neutral pose body saved: ${OUTPUT_DIR}/body_person0_neutral.obj"

# Step 3: Extract skin tone from face (use venv310 - has cv2)
echo ""
echo "🎨 Step 3: Extracting skin tone from ${FACE_IMAGE}..."
source venv310/bin/activate
python extract_skin_tone.py \
    --face-image "${PROJECT_ROOT}/${FACE_IMAGE}" \
    --mesh "${OUTPUT_DIR}/body_person0_neutral.obj" \
    --output "${OUTPUT_DIR}"
deactivate

if [ ! -f "${OUTPUT_DIR}/body_person0_neutral_textured.obj" ]; then
    echo "❌ Error: Skin tone extraction failed!"
    exit 1
fi

echo "✓ Textured body saved: ${OUTPUT_DIR}/body_person0_neutral_textured.obj"
echo "✓ Skin texture saved: ${OUTPUT_DIR}/skin_texture.png"
echo "✓ Skin mask saved: ${OUTPUT_DIR}/skin_detection_mask.png"

# Step 4: Generate t-shirt for ALL sizes (TailorNet, venv310) - same pose as avatar (45 degrees down)
echo ""
echo "👕 Step 4: Generating t-shirts for ALL sizes (XS, S, M, L, XL) with TailorNet..."
echo "🔧 Using venv310 for TailorNet..."
source venv310/bin/activate
python generate_all_sizes.py \
    --smpl-params "${BODY_PARAMS}" \
    --output "${PROJECT_ROOT}/output/playboy_tshirt_all_sizes" \
    --arm-angle 45 \
    --fit-adjustment 0.0
deactivate

# Check if at least one size was generated
TSHIRT_DIR="${PROJECT_ROOT}/output/playboy_tshirt_all_sizes"
if [ ! -d "${TSHIRT_DIR}" ] || [ -z "$(ls -A ${TSHIRT_DIR}/*.ply 2>/dev/null)" ]; then
    echo "❌ Error: T-shirt generation failed!"
    exit 1
fi

echo "✓ T-shirts generated for all sizes in: ${TSHIRT_DIR}"

# Step 5: Generate stress heatmaps for ALL sizes (V1 - Experimental)
echo ""
echo "🔥 Step 5: Generating stress heatmaps for ALL sizes (V1)..."
echo "🔧 Using venv310 for heatmap generation..."
source venv310/bin/activate

# Create heatmap output directory
HEATMAP_OUTPUT_DIR="${PROJECT_ROOT}/output/heatmaps/v1tweaking"
mkdir -p "${HEATMAP_OUTPUT_DIR}"

# Generate heatmaps for all sizes
for size in xs s m l xl; do
    GARMENT_PLY="${TSHIRT_DIR}/playboy_tshirt_${size}_perfect.ply"
    BODY_PLY="${TSHIRT_DIR}/body_apose_m.ply"
    
    if [ -f "${GARMENT_PLY}" ] && [ -f "${BODY_PLY}" ]; then
        echo "   Generating heatmap for ${size}..."
        python generate_stress_heatmap_simple.py \
            --garment "${GARMENT_PLY}" \
            --body "${BODY_PLY}" \
            --output "${HEATMAP_OUTPUT_DIR}/temp.ply" 2>&1 | grep -E "(✅ Saved|Detected size)" || echo "   Processing ${size}..."
    else
        echo "   ⚠️  Skipping ${size} - files not found"
    fi
done
deactivate

echo "✓ Heatmaps generated for all sizes in: ${HEATMAP_OUTPUT_DIR}"

# Step 6: Combine heatmaps with avatar body and export as GLB
echo ""
echo "🔗 Step 6: Combining heatmaps with avatar body → GLB for ALL sizes..."
source venv310/bin/activate

# Create heatmap GLB output directory
HEATMAP_GLB_DIR="${PROJECT_ROOT}/output/heatmaps/v1tweaking"
mkdir -p "${HEATMAP_GLB_DIR}"

# Use M body for all sizes (as per current workflow)
BODY_FOR_HEATMAP="${TSHIRT_DIR}/body_apose_m.ply"

if [ ! -f "${BODY_FOR_HEATMAP}" ]; then
    echo "   ⚠️  Body file not found, using neutral body..."
    BODY_FOR_HEATMAP="${OUTPUT_DIR}/body_person0_neutral_textured.obj"
fi

# Combine heatmaps with body for all sizes
for size in xs s m l xl; do
    HEATMAP_PLY="${HEATMAP_OUTPUT_DIR}/playboy_tshirt_${size}_perfect_stress_heatmap_v1.ply"
    HEATMAP_GLB="${HEATMAP_GLB_DIR}/avatar_${size}_heatmap.glb"
    
    if [ -f "${HEATMAP_PLY}" ] && [ -f "${BODY_FOR_HEATMAP}" ]; then
        echo "   Combining ${size} heatmap with avatar..."
        python combine_heatmap_avatar_glb.py \
            --heatmap_garment "${HEATMAP_PLY}" \
            --body "${BODY_FOR_HEATMAP}" \
            --output "${HEATMAP_GLB}" 2>&1 | grep -E "(✓|Successfully)" || echo "   Processing ${size}..."
    else
        echo "   ⚠️  Skipping ${size} - heatmap or body file not found"
    fi
done
deactivate

echo "✓ Heatmap GLBs generated for all sizes in: ${HEATMAP_GLB_DIR}"

# Step 7: Extract NPC logo from artwork → npc_texture_4k.png (4096x4096)
echo ""
echo "🖼️ Step 7: Extracting NPC logo texture from artwork (4K)..."
source venv310/bin/activate

# Check if 4K texture already exists
NPC_TEXTURE_4K="${PROJECT_ROOT}/output/npc_texture_4k.png"
if [ -f "${NPC_TEXTURE_4K}" ]; then
    echo "✓ Using existing 4K texture: ${NPC_TEXTURE_4K}"
else
    echo "📐 Creating 4K texture (4096x4096)..."
python extract_npc_logo.py \
    --artwork-image "${PROJECT_ROOT}/arwork.jpg" \
        --output "${NPC_TEXTURE_4K}" \
        --size 4096

    if [ ! -f "${NPC_TEXTURE_4K}" ]; then
        echo "❌ Error: NPC logo 4K extraction failed!"
    exit 1
fi
    echo "✓ NPC logo 4K texture created: ${NPC_TEXTURE_4K}"
fi
deactivate

# Step 8: Apply NPC texture and combine with avatar for ALL sizes using Blender (xatlas UV mapping)
echo ""
echo "🎨 Step 8: Applying NPC texture and combining with avatar for ALL sizes (Blender + xatlas)..."
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
if [ ! -f "${BLENDER}" ]; then
    echo "⚠️  Blender not found at ${BLENDER}"
    echo "   Please set BLENDER environment variable or install Blender"
    exit 1
fi

# Use texture_map_all_sizes.py to process all sizes at once
source venv310/bin/activate
python texture_map_all_sizes.py \
    --garment-dir "${TSHIRT_DIR}" \
    --body "${OUTPUT_DIR}/body_person0_neutral_textured.obj" \
    --texture "${PROJECT_ROOT}/output/npc_texture_4k.png" \
    --output-dir "${PROJECT_ROOT}/output/avatar_all_sizes"
deactivate

FINAL_AVATAR_DIR="${PROJECT_ROOT}/output/avatar_all_sizes"
if [ ! -d "${FINAL_AVATAR_DIR}" ] || [ -z "$(ls -A ${FINAL_AVATAR_DIR}/*.glb 2>/dev/null)" ]; then
    echo "❌ Error: Blender texture mapping/export failed!"
    exit 1
fi

echo "✓ Combined avatars GLB for all sizes in: ${FINAL_AVATAR_DIR}"
for size in xs s m l xl; do
    if [ -f "${FINAL_AVATAR_DIR}/avatar_with_tshirt_${size}.glb" ]; then
        echo "   ✓ ${size}: avatar_with_tshirt_${size}.glb"
    fi
done

echo ""
echo "============================================================"
echo "✅ PIPELINE COMPLETE!"
echo "============================================================"
echo ""
echo "📁 Output files:"
echo "   Body (A-pose):          ${OUTPUT_DIR}/body_person0_neutral.obj"
echo "   Body (textured):        ${OUTPUT_DIR}/body_person0_neutral_textured.obj"
echo "   T-shirts (all sizes):   ${TSHIRT_DIR}/"
echo "   Heatmaps (all sizes):   ${HEATMAP_OUTPUT_DIR}/"
echo "   Heatmap GLBs (all sizes): ${HEATMAP_GLB_DIR}/"
echo "   NPC logo texture 4K:    ${NPC_TEXTURE_4K}"
echo "   FINAL GLBs (all sizes):  ${FINAL_AVATAR_DIR}/"
echo ""
echo "   Generated files:"
for size in xs s m l xl; do
    if [ -f "${FINAL_AVATAR_DIR}/avatar_with_tshirt_${size}.glb" ]; then
        echo "      ✓ avatar_with_tshirt_${size}.glb"
    fi
    if [ -f "${HEATMAP_GLB_DIR}/avatar_${size}_heatmap.glb" ]; then
        echo "      ✓ avatar_${size}_heatmap.glb (heatmap)"
    fi
done
echo ""

