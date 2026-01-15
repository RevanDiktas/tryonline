#!/bin/bash
# TryOn MVP Avatar Pipeline - Shell Wrapper
# ==========================================
#
# Usage:
#   ./run_pipeline.sh <body_image> <height_cm> <gender> [output_dir]
#
# Example:
#   ./run_pipeline.sh body.jpg 175 male ./output/my_avatar
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Input arguments
BODY_IMAGE="${1:-}"
HEIGHT_CM="${2:-175}"
GENDER="${3:-neutral}"
OUTPUT_DIR="${4:-${PROJECT_ROOT}/output/avatar}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "TRYON MVP AVATAR PIPELINE"
echo "============================================================"
echo ""

# Validate arguments
if [ -z "$BODY_IMAGE" ]; then
    echo -e "${RED}Error: Body image path required${NC}"
    echo ""
    echo "Usage: $0 <body_image> <height_cm> <gender> [output_dir]"
    echo ""
    echo "Example:"
    echo "  $0 body.jpg 175 male ./output/my_avatar"
    exit 1
fi

# Check if image exists
if [ ! -f "$BODY_IMAGE" ]; then
    # Try relative to project root
    if [ -f "${PROJECT_ROOT}/${BODY_IMAGE}" ]; then
        BODY_IMAGE="${PROJECT_ROOT}/${BODY_IMAGE}"
    else
        echo -e "${RED}Error: Image not found: ${BODY_IMAGE}${NC}"
        exit 1
    fi
fi

echo "Configuration:"
echo "  Body Image: ${BODY_IMAGE}"
echo "  Height: ${HEIGHT_CM} cm"
echo "  Gender: ${GENDER}"
echo "  Output: ${OUTPUT_DIR}"
echo ""

# Check for Python environment
if [ -d "${PROJECT_ROOT}/venv310" ] && [ -f "${PROJECT_ROOT}/venv310/bin/activate" ]; then
    echo -e "${GREEN}Using venv310 environment${NC}"
    source "${PROJECT_ROOT}/venv310/bin/activate"
elif command -v conda &> /dev/null; then
    # Try conda
    CONDA_BASE=$(conda info --base 2>/dev/null || echo "")
    if [ -n "$CONDA_BASE" ]; then
        source "${CONDA_BASE}/etc/profile.d/conda.sh"
        if conda env list | grep -q "4D-humans"; then
            echo -e "${GREEN}Using conda 4D-humans environment${NC}"
            conda activate 4D-humans
        else
            echo -e "${YELLOW}Warning: No 4D-humans conda env found${NC}"
        fi
    fi
else
    echo -e "${YELLOW}Warning: No virtual environment found, using system Python${NC}"
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "  Python version: ${PYTHON_VERSION}"

if [[ "$PYTHON_VERSION" != "3.10" && "$PYTHON_VERSION" != "3.11" ]]; then
    echo -e "${YELLOW}Warning: Recommended Python version is 3.10${NC}"
fi

echo ""
echo "Starting pipeline..."
echo ""

# Run the Python pipeline
python3 "${SCRIPT_DIR}/run_avatar_pipeline.py" \
    --image "$BODY_IMAGE" \
    --height "$HEIGHT_CM" \
    --gender "$GENDER" \
    --output "$OUTPUT_DIR"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}PIPELINE COMPLETED SUCCESSFULLY!${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    echo "Output files in: ${OUTPUT_DIR}"
    ls -la "${OUTPUT_DIR}/" 2>/dev/null || true
else
    echo ""
    echo -e "${RED}============================================================${NC}"
    echo -e "${RED}PIPELINE FAILED (exit code: ${EXIT_CODE})${NC}"
    echo -e "${RED}============================================================${NC}"
fi

# Deactivate environment if we activated one
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate 2>/dev/null || true
elif [ -n "$CONDA_DEFAULT_ENV" ]; then
    conda deactivate 2>/dev/null || true
fi

exit $EXIT_CODE
