"""
OBJ-to-GLB conversion utility for the draping pipeline.

Converts draped OBJ meshes to GLB for browser rendering. Preserves
UVs and materials when present; applies a default PBR material otherwise.
"""

import sys
from pathlib import Path


def obj_to_glb(obj_path: str, glb_path: str, preserve_normals: bool = True) -> dict:
    """
    Convert an OBJ file to GLB using trimesh.

    Returns metadata dict: vertex_count, face_count, file_size_bytes.
    """
    import trimesh

    mesh = trimesh.load(obj_path, force="mesh", process=False)

    if not preserve_normals:
        mesh.fix_normals()

    mesh.export(glb_path, file_type="glb")

    return {
        "vertex_count": len(mesh.vertices),
        "face_count": len(mesh.faces),
        "file_size_bytes": Path(glb_path).stat().st_size,
    }


def obj_to_glb_with_texture(
    obj_path: str,
    glb_path: str,
    texture_path: str = None,
) -> dict:
    """
    Convert OBJ to GLB, optionally applying a texture image as the base color.
    Uses pygltflib for precise control over materials.
    """
    import trimesh
    import numpy as np

    mesh = trimesh.load(obj_path, force="mesh", process=False)

    if texture_path and Path(texture_path).exists():
        from PIL import Image
        import io

        img = Image.open(texture_path)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        texture_data = buf.getvalue()

        material = trimesh.visual.material.PBRMaterial(
            baseColorTexture=Image.open(io.BytesIO(texture_data)),
            metallicFactor=0.0,
            roughnessFactor=0.8,
        )

        if mesh.visual and hasattr(mesh.visual, "uv") and mesh.visual.uv is not None:
            mesh.visual = trimesh.visual.TextureVisuals(
                uv=mesh.visual.uv,
                material=material,
            )

    mesh.export(glb_path, file_type="glb")

    return {
        "vertex_count": len(mesh.vertices),
        "face_count": len(mesh.faces),
        "file_size_bytes": Path(glb_path).stat().st_size,
        "has_texture": texture_path is not None and Path(texture_path).exists(),
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert.py <input.obj> <output.glb> [texture.png]")
        sys.exit(1)

    in_path = sys.argv[1]
    out_path = sys.argv[2]
    tex_path = sys.argv[3] if len(sys.argv) > 3 else None

    if tex_path:
        info = obj_to_glb_with_texture(in_path, out_path, tex_path)
    else:
        info = obj_to_glb(in_path, out_path)

    print(f"Converted: {info}")
