#!/usr/bin/env python3
"""
Remove uniform dark grey background from the A-pose guide image.
Makes background transparent so the figure can be placed on any page background.
Usage: python scripts/remove_bg_pose_guide.py [input.png] [output.png]
Defaults: input from assets path, output frontend/public/pose-guide.png
"""
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Install Pillow: pip install Pillow")
    sys.exit(1)


def rgb_distance(c1, c2):
    return sum((a - b) ** 2 for a, b in zip(c1[:3], c2[:3])) ** 0.5


def remove_dark_bg(input_path: str, output_path: str, tolerance: int = 55) -> None:
    img = Image.open(input_path).convert("RGBA")
    data = img.getdata()

    # Sample background from corners (assume dark grey is the bg)
    w, h = img.size
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    bg_samples = [img.getpixel(p) for p in corners]
    # Use median-ish to avoid any single outlier
    bg_r = int(sum(p[0] for p in bg_samples) / 4)
    bg_g = int(sum(p[1] for p in bg_samples) / 4)
    bg_b = int(sum(p[2] for p in bg_samples) / 4)
    bg = (bg_r, bg_g, bg_b)

    new_data = []
    for item in data:
        r, g, b, a = item
        if rgb_distance((r, g, b), bg) <= tolerance:
            new_data.append((r, g, b, 0))
        else:
            new_data.append(item)

    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    repo = Path(__file__).resolve().parent.parent
    default_input = repo / "frontend" / "public" / "pose-guide-original.png"
    # Allow passing path from Cursor assets
    if len(sys.argv) >= 2:
        input_path = Path(sys.argv[1])
    else:
        # Try Cursor project assets path
        cursor_assets = Path.home() / ".cursor" / "projects" / "Volumes-Expansion-mvp-pipeline" / "assets"
        candidates = list(cursor_assets.glob("Screenshot_2026-03-09*pose*")) or list(cursor_assets.glob("Screenshot_2026-03-09*20.37*"))
        if not candidates:
            input_path = default_input
        else:
            input_path = candidates[0]

    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = repo / "frontend" / "public" / "pose-guide.png"

    if not input_path.exists():
        print(f"Input not found: {input_path}")
        print("Usage: python scripts/remove_bg_pose_guide.py <input.png> [output.png]")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    remove_dark_bg(str(input_path), str(output_path))
