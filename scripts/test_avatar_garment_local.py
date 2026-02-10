#!/usr/bin/env python3
"""
Test avatar + garment compositing locally.
Loads both GLBs and checks alignment / overlap — helps diagnose skin poke-through.

Usage:
  1. Download avatar: avatars/{user_id}/avatar_textured.glb
  2. Download garment: garments/demo-npc-tshirt/l.glb
  3. python scripts/test_avatar_garment_local.py path/to/avatar.glb path/to/tshirt_l.glb

Output: prints bbox info; optionally exports combined GLB for inspection.
"""
import sys
from pathlib import Path

def main():
    try:
        import trimesh
        import numpy as np
    except ImportError:
        print("pip install trimesh numpy")
        sys.exit(1)

    if len(sys.argv) < 3:
        print("Usage: python test_avatar_garment_local.py <avatar.glb> <garment.glb>")
        print("  Example: python test_avatar_garment_local.py avatar.glb tshirt_l.glb")
        sys.exit(1)

    avatar_path = Path(sys.argv[1])
    garment_path = Path(sys.argv[2])

    if not avatar_path.exists():
        print(f"Avatar not found: {avatar_path}")
        sys.exit(1)
    if not garment_path.exists():
        print(f"Garment not found: {garment_path}")
        sys.exit(1)

    print("Loading...")
    avatar = trimesh.load(str(avatar_path), process=False)
    garment = trimesh.load(str(garment_path), process=False)

    def bbox_info(obj, name):
        geoms = []
        if hasattr(obj, "geometry"):
            geoms = list(obj.geometry.values())
        elif hasattr(obj, "bounds"):
            geoms = [obj]
        if not geoms:
            return None, None
        all_verts = np.vstack([g.vertices for g in geoms if hasattr(g, "vertices")])
        if len(all_verts) == 0:
            return None, None
        bmin, bmax = all_verts.min(axis=0), all_verts.max(axis=0)
        size = bmax - bmin
        center = (bmin + bmax) / 2
        print(f"  {name}: center {center}, size {size}, height Y={size[1]:.1f}")
        return center, size

    print("\nBounding boxes (same coords = should align):")
    ac, asize = bbox_info(avatar, "Avatar")
    gc, gsize = bbox_info(garment, "Garment")

    if ac is not None and gc is not None:
        offset = ac - gc
        print(f"\n  Offset (avatar_center - garment_center): {offset}")
        print(f"  If garment sits too low, it needs +Y translation of ~{offset[1]:.1f}")

    out_path = Path("output_local_test.glb")
    try:
        scene = trimesh.Scene()
        if hasattr(avatar, "geometry"):
            for g in avatar.geometry.values():
                scene.add_geometry(g, geom_name="avatar")
        else:
            scene.add_geometry(avatar, geom_name="avatar")
        if hasattr(garment, "geometry"):
            for g in garment.geometry.values():
                scene.add_geometry(g, geom_name="garment")
        else:
            scene.add_geometry(garment, geom_name="garment")
        scene.export(str(out_path))
        print(f"\nExported combined scene to {out_path} — inspect in Blender or online GLB viewer")
    except Exception as e:
        print(f"Export skipped: {e}")

if __name__ == "__main__":
    main()
