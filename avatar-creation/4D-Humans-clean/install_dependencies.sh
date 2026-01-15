#!/bin/bash
# 4D-Humans Installation Script
# Run this with: bash install_dependencies.sh

set -e

echo "================================================"
echo "4D-Humans Installation Script"
echo "================================================"

# Ensure we're in the right directory
cd /Volumes/Expansion/avatar-creation/4D-Humans-clean

# Activate conda environment
source /Volumes/Expansion/miniconda3/etc/profile.d/conda.sh
conda activate 4D-humans

echo ""
echo "Step 1: Installing main dependencies..."
echo "------------------------------------------------"
pip install gdown pytorch-lightning smplx==0.1.28 pyrender opencv-python yacs scikit-image einops timm webdataset dill pandas

echo ""
echo "Step 2: Working around chumpy installation issue..."
echo "------------------------------------------------"
# Clone and manually install chumpy
cd /tmp
rm -rf chumpy
git clone https://github.com/mattloper/chumpy.git
cd chumpy

# Fix the setup.py by removing the pip import
cat > setup.py << 'EOF'
from setuptools import setup

setup(
    name='chumpy',
    version='0.70',
    packages=['chumpy', 'chumpy.utils'],
    install_requires=[
        'numpy',
        'scipy',
        'matplotlib',
    ],
    author='Matthew Loper',
    author_email='matt.loper@gmail.com',
    url='https://github.com/mattloper/chumpy',
    description='chumpy',
)
EOF

pip install -e .

echo ""
echo "Step 3: Installing 4D-Humans package..."
echo "------------------------------------------------"
cd /Volumes/Expansion/avatar-creation/4D-Humans-clean
pip install -e .

echo ""
echo "Step 4: Downloading pretrained models..."
echo "------------------------------------------------"
# Create data directory
mkdir -p data

# Download HMR2 checkpoint
python -c "
from hmr2.utils.download import download_models
try:
    download_models()
    print('✓ Models downloaded successfully')
except Exception as e:
    print(f'Note: {e}')
    print('You may need to manually download models')
"

echo ""
echo "================================================"
echo "Installation Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Download SMPL model from: https://smpl.is.tue.mpg.de/"
echo "   - Register and download: basicModel_neutral_lbs_10_207_0_v1.0.0.pkl"
echo "   - Place it in: /Volumes/Expansion/avatar-creation/4D-Humans-clean/data/"
echo ""
echo "2. Test the installation with:"
echo "   python demo.py --img_folder example_data/images --out_folder demo_out --batch_size=1"
echo ""

