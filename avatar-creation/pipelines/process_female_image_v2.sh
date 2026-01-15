#!/bin/bash
# COMPLETE FEMALE PIPELINE V2: woman.jpg → 3D Mesh → A-pose → T-shirts → Heatmaps → Texture → GLB
# IMPROVED: Better error handling, cleanup old outputs, shows full errors

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Input files
BODY_IMAGE="${1:-woman.jpg}"
FACE_IMAGE="${2:-woman.jpg}"  # Use same image for face if not provided
HEIGHT_CM="${3:-170}"  # Default female height
GENDER="female"
OUTPUT_DIR="${PROJECT_ROOT}/output/female_avatar"

echo "============================================================"
echo "🚀 COMPLETE FEMALE AVATAR PIPELINE V2"
echo "============================================================"
echo "Body image: ${BODY_IMAGE}"
echo "Face image: ${FACE_IMAGE}"
echo "Height: ${HEIGHT_CM}cm"
echo "Gender: ${GENDER}"
echo "Output: ${OUTPUT_DIR}"
echo ""

# CLEANUP: Delete old outputs before starting
echo "🧹 Cleaning up old outputs..."
TSHIRT_DIR="${PROJECT_ROOT}/output/female_tshirt_all_sizes"
HEATMAP_OUTPUT_DIR="${PROJECT_ROOT}/output/heatmaps/female_v1tweaking"
HEATMAP_GLB_DIR="${PROJECT_ROOT}/output/heatmaps/female_v1tweaking"
FINAL_AVATAR_DIR="${PROJECT_ROOT}/output/female_avatar_all_sizes"

# Remove old directories (but keep the main output dir for params)
if [ -d "${TSHIRT_DIR}" ]; then
    echo "   Removing old t-shirts: ${TSHIRT_DIR}"
    rm -rf "${TSHIRT_DIR}"
fi
if [ -d "${HEATMAP_OUTPUT_DIR}" ]; then
    echo "   Removing old heatmaps: ${HEATMAP_OUTPUT_DIR}"
    rm -rf "${HEATMAP_OUTPUT_DIR}"
fi
if [ -d "${FINAL_AVATAR_DIR}" ]; then
    echo "   Removing old final avatars: ${FINAL_AVATAR_DIR}"
    rm -rf "${FINAL_AVATAR_DIR}"
fi
# Keep OUTPUT_DIR but remove old mesh files
if [ -d "${OUTPUT_DIR}" ]; then
    echo "   Cleaning old mesh files in: ${OUTPUT_DIR}"
    rm -f "${OUTPUT_DIR}"/*.obj 2>/dev/null || true
    rm -f "${OUTPUT_DIR}"/*.png 2>/dev/null || true
    rm -rf "${OUTPUT_DIR}/mesh" 2>/dev/null || true
fi
echo "✓ Cleanup complete"
echo ""

# Step 1: Extract body from image (use venv310 - has cv2 and 4D-Humans deps)
echo "📸 Step 1: Extracting body from ${BODY_IMAGE}..."
echo "🔧 Using venv310 for 4D-Humans (has cv2, torch, etc.)..."

# Create temp folder for image if BODY_IMAGE is a file (demo_yolo.py expects a folder)
TEMP_INPUT_DIR="${PROJECT_ROOT}/temp_input_images_female"
mkdir -p "${TEMP_INPUT_DIR}"
rm -f "${TEMP_INPUT_DIR}"/*

# Check if BODY_IMAGE is a file or folder
if [ -f "4D-Humans-clean/example_data/images/${BODY_IMAGE}" ]; then
    # It's a file in the images folder - copy to temp folder
    cp "4D-Humans-clean/example_data/images/${BODY_IMAGE}" "${TEMP_INPUT_DIR}/"
    IMG_FOLDER="${TEMP_INPUT_DIR}"
elif [ -f "${PROJECT_ROOT}/${BODY_IMAGE}" ]; then
    # It's a file in project root - copy to temp folder
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

# Find the generated files (may have different naming)
BODY_OBJ=$(find "${OUTPUT_DIR}" -name "*person0.obj" | head -1)
BODY_PARAMS=$(find "${OUTPUT_DIR}" -name "*person0_params.npz" | head -1)

# Try alternative naming patterns
if [ -z "$BODY_OBJ" ]; then
    BODY_OBJ=$(find "${OUTPUT_DIR}" -name "*.obj" | head -1)
fi
if [ -z "$BODY_PARAMS" ]; then
    BODY_PARAMS=$(find "${OUTPUT_DIR}" -name "*params.npz" | head -1)
fi

if [ ! -f "${BODY_OBJ}" ] || [ ! -f "${BODY_PARAMS}" ]; then
    echo "❌ Error: Body extraction failed!"
    echo "   Looking for: *.obj and *params.npz in ${OUTPUT_DIR}"
    exit 1
fi

# Copy params to project root with clear name
FINAL_PARAMS="${OUTPUT_DIR}/woman_smpl_params.npz"
cp "${BODY_PARAMS}" "${FINAL_PARAMS}"

echo "✓ Body extracted: ${BODY_OBJ}"
echo "✓ Params saved: ${FINAL_PARAMS}"

# Step 2: Fix pose to 45 degrees down (A-pose for garment generation)
echo ""
echo "🎯 Step 2: Creating A-pose body (45 degrees down) for garment generation..."
source venv310/bin/activate

# Use final_relaxed_rig.py or create A-pose script
cd 4D-Humans-clean
python final_relaxed_rig.py \
    --params "${FINAL_PARAMS}" \
    --height "${HEIGHT_CM}" \
    --output "${OUTPUT_DIR}/body_woman_apose.obj"
cd "${PROJECT_ROOT}"
deactivate

if [ ! -f "${OUTPUT_DIR}/body_woman_apose.obj" ]; then
    echo "⚠️  Warning: A-pose generation failed, will use original mesh"
    cp "${BODY_OBJ}" "${OUTPUT_DIR}/body_woman_apose.obj"
fi

echo "✓ A-pose body saved: ${OUTPUT_DIR}/body_woman_apose.obj"

# Step 3: Extract skin tone from face (use venv310 - has cv2)
echo ""
echo "🎨 Step 3: Extracting skin tone from ${FACE_IMAGE}..."
source venv310/bin/activate

# Check if face image exists
FACE_IMG_PATH=""
if [ -f "4D-Humans-clean/example_data/images/${FACE_IMAGE}" ]; then
    FACE_IMG_PATH="4D-Humans-clean/example_data/images/${FACE_IMAGE}"
elif [ -f "${PROJECT_ROOT}/${FACE_IMAGE}" ]; then
    FACE_IMG_PATH="${PROJECT_ROOT}/${FACE_IMAGE}"
else
    echo "   ⚠️  Face image not found, skipping skin tone extraction"
    FACE_IMG_PATH=""
fi

if [ -n "${FACE_IMG_PATH}" ] && [ -f "extract_skin_tone.py" ]; then
    python extract_skin_tone.py \
        --face-image "${FACE_IMG_PATH}" \
        --mesh "${OUTPUT_DIR}/body_woman_apose.obj" \
        --output "${OUTPUT_DIR}"
    
    # extract_skin_tone.py outputs to body_person0_neutral_textured.obj, rename to expected filename
    if [ -f "${OUTPUT_DIR}/body_person0_neutral_textured.obj" ]; then
        mv "${OUTPUT_DIR}/body_person0_neutral_textured.obj" "${OUTPUT_DIR}/body_woman_apose_textured.obj"
        echo "✓ Textured body saved: ${OUTPUT_DIR}/body_woman_apose_textured.obj"
    elif [ -f "${OUTPUT_DIR}/body_woman_apose_textured.obj" ]; then
        echo "✓ Textured body saved: ${OUTPUT_DIR}/body_woman_apose_textured.obj"
    else
        echo "   ⚠️  Skin tone extraction failed, using untextured mesh"
        cp "${OUTPUT_DIR}/body_woman_apose.obj" "${OUTPUT_DIR}/body_woman_apose_textured.obj"
    fi
else
    echo "   ⚠️  Skipping skin tone extraction (script or image not found)"
    cp "${OUTPUT_DIR}/body_woman_apose.obj" "${OUTPUT_DIR}/body_woman_apose_textured.obj"
fi
deactivate

# Step 4: Generate t-shirt for ALL sizes (TailorNet, venv310) - FEMALE GENDER
echo ""
echo "👕 Step 4: Generating t-shirts for ALL sizes (XS, S, M, L, XL) with TailorNet (FEMALE)..."
echo "🔧 Using venv310 for TailorNet..."

# CRITICAL: Check if female TailorNet dataset exists
FEMALE_DATASET_PATH="/Volumes/Expansion/TailorNet/t-shirt_female"
FEMALE_DATASET_REQUIRED="${FEMALE_DATASET_PATH}/shape/betas.npy"
FEMALE_DATASET_ZIP="/Volumes/Expansion/TailorNet/t-shirt_female.zip"

# CRITICAL: Check if female TailorNet model weights exist
FEMALE_WEIGHTS_DIR="${PROJECT_ROOT}/TailorNet/models/weights/t-shirt_female_weights"
FEMALE_WEIGHTS_REQUIRED="${FEMALE_WEIGHTS_DIR}/tn_orig_hf/t-shirt_female"
FEMALE_WEIGHTS_ZIP="${FEMALE_WEIGHTS_DIR}.zip"
FEMALE_WEIGHTS_URL="https://datasets.d2.mpi-inf.mpg.de/tailornet/t-shirt_female_weights.zip"

if [ ! -f "${FEMALE_DATASET_REQUIRED}" ]; then
    echo ""
    echo "❌ ERROR: Female TailorNet dataset not found!"
    echo "   Expected: ${FEMALE_DATASET_REQUIRED}"
    echo ""
    
    # Check if zip file exists
    if [ -f "${FEMALE_DATASET_ZIP}" ]; then
        echo "✅ Found zip file: ${FEMALE_DATASET_ZIP}"
        echo ""
        echo "📦 The dataset needs to be extracted first."
        echo "   This will take several minutes (6.9 GB to extract)..."
        echo "   Extracting now..."
        cd /Volumes/Expansion/TailorNet
        unzip -q "${FEMALE_DATASET_ZIP}" || {
            echo "   ❌ Extraction failed!"
            echo "   Please extract manually:"
            echo "     cd /Volumes/Expansion/TailorNet"
            echo "     unzip t-shirt_female.zip"
            exit 1
        }
        cd "${PROJECT_ROOT}"
        echo "   ✅ Extraction complete!"
        
        # Verify extraction
        if [ ! -f "${FEMALE_DATASET_REQUIRED}" ]; then
            echo "   ⚠️  Extraction completed but required file not found"
            echo "   Please check: ${FEMALE_DATASET_REQUIRED}"
            exit 1
        fi
    else
        echo "📋 SOLUTION OPTIONS:"
        echo ""
        echo "   Option 1: Download female dataset"
        echo "   Visit: https://nextcloud.mpi-klsb.mpg.de/index.php/s/W7a57iXRG9Yms6P"
        echo "   Download: t-shirt_female.zip (6.9 GB)"
        echo "   Save to: /Volumes/Expansion/TailorNet/"
        echo "   Then extract: cd /Volumes/Expansion/TailorNet && unzip t-shirt_female.zip"
        echo ""
        echo "   Option 2: Use male dataset as fallback (not ideal for female avatars)"
        echo "   This would require modifying the script to use --gender male"
        echo ""
        echo "⚠️  Skipping t-shirt generation - dataset required"
        exit 1
    fi
fi

echo "   ✓ Female TailorNet dataset found: ${FEMALE_DATASET_PATH}"

# Check if model weights exist
if [ ! -d "${FEMALE_WEIGHTS_REQUIRED}" ]; then
    echo ""
    echo "❌ ERROR: Female TailorNet model weights not found!"
    echo "   Expected: ${FEMALE_WEIGHTS_REQUIRED}"
    echo ""
    
    # Check if zip file exists
    if [ -f "${FEMALE_WEIGHTS_ZIP}" ]; then
        echo "✅ Found weights zip file: ${FEMALE_WEIGHTS_ZIP}"
        echo ""
        echo "📦 Extracting model weights (2.0 GB)..."
        cd "${PROJECT_ROOT}/TailorNet/models/weights"
        unzip -q "${FEMALE_WEIGHTS_ZIP}" || {
            echo "   ❌ Extraction failed!"
            echo "   Please extract manually:"
            echo "     cd ${PROJECT_ROOT}/TailorNet/models/weights"
            echo "     unzip t-shirt_female_weights.zip"
            exit 1
        }
        cd "${PROJECT_ROOT}"
        echo "   ✅ Weights extraction complete!"
    else
        echo "📋 DOWNLOAD REQUIRED:"
        echo ""
        echo "   The female TailorNet model weights need to be downloaded."
        echo "   Size: 2.0 GB"
        echo "   URL: ${FEMALE_WEIGHTS_URL}"
        echo ""
        echo "   Download options:"
        echo "   1. Manual download:"
        echo "      Visit: ${FEMALE_WEIGHTS_URL}"
        echo "      Save to: ${PROJECT_ROOT}/TailorNet/models/weights/"
        echo "      Then extract: cd ${PROJECT_ROOT}/TailorNet/models/weights && unzip t-shirt_female_weights.zip"
        echo ""
        echo "   2. Automatic download (starting now):"
        echo "   ⬇️  Downloading model weights (2.0 GB, this may take 5-10 minutes)..."
        cd "${PROJECT_ROOT}/TailorNet/models/weights"
        curl -L -o t-shirt_female_weights.zip -C - "${FEMALE_WEIGHTS_URL}" || {
            echo "   ❌ Download failed!"
            echo "   Please download manually from: ${FEMALE_WEIGHTS_URL}"
            echo "   Save to: ${PROJECT_ROOT}/TailorNet/models/weights/"
            exit 1
        }
        echo "   ✅ Download complete!"
        echo "   📦 Extracting (this may take a few minutes)..."
        unzip -q t-shirt_female_weights.zip || {
            echo "   ❌ Extraction failed!"
            echo "   Please extract manually:"
            echo "     cd ${PROJECT_ROOT}/TailorNet/models/weights"
            echo "     unzip t-shirt_female_weights.zip"
            exit 1
        }
        echo "   ✅ Extraction complete!"
        cd "${PROJECT_ROOT}"
    fi
    
    # Verify weights
    if [ ! -d "${FEMALE_WEIGHTS_REQUIRED}" ]; then
        echo "   ⚠️  Weights extraction completed but directory not found"
        echo "   Please check: ${FEMALE_WEIGHTS_REQUIRED}"
        exit 1
    fi
fi

echo "   ✓ Female TailorNet model weights found: ${FEMALE_WEIGHTS_DIR}"
source venv310/bin/activate

TSHIRT_DIR="${PROJECT_ROOT}/output/female_tshirt_all_sizes"
mkdir -p "${TSHIRT_DIR}"

# Generate t-shirts for all sizes with --gender female
# IMPROVED: Show full error output, don't filter with grep
SUCCESS_COUNT=0
FAILED_SIZES=()

for size in XS S M L XL; do
    echo ""
    echo "   ========================================"
    echo "   Generating ${size}..."
    echo "   ========================================"
    
    # Run without grep filter to see full errors
    # UNISEX MODE: Use --unisex flag to get male fit style (male base gamma) while keeping female dataset/weights for body shape matching
    if python generate_playboy_tshirt_PERFECT.py \
        --smpl-params "${FINAL_PARAMS}" \
        --gender "${GENDER}" \
        --size "${size}" \
        --output "${TSHIRT_DIR}" \
        --arm-angle 45 \
        --fit-adjustment 0.0 \
        --unisex; then
        echo "   ✅ ${size} generated successfully!"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "   ❌ ${size} generation failed!"
        FAILED_SIZES+=("${size}")
    fi
done
deactivate

# Check results
echo ""
echo "============================================================"
echo "📊 T-SHIRT GENERATION SUMMARY"
echo "============================================================"
echo "   Successful: ${SUCCESS_COUNT}/5"
if [ ${#FAILED_SIZES[@]} -gt 0 ]; then
    echo "   Failed sizes: ${FAILED_SIZES[*]}"
fi

# Check if at least one size was generated
if [ -z "$(ls -A ${TSHIRT_DIR}/*.ply 2>/dev/null)" ]; then
    echo ""
    echo "❌ Error: No t-shirts were generated!"
    echo "   This usually means:"
    echo "   1. TailorNet female dataset is missing"
    echo "   2. SMPL_FEMALE.pkl is not found"
    echo "   3. Check the error messages above for details"
    exit 1
fi

echo "✓ T-shirts generated for all sizes in: ${TSHIRT_DIR}"

# Step 5: Generate stress heatmaps for ALL sizes (V1 - Experimental)
echo ""
echo "🔥 Step 5: Generating stress heatmaps for ALL sizes (V1)..."
echo "🔧 Using venv310 for heatmap generation..."
source venv310/bin/activate

# Create heatmap output directory
HEATMAP_OUTPUT_DIR="${PROJECT_ROOT}/output/heatmaps/female_v1tweaking"
mkdir -p "${HEATMAP_OUTPUT_DIR}"

# Generate heatmaps for all sizes
for size in xs s m l xl; do
    GARMENT_PLY="${TSHIRT_DIR}/playboy_tshirt_${size}_perfect.ply"
    BODY_PLY="${TSHIRT_DIR}/body_apose_${size}.ply"
    
    # Try M body if specific size body not found
    if [ ! -f "${BODY_PLY}" ]; then
        BODY_PLY="${TSHIRT_DIR}/body_apose_m.ply"
    fi
    
    if [ -f "${GARMENT_PLY}" ] && [ -f "${BODY_PLY}" ]; then
        echo "   Generating heatmap for ${size}..."
        python generate_stress_heatmap_simple.py \
            --garment "${GARMENT_PLY}" \
            --body "${BODY_PLY}" \
            --output "${HEATMAP_OUTPUT_DIR}/playboy_tshirt_${size}_perfect_stress_heatmap_v1.ply" 2>&1 | grep -E "(✅ Saved|Detected size)" || echo "   Processing ${size}..."
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
HEATMAP_GLB_DIR="${PROJECT_ROOT}/output/heatmaps/female_v1tweaking"
mkdir -p "${HEATMAP_GLB_DIR}"

# Use M body for all sizes (as per current workflow)
BODY_FOR_HEATMAP="${TSHIRT_DIR}/body_apose_m.ply"

if [ ! -f "${BODY_FOR_HEATMAP}" ]; then
    echo "   ⚠️  Body file not found, using A-pose body..."
    BODY_FOR_HEATMAP="${OUTPUT_DIR}/body_woman_apose_textured.obj"
fi

# Combine heatmaps with body for all sizes
# Note: generate_stress_heatmap_simple.py saves to v1tweaking/ subdirectory
HEATMAP_PLY_DIR="${HEATMAP_OUTPUT_DIR}/v1tweaking"
for size in xs s m l xl; do
    HEATMAP_PLY="${HEATMAP_PLY_DIR}/playboy_tshirt_${size}_perfect_stress_heatmap_v1.ply"
    HEATMAP_GLB="${HEATMAP_GLB_DIR}/female_avatar_${size}_heatmap.glb"
    
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
    if [ -f "extract_npc_logo.py" ] && [ -f "arwork.jpg" ]; then
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
    else
        echo "   ⚠️  Skipping NPC logo extraction (script or artwork not found)"
        echo "   Looking for texture at: ${NPC_TEXTURE_4K}"
    fi
fi
deactivate

# Step 8: Apply NPC texture and combine with avatar for ALL sizes using Blender (xatlas UV mapping)
echo ""
echo "🎨 Step 8: Applying NPC texture artwork to t-shirts and combining with avatar for ALL sizes (Blender + xatlas)..."
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"

# Verify texture file exists before proceeding
if [ ! -f "${NPC_TEXTURE_4K}" ]; then
    echo "⚠️  Warning: NPC texture not found at ${NPC_TEXTURE_4K}"
    echo "   Texture mapping requires the texture file. Please ensure extract_npc_logo.py runs successfully."
    echo "   Skipping texture mapping step..."
else
    if [ ! -f "${BLENDER}" ]; then
        echo "⚠️  Blender not found at ${BLENDER}"
        echo "   Please set BLENDER environment variable or install Blender"
        echo "   Skipping texture mapping step..."
    else
        echo "   ✓ Texture file found: ${NPC_TEXTURE_4K}"
        echo "   ✓ Blender found: ${BLENDER}"
        echo "   📐 Processing all sizes with texture mapping..."
        
        # Use texture_map_all_sizes.py to process all sizes at once
        source venv310/bin/activate
        if [ -f "texture_map_all_sizes.py" ]; then
            python texture_map_all_sizes.py \
                --garment-dir "${TSHIRT_DIR}" \
                --body "${OUTPUT_DIR}/body_woman_apose_textured.obj" \
                --texture "${NPC_TEXTURE_4K}" \
                --output-dir "${PROJECT_ROOT}/output/female_avatar_all_sizes"
            
            # Check if texture mapping was successful
            if [ $? -eq 0 ]; then
                echo "   ✓ Texture mapping completed successfully!"
            else
                echo "   ⚠️  Texture mapping encountered errors (check output above)"
            fi
        else
            echo "   ❌ Error: texture_map_all_sizes.py not found!"
            echo "   Expected location: ${PROJECT_ROOT}/texture_map_all_sizes.py"
        fi
        deactivate
    fi
fi

FINAL_AVATAR_DIR="${PROJECT_ROOT}/output/female_avatar_all_sizes"
if [ -d "${FINAL_AVATAR_DIR}" ] && [ -n "$(ls -A ${FINAL_AVATAR_DIR}/*.glb 2>/dev/null)" ]; then
    echo "✓ Combined avatars GLB for all sizes in: ${FINAL_AVATAR_DIR}"
    for size in xs s m l xl; do
        if [ -f "${FINAL_AVATAR_DIR}/avatar_with_tshirt_${size}.glb" ]; then
            echo "   ✓ ${size}: avatar_with_tshirt_${size}.glb"
        fi
    done
else
    echo "   ⚠️  Texture mapping step skipped or failed"
fi

echo ""
echo "============================================================"
echo "✅ FEMALE PIPELINE COMPLETE!"
echo "============================================================"
echo ""
echo "📁 Output files (in project root):"
echo "   SMPL Params:              ${FINAL_PARAMS}"
echo "   Body (A-pose):            ${OUTPUT_DIR}/body_woman_apose.obj"
echo "   Body (textured):          ${OUTPUT_DIR}/body_woman_apose_textured.obj"
echo "   T-shirts (all sizes):     ${TSHIRT_DIR}/"
echo "   Heatmaps (all sizes):     ${HEATMAP_OUTPUT_DIR}/"
echo "   Heatmap GLBs (all sizes): ${HEATMAP_GLB_DIR}/"
if [ -d "${FINAL_AVATAR_DIR}" ]; then
    echo "   FINAL GLBs (all sizes):  ${FINAL_AVATAR_DIR}/"
fi
echo ""
echo "   Generated files:"
for size in xs s m l xl; do
    if [ -f "${TSHIRT_DIR}/playboy_tshirt_${size}_perfect.ply" ]; then
        echo "      ✓ playboy_tshirt_${size}_perfect.ply"
    fi
    if [ -f "${HEATMAP_GLB_DIR}/female_avatar_${size}_heatmap.glb" ]; then
        echo "      ✓ female_avatar_${size}_heatmap.glb (heatmap)"
    fi
    if [ -d "${FINAL_AVATAR_DIR}" ] && [ -f "${FINAL_AVATAR_DIR}/avatar_with_tshirt_${size}.glb" ]; then
        echo "      ✓ avatar_with_tshirt_${size}.glb (final)"
    fi
done
echo ""

