#!/usr/bin/env python3
"""
Download body_apose.obj + a garment GLB from signed HTTPS URLs and print bbox stats.
Phase 0.5: confirms mm-scale assets load together (no sim yet).
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np
import requests
import trimesh


def _load_mesh_from_url(url: str, suffix: str) -> trimesh.Trimesh:
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    data = r.content
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        path = f.name
    try:
        loaded = trimesh.load(path, process=False, force="mesh")
    finally:
        Path(path).unlink(missing_ok=True)

    if isinstance(loaded, trimesh.Scene):
        geoms = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if not geoms:
            raise ValueError("Scene has no Trimesh geometry")
        mesh = trimesh.util.concatenate(geoms)
    elif isinstance(loaded, trimesh.Trimesh):
        mesh = loaded
    else:
        raise TypeError(f"Unexpected load type: {type(loaded)}")
    return mesh


def _print_mesh(name: str, mesh: trimesh.Trimesh) -> None:
    v = np.asarray(mesh.vertices, dtype=np.float64)
    h = float(v[:, 1].max() - v[:, 1].min())
    print(f"{name}: verts={len(v)} faces={len(mesh.faces)}  bbox_y_extents_mm≈{h:.1f} (assuming mm units)")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--body-url", required=True, help="HTTPS URL to body_apose.obj")
    p.add_argument("--garment-url", required=True, help="HTTPS URL to e.g. m.glb")
    args = p.parse_args()

    try:
        body = _load_mesh_from_url(args.body_url, ".obj")
        garment = _load_mesh_from_url(args.garment_url, ".glb")
    except Exception as e:
        print("Load failed:", e, file=sys.stderr)
        return 1

    _print_mesh("body", body)
    _print_mesh("garment", garment)
    print("Asset load OK (no simulation).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
