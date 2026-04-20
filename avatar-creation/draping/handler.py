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

# --- numpy<2.0 shim for Newton 1.1.0 ---
# Newton's Style3D cloth module calls np.atan2 / np.pow, which only exist in
# numpy>=2.0. The RunPod pytorch:2.1.0 base image pins numpy<2 for torch ABI
# compatibility, so we expose the new names as aliases here. Must run BEFORE
# the Newton import below.
for _new, _old in (("atan2", "arctan2"), ("pow", "power"),
                   ("asin", "arcsin"), ("acos", "arccos"), ("atan", "arctan")):
    if not hasattr(np, _new):
        setattr(np, _new, getattr(np, _old))

try:
    import httpx
    USE_HTTPX = True
except ImportError:
    import requests
    USE_HTTPX = False

CONFIGS_DIR = Path("/workspace/configs")
RUNPOD_VOLUME = Path("/runpod-volume")

# --- Newton / Warp GPU cloth simulation ---
NEWTON_AVAILABLE = False
try:
    import warp as wp
    import newton
    from newton.solvers import style3d
    wp.init()
    NEWTON_AVAILABLE = True
    print(f"[Draping] Newton {newton.__version__} + Warp {wp.__version__} loaded — GPU cloth sim available")
except Exception as e:
    print(f"[Draping] Newton/Warp not available ({e}) — will use geometric fallback")


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
    with open(obj_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                parts = line.strip().split()
                if len(parts) >= 4:
                    try:
                        verts.append([float(parts[1]), float(parts[2]), float(parts[3])])
                    except ValueError:
                        continue
    return np.array(verts, dtype=np.float64)


def write_obj_with_new_verts(original_obj: Path, new_verts: np.ndarray, output_obj: Path):
    """Rewrite an OBJ file replacing only vertex positions, preserving faces/normals/UVs."""
    vi = 0
    lines_out = []
    with open(original_obj, "r", encoding="utf-8", errors="replace") as f:
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
    with open(body_obj, "r", encoding="utf-8", errors="replace") as f:
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


def align_meshes(body_verts: np.ndarray, garment_verts: np.ndarray) -> tuple:
    """
    Auto-align garment to body by matching height ranges and centering.
    CLO3D and SMPL may use different coordinate origins and scales.
    Returns (aligned_garment_verts, scale_factor, translation).
    """
    body_min_y, body_max_y = body_verts[:, 1].min(), body_verts[:, 1].max()
    garm_min_y, garm_max_y = garment_verts[:, 1].min(), garment_verts[:, 1].max()
    body_h = body_max_y - body_min_y
    garm_h = garm_max_y - garm_min_y

    if body_h < 1e-6 or garm_h < 1e-6:
        return garment_verts, 1.0, np.zeros(3)

    scale = body_h / garm_h
    height_ratio = garm_h / body_h
    print(f"[Draping] Alignment: body_h={body_h:.4f} garment_h={garm_h:.4f} ratio={height_ratio:.4f}")

    # Only rescale if significantly off (>20% difference)
    if 0.8 < height_ratio < 1.2:
        scale = 1.0
        print(f"[Draping] Scale close enough — no rescale")
    else:
        print(f"[Draping] Rescaling garment by {scale:.4f}")

    aligned = garment_verts.copy()
    aligned *= scale

    # Recalculate after scale
    garm_min_y = aligned[:, 1].min()
    garm_max_y = aligned[:, 1].max()

    # Match XZ center
    body_cx = (body_verts[:, 0].min() + body_verts[:, 0].max()) / 2
    body_cz = (body_verts[:, 2].min() + body_verts[:, 2].max()) / 2
    garm_cx = (aligned[:, 0].min() + aligned[:, 0].max()) / 2
    garm_cz = (aligned[:, 2].min() + aligned[:, 2].max()) / 2

    # Match feet (bottom Y)
    translation = np.array([
        body_cx - garm_cx,
        body_min_y - garm_min_y,
        body_cz - garm_cz,
    ])

    aligned += translation
    print(f"[Draping] Translation: dx={translation[0]:.4f} dy={translation[1]:.4f} dz={translation[2]:.4f}")

    return aligned, scale, translation


def load_obj_faces(obj_path: Path) -> np.ndarray:
    """Parse OBJ file and return triangle face indices as (M,3) int32 array."""
    faces = []
    with open(obj_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("f "):
                parts = line.strip().split()[1:]
                idxs = [int(p.split("/")[0]) - 1 for p in parts]
                if len(idxs) == 3:
                    faces.append(idxs)
                elif len(idxs) > 3:
                    for i in range(1, len(idxs) - 1):
                        faces.append([idxs[0], idxs[i], idxs[i + 1]])
    return np.array(faces, dtype=np.int32)


def load_obj_uvs(obj_path: Path) -> tuple:
    """Parse OBJ UV coords (vt lines) and face UV indices. Returns (uv_verts, uv_faces)."""
    uv_verts = []
    uv_faces = []
    with open(obj_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("vt "):
                parts = line.strip().split()
                if len(parts) >= 3:
                    try:
                        uv_verts.append([float(parts[1]), float(parts[2])])
                    except ValueError:
                        continue
            elif line.startswith("f "):
                parts = line.strip().split()[1:]
                idxs = []
                for p in parts:
                    segs = p.split("/")
                    if len(segs) >= 2 and segs[1]:
                        try:
                            idxs.append(int(segs[1]) - 1)
                        except ValueError:
                            break
                if len(idxs) == 3:
                    uv_faces.append(idxs)
                elif len(idxs) > 3:
                    for i in range(1, len(idxs) - 1):
                        uv_faces.append([idxs[0], idxs[i], idxs[i + 1]])
    uv_verts_arr = np.array(uv_verts, dtype=np.float32) if uv_verts else np.zeros((0, 2), dtype=np.float32)
    uv_faces_arr = np.array(uv_faces, dtype=np.int32) if uv_faces else np.zeros((0, 3), dtype=np.int32)
    return uv_verts_arr, uv_faces_arr


FABRIC_PRESETS = {
    "cotton_light":  {"density": 0.15, "tri_ke": 40.0,  "edge_ke": 5.0e-6, "particle_r": 2.0e-3},
    "cotton_medium": {"density": 0.30, "tri_ke": 50.0,  "edge_ke": 1.0e-5, "particle_r": 2.0e-3},
    "denim":         {"density": 0.50, "tri_ke": 150.0, "edge_ke": 4.0e-5, "particle_r": 2.0e-3},
    "silk":          {"density": 0.08, "tri_ke": 20.0,  "edge_ke": 2.5e-6, "particle_r": 2.0e-3},
    "jersey_knit":   {"density": 0.20, "tri_ke": 30.0,  "edge_ke": 5.0e-6, "particle_r": 2.0e-3},
    "wool":          {"density": 0.40, "tri_ke": 100.0, "edge_ke": 2.5e-5, "particle_r": 2.0e-3},
    "polyester":     {"density": 0.25, "tri_ke": 50.0,  "edge_ke": 7.5e-6, "particle_r": 2.0e-3},
}


def _inflate_garment_off_body(garment_verts, body_verts, body_obj, target_offset, max_iters=12):
    """Iteratively push every garment vertex outward along its nearest body normal
    until it sits at least `target_offset` (m) away from the body surface.

    Single-pass push is insufficient: after one push, the nearest body vertex can
    change, and a vert that was "outside" the old nearest body point may still
    be inside the new one. We loop until no vert is still penetrating (or we hit
    max_iters), which gives us a guaranteed non-penetrating initial state.

    Any residual non-finite positions after inflation are a hard error — better
    to fail fast than to hand a NaN mesh to Newton and burn 5 minutes on a
    guaranteed-NaN sim.
    """
    from scipy.spatial import cKDTree
    body_normals = compute_body_normals(body_verts, body_obj)
    tree = cKDTree(body_verts)

    inflated = garment_verts.astype(np.float64).copy()
    max_pushed = 0

    for it in range(max_iters):
        _, indices = tree.query(inflated, k=1)
        nearest_body = body_verts[indices]
        nearest_normals = body_normals[indices]
        diff = inflated - nearest_body
        signed_dist = np.sum(diff * nearest_normals, axis=1)

        needs_push = signed_dist < target_offset
        n_pushed = int(needs_push.sum())
        if n_pushed == 0:
            print(f"[Newton] Inflation converged after {it} iterations")
            break
        max_pushed = max(max_pushed, n_pushed)
        # Overshoot 10% + 0.1mm so the next iteration's nearest-vertex query
        # doesn't immediately re-flag the same vert due to floating-point noise.
        push_amt = ((target_offset - signed_dist[needs_push]) * 1.1 + 1e-4)[:, None] * nearest_normals[needs_push]
        inflated[needs_push] += push_amt
    else:
        print(f"[Newton] Inflation WARNING: hit max_iters={max_iters} with {n_pushed} verts still inside")

    if not np.isfinite(inflated).all():
        raise ValueError("Inflation produced non-finite garment vertices — body normals likely zero")

    # Post-check: how many verts are still within half the target offset?
    _, indices = tree.query(inflated, k=1)
    diff = inflated - body_verts[indices]
    signed_dist = np.sum(diff * body_normals[indices], axis=1)
    n_close = int((signed_dist < target_offset * 0.5).sum())
    print(f"[Newton] Inflation done: max {max_pushed}/{len(inflated)} verts pushed, "
          f"{n_close} still within {target_offset*500:.1f}mm of body")

    return inflated, max_pushed


def _normalize_to_meters(verts: np.ndarray, label: str) -> tuple:
    """If a mesh appears to be in millimetres (height >> 10), convert to meters.
    Newton/Warp expect SI units — gravity is m/s², so mm-scale meshes get effectively
    zero gravity force."""
    h = verts[:, 1].max() - verts[:, 1].min()
    if h > 50.0:
        print(f"[Newton] {label} looks like mm (height={h:.1f}), converting to meters")
        return verts / 1000.0, 1.0 / 1000.0
    return verts, 1.0


def _clean_garment_for_newton(verts, faces, uv_verts, uv_faces, area_eps=1e-6):
    """
    Pre-filter degenerate triangles before handing off to style3d.add_cloth_mesh().

    Newton 1.1.0 has a known bug where add_cloth_mesh runs two independent
    degeneracy filters (2D panel area in cloth.py and 3D world area in
    builder.add_triangles). When they disagree, tri_poses ends up longer than
    tri_indices, and SolverStyle3D's BVH constructor blows the assert
    `tri_indices.shape[0] == self.lower_bounds.shape[0]`.

    By dropping every triangle that BOTH filters would have dropped, we leave
    Newton's filters with nothing to do and the counts stay in sync.

    Returns (clean_verts, clean_faces, clean_uv_faces_or_None,
             clean_to_orig_vert_idx).
    """
    n_orig_faces = len(faces)
    n_orig_verts = len(verts)
    keep = np.ones(n_orig_faces, dtype=bool)

    # 1. Faces with repeated vertex indices (always zero-area in 3D AND UV)
    keep &= (faces[:, 0] != faces[:, 1])
    keep &= (faces[:, 1] != faces[:, 2])
    keep &= (faces[:, 0] != faces[:, 2])

    # 2. 3D zero-area triangles (matches builder.add_triangles filter)
    v0 = verts[faces[:, 0]]
    v1 = verts[faces[:, 1]]
    v2 = verts[faces[:, 2]]
    cross = np.cross(v1 - v0, v2 - v0)
    area_3d = 0.5 * np.linalg.norm(cross, axis=1)
    keep &= area_3d > area_eps

    # 3. Panel-area degeneracies (matches cloth.add_cloth_mesh filter)
    has_uvs = (
        uv_verts is not None and uv_faces is not None
        and len(uv_verts) > 0 and len(uv_faces) == n_orig_faces
    )
    if has_uvs:
        u0 = uv_verts[uv_faces[:, 0]]
        u1 = uv_verts[uv_faces[:, 1]]
        u2 = uv_verts[uv_faces[:, 2]]
        area_uv = 0.5 * np.abs(
            (u1[:, 0] - u0[:, 0]) * (u2[:, 1] - u0[:, 1])
            - (u2[:, 0] - u0[:, 0]) * (u1[:, 1] - u0[:, 1])
        )
        keep &= area_uv > area_eps
    else:
        # Newton falls back to vertices[:, :2] when panel_verts=None — drop
        # triangles that are degenerate in the XY projection too.
        e1_xy = (v1 - v0)[:, :2]
        e2_xy = (v2 - v0)[:, :2]
        area_xy = 0.5 * np.abs(e1_xy[:, 0] * e2_xy[:, 1] - e1_xy[:, 1] * e2_xy[:, 0])
        keep &= area_xy > area_eps

    n_kept_faces = int(keep.sum())
    n_dropped = n_orig_faces - n_kept_faces
    print(f"[Newton] Mesh cleanup: dropped {n_dropped}/{n_orig_faces} degenerate tris "
          f"(uvs={'yes' if has_uvs else 'no'})")

    if n_kept_faces < 4:
        raise ValueError(f"Garment cleanup left only {n_kept_faces} valid triangles")

    clean_faces = faces[keep]
    clean_uv_faces = uv_faces[keep] if has_uvs else None

    # Drop unreferenced verts and re-index faces; track mapping back to original.
    used_verts = np.unique(clean_faces.ravel())
    orig_to_clean = -np.ones(n_orig_verts, dtype=np.int64)
    orig_to_clean[used_verts] = np.arange(len(used_verts))
    clean_verts = verts[used_verts]
    clean_faces_remapped = orig_to_clean[clean_faces].astype(np.int32)
    print(f"[Newton] Mesh cleanup: {n_orig_verts - len(used_verts)} unused verts removed "
          f"({n_orig_verts} → {len(used_verts)})")

    return clean_verts, clean_faces_remapped, clean_uv_faces, used_verts


def newton_drape(
    body_obj: Path,
    garment_obj: Path,
    output_obj: Path,
    fabric_config: dict,
    simulation_mode: str = "swift",
) -> dict:
    """
    GPU-accelerated cloth draping using NVIDIA Newton 1.1.0 (Style3D XPBD solver).
    Real gravity, body collision, fabric tension. Y-up world coords, SI units.
    """
    from newton.solvers import SolverStyle3D

    body_verts_raw = load_obj_vertices(body_obj)
    garment_verts_raw = load_obj_vertices(garment_obj)
    body_faces = load_obj_faces(body_obj)
    garment_faces = load_obj_faces(garment_obj)

    if len(body_verts_raw) == 0 or len(garment_verts_raw) == 0:
        raise ValueError(f"Empty mesh: body={len(body_verts_raw)} garment={len(garment_verts_raw)} verts")
    if len(body_faces) == 0 or len(garment_faces) == 0:
        raise ValueError(f"No faces: body={len(body_faces)} garment={len(garment_faces)} tris")

    print(f"[Newton] Body raw: {len(body_verts_raw)} verts, {len(body_faces)} tris")
    print(f"[Newton] Garment raw: {len(garment_verts_raw)} verts, {len(garment_faces)} tris")

    # Normalize both meshes to meters BEFORE alignment so gravity (m/s²) is meaningful
    body_verts, _ = _normalize_to_meters(body_verts_raw, "Body")
    garment_verts, garment_unit_scale = _normalize_to_meters(garment_verts_raw, "Garment")

    aligned_verts, align_scale, translation = align_meshes(body_verts, garment_verts)

    # Resolve fabric properties
    preset_name = fabric_config.get("preset", "cotton_medium")
    preset = FABRIC_PRESETS.get(preset_name, FABRIC_PRESETS["cotton_medium"])
    density = fabric_config.get("density", preset["density"])
    tri_ke = preset["tri_ke"]
    edge_ke = preset["edge_ke"]
    particle_r = preset["particle_r"]

    # Inflate the garment off the body BEFORE cleanup + sim. 20mm gives us headroom
    # for nearest-vertex approximation error (true surface distance can be less than
    # nearest-vertex signed distance when the closest body point is on a triangle
    # face rather than a vertex). Iterative push handles the case where one push
    # changes the nearest-body-vertex for a given garment vert.
    inflate_offset = 20.0e-3
    aligned_verts, n_inflated = _inflate_garment_off_body(
        aligned_verts, body_verts, body_obj, inflate_offset
    )
    print(f"[Newton] Garment inflation summary: max pushed {n_inflated}/{len(aligned_verts)} "
          f"(target ≥{inflate_offset*1000:.1f}mm off body)")

    n_frames = 200 if simulation_mode == "quality" else 120
    # Match the canonical example_cloth_style3d.py: 10 substeps @ 1/600s = 16.67ms/frame.
    # Smaller dt is critical for stability — sim_dt=1/240 was too coarse and diverged.
    sim_substeps = 10
    dt = 1.0 / (60.0 * sim_substeps)

    print(f"[Newton] Fabric: {preset_name} (density={density}, tri_ke={tri_ke}, edge_ke={edge_ke})")
    print(f"[Newton] Sim: {n_frames} frames x {sim_substeps} substeps @ dt={dt:.5f}s")

    # Load UVs for Style3D panel data (used for warp/weft direction)
    uv_verts_raw, uv_faces_raw = load_obj_uvs(garment_obj)

    # Pre-clean garment to dodge Newton 1.1.0's add_cloth_mesh dual-filter bug.
    # Both filters (3D area in builder.add_triangles, 2D area in cloth.add_cloth_mesh)
    # must agree on which triangles to drop, or SolverStyle3D's BVH crashes.
    clean_garment_verts, clean_garment_faces, clean_uv_faces, clean_to_orig = \
        _clean_garment_for_newton(aligned_verts, garment_faces, uv_verts_raw, uv_faces_raw)
    has_uvs = clean_uv_faces is not None

    # Defensive: the sim burns 4+ minutes, so fail fast if inputs are already NaN.
    if not np.isfinite(clean_garment_verts).all():
        raise ValueError("Cleaned garment contains non-finite vertices — aborting before sim")
    cv_min = clean_garment_verts.min(axis=0)
    cv_max = clean_garment_verts.max(axis=0)
    print(f"[Newton] Pre-sim cloth bbox: x=[{cv_min[0]:.3f},{cv_max[0]:.3f}] "
          f"y=[{cv_min[1]:.3f},{cv_max[1]:.3f}] z=[{cv_min[2]:.3f},{cv_max[2]:.3f}]")

    # --- Build Newton scene (single builder, Y-up to match input meshes) ---
    builder = newton.ModelBuilder(up_axis=newton.Axis.Y)
    SolverStyle3D.register_custom_attributes(builder)

    body_mesh = newton.Mesh(
        body_verts.astype(np.float32),
        body_faces.flatten().astype(np.int32),
    )
    # CRITICAL: use builder.add_body() to register the static collider.
    # body=-1 sends the contact kernel into undefined memory (issue #1130 pattern)
    # because Style3D's eval_body_contact_kernel indexes body_q[shape_body[shape_idx]].
    # add_body() defaults to mass=0 → body_inv_mass=0 → ignores gravity. The
    # is_kinematic flag (BodyFlags.KINEMATIC) is belt-and-suspenders so any future
    # solver path that checks the flag also treats it as fixed. This is the
    # canonical static-avatar pattern from example_cloth_style3d.py:74-81.
    avatar_body = builder.add_body(is_kinematic=True)
    builder.add_shape_mesh(
        body=avatar_body,
        xform=wp.transform(p=wp.vec3(0.0, 0.0, 0.0), q=wp.quat_identity()),
        mesh=body_mesh,
        scale=wp.vec3(1.0, 1.0, 1.0),
    )

    # NOTE: panel_verts deliberately OMITTED. CLO3D UV atlas layout doesn't
    # match the scale/topology Style3D expects for rest-pose reconstruction:
    # passing face-indexed UVs caused instant 99% NaN at frame 1. With
    # panel_verts=None, Style3D falls back to using the initial 3D positions
    # as the rest pose — which is exactly what we want after inflation, because
    # the cloth starts stress-free instead of being flagged as "50% stretched"
    # and released like a catapult. We lose CLO3D's anisotropic warp/weft
    # direction but gain a sim that actually converges.
    style3d.add_cloth_mesh(
        builder,
        pos=wp.vec3(0.0, 0.0, 0.0),
        rot=wp.quat_identity(),
        vel=wp.vec3(0.0, 0.0, 0.0),
        vertices=clean_garment_verts.astype(np.float32).tolist(),
        indices=clean_garment_faces.flatten().tolist(),
        density=density,
        scale=1.0,
        particle_radius=particle_r,
        tri_aniso_ke=wp.vec3(tri_ke, tri_ke, tri_ke * 0.1),
        edge_aniso_ke=wp.vec3(edge_ke * 2.0, edge_ke, edge_ke * 0.25),
        panel_verts=None,
        panel_indices=None,
    )

    # Defensive: surface the dual-filter mismatch with a clear error rather than
    # letting SolverStyle3D's BVH assert blow up cryptically.
    n_tri_idx = len(builder.tri_indices)
    n_tri_pos = len(builder.tri_poses)
    if n_tri_idx != n_tri_pos:
        raise RuntimeError(
            f"Newton tri-list mismatch after cleanup: tri_indices={n_tri_idx} "
            f"tri_poses={n_tri_pos}. Tighten area_eps in _clean_garment_for_newton."
        )
    print(f"[Newton] Builder OK: {n_tri_idx} cloth tris registered")

    device = "cuda:0"
    model = builder.finalize(device=device)
    model.set_gravity((0.0, -9.81, 0.0))
    # Match canonical example_cloth_style3d.py soft-contact params. Newton's defaults
    # (radius=0.01, ke=1e3, kf=1e3, mu=0.5) are tuned for rigid bodies and explode
    # cloth on contact. mu=0.0 also matches PR #1500 H1 fix — friction sign-flip at
    # near-zero tangential velocity is a known NaN source.
    # Contact tuning: ke=1e2 is 10x the prior value (which let cloth drift through
    # the body faster than the restoring force could push it back) but still 10x
    # softer than Newton's rigid-body default (1e3) which explodes cloth. kd adds
    # damping so contact oscillations decay instead of resonating.
    model.soft_contact_radius = 0.3e-2
    model.soft_contact_margin = 0.5e-2
    model.soft_contact_ke = 1.0e2
    model.soft_contact_kd = 1.0e0
    model.soft_contact_kf = 0.0
    model.soft_contact_mu = 0.0

    state_0 = model.state()
    state_1 = model.state()
    control = model.control()
    contacts = model.contacts()

    # iterations=4 matches canonical. Higher counts over-relax with stiff cloth + PD
    # solver and can diverge when the contact Hessian is rank-deficient.
    solver = SolverStyle3D(model=model, iterations=4)
    solver._precompute(builder)

    print(f"[Newton] Running {n_frames} frames on {device}...")
    sim_start = time.time()

    diag_every = 10  # log finite-mask + position bounds every N frames
    first_nan_frame = None

    for frame in range(n_frames):
        # collide() inside the substep loop, not once per outer frame. With moving
        # cloth the contact normals from frame start are stale by the last substep,
        # producing wrong-direction forces — matches example_cloth_h1.py simulate().
        for _ in range(sim_substeps):
            model.collide(state_0, contacts)
            state_0.clear_forces()
            solver.step(state_0, state_1, control, contacts, dt)
            state_0, state_1 = state_1, state_0

        if (frame + 1) % diag_every == 0 or frame == 0:
            q = state_0.particle_q.numpy()
            n_cloth_now = len(clean_garment_verts)
            cloth_q = q[:n_cloth_now]
            n_nan = int((~np.isfinite(cloth_q).all(axis=1)).sum())
            finite_mask_q = np.isfinite(cloth_q).all(axis=1)
            if finite_mask_q.any():
                qmin = float(cloth_q[finite_mask_q].min())
                qmax = float(cloth_q[finite_mask_q].max())
            else:
                qmin = qmax = float("nan")
            elapsed = time.time() - sim_start
            print(f"[Newton] Frame {frame+1}/{n_frames} ({elapsed:.1f}s) "
                  f"nan={n_nan}/{n_cloth_now} q∈[{qmin:.3f},{qmax:.3f}]")
            if n_nan > 0 and first_nan_frame is None:
                first_nan_frame = frame + 1
                print(f"[Newton] FIRST NAN appeared by frame {first_nan_frame}")

    sim_time = time.time() - sim_start
    print(f"[Newton] Simulation done in {sim_time:.1f}s")

    # Extract final cloth vertex positions. Static collision shapes (body=-1) add
    # NO particles, so cloth particles occupy [0:n_clean) in input order. n_clean
    # is the post-cleanup vertex count, NOT the original garment vertex count.
    final_positions = state_0.particle_q.numpy()
    n_clean = len(clean_garment_verts)
    if len(final_positions) < n_clean:
        raise RuntimeError(f"Expected {n_clean} cloth particles, got {len(final_positions)}")
    cloth_positions_clean = final_positions[:n_clean]
    print(f"[Newton] Extracted {len(cloth_positions_clean)} draped vertex positions")

    # Sanitize: any particle that exploded to NaN/inf gets reset to its pre-sim
    # position. Common when stiff cloth starts with verts inside the body
    # collision mesh (e.g. hood interior inside the head). Better to keep a few
    # un-draped verts than to crash the downstream KDTree/GLB pipeline.
    finite_mask = np.isfinite(cloth_positions_clean).all(axis=1)
    n_bad = int((~finite_mask).sum())
    if n_bad > 0:
        pre_sim_clean = aligned_verts[clean_to_orig].astype(np.float64)
        cloth_positions_clean = np.where(
            finite_mask[:, None], cloth_positions_clean.astype(np.float64), pre_sim_clean
        )
        print(f"[Newton] WARNING: {n_bad}/{n_clean} particles NaN/inf — restored pre-sim pos")

    # Map cleaned vertex positions back into the original garment vertex array.
    # Verts that were unreferenced after cleanup keep their pre-sim aligned position
    # so the original OBJ topology + texture pipeline still works downstream.
    cloth_positions_full = aligned_verts.copy().astype(np.float64)
    cloth_positions_full[clean_to_orig] = cloth_positions_clean.astype(np.float64)

    # Undo alignment translation/scale (still in meters)
    if align_scale != 1.0:
        final_verts_m = (cloth_positions_full - translation) / align_scale
    else:
        final_verts_m = cloth_positions_full - translation

    # Restore original garment units (e.g. back to mm if input was mm)
    if garment_unit_scale != 1.0:
        final_verts = final_verts_m / garment_unit_scale
    else:
        final_verts = final_verts_m

    write_obj_with_new_verts(garment_obj, final_verts.astype(np.float64), output_obj)

    return {
        "vertices_total": len(garment_verts_raw),
        "vertices_simulated": int(n_clean),
        "triangles_simulated": int(len(clean_garment_faces)),
        "simulation_frames": n_frames,
        "simulation_substeps": sim_substeps,
        "simulation_time_seconds": round(sim_time, 2),
        "fabric_preset": preset_name,
        "align_scale": round(align_scale, 6),
        "translation_m": [round(float(t), 6) for t in translation],
        "garment_unit_scale": round(garment_unit_scale, 6),
    }


def _build_adjacency(faces, n_verts):
    """Build vertex adjacency list from face list."""
    adjacency = [set() for _ in range(n_verts)]
    for face in faces:
        for i in range(len(face)):
            for j in range(len(face)):
                if i != j:
                    adjacency[face[i]].add(face[j])
    return [list(s) for s in adjacency]


def _build_edge_rest_lengths(verts, adjacency):
    """Compute rest-state edge lengths for spring constraints."""
    rest_lengths = {}
    for vi, neighbors in enumerate(adjacency):
        for ni in neighbors:
            key = (min(vi, ni), max(vi, ni))
            if key not in rest_lengths:
                rest_lengths[key] = np.linalg.norm(verts[vi] - verts[ni])
    return rest_lengths


def geometric_drape(
    body_obj: Path,
    garment_obj: Path,
    output_obj: Path,
    fabric_config: dict,
) -> dict:
    """
    Multi-pass geometric draping with gravity settling, spring constraints,
    and iterative collision resolution. Runs DRAPE_PASSES full cycles so
    the fabric has time to "settle" onto the body.

    Each pass:
      a. Gravity pull (small downward step on free-hanging verts)
      b. Collision push (push penetrating verts outward along body normals)
      c. Spring relaxation (prevent excessive stretching vs rest pose)
      d. Laplacian smoothing (reduce harsh artifacts)
      e. Final collision cleanup (catch anything smoothing re-introduced)
    """
    from scipy.spatial import cKDTree

    body_verts = load_obj_vertices(body_obj)
    garment_verts = load_obj_vertices(garment_obj)

    if len(body_verts) == 0 or len(garment_verts) == 0:
        raise ValueError(f"Empty mesh: body={len(body_verts)} garment={len(garment_verts)} verts")

    print(f"[Draping] Body: {len(body_verts)} verts, Y=[{body_verts[:,1].min():.4f}, {body_verts[:,1].max():.4f}]")
    print(f"[Draping] Garment: {len(garment_verts)} verts, Y=[{garment_verts[:,1].min():.4f}, {garment_verts[:,1].max():.4f}]")

    aligned_verts, scale, translation = align_meshes(body_verts, garment_verts)

    thickness = fabric_config.get("thickness", 0.006)
    offset = max(thickness, 0.006)

    body_normals = compute_body_normals(body_verts, body_obj)
    tree = cKDTree(body_verts)

    garment_faces = []
    with open(garment_obj, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("f "):
                parts = line.strip().split()[1:]
                idxs = [int(p.split("/")[0]) - 1 for p in parts]
                if len(idxs) >= 3:
                    garment_faces.append(idxs[:3])

    adjacency = _build_adjacency(garment_faces, len(aligned_verts))
    rest_lengths = _build_edge_rest_lengths(aligned_verts, adjacency)

    DRAPE_PASSES = 8
    SMOOTH_ITERS = 4
    GRAVITY_STEP = 0.0008
    SPRING_STIFFNESS = 0.3
    SMOOTH_FACTOR = 0.25

    new_verts = aligned_verts.copy()
    total_pushed = 0

    print(f"[Draping] Running {DRAPE_PASSES} drape passes (offset={offset:.4f}m)...")

    for p in range(DRAPE_PASSES):
        # (a) Gravity: gently pull free-hanging verts down
        distances_g, _ = tree.query(new_verts, k=1)
        gravity_mask = distances_g > offset * 2
        if np.any(gravity_mask):
            new_verts[gravity_mask, 1] -= GRAVITY_STEP

        # (b) Collision: push penetrating verts outward
        distances, indices = tree.query(new_verts, k=1)
        nearest_body = body_verts[indices]
        nearest_normals = body_normals[indices]
        diff = new_verts - nearest_body
        dots = np.sum(diff * nearest_normals, axis=1)
        needs_push = dots < offset
        if np.any(needs_push):
            push_amount = (offset - dots[needs_push])[:, np.newaxis] * nearest_normals[needs_push]
            new_verts[needs_push] += push_amount * 1.1
            total_pushed += int(np.sum(needs_push))

        # (c) Spring relaxation: prevent excessive stretching
        for edge, rest_len in rest_lengths.items():
            vi, vj = edge
            delta = new_verts[vj] - new_verts[vi]
            current_len = np.linalg.norm(delta)
            if current_len < 1e-10:
                continue
            stretch = current_len - rest_len
            if abs(stretch) > rest_len * 0.01:
                correction = (delta / current_len) * stretch * SPRING_STIFFNESS * 0.5
                new_verts[vi] += correction
                new_verts[vj] -= correction

        # (d) Laplacian smoothing
        for _ in range(SMOOTH_ITERS):
            smoothed = new_verts.copy()
            for vi in range(len(new_verts)):
                if not adjacency[vi]:
                    continue
                avg = np.mean(new_verts[adjacency[vi]], axis=0)
                smoothed[vi] = (1 - SMOOTH_FACTOR) * new_verts[vi] + SMOOTH_FACTOR * avg
            new_verts = smoothed

        # (e) Post-smooth collision cleanup
        distances2, indices2 = tree.query(new_verts, k=1)
        diff2 = new_verts - body_verts[indices2]
        dots2 = np.sum(diff2 * body_normals[indices2], axis=1)
        still_pen = dots2 < offset
        if np.any(still_pen):
            push2 = (offset - dots2[still_pen])[:, np.newaxis] * body_normals[indices2[still_pen]]
            new_verts[still_pen] += push2

        n_pen = int(np.sum(still_pen))
        print(f"[Draping] Pass {p+1}/{DRAPE_PASSES}: {n_pen} verts still penetrating")

    # Final stats
    distances_f, indices_f = tree.query(new_verts, k=1)
    diff_f = new_verts - body_verts[indices_f]
    dots_f = np.sum(diff_f * body_normals[indices_f], axis=1)
    final_penetrating = int(np.sum(dots_f < offset * 0.5))
    print(f"[Draping] Final: {final_penetrating} verts within half-offset of body")

    # Undo alignment to restore original garment coordinate space
    final_verts = (new_verts - translation) / scale if scale != 1.0 else new_verts - translation

    write_obj_with_new_verts(garment_obj, final_verts, output_obj)

    return {
        "vertices_total": len(garment_verts),
        "vertices_fixed": total_pushed,
        "final_penetrating": final_penetrating,
        "penetration_ratio": round(final_penetrating / len(garment_verts), 4) if len(garment_verts) > 0 else 0,
        "passes": DRAPE_PASSES,
        "scale_applied": round(scale, 6),
        "translation": [round(float(t), 6) for t in translation],
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


def inject_verts_into_glb(draped_obj: Path, original_glb: Path, output_glb: Path) -> bool:
    """
    Take draped vertex positions from OBJ and inject them into the original GLB,
    preserving all materials, textures, UVs, and face topology.
    Falls back to bare trimesh conversion if the original GLB isn't available.
    """
    try:
        import trimesh
        import struct

        draped_verts = load_obj_vertices(draped_obj)
        if len(draped_verts) == 0:
            print("[Draping] No vertices in draped OBJ, falling back to bare conversion")
            return _obj_to_glb_bare(draped_obj, output_glb)

        if not original_glb.exists():
            print("[Draping] No original GLB, falling back to bare conversion")
            return _obj_to_glb_bare(draped_obj, output_glb)

        # Load original GLB with all materials intact
        scene = trimesh.load(str(original_glb), process=False)

        # Extract meshes from scene
        if isinstance(scene, trimesh.Scene):
            meshes = list(scene.geometry.values())
        else:
            meshes = [scene]

        total_original_verts = sum(len(m.vertices) for m in meshes)
        print(f"[Draping] Original GLB: {len(meshes)} mesh(es), {total_original_verts} total verts")
        print(f"[Draping] Draped OBJ: {len(draped_verts)} verts")

        if total_original_verts == len(draped_verts):
            # Vertex counts match — replace positions directly
            vi = 0
            for m in meshes:
                n = len(m.vertices)
                m.vertices = draped_verts[vi:vi + n].astype(np.float64)
                vi += n
            print(f"[Draping] Injected {vi} draped verts into original GLB (exact match)")
        else:
            print(f"[Draping] Vertex count mismatch ({total_original_verts} vs {len(draped_verts)}), "
                  f"using nearest-vertex mapping")
            from scipy.spatial import cKDTree

            # Map draped verts to original mesh verts by proximity
            draped_tree = cKDTree(draped_verts)
            vi = 0
            for m in meshes:
                orig_verts = np.array(m.vertices)
                _, indices = draped_tree.query(orig_verts, k=1)
                m.vertices = draped_verts[indices].astype(np.float64)
                vi += len(orig_verts)

        if isinstance(scene, trimesh.Scene):
            scene.export(str(output_glb), file_type="glb")
        else:
            meshes[0].export(str(output_glb), file_type="glb")

        print(f"[Draping] GLB with textures: {output_glb.stat().st_size / 1024:.1f} KB")
        return True

    except Exception as e:
        print(f"[Draping] Texture-preserving GLB failed: {e}")
        import traceback
        traceback.print_exc()
        return _obj_to_glb_bare(draped_obj, output_glb)


def _obj_to_glb_bare(obj_path: Path, glb_path: Path) -> bool:
    """Bare OBJ→GLB conversion without textures (last resort)."""
    try:
        import trimesh
        mesh = trimesh.load(str(obj_path), force="mesh", process=False)
        mesh.export(str(glb_path), file_type="glb")
        return True
    except Exception as e:
        print(f"[Draping] Bare OBJ→GLB conversion failed: {e}")
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

    garment_glb_url = job_input.get("garment_glb_url")

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
        garment_glb = tmp_dir / "garment_original.glb"
        smpl_params = tmp_dir / "smpl_params.npz"
        output_dir = tmp_dir / "output"
        output_dir.mkdir()

        print("[Draping] Downloading input files...")
        if not download_file(body_obj_url, body_obj):
            return {"error": "Failed to download body OBJ", "success": False}
        if not download_file(garment_obj_url, garment_obj):
            return {"error": "Failed to download garment OBJ", "success": False}

        # Also pull the MTL and any referenced texture files from the same
        # Supabase folder as the OBJ so the frontend can render OBJ+MTL with
        # proper diffuse textures (CLO3D exports OBJ, MTL, and PNG/JPG side by
        # side). Without this the OBJ path always falls back to GLB.
        url_dir = garment_obj_url.rsplit("/", 1)[0]
        obj_text_pre = garment_obj.read_bytes().decode("utf-8", errors="replace")
        mtl_name_in_obj = None
        for _line in obj_text_pre.split("\n"):
            if _line.startswith("mtllib "):
                mtl_name_in_obj = _line.strip().split(None, 1)[1].strip()
                break
        mtl_candidates = []
        if mtl_name_in_obj:
            mtl_candidates.append(mtl_name_in_obj)
        obj_basename = garment_obj_url.rsplit("/", 1)[-1]
        if obj_basename.endswith(".obj"):
            mtl_candidates.append(obj_basename[:-4] + ".mtl")
        seen = set()
        for mtl_cand in mtl_candidates:
            if mtl_cand in seen:
                continue
            seen.add(mtl_cand)
            mtl_dest = garment_obj.parent / mtl_cand
            if mtl_dest.exists():
                continue
            if download_file(f"{url_dir}/{mtl_cand}", mtl_dest):
                print(f"[Draping] Downloaded MTL: {mtl_cand} ({mtl_dest.stat().st_size / 1024:.1f} KB)")
                # CLO3D bakes absolute local paths into MTLs (e.g.
                # "/Users/someone/Downloads/1.png"). Neither Supabase nor the
                # frontend MTLLoader can resolve those, so rewrite every
                # map_*/bump line to use just the basename. We upload textures
                # under the same basename to Supabase, and Three.js MTLLoader
                # then keys its sourceFile lookup on that same basename.
                _mtl_text = mtl_dest.read_bytes().decode("utf-8", errors="replace")
                _rewritten_lines = []
                for _mline in _mtl_text.split("\n"):
                    _stripped = _mline.strip()
                    if _stripped.startswith("map_") or _stripped.startswith("bump"):
                        _parts = _stripped.split()
                        if len(_parts) >= 2:
                            _tex_full = _parts[-1]
                            # Handle both POSIX and Windows-style path separators
                            _tex_base = _tex_full.replace("\\", "/").rsplit("/", 1)[-1]
                            _parts[-1] = _tex_base
                            _rewritten_lines.append(" ".join(_parts))
                            continue
                    _rewritten_lines.append(_mline)
                mtl_dest.write_text("\n".join(_rewritten_lines))

                # Parse rewritten MTL (now all basenames) and download each texture
                for _mline in mtl_dest.read_text().split("\n"):
                    _mline = _mline.strip()
                    if _mline.startswith("map_") or _mline.startswith("bump"):
                        _parts = _mline.split()
                        if len(_parts) >= 2:
                            tex_name = _parts[-1]  # already basename after rewrite
                            tex_dest = garment_obj.parent / tex_name
                            if not tex_dest.exists():
                                if download_file(f"{url_dir}/{tex_name}", tex_dest):
                                    print(f"[Draping] Downloaded texture: {tex_name} "
                                          f"({tex_dest.stat().st_size / 1024:.1f} KB)")
                                else:
                                    print(f"[Draping] Texture missing on Supabase: {tex_name} "
                                          f"(upload it to {url_dir}/)")
                break  # first MTL candidate that works wins

        if garment_glb_url:
            download_file(garment_glb_url, garment_glb)
            print(f"[Draping] Original GLB: {garment_glb.stat().st_size / 1024:.1f} KB")
        elif garment_obj_url.endswith(".obj"):
            glb_guess = garment_obj_url.rsplit(".obj", 1)[0] + ".glb"
            print(f"[Draping] Trying to download matching GLB: {glb_guess}")
            download_file(glb_guess, garment_glb)
        if smpl_params_url:
            download_file(smpl_params_url, smpl_params)

        print(f"[Draping] Body OBJ: {body_obj.stat().st_size / 1024:.1f} KB")
        print(f"[Draping] Garment OBJ: {garment_obj.stat().st_size / 1024:.1f} KB")

        simulation_method = "unknown"
        draped_obj = None
        sim_stats = {}

        # Strategy 1: Newton GPU cloth simulation (real physics)
        if NEWTON_AVAILABLE:
            try:
                print("[Draping] Running Newton GPU cloth simulation...")
                draped_obj = output_dir / "draped.obj"
                sim_stats = newton_drape(
                    body_obj=body_obj,
                    garment_obj=garment_obj,
                    output_obj=draped_obj,
                    fabric_config=merged_fabric,
                    simulation_mode=simulation_mode,
                )
                simulation_method = "newton_gpu"
                print(f"[Draping] Newton success: {sim_stats}")
            except Exception as e:
                print(f"[Draping] Newton failed, falling back to geometric: {e}")
                import traceback
                traceback.print_exc()
                draped_obj = None

        # Strategy 2: geometric fallback (no real physics, just collision resolution)
        if draped_obj is None:
            try:
                print("[Draping] Running geometric drape fallback...")
                draped_obj = output_dir / "draped.obj"
                sim_stats = geometric_drape(
                    body_obj=body_obj,
                    garment_obj=garment_obj,
                    output_obj=draped_obj,
                    fabric_config=merged_fabric,
                )
                simulation_method = "geometric_fallback"
                print(f"[Draping] Geometric drape done: {sim_stats}")
            except Exception as e:
                print(f"[Draping] Geometric drape failed: {e}")
                import traceback
                traceback.print_exc()
                return {"error": f"All draping methods failed: {e}", "success": False}

        # Read draped OBJ
        obj_bytes = draped_obj.read_bytes()
        obj_b64 = base64.b64encode(obj_bytes).decode("utf-8")

        # Collect MTL + texture files from the original garment OBJ directory
        mtl_b64 = ""
        textures_b64 = {}
        mtl_name = None
        obj_text = obj_bytes.decode("utf-8", errors="replace")
        for line in obj_text.split("\n"):
            if line.startswith("mtllib "):
                mtl_name = line.strip().split(None, 1)[1].strip()
                break

        if mtl_name:
            mtl_source = garment_obj.parent / mtl_name
            if mtl_source.exists():
                mtl_bytes = mtl_source.read_bytes()
                mtl_b64 = base64.b64encode(mtl_bytes).decode("utf-8")
                print(f"[Draping] MTL: {mtl_name} ({len(mtl_bytes)/1024:.1f} KB)")

                mtl_text = mtl_bytes.decode("utf-8", errors="replace")
                for mtl_line in mtl_text.split("\n"):
                    mtl_line = mtl_line.strip()
                    if mtl_line.startswith("map_") or mtl_line.startswith("bump"):
                        parts = mtl_line.split()
                        if len(parts) >= 2:
                            # Belt-and-suspenders: the pre-sim download pass already
                            # rewrote the MTL to use basenames, but if anything else
                            # injected an absolute path, fall back to basename here too.
                            tex_filename = parts[-1].replace("\\", "/").rsplit("/", 1)[-1]
                            tex_path = garment_obj.parent / tex_filename
                            if tex_path.exists() and tex_path.stat().st_size < 10_000_000:
                                tex_bytes = tex_path.read_bytes()
                                textures_b64[tex_filename] = base64.b64encode(tex_bytes).decode("utf-8")
                                print(f"[Draping] Texture: {tex_filename} ({len(tex_bytes)/1024:.1f} KB)")

        # Convert to GLB (preserve original textures/materials when possible)
        glb_path = output_dir / "draped.glb"
        glb_b64 = ""
        glb_bytes = b""
        if garment_glb.exists() and garment_glb.stat().st_size > 0:
            print("[Draping] Using texture-preserving GLB conversion...")
            if inject_verts_into_glb(draped_obj, garment_glb, glb_path):
                glb_bytes = glb_path.read_bytes()
                glb_b64 = base64.b64encode(glb_bytes).decode("utf-8")
        else:
            print("[Draping] No original GLB available, bare conversion...")
            if _obj_to_glb_bare(draped_obj, glb_path):
                glb_bytes = glb_path.read_bytes()
                glb_b64 = base64.b64encode(glb_bytes).decode("utf-8")
                print(f"[Draping] GLB (no textures): {len(glb_bytes) / 1024:.1f} KB")

        vertex_count = len(load_obj_vertices(draped_obj))
        processing_time = time.time() - start_time

        print(f"[Draping] Complete in {processing_time:.1f}s via {simulation_method}")

        return {
            "draped_obj_base64": obj_b64,
            "draped_mtl_base64": mtl_b64,
            "draped_textures_base64": textures_b64,
            "draped_glb_base64": glb_b64,
            "processing_time_seconds": round(processing_time, 1),
            "simulation_method": simulation_method,
            "vertex_count": vertex_count,
            "obj_size_bytes": len(obj_bytes),
            "glb_size_bytes": len(glb_bytes) if glb_b64 else 0,
            "garment_id": garment_id,
            "size": size,
            "user_id": user_id,
            "sim_stats": sim_stats,
            "success": True,
        }


def runpod_handler(event):
    """Wrapper for RunPod serverless."""
    return handler(event)


HANDLER_BUILD = "drape-handler 2026-04-20/v4.1-mtl-basename (v4+rewrite-CLO3D-absolute-tex-paths-to-basenames)"

try:
    import runpod
    print(f"[Draping] === {HANDLER_BUILD} ===")
    print("[Draping] Starting serverless cloth draping handler...")
    print(f"[Draping] Newton GPU sim available: {NEWTON_AVAILABLE}")
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
