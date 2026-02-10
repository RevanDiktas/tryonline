#!/usr/bin/env python3
"""
Convert CLO3D garment OBJ files to GLB for upload to Supabase garments bucket.
Input: avatar-creation/output/clo3d_garments/tshirt_{xs,s,m,l,xl}.obj
Output: mvp_pipeline/garments/demo-npc-tshirt/{xs,s,m,l,xl}.glb
"""
import os
import sys
from pathlib import Path

# Paths — adjust if your structure differs
SCRIPT_DIR = Path(__file__).resolve().parent
MVP_ROOT = SCRIPT_DIR.parent
AVATAR_CREATION = MVP_ROOT.parent / "avatar-creation"
INPUT_DIR = AVATAR_CREATION / "output" / "clo3d_garments"
OUTPUT_DIR = MVP_ROOT / "garments" / "demo-npc-tshirt"

SIZES = ["xs", "s", "m", "l", "xl"]


def main():
    try:
        import trimesh
    except ImportError:
        print("Installing trimesh...")
        os.system(f"{sys.executable} -m pip install trimesh -q")
        import trimesh

    if not INPUT_DIR.exists():
        print(f"Error: Input directory not found: {INPUT_DIR}")
        print("Expected: expansion/avatar-creation/output/clo3d_garments/")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for size in SIZES:
        obj_path = INPUT_DIR / f"tshirt_{size}.obj"
        glb_path = OUTPUT_DIR / f"{size}.glb"

        if not obj_path.exists():
            print(f"  Skip {size}: {obj_path} not found")
            continue

        try:
            scene = trimesh.load(str(obj_path), force="scene")
            if hasattr(scene, "export"):
                scene.export(str(glb_path), file_type="glb")
            else:
                # Single mesh
                mesh = trimesh.load(str(obj_path))
                mesh.export(str(glb_path), file_type="glb")
            print(f"  OK {size}: {glb_path}")
        except Exception as e:
            print(f"  FAIL {size}: {e}")

    print(f"\nDone. GLBs saved to: {OUTPUT_DIR}")
    print("Upload these to Supabase: garments/demo-npc-tshirt/")


if __name__ == "__main__":
    main()
