#!/bin/bash
# Quick fix for chumpy installation issue

set -e

echo "Fixing chumpy installation..."

# Activate conda environment
source /Volumes/Expansion/miniconda3/etc/profile.d/conda.sh
conda activate 4D-humans

# Install scipy and matplotlib first (chumpy dependencies)
pip install scipy matplotlib

# Clone chumpy to temp directory
cd /tmp
rm -rf chumpy
git clone https://github.com/mattloper/chumpy.git
cd chumpy

# Replace the broken setup.py
cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name='chumpy',
    version='0.70',
    packages=find_packages(),
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

# Install it
pip install -e .

echo ""
echo "✓ Chumpy installed successfully!"
echo ""
echo "Now you can continue with:"
echo "  cd /Volumes/Expansion/avatar-creation/4D-Humans-clean"
echo "  pip install -e ."

