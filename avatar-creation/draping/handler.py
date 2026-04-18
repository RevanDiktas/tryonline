"""
RunPod Serverless Handler for Cloth Draping Service
====================================================

Receives SMPL body parameters + garment OBJ mesh, runs cloth physics
simulation via XRTailor (GPU) or geometric fallback, returns draped OBJ.

Expected input:
{
    "smpl_params_url": "https://...",   # URL to smpl_params.npz
    "body_obj_url": "https://...",      # URL to body_tpose.obj (SMPL T-pose mesh)
    "garment_obj_url": "https://...",   # URL to garment .obj file
    "fabric_config": {                  # Optional fabric material properties
        "stretch_compliance": 0.001,
        "bend_compliance": 0.01,
        "thickness": 0.002,
        "density": 0.3
    },
    "simulation_mode": "swift",         # "swift" or "quality"
    "garment_id": "uuid",              # For logging
    "size": "m",                        # For logging
    "user_id": "uuid"                   # For logging
}

Output:
{
    "draped_obj_base64": "...",          # Base64-encoded draped OBJ
    "draped_glb_base64": "...",          # Base64-encoded draped GLB (converted)
    "processing_time_seconds": 2.1,
    "simulation_method": "xrtailor" | "geometric_fallback",
    "vertex_count": 12345,
    "success": true
}
"""

import os
import sys
import time
import json
import base64
import hashlib
import shutil
import tempfile
import subprocess
from pathlib import Path

import numpy as np

try:
    import httpx
    USE_HTTPX = True
except ImportError:
    import requests
    USE_HTTPX = False

XRTAILOR_BIN = os.environ.get("XRTAILOR_BIN", "/opt/xrtailor/build/XRTailor")
CONFIGS_DIR = Path("/workspace/configs")
RUNPOD_VOLUME = Path("/runpod-volume")
SMPL_MODELS_DIR = RUNPOD_VOLUME / "smpl"

XRTAILOR_AVAILABLE = Path(XRTAILOR_BIN).exists() and os.access(XRTAILOR_BIN, os.X_OK)

if XRTAILOR_AVAILABLE:
    print(f"[Draping] XRTailor binary found at {XRTAILOR_BIN}")
else:
    print(f"[Draping] XRTailor binary NOT found — will use geometric fallback")


def download_file(url: str, dest: Path) -> bool:
    """Download a file from URL to local path."""
    try:
        if url.startswith("file://"):
            shutil.copy(url[7:], dest)
            return True
        if USE_HTTPX:
            with httpx.Client(timeout=120.0) as client:
                r = client.get(url)
                r.raise_for_status()
                dest.write_bytes(r.content)
        else:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            dest.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"[Draping] Download failed {url}: {e}")
        return False


def load_obj_vertices(obj_path: Path) -> np.ndarray:
    """Parse OBJ file and return vertex positions as (N,3) array."""
    verts = []
    with open(obj_path, "r") as f:
        for line in f:
            if line.startswith("v "):
                parts = line.strip().split()
                verts.append([float(parts[1]), float(parts[2]), float(parts[3])])
    return np.array(verts, dtype=np.float64)


def write_obj_with_new_verts(original_obj: Path, new_verts: np.ndarray, output_obj: Path):
    """Rewrite an OBJ file replacing only vertex positions, preserving faces/normals/UVs."""
    vi = 0
    lines_out = []
    with open(original_obj, "r") as f:
        for line in f:
            if line.startswith("v ") and vi < len(new_verts):
                v = new_verts[vi]
                lines_out.append(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
                vi += 1
            else:
                lines_out.append(line)
    with open(output_obj, "w") as f:
        f.writelines(lines_out)


def compute_body_normals(body_verts: np.ndarray, body_obj: Path) -> np.ndarray:
    """Compute per-vertex normals from body mesh faces."""
    faces = []
    with open(body_obj, "r") as f:
        for line in f:
            if line.startswith("f "):
                parts = line.strip().split()[1:]
                idxs = [int(p.split("/")[0]) - 1 for p in parts]
                if len(idxs) >= 3:
                    faces.append(idxs[:3])
    faces = np.array(faces, dtype=np.int64)
    normals = np.zeros_like(body_verts)
    for face in faces:
        v0, v1, v2 = body_verts[face[0]], body_verts[face[1]], body_verts[face[2]]
        n = np.cross(v1 - v0, v2 - v0)
        norm = np.linalg.norm(n)
        if norm > 1e-12:
            n /= norm
        for idx in face:
            normals[idx] += n
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms[norms < 1e-12] = 1.0
    return normals / norms


def geometric_drape(
    body_obj: Path,
    garment_obj: Path,
    output_obj: Path,
    fabric_config: dict,
) -> dict:
    """
    Geometric draping fallback: inflates garment vertices outward from the body
    surface to prevent penetration. Not true physics, but eliminates skin-poking.

    Algorithm:
    1. For each garment vertex, find nearest body vertex
    2. If garment vertex is inside the body (dot with body normal < 0), push it out
    3. Apply smoothing pass to avoid harsh discontinuities
    """
    body_verts = load_obj_vertices(body_obj)
    garment_verts = load_obj_vertices(garment_obj)

    if len(body_verts) == 0 or len(garment_verts) == 0:
        raise ValueError(f"Empty mesh: body={len(body_verts)} garment={len(garment_verts)} verts")

    thickness = fabric_config.get("thickness", 0.003)
    offset = max(thickness, 0.002)

    body_normals = compute_body_normals(body_verts, body_obj)

    from scipy.spatial import cKDTree
    tree = cKDTree(body_verts)

    distances, indices = tree.query(garment_verts, k=1)
    nearest_body = body_verts[indices]
    nearest_normals = body_normals[indices]

    diff = garment_verts - nearest_body
    dots = np.sum(diff * nearest_normals, axis=1)

    penetrating = dots < offset
    new_verts = garment_verts.copy()

    if np.any(penetrating):
        push = (offset - dots[penetrating])[:, np.newaxis] * nearest_normals[penetrating]
        new_verts[penetrating] += push

    # Laplacian smoothing pass on modified vertices (2 iterations)
    garment_faces = []
    with open(garment_obj, "r") as f:
        for line in f:
            if line.startswith("f "):
                parts = line.strip().split()[1:]
                idxs = [int(p.split("/")[0]) - 1 for p in parts]
                if len(idxs) >= 3:
                    garment_faces.append(idxs[:3])

    if garment_faces:
        adjacency = [[] for _ in range(len(new_verts))]
        for face in garment_faces:
            for i in range(3):
                for j in range(3):
                    if i != j:
                        adjacency[face[i]].append(face[j])
        for _ in range(2):
            smoothed = new_verts.copy()
            for vi in range(len(new_verts)):
                if not penetrating[vi] or not adjacency[vi]:
                    continue
                neighbors = adjacency[vi]
                avg = np.mean(new_verts[neighbors], axis=0)
                smoothed[vi] = 0.7 * new_verts[vi] + 0.3 * avg
            new_verts = smoothed

    write_obj_with_new_verts(garment_obj, new_verts, output_obj)

    n_fixed = int(np.sum(penetrating))
    return {
        "vertices_total": len(garment_verts),
        "vertices_fixed": n_fixed,
        "penetration_ratio": round(n_fixed / len(garment_verts), 4) if len(garment_verts) > 0 else 0,
    }


def run_xrtailor(
    body_obj: Path,
    garment_obj: Path,
    output_dir: Path,
    fabric_config: dict,
    simulation_mode: str = "swift",
    smpl_params_path: Path = None,
) -> Path:
    """
    Run XRTailor cloth simulation.
    Returns path to the draped output OBJ.
    """
    engine_cfg = CONFIGS_DIR / "engine_config.json"
    fabric_cfg_path = output_dir / "fabric_runtime.json"
    fabric_cfg_path.write_text(json.dumps(fabric_config, indent=2))

    sim_cfg_path = output_dir / "simulation_config.json"
    sim_config = {
        "garment": str(garment_obj),
        "body": str(body_obj),
        "output_dir": str(output_dir),
        "output_format": "obj",
        "fabric_config": str(fabric_cfg_path),
        "mode": simulation_mode,
        "frames": 1,
    }
    if smpl_params_path and smpl_params_path.exists():
        sim_config["smpl_params"] = str(smpl_params_path)
    sim_cfg_path.write_text(json.dumps(sim_config, indent=2))

    cmd = [
        XRTAILOR_BIN,
        "--engine-config", str(engine_cfg),
        "--simulation-config", str(sim_cfg_path),
        "--headless",
    ]

    print(f"[Draping] Running XRTailor: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"[Draping] XRTailor stderr: {result.stderr}")
        raise RuntimeError(f"XRTailor failed (exit {result.returncode}): {result.stderr[:500]}")

    output_obj = output_dir / "frame_0000.obj"
    if not output_obj.exists():
        candidates = list(output_dir.glob("*.obj"))
        candidates = [c for c in candidates if c.name != garment_obj.name and c.name != body_obj.name]
        if candidates:
            output_obj = candidates[0]
        else:
            raise FileNotFoundError(f"No draped OBJ output in {output_dir}")

    return output_obj


def obj_to_glb(obj_path: Path, glb_path: Path) -> bool:
    """Convert OBJ to GLB using trimesh."""
    try:
        import trimesh
        mesh = trimesh.load(str(obj_path), force="mesh", process=False)
        mesh.export(str(glb_path), file_type="glb")
        return True
    except Exception as e:
        print(f"[Draping] OBJ→GLB conversion failed: {e}")
        return False


def handler(event: dict) -> dict:
    """RunPod serverless handler for cloth draping."""
    start_time = time.time()

    job_input = event.get("input", {})
    smpl_params_url = job_input.get("smpl_params_url")
    body_obj_url = job_input.get("body_obj_url")
    garment_obj_url = job_input.get("garment_obj_url")
    fabric_config = job_input.get("fabric_config", {})
    simulation_mode = job_input.get("simulation_mode", "swift")
    garment_id = job_input.get("garment_id", "unknown")
    size = job_input.get("size", "?")
    user_id = job_input.get("user_id", "unknown")

    if not garment_obj_url:
        return {"error": "garment_obj_url is required", "success": False}
    if not body_obj_url:
        return {"error": "body_obj_url is required", "success": False}

    default_fabric = {
        "stretch_compliance": 0.001,
        "bend_compliance": 0.01,
        "thickness": 0.003,
        "density": 0.3,
    }
    merged_fabric = {**default_fabric, **fabric_config}

    print(f"[Draping] Job: user={user_id} garment={garment_id} size={size} mode={simulation_mode}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        body_obj = tmp_dir / "body.obj"
        garment_obj = tmp_dir / "garment.obj"
        smpl_params = tmp_dir / "smpl_params.npz"
        output_dir = tmp_dir / "output"
        output_dir.mkdir()

        print("[Draping] Downloading input files...")
        if not download_file(body_obj_url, body_obj):
            return {"error": "Failed to download body OBJ", "success": False}
        if not download_file(garment_obj_url, garment_obj):
            return {"error": "Failed to download garment OBJ", "success": False}
        if smpl_params_url:
            download_file(smpl_params_url, smpl_params)

        print(f"[Draping] Body OBJ: {body_obj.stat().st_size / 1024:.1f} KB")
        print(f"[Draping] Garment OBJ: {garment_obj.stat().st_size / 1024:.1f} KB")

        simulation_method = "unknown"
        draped_obj = None

        # Strategy 1: XRTailor GPU simulation
        if XRTAILOR_AVAILABLE:
            try:
                print("[Draping] Running XRTailor GPU simulation...")
                draped_obj = run_xrtailor(
                    body_obj=body_obj,
                    garment_obj=garment_obj,
                    output_dir=output_dir,
                    fabric_config=merged_fabric,
                    simulation_mode=simulation_mode,
                    smpl_params_path=smpl_params if smpl_params.exists() else None,
                )
                simulation_method = "xrtailor"
                print(f"[Draping] XRTailor success: {draped_obj}")
            except Exception as e:
                print(f"[Draping] XRTailor failed, falling back to geometric: {e}")

        # Strategy 2: geometric inflation fallback
        if draped_obj is None:
            try:
                print("[Draping] Running geometric drape fallback...")
                draped_obj = output_dir / "draped.obj"
                stats = geometric_drape(
                    body_obj=body_obj,
                    garment_obj=garment_obj,
                    output_obj=draped_obj,
                    fabric_config=merged_fabric,
                )
                simulation_method = "geometric_fallback"
                print(f"[Draping] Geometric drape done: {stats}")
            except Exception as e:
                print(f"[Draping] Geometric drape failed: {e}")
                import traceback
                traceback.print_exc()
                return {"error": f"All draping methods failed: {e}", "success": False}

        # Read draped OBJ
        obj_bytes = draped_obj.read_bytes()
        obj_b64 = base64.b64encode(obj_bytes).decode("utf-8")

        # Convert to GLB
        glb_path = output_dir / "draped.glb"
        glb_b64 = ""
        if obj_to_glb(draped_obj, glb_path):
            glb_bytes = glb_path.read_bytes()
            glb_b64 = base64.b64encode(glb_bytes).decode("utf-8")
            print(f"[Draping] GLB: {len(glb_bytes) / 1024:.1f} KB")

        vertex_count = len(load_obj_vertices(draped_obj))
        processing_time = time.time() - start_time

        print(f"[Draping] Complete in {processing_time:.1f}s via {simulation_method}")

        return {
            "draped_obj_base64": obj_b64,
            "draped_glb_base64": glb_b64,
            "processing_time_seconds": round(processing_time, 1),
            "simulation_method": simulation_method,
            "vertex_count": vertex_count,
            "obj_size_bytes": len(obj_bytes),
            "glb_size_bytes": len(glb_bytes) if glb_b64 else 0,
            "garment_id": garment_id,
            "size": size,
            "user_id": user_id,
            "success": True,
        }


def runpod_handler(event):
    """Wrapper for RunPod serverless."""
    return handler(event)


try:
    import runpod
    print("[Draping] Starting serverless cloth draping handler...")
    print(f"[Draping] XRTailor available: {XRTAILOR_AVAILABLE}")
    print(f"[Draping] Python path: {sys.path[:3]}")
    runpod.serverless.start({"handler": runpod_handler})
except ImportError:
    print("[Draping] RunPod not installed — local mode")
except Exception as e:
    print(f"[Draping] Startup error: {e}")
    import traceback
    traceback.print_exc()
    raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test draping handler locally")
    parser.add_argument("--body-obj", required=True, help="Path to body T-pose OBJ")
    parser.add_argument("--garment-obj", required=True, help="Path to garment OBJ")
    parser.add_argument("--smpl-params", default=None, help="Path to smpl_params.npz")
    parser.add_argument("--mode", default="swift", choices=["swift", "quality"])
    args = parser.parse_args()

    test_event = {
        "input": {
            "body_obj_url": f"file://{os.path.abspath(args.body_obj)}",
            "garment_obj_url": f"file://{os.path.abspath(args.garment_obj)}",
            "smpl_params_url": f"file://{os.path.abspath(args.smpl_params)}" if args.smpl_params else None,
            "simulation_mode": args.mode,
            "garment_id": "test-garment",
            "size": "m",
            "user_id": "test-user",
        }
    }

    result = handler(test_event)

    if result.get("success"):
        print(f"\nSuccess! Method: {result['simulation_method']}")
        print(f"  Vertices: {result['vertex_count']}")
        print(f"  OBJ size: {result['obj_size_bytes'] / 1024:.1f} KB")
        print(f"  GLB size: {result['glb_size_bytes'] / 1024:.1f} KB")
        print(f"  Time: {result['processing_time_seconds']}s")

        if result.get("draped_glb_base64"):
            out = Path("test_draped_output.glb")
            out.write_bytes(base64.b64decode(result["draped_glb_base64"]))
            print(f"  Saved GLB: {out}")
    else:
        print(f"\nError: {result.get('error')}")
