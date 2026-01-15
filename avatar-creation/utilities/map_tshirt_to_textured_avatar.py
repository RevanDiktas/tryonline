#!/usr/bin/env python3
"""
Map t-shirt onto textured avatar (body with skin tone)
Combines the garment mesh with the textured body mesh
"""

import numpy as np
import trimesh
from pathlib import Path
import argparse

def map_tshirt_to_avatar(garment_path, body_path, output_path):
    """
    Combine t-shirt garment with textured body avatar
    """
    print("=" * 60)
    print("👕 MAPPING T-SHIRT TO TEXTURED AVATAR")
    print("=" * 60)
    
    # Load garment
    print(f"\n📥 Loading garment: {garment_path}")
    garment = trimesh.load(str(garment_path))
    if not isinstance(garment, trimesh.Trimesh):
        garment = list(garment.geometry.values())[0]
    print(f"   ✓ Garment: {len(garment.vertices)} vertices, {len(garment.faces)} faces")
    
    # Load textured body
    print(f"\n📥 Loading textured body: {body_path}")
    body = trimesh.load(str(body_path))
    if not isinstance(body, trimesh.Trimesh):
        body = list(body.geometry.values())[0]
    print(f"   ✓ Body: {len(body.vertices)} vertices, {len(body.faces)} faces")
    
    # Combine meshes
    print(f"\n🔧 Combining meshes...")
    combined = trimesh.util.concatenate([body, garment])
    print(f"   ✓ Combined: {len(combined.vertices)} vertices, {len(combined.faces)} faces")
    
    # Save combined mesh
    print(f"\n💾 Saving combined avatar with t-shirt: {output_path}")
    combined.export(str(output_path))
    print(f"   ✓ Saved: {output_path}")
    
    print("\n✅ COMPLETE!")
    print("=" * 60)
    
    return combined

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Map t-shirt onto textured avatar')
    parser.add_argument('--garment', type=str, required=True, help='Path to garment PLY file')
    parser.add_argument('--body', type=str, required=True, help='Path to textured body OBJ file')
    parser.add_argument('--output', type=str, required=True, help='Output combined OBJ file')
    
    args = parser.parse_args()
    
    map_tshirt_to_avatar(args.garment, args.body, args.output)

