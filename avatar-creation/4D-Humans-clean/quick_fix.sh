#!/bin/bash
# Quick fix for NumPy compatibility issue

set -e

echo "Fixing NumPy compatibility..."
conda activate 4D-humans
pip install "numpy<2.0"

echo ""
echo "✓ NumPy downgraded to 1.x for PyTorch compatibility"
echo ""
echo "Now you can proceed with downloading models"

