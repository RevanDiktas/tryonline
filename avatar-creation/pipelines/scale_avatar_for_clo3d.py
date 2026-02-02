#!/usr/bin/env python3
"""
Scale Avatar for CLO 3D Compatibility
4D-Humans exports avatars in meters, but CLO 3D imports OBJ files in MILLIMETERS by default.
This script scales the avatar to match CLO 3D's import settings (meters → millimeters).
"""

import os
import trimesh
import numpy as np


def scale_avatar_for_clo3d(input_path, output_path, scale_factor=100.0, target_height_cm=None):
    """
    Scale avatar mesh for CLO 3D compatibility.

    Args:
        input_path: Path to input OBJ/PLY file (in meters)
        output_path: Path to output OBJ/PLY file (in millimeters)
        scale_factor: Scale factor (default 100.0, overridden by target_height_cm)
        target_height_cm: If provided, scale to match this height in cm (recommended)

    Returns:
        dict with scaling information, or None on failure
    """
    try:
        loaded = trimesh.load(str(input_path), process=False)
    except Exception as e:
        print(f"   [scale_avatar] Error loading mesh: {e}")
        return None

    # Extract single mesh (trimesh can return Scene or Trimesh)
    if isinstance(loaded, trimesh.Scene):
        geometries = list(loaded.geometry.values())
        if not geometries:
            print("   [scale_avatar] Scene has no geometry")
            return None
        mesh = geometries[0]
        if not isinstance(mesh, trimesh.Trimesh):
            mesh = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces, process=False)
    elif isinstance(loaded, trimesh.Trimesh):
        mesh = loaded
    else:
        print(f"   [scale_avatar] Unexpected type: {type(loaded)}")
        return None

    vertices = np.array(mesh.vertices, dtype=np.float64)
    faces = mesh.faces
    bounds = mesh.bounds
    height_m = float(bounds[1][1] - bounds[0][1])

    # Calculate scale factor
    if target_height_cm is not None:
        target_height_mm = target_height_cm * 10
        scale_factor = target_height_mm / height_m

    scaled_vertices = vertices * scale_factor

    # Align bottom to ground (Y=0)
    y_min = float(scaled_vertices[:, 1].min())
    scaled_vertices[:, 1] += -y_min

    scaled_mesh = trimesh.Trimesh(vertices=scaled_vertices, faces=faces, process=False)

    if hasattr(mesh, "visual") and mesh.visual is not None:
        if hasattr(mesh.visual, "vertex_colors") and mesh.visual.vertex_colors is not None:
            scaled_mesh.visual.vertex_colors = mesh.visual.vertex_colors

    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".obj":
        scaled_mesh.export(output_path, file_type="obj")
    elif ext == ".ply":
        scaled_mesh.export(output_path, file_type="ply")
    else:
        output_path = output_path + ".obj" if not ext else output_path.replace(ext, ".obj")
        scaled_mesh.export(output_path, file_type="obj")

    return {
        "output_path": output_path,
        "scale_factor": scale_factor,
        "scaled_height_mm": float(scaled_mesh.bounds[1][1] - scaled_mesh.bounds[0][1]),
    }
