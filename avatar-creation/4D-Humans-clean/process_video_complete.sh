#!/bin/bash
# Complete Video Processing Pipeline
# Extracts frames → Generates 3D meshes → Extracts measurements

set -e  # Exit on error

# Default values
VIDEO=""
OUTPUT_DIR="video_output"
FRAME_INTERVAL=30
MAX_FRAMES=10
HEIGHT=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 --video VIDEO_FILE [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --video FILE          Input video file (required)"
    echo "  --output DIR          Output directory (default: video_output)"
    echo "  --interval N          Extract every Nth frame (default: 30)"
    echo "  --max-frames N        Maximum frames to process (default: 10)"
    echo "  --height CM           Height in cm for measurement calibration (optional)"
    echo ""
    echo "Example:"
    echo "  $0 --video gymnasts.mp4 --height 165 --max-frames 5"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --video)
            VIDEO="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --interval)
            FRAME_INTERVAL="$2"
            shift 2
            ;;
        --max-frames)
            MAX_FRAMES="$2"
            shift 2
            ;;
        --height)
            HEIGHT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Validate
if [ -z "$VIDEO" ]; then
    echo -e "${RED}Error: --video is required${NC}"
    usage
fi

if [ ! -f "$VIDEO" ]; then
    echo -e "${RED}Error: Video file not found: $VIDEO${NC}"
    exit 1
fi

# Setup directories
FRAMES_DIR="${OUTPUT_DIR}/frames"
MESHES_DIR="${OUTPUT_DIR}/meshes"
MEASUREMENTS_DIR="${OUTPUT_DIR}/measurements"

mkdir -p "$FRAMES_DIR" "$MESHES_DIR" "$MEASUREMENTS_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        VIDEO TO 3D MESH PROCESSING PIPELINE                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Video: $VIDEO"
echo "  Output: $OUTPUT_DIR"
echo "  Frame interval: $FRAME_INTERVAL"
echo "  Max frames: $MAX_FRAMES"
if [ -n "$HEIGHT" ]; then
    echo "  Height calibration: ${HEIGHT}cm"
else
    echo "  Height calibration: Not provided (measurements will be uncalibrated)"
fi
echo ""

# Step 1: Extract frames
echo -e "${GREEN}[Step 1/3] Extracting frames from video...${NC}"
ffmpeg -i "$VIDEO" \
    -vf "select='not(mod(n\,${FRAME_INTERVAL}))'" \
    -vsync vfr \
    -frames:v "$MAX_FRAMES" \
    -q:v 2 \
    "${FRAMES_DIR}/frame_%04d.jpg" \
    -y \
    -loglevel warning \
    -stats

FRAME_COUNT=$(ls -1 "${FRAMES_DIR}"/*.jpg 2>/dev/null | wc -l)
echo -e "${GREEN}✓ Extracted $FRAME_COUNT frames${NC}"
echo ""

if [ "$FRAME_COUNT" -eq 0 ]; then
    echo -e "${RED}Error: No frames extracted${NC}"
    exit 1
fi

# Step 2: Generate 3D meshes
echo -e "${GREEN}[Step 2/3] Generating 3D meshes with HMR2 + YOLO...${NC}"
python demo_yolo.py \
    --img_folder "$FRAMES_DIR" \
    --out_folder "$MESHES_DIR" \
    --batch_size=1

MESH_COUNT=$(ls -1 "${MESHES_DIR}"/*.obj 2>/dev/null | wc -l)
echo ""
echo -e "${GREEN}✓ Generated $MESH_COUNT 3D meshes${NC}"
echo ""

if [ "$MESH_COUNT" -eq 0 ]; then
    echo -e "${RED}Error: No meshes generated${NC}"
    exit 1
fi

# Step 3: Extract measurements
echo -e "${GREEN}[Step 3/3] Extracting body measurements...${NC}"

if [ -n "$HEIGHT" ]; then
    # With height calibration
    for mesh in "${MESHES_DIR}"/*.obj; do
        basename=$(basename "$mesh" .obj)
        output_json="${MEASUREMENTS_DIR}/${basename}_measurements.json"
        
        echo "  Processing: $basename"
        python extract_accurate_measurements.py \
            --mesh "$mesh" \
            --height "$HEIGHT" \
            --output "$output_json" \
            > /dev/null 2>&1
        
        echo "    ✓ Saved: $output_json"
    done
    
    echo ""
    echo -e "${GREEN}✓ Extracted measurements (calibrated to ${HEIGHT}cm)${NC}"
else
    # Without height calibration - show warning
    echo ""
    echo -e "${YELLOW}⚠️  Warning: No height provided${NC}"
    echo -e "${YELLOW}   Measurements will NOT be accurate!${NC}"
    echo ""
    echo "  To get accurate measurements, rerun with --height:"
    echo "  $0 --video $VIDEO --output $OUTPUT_DIR --height [HEIGHT_IN_CM]"
    echo ""
    echo "  Skipping measurement extraction..."
fi

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    PROCESSING COMPLETE!                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Output Summary:${NC}"
echo "  📹 Frames:       ${FRAMES_DIR}/ ($FRAME_COUNT files)"
echo "  🧍 Meshes:       ${MESHES_DIR}/ ($MESH_COUNT files)"
if [ -n "$HEIGHT" ]; then
    MEASUREMENT_COUNT=$(ls -1 "${MEASUREMENTS_DIR}"/*.json 2>/dev/null | wc -l)
    echo "  📏 Measurements: ${MEASUREMENTS_DIR}/ ($MEASUREMENT_COUNT files)"
fi
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. View meshes in Blender:"
echo "     open -a Blender ${MESHES_DIR}/*.obj"
echo ""
if [ -n "$HEIGHT" ]; then
    echo "  2. Check measurements:"
    echo "     cat ${MEASUREMENTS_DIR}/*.json"
else
    echo "  2. Extract measurements (requires height):"
    echo "     python extract_accurate_measurements.py --mesh ${MESHES_DIR}/[MESH].obj --height [HEIGHT_CM]"
fi
echo ""
echo -e "${GREEN}Done! 🎉${NC}"


