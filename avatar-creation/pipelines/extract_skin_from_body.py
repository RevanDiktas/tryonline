#!/usr/bin/env python3
"""
Extract skin tone from BODY image (not face) and apply to mesh.

This script detects skin pixels from a full-body photo and extracts
the median skin color, then applies it to an avatar mesh.

Usage:
    python extract_skin_from_body.py --body-image body.jpg --mesh avatar.obj --output ./output
"""

import cv2
import numpy as np
import argparse
from pathlib import Path
import trimesh
from PIL import Image


def detect_skin_pixels_body(image: np.ndarray) -> tuple:
    """
    Detect skin pixels from a full-body image using HSV color space.
    
    Unlike face detection, this focuses on exposed skin areas in
    the upper body region (neck, arms, etc.)
    
    Args:
        image: BGR image (OpenCV format)
    
    Returns:
        skin_mask: Binary mask of skin pixels
        skin_color: Median skin color (BGR)
    """
    h, w = image.shape[:2]
    
    # Convert to HSV for skin detection
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Skin detection ranges (works well for various skin tones)
    # Range 1: Light to medium skin
    lower_skin1 = np.array([0, 20, 70], dtype=np.uint8)
    upper_skin1 = np.array([20, 255, 255], dtype=np.uint8)
    
    # Range 2: Darker skin tones (wraps around hue)
    lower_skin2 = np.array([170, 20, 70], dtype=np.uint8)
    upper_skin2 = np.array([180, 255, 255], dtype=np.uint8)
    
    # Create combined mask
    mask1 = cv2.inRange(hsv, lower_skin1, upper_skin1)
    mask2 = cv2.inRange(hsv, lower_skin2, upper_skin2)
    skin_mask = cv2.bitwise_or(mask1, mask2)
    
    # For body images: focus on upper body where skin is usually visible
    # (neck, arms, face area - but not lower body which may be clothed)
    roi_mask = np.zeros((h, w), dtype=np.uint8)
    
    # Upper 60% of image, center 70% width
    roi_y_start = int(h * 0.05)   # Start just below top
    roi_y_end = int(h * 0.65)     # Upper 60%
    roi_x_start = int(w * 0.15)   # Center 70%
    roi_x_end = int(w * 0.85)
    
    roi_mask[roi_y_start:roi_y_end, roi_x_start:roi_x_end] = 255
    
    # Apply ROI mask
    skin_mask = cv2.bitwise_and(skin_mask, roi_mask)
    
    # Morphological operations to clean up noise
    kernel = np.ones((5, 5), np.uint8)
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
    
    # Get skin pixels
    skin_pixels = image[skin_mask > 0]
    
    if len(skin_pixels) < 100:
        print("  Warning: Few skin pixels detected, using fallback region")
        # Fallback: use center-upper region
        center_region = image[h//4:h//2, w//3:2*w//3]
        skin_color = np.median(center_region.reshape(-1, 3), axis=0)
    else:
        # Use median for robust color (less affected by outliers)
        skin_color = np.median(skin_pixels, axis=0)
    
    return skin_mask, skin_color.astype(np.uint8)


def apply_skin_to_mesh(mesh_path: Path, skin_color: np.ndarray, output_path: Path):
    """
    Apply skin color as vertex colors to mesh.
    
    Args:
        mesh_path: Path to input OBJ mesh
        skin_color: BGR skin color
        output_path: Path to save textured mesh
    """
    # Load mesh
    mesh = trimesh.load(str(mesh_path), process=False)
    if not isinstance(mesh, trimesh.Trimesh):
        mesh = list(mesh.geometry.values())[0]
    
    # Convert BGR to RGB and normalize
    skin_color_rgb = skin_color[::-1] / 255.0
    
    # Apply as vertex colors (RGBA)
    vertex_colors = np.tile(skin_color_rgb, (len(mesh.vertices), 1))
    vertex_colors = np.column_stack([vertex_colors, np.ones(len(mesh.vertices))])
    mesh.visual.vertex_colors = (vertex_colors * 255).astype(np.uint8)
    
    # Save
    mesh.export(str(output_path))
    return mesh


def create_skin_texture_png(skin_color: np.ndarray, output_path: Path, size: int = 512):
    """Create a solid color PNG texture of the skin tone."""
    # Convert BGR to RGB
    skin_color_rgb = skin_color[::-1]
    
    # Create solid color image
    texture = np.full((size, size, 3), skin_color_rgb, dtype=np.uint8)
    
    # Save using PIL (ensures correct RGB format)
    Image.fromarray(texture, 'RGB').save(str(output_path))
    return output_path


def save_mask_visualization(image: np.ndarray, mask: np.ndarray, output_path: Path):
    """Save visualization of skin detection mask."""
    vis = image.copy()
    vis[mask > 0] = [0, 255, 0]  # Green overlay for detected skin
    cv2.imwrite(str(output_path), vis)
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Extract skin tone from body image and apply to mesh'
    )
    parser.add_argument(
        '--body-image', '-b',
        type=str,
        required=True,
        help='Path to full-body image'
    )
    parser.add_argument(
        '--mesh', '-m',
        type=str,
        help='Path to body mesh OBJ (optional)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='./output',
        help='Output directory'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SKIN EXTRACTION FROM BODY IMAGE")
    print("=" * 60)
    
    # Setup paths
    body_image_path = Path(args.body_image)
    if not body_image_path.exists():
        raise FileNotFoundError(f"Body image not found: {body_image_path}")
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load image
    print(f"\nLoading body image: {body_image_path}")
    image = cv2.imread(str(body_image_path))
    if image is None:
        raise ValueError(f"Could not load image: {body_image_path}")
    
    print(f"  Image size: {image.shape[1]}x{image.shape[0]}")
    
    # Detect skin
    print("\nDetecting skin pixels from body...")
    skin_mask, skin_color = detect_skin_pixels_body(image)
    
    print(f"  Skin pixels detected: {np.sum(skin_mask > 0)}")
    print(f"  Skin color (BGR): {skin_color}")
    print(f"  Skin color (RGB): {skin_color[::-1]}")
    
    # Save mask visualization
    mask_vis_path = output_dir / "skin_detection_mask.png"
    save_mask_visualization(image, skin_mask, mask_vis_path)
    print(f"  Mask visualization saved: {mask_vis_path}")
    
    # Create skin texture PNG
    texture_path = output_dir / "skin_texture.png"
    create_skin_texture_png(skin_color, texture_path)
    print(f"  Skin texture saved: {texture_path}")
    
    # Apply to mesh if provided
    if args.mesh:
        mesh_path = Path(args.mesh)
        if not mesh_path.exists():
            print(f"  Warning: Mesh not found: {mesh_path}")
        else:
            print(f"\nApplying skin to mesh: {mesh_path}")
            textured_mesh_path = output_dir / f"{mesh_path.stem}_textured.obj"
            apply_skin_to_mesh(mesh_path, skin_color, textured_mesh_path)
            print(f"  Textured mesh saved: {textured_mesh_path}")
    
    print("\n" + "=" * 60)
    print("COMPLETE!")
    print("=" * 60)
    print(f"\nOutput files:")
    print(f"  Skin texture: {texture_path}")
    print(f"  Mask visualization: {mask_vis_path}")
    if args.mesh:
        print(f"  Textured mesh: {output_dir / f'{Path(args.mesh).stem}_textured.obj'}")


if __name__ == '__main__':
    main()
