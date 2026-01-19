#!/bin/bash
# Script to copy models from Git repo to expected cache location
# This runs during Docker build if models are in the repo

set -e

MODELS_DIR="/workspace/avatar-creation/models"
CACHE_DIR="/root/.cache/4DHumans"

echo "============================================================"
echo "SETTING UP MODELS FROM GIT REPOSITORY"
echo "============================================================"

# Check if models directory exists
if [ ! -d "$MODELS_DIR" ]; then
    echo "⚠️  Models directory not found: $MODELS_DIR"
    echo "   Models will be downloaded at runtime if needed."
    exit 0
fi

# Create cache directory structure
mkdir -p "$CACHE_DIR/logs/train/multiruns/hmr2/0/checkpoints"
mkdir -p "$CACHE_DIR/data/smpl"

# Copy checkpoint if it exists
CHECKPOINT_SRC="$MODELS_DIR/checkpoints/epoch=35-step=1000000.ckpt"
CHECKPOINT_DST="$CACHE_DIR/logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"

if [ -f "$CHECKPOINT_SRC" ]; then
    echo "✓ Copying checkpoint (2.5GB)..."
    cp "$CHECKPOINT_SRC" "$CHECKPOINT_DST"
    echo "  ✅ Checkpoint copied to: $CHECKPOINT_DST"
else
    echo "⚠️  Checkpoint not found: $CHECKPOINT_SRC"
fi

# Copy SMPL models if they exist
SMPL_NEUTRAL_SRC="$MODELS_DIR/data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl"
SMPL_MALE_SRC="$MODELS_DIR/data/basicmodel_m_lbs_10_207_0_v1.1.0.pkl"
SMPL_FEMALE_SRC="$MODELS_DIR/data/basicmodel_f_lbs_10_207_0_v1.1.0.pkl"

SMPL_NEUTRAL_DST="$CACHE_DIR/data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl"
SMPL_MALE_DST="$CACHE_DIR/data/basicmodel_m_lbs_10_207_0_v1.1.0.pkl"
SMPL_FEMALE_DST="$CACHE_DIR/data/basicmodel_f_lbs_10_207_0_v1.1.0.pkl"

for src in "$SMPL_NEUTRAL_SRC" "$SMPL_MALE_SRC" "$SMPL_FEMALE_SRC"; do
    if [ -f "$src" ]; then
        filename=$(basename "$src")
        dst="$CACHE_DIR/data/$filename"
        echo "✓ Copying $filename (~247MB)..."
        cp "$src" "$dst"
        echo "  ✅ Copied to: $dst"
    else
        echo "⚠️  SMPL model not found: $src"
    fi
done

# Copy supporting files
MEAN_PARAMS_SRC="$MODELS_DIR/data/smpl_mean_params.npz"
JOINT_REGRESSOR_SRC="$MODELS_DIR/data/SMPL_to_J19.pkl"

if [ -f "$MEAN_PARAMS_SRC" ]; then
    cp "$MEAN_PARAMS_SRC" "$CACHE_DIR/data/smpl_mean_params.npz"
    echo "✓ Copied smpl_mean_params.npz"
fi

if [ -f "$JOINT_REGRESSOR_SRC" ]; then
    cp "$JOINT_REGRESSOR_SRC" "$CACHE_DIR/data/SMPL_to_J19.pkl"
    echo "✓ Copied SMPL_to_J19.pkl"
fi

echo ""
echo "============================================================"
echo "MODEL SETUP COMPLETE"
echo "============================================================"
echo "Models are now in the expected cache location."
echo "Runtime downloads will be skipped."
