#!/bin/bash
# 4D-Humans Pipeline Only: Body Extraction → Pose Fix → Skin Texture
# This tests the 4D-Humans part before TailorNet

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Initialize conda
CONDA_BASE=$(conda info --base 2>/dev/null || echo "/Users/revandaldaban/miniconda3")
source "${CONDA_BASE}/etc/profile.d/conda.sh"

# Input files
BODY_IMAGE="${1:-body.jpg}"
FACE_IMAGE="${2:-face.jpg}"
OUTPUT_DIR="${PROJECT_ROOT}/output/your_body"

echo "============================================================"
echo "🚀 4D-HUMANS PIPELINE (Body Extraction → Pose → Skin Texture)"
echo "============================================================"
echo "Body image: ${BODY_IMAGE}"
echo "Face image: ${FACE_IMAGE}"
echo "Output: ${OUTPUT_DIR}"
echo ""

# Step 1: Extract body from image
echo "📸 Step 1: Extracting body from ${BODY_IMAGE}..."
echo "🔧 Using conda environment '4D-humans'..."
conda activate 4D-humans
mkdir -p "${OUTPUT_DIR}"

# Don't clean old outputs - keep all files
# echo "🧹 Cleaning old outputs..."
# rm -f "${OUTPUT_DIR}"/body_person0*.obj "${OUTPUT_DIR}"/body_person0*.npz "${OUTPUT_DIR}"/*.png 2>/dev/null || true

# Handle single image file vs folder
if [ -f "${PROJECT_ROOT}/${BODY_IMAGE}" ]; then
    # Single file - create temp folder with the image
    TEMP_IMG_DIR=$(mktemp -d)
    cp "${PROJECT_ROOT}/${BODY_IMAGE}" "${TEMP_IMG_DIR}/"
    IMG_FOLDER="${TEMP_IMG_DIR}"
else
    # Already a folder
    IMG_FOLDER="${PROJECT_ROOT}/${BODY_IMAGE}"
fi

cd 4D-Humans-clean
python demo_yolo.py \
    --img_folder "${IMG_FOLDER}" \
    --out_folder "${OUTPUT_DIR}" \
    --batch_size 1
cd "${PROJECT_ROOT}"

# Clean up temp folder if created
if [ -d "${TEMP_IMG_DIR}" ]; then
    rm -rf "${TEMP_IMG_DIR}"
fi

# Find the generated files
BODY_OBJ=$(find "${OUTPUT_DIR}" -name "body_person0.obj" | head -1)
BODY_PARAMS=$(find "${OUTPUT_DIR}" -name "body_person0_params.npz" | head -1)

if [ ! -f "${BODY_OBJ}" ] || [ ! -f "${BODY_PARAMS}" ]; then
    echo "❌ Error: Body extraction failed!"
    conda deactivate
    exit 1
fi

echo "✓ Body extracted: ${BODY_OBJ}"
echo "✓ Params saved: ${BODY_PARAMS}"

# Step 2: Fix pose to A-pose
echo ""
echo "🎯 Step 2: Fixing pose to A-pose..."
python fix_pose_neutral.py \
    --params "${BODY_PARAMS}" \
    --output "${OUTPUT_DIR}/body_person0_neutral.obj"

if [ ! -f "${OUTPUT_DIR}/body_person0_neutral.obj" ]; then
    echo "❌ Error: Pose fixing failed!"
    conda deactivate
    exit 1
fi

echo "✓ A-pose body saved: ${OUTPUT_DIR}/body_person0_neutral.obj"

# Step 3: Extract skin tone from face
echo ""
echo "🎨 Step 3: Extracting skin tone from ${FACE_IMAGE}..."
python extract_skin_tone.py \
    --face-image "${PROJECT_ROOT}/${FACE_IMAGE}" \
    --mesh "${OUTPUT_DIR}/body_person0_neutral.obj" \
    --output "${OUTPUT_DIR}"

if [ ! -f "${OUTPUT_DIR}/body_person0_neutral_textured.obj" ]; then
    echo "❌ Error: Skin tone extraction failed!"
    conda deactivate
    exit 1
fi

conda deactivate

echo ""
echo "============================================================"
echo "✅ 4D-HUMANS PIPELINE COMPLETE!"
echo "============================================================"
echo ""
echo "📁 Output files in ${OUTPUT_DIR}:"
echo "   ✓ body_person0.obj (original extracted body)"
echo "   ✓ body_person0_params.npz (SMPL parameters)"
echo "   ✓ body_person0_neutral.obj (A-pose body)"
echo "   ✓ body_person0_neutral_textured.obj (A-pose with skin texture)"
echo "   ✓ skin_texture.png (extracted skin tone)"
echo "   ✓ skin_detection_mask.png (skin detection visualization)"
echo ""
echo "🎯 Next: Run TailorNet to generate t-shirt on this body"
echo ""

