#!/usr/bin/env python3
"""
Map garment(s) on avatar locally and export combined GLB files.

Input: ~/Downloads/
  - avatar_textured.glb
  - xs.glb, s.glb, m.glb, l.glb, xl.glb (garment sizes)

Output: mvp_pipeline/garments/mapped/
  - avatar_with_tshirt_xs.glb, avatar_with_tshirt_s.glb, etc.

Usage:
  python scripts/map_garment_on_avatar.py
  python scripts/map_garment_on_avatar.py ~/Downloads  # custom input dir
"""
import sys
from pathlib import Path

# Default: user's Downloads folder
DEFAULT_INPUT = Path.home() / "Downloads"
SCRIPT_DIR = Path(__file__).resolve().parent
MVP_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = MVP_ROOT / "garments" / "mapped"

# Garment Y offset (0.06 = 6% of avatar height)
GARMENT_Y_OFFSET = 0.06


def get_geometries(obj):
    """Extract trimesh geometries from loaded GLB (Scene or Trimesh)."""
    if hasattr(obj, "geometry"):
        return list(obj.geometry.values())
    if hasattr(obj, "vertices"):
        return [obj]
    return []


def main():
    try:
        import trimesh
        import numpy as np
    except ImportError:
        print("pip install trimesh numpy")
        sys.exit(1)

    input_dir = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_INPUT

    avatar_path = input_dir / "avatar_textured.glb"
    if not avatar_path.exists():
        print(f"Avatar not found: {avatar_path}")
        print("Expected: avatar_textured.glb in", input_dir)
        sys.exit(1)

    sizes = ["xs", "s", "m", "l", "xl"]
    garment_paths = {s: input_dir / f"{s}.glb" for s in sizes}
    missing = [s for s, p in garment_paths.items() if not p.exists()]
    if missing:
        print(f"Missing garments: {missing}")
        print("Expected: xs.glb, s.glb, m.glb, l.glb, xl.glb in", input_dir)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Input:  {input_dir}")
    print(f"Output: {OUTPUT_DIR}\n")

    # Load avatar
    print("Loading avatar...")
    avatar = trimesh.load(str(avatar_path), process=False)
    avatar_geoms = get_geometries(avatar)
    if not avatar_geoms:
        print("Could not extract avatar geometry")
        sys.exit(1)

    # Avatar bbox for offset
    all_verts = np.vstack([g.vertices for g in avatar_geoms if hasattr(g, "vertices")])
    av_min, av_max = all_verts.min(axis=0), all_verts.max(axis=0)
    av_height = float(av_max[1] - av_min[1])
    y_offset = av_height * GARMENT_Y_OFFSET
    print(f"  Avatar height: {av_height:.1f} units, garment Y offset: {y_offset:.1f}\n")

    for size in sizes:
        garment_path = garment_paths[size]
        garment = trimesh.load(str(garment_path), process=False)
        garment_geoms = get_geometries(garment)
        if not garment_geoms:
            print(f"  Skip {size}: no geometry")
            continue

        # Apply Y offset to garment (move up)
        for g in garment_geoms:
            if hasattr(g, "vertices"):
                g.vertices[:, 1] += y_offset

        # Build combined scene
        scene = trimesh.Scene()
        for i, g in enumerate(avatar_geoms):
            scene.add_geometry(g, geom_name=f"avatar_{i}")
        for i, g in enumerate(garment_geoms):
            scene.add_geometry(g, geom_name=f"garment_{i}")

        out_file = OUTPUT_DIR / f"avatar_with_tshirt_{size}.glb"
        scene.export(str(out_file))
        print(f"  ✓ {size}: {out_file.name}")

    print(f"\nDone. Mapped files in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
