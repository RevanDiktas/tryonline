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
    from newton import ParticleFlags
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


def _weld_duplicate_vertices(verts: np.ndarray, faces: np.ndarray, tol: float = 1.0e-3) -> tuple:
    """Merge vertices within `tol` metres into one. Returns
    (welded_verts, welded_faces, orig_to_welded).

    CLO3D's OBJ exporter writes seam-split vertices — the same 3D point
    appears as several distinct vertex indices, one per panel piece it
    belongs to. Without welding, the face-graph splits into as many
    topologically-disconnected components as there are panels, so
    stretch/bending forces cannot hold the garment together and the
    panels fall independently under gravity. Welding fixes this by
    collapsing positions within `tol` to a single canonical index.

    Verified against m.obj (Ramin Studios hoodie): raw 27718 verts → 28
    topological components. Welding at tol=1mm collapses 1511 duplicate
    pairs → 1 component.
    """
    from scipy.spatial import cKDTree
    n_orig = len(verts)
    tree = cKDTree(verts)
    pairs = tree.query_pairs(tol, output_type="ndarray")

    parent = np.arange(n_orig)

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = int(parent[i])
        return int(i)

    for a, b in pairs:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[ra] = rb

    roots = np.array([find(i) for i in range(n_orig)], dtype=np.int64)
    unique_roots, welded_idx = np.unique(roots, return_inverse=True)
    welded_verts = verts[unique_roots].copy()
    welded_faces = welded_idx[faces].astype(np.int32)

    n_welded = len(welded_verts)
    print(f"[Newton] Weld: {n_orig} → {n_welded} verts "
          f"({n_orig - n_welded} duplicates merged at tol={tol*1000:.2f}mm, "
          f"{len(pairs)} pair candidates)")
    return welded_verts, welded_faces, welded_idx.astype(np.int64)


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
    # tri_ke/edge_ke/particle_r aligned with canonical example_cloth_style3d.py
    # (cotton: tri_ke=100, particle_r=5e-3). Other fabrics scaled proportionally.
    "cotton_light":  {"density": 0.15, "tri_ke": 80.0,  "edge_ke": 5.0e-6, "particle_r": 5.0e-3},
    "cotton_medium": {"density": 0.30, "tri_ke": 100.0, "edge_ke": 1.0e-5, "particle_r": 5.0e-3},
    "denim":         {"density": 0.50, "tri_ke": 300.0, "edge_ke": 4.0e-5, "particle_r": 5.0e-3},
    "silk":          {"density": 0.08, "tri_ke": 40.0,  "edge_ke": 2.5e-6, "particle_r": 5.0e-3},
    "jersey_knit":   {"density": 0.20, "tri_ke": 60.0,  "edge_ke": 5.0e-6, "particle_r": 5.0e-3},
    "wool":          {"density": 0.40, "tri_ke": 200.0, "edge_ke": 2.5e-5, "particle_r": 5.0e-3},
    "polyester":     {"density": 0.25, "tri_ke": 100.0, "edge_ke": 7.5e-6, "particle_r": 5.0e-3},
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

    # Post-check: which verts are still inside (signed_dist < 0) or within a
    # thin safety margin? Those will be pinned in the sim so they don't produce
    # explosive contact forces on their neighbors.
    _, indices = tree.query(inflated, k=1)
    diff = inflated - body_verts[indices]
    signed_dist = np.sum(diff * body_normals[indices], axis=1)
    # "Stuck" = still penetrating or within 1mm of surface after inflation.
    stuck_mask = signed_dist < 1.0e-3
    n_stuck = int(stuck_mask.sum())
    n_close = int((signed_dist < target_offset * 0.5).sum())
    print(f"[Newton] Inflation done: max {max_pushed}/{len(inflated)} verts pushed, "
          f"{n_close} still within {target_offset*500:.1f}mm of body, "
          f"{n_stuck} stuck (<1mm) → will be pinned")

    return inflated, max_pushed, stuck_mask


def _build_geodesic_unfold_panel(verts_3d: np.ndarray, faces: np.ndarray) -> tuple:
    """Build a 2D panel by BFS-unfolding the 3D mesh while preserving edge lengths.

    Each triangle gets 3 unique panel-vert indices (3*N_tris panel verts total),
    but their 2D COORDINATES are assigned such that for every edge shared by
    two adjacent triangles, both triangles' panel verts at that edge coincide
    in 2D. This is the "orange peel" unfold: isometric per-tri, consistent
    across shared edges.

    Why this matters:
      - Stretch (eval_stretch_kernel): F^T F = I per-triangle at t=0 because
        each tri's panel edges match its 3D edges exactly. Zero stretch force.
      - Bending (eval_bend_kernel): bend_weight × pos_3d is proportional only
        to LOCAL dihedral deviation from flat (not global curvature). For a
        smooth garment, local deviations are small → bounded bending force.

    Prior attempts:
      - v4/v5 (UV panel): per-tri UV ↔ 3D area ratios vary wildly in CLO3D
        atlas UVs → some tris hit edge_stiff = edge_ke / tiny_area → explosion.
      - v6 (per-tri flat, disconnected): every triangle has its own 2D frame,
        so adjacent tris disagree on shared-edge 2D coords → bend_weight's
        linear combination doesn't zero out at any 3D config → explosion.
      - v7 (per-tri flat + bending off): no NaN, but cloth collapses since
        stretch alone can't prevent triangle folding.

    This function fixes both by keeping per-tri isometric (for stretch) AND
    making shared-edge coords consistent (for bending).
    """
    from collections import deque
    n_t = len(faces)

    # Pre-compute edge-to-faces adjacency.
    edge_to_faces: dict[tuple[int, int], list[int]] = {}
    for fi in range(n_t):
        for i in range(3):
            a = int(faces[fi, i])
            b = int(faces[fi, (i + 1) % 3])
            e = (a, b) if a < b else (b, a)
            edge_to_faces.setdefault(e, []).append(fi)

    face_neighbors: list[list[tuple[int, tuple[int, int]]]] = [[] for _ in range(n_t)]
    for e, fs in edge_to_faces.items():
        if len(fs) == 2:
            f0, f1 = fs
            face_neighbors[f0].append((f1, e))
            face_neighbors[f1].append((f0, e))

    panel_verts = np.zeros((3 * n_t, 2), dtype=np.float64)
    panel_indices = np.arange(3 * n_t, dtype=np.int32).reshape(-1, 3)
    visited = np.zeros(n_t, dtype=bool)

    def place_seed(fi: int):
        f = faces[fi]
        p0 = verts_3d[f[0]]
        p1 = verts_3d[f[1]]
        p2 = verts_3d[f[2]]
        e01 = p1 - p0
        L = float(np.linalg.norm(e01))
        if L < 1e-12:
            L = 1e-12
        e02 = p2 - p0
        proj = float(np.dot(e01, e02)) / L
        h = float(np.linalg.norm(np.cross(e01, e02))) / L
        panel_verts[fi * 3 + 0] = (0.0, 0.0)
        panel_verts[fi * 3 + 1] = (L, 0.0)
        panel_verts[fi * 3 + 2] = (proj, h)
        visited[fi] = True

    def place_neighbor(fi: int, fj: int, shared_edge: tuple[int, int]) -> bool:
        """Place fj so its shared edge with fi has the same 2D coords.
        Returns False on degenerate placement (falls back to seed)."""
        f_i = faces[fi]
        f_j = faces[fj]
        a, b = shared_edge

        # Positions of a, b in f_i and f_j (0, 1, or 2).
        pos_a_i = int(np.where(f_i == a)[0][0])
        pos_b_i = int(np.where(f_i == b)[0][0])
        pos_a_j = int(np.where(f_j == a)[0][0])
        pos_b_j = int(np.where(f_j == b)[0][0])
        pos_c_j = 3 - pos_a_j - pos_b_j  # the remaining index (0+1+2 = 3)
        pos_c_i = 3 - pos_a_i - pos_b_i
        c_j = int(f_j[pos_c_j])

        pa = panel_verts[fi * 3 + pos_a_i]
        pb = panel_verts[fi * 3 + pos_b_i]
        ab = pb - pa
        L_ab = float(np.linalg.norm(ab))
        if L_ab < 1e-12:
            return False

        # 3D distances from c_j to a and b.
        d_ca = float(np.linalg.norm(verts_3d[c_j] - verts_3d[a]))
        d_cb = float(np.linalg.norm(verts_3d[c_j] - verts_3d[b]))

        # Circle intersection: place c in the local (e_x, e_y) frame anchored at pa.
        e_x = ab / L_ab
        e_y = np.array([-e_x[1], e_x[0]])  # 90° CCW

        x_local = (d_ca * d_ca - d_cb * d_cb + L_ab * L_ab) / (2.0 * L_ab)
        y_sq = d_ca * d_ca - x_local * x_local
        y_local = float(np.sqrt(max(y_sq, 0.0)))

        # Choose sign so c_j sits on the OPPOSITE side of edge ab from fi's
        # third vert (standard triangle-pair unfold: "open the book").
        fi_c_2d = panel_verts[fi * 3 + pos_c_i]
        fi_c_local_y = float(np.dot(fi_c_2d - pa, e_y))
        if fi_c_local_y > 0:
            y_local = -y_local

        pc = pa + x_local * e_x + y_local * e_y
        panel_verts[fj * 3 + pos_a_j] = pa
        panel_verts[fj * 3 + pos_b_j] = pb
        panel_verts[fj * 3 + pos_c_j] = pc
        visited[fj] = True
        return True

    n_components = 0
    q: deque[int] = deque()
    for seed in range(n_t):
        if visited[seed]:
            continue
        n_components += 1
        place_seed(seed)
        q.append(seed)
        while q:
            fi = q.popleft()
            for (fj, shared) in face_neighbors[fi]:
                if visited[fj]:
                    continue
                ok = place_neighbor(fi, fj, shared)
                if not ok:
                    place_seed(fj)
                q.append(fj)

    # Degeneracy diagnostic
    v0 = verts_3d[faces[:, 0]]
    v1 = verts_3d[faces[:, 1]]
    v2 = verts_3d[faces[:, 2]]
    cross_mag = np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)
    n_degen = int((cross_mag < 1e-12).sum())

    # Shared-edge consistency diagnostic. For DEVELOPABLE local patches BFS is
    # exact (zero mismatch). For non-developable regions (seams, curved hoods),
    # non-tree edges accumulate error. We report the distribution so bending
    # stiffness can be tuned against it: force scales linearly with edge_ke
    # and with mismatch, so max_mismatch × edge_ke must stay bounded.
    mismatch = []
    for e, fs in edge_to_faces.items():
        if len(fs) != 2:
            continue
        a, b = e
        fa, fb = fs
        pa_a = panel_verts[fa * 3 + int(np.where(faces[fa] == a)[0][0])]
        pb_a = panel_verts[fb * 3 + int(np.where(faces[fb] == a)[0][0])]
        pa_b = panel_verts[fa * 3 + int(np.where(faces[fa] == b)[0][0])]
        pb_b = panel_verts[fb * 3 + int(np.where(faces[fb] == b)[0][0])]
        mismatch.append(max(float(np.linalg.norm(pa_a - pb_a)),
                            float(np.linalg.norm(pa_b - pb_b))))
    max_mismatch = float(max(mismatch)) if mismatch else 0.0
    if mismatch:
        m = np.asarray(mismatch)
        print(f"[Newton] Geodesic unfold: {n_t} tris, {n_components} components, {n_degen} degen; "
              f"shared-edge mismatch (m): max={m.max():.4f} median={np.median(m):.4f} "
              f"mean={m.mean():.4f} [>1mm: {int((m > 1e-3).sum())}/{len(m)}]")
    else:
        print(f"[Newton] Geodesic unfold: {n_t} tris, {n_components} components, {n_degen} degen; "
              f"no shared edges")
    return panel_verts, panel_indices, max_mismatch


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

    # WELD duplicated garment vertices. CLO3D OBJ exports write seam-split
    # verts (same 3D position, distinct vertex indices per panel). That
    # leaves the face graph topologically disconnected (v8 log: 31
    # components) so stretch/bending can't connect panels and they fall
    # independently. tol=1mm collapses seam pairs without touching distinct
    # geometric features.
    aligned_verts, garment_faces, orig_to_welded = _weld_duplicate_vertices(
        aligned_verts, garment_faces, tol=1.0e-3
    )

    # Resolve fabric properties
    preset_name = fabric_config.get("preset", "cotton_medium")
    preset = FABRIC_PRESETS.get(preset_name, FABRIC_PRESETS["cotton_medium"])
    density = fabric_config.get("density", preset["density"])
    tri_ke = preset["tri_ke"]
    edge_ke = preset["edge_ke"]
    particle_r = preset["particle_r"]

    # Inflate the garment off the body BEFORE cleanup + sim. With per-tri-flat
    # rest pose (built post-inflation), the rest pose IS the inflated shape, so
    # inflation doesn't introduce initial strain. Generous target for safety.
    inflate_offset = 15.0e-3
    aligned_verts, n_inflated, stuck_mask_orig = _inflate_garment_off_body(
        aligned_verts, body_verts, body_obj, inflate_offset, max_iters=30
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
    # Static avatar collider. Matches canonical example_cloth_style3d.py:74-81:
    # default add_body() (no is_kinematic flag) + add_shape_mesh. Default body
    # has mass=0 → body_inv_mass=0 → immovable under gravity. Our earlier
    # is_kinematic=True was belt-and-suspenders but diverged from the canonical
    # path; removing to minimise surprise.
    avatar_body = builder.add_body()
    builder.add_shape_mesh(
        body=avatar_body,
        xform=wp.transform(p=wp.vec3(0.0, 0.0, 0.0), q=wp.quat_identity()),
        mesh=body_mesh,
        scale=wp.vec3(1.0, 1.0, 1.0),
    )

    # Geodesic BFS unfold: per-triangle-isometric (F^T F = I at t=0 → zero
    # stretch force) AND shared-edge-consistent where the mesh is developable.
    # Non-developable regions (hood curvature, seams) accumulate mismatch on
    # loop-closure edges, which would produce non-zero bending force at rest.
    # We measure the actual max mismatch and SCALE edge_ke accordingly so the
    # worst-case bending acceleration stays below ~60 m/s² (Δv/substep <
    # 0.1 m/s). Derivation in /tmp/test_bending_force_magnitudes.py:
    #   accel ≈ 7e13 × edge_ke² × mismatch / (edge_area² × mass) [hoodie-scale]
    #   → safe_edge_ke ≈ 9.2e-7 / sqrt(max(1mm, mismatch))
    # Clamped to canonical 2e-5 as ceiling so near-perfect unfolds get full
    # bending.
    panel_verts_np, panel_indices_np, max_mismatch = _build_geodesic_unfold_panel(
        clean_garment_verts, clean_garment_faces
    )
    safe_mismatch = max(max_mismatch, 1.0e-3)
    edge_ke_safe = min(2.0e-5, 9.2e-7 / float(np.sqrt(safe_mismatch)))
    print(f"[Newton] Panel: {len(panel_verts_np)} 2D verts, {len(panel_indices_np)} tris; "
          f"auto-tuned edge_ke={edge_ke_safe:.2e} (from max_mismatch={max_mismatch:.4f}m)")
    panel_verts_arg = panel_verts_np.tolist()
    panel_indices_arg = panel_indices_np.flatten().tolist()

    # edge_aniso_ke auto-tuned from measured panel mismatch (see above).
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
        edge_aniso_ke=wp.vec3(edge_ke_safe, edge_ke_safe * 0.5, edge_ke_safe * 0.25),
        panel_verts=panel_verts_arg,
        panel_indices=panel_indices_arg,
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

    # No ground plane: our garment's bottom hem sits at y≈-0.009m, below the
    # default ground at y=0 → 9mm penetration → ~3 m/s velocity spike per
    # substep on those particles from the contact kernel. With ke=10 it's not
    # instantly explosive but compounds over 10 substeps. Safer to let the
    # body mesh handle all collisions.
    device = "cuda:0"
    model = builder.finalize(device=device)
    model.set_gravity((0.0, -9.81, 0.0))

    # --- PIN unstable particles BEFORE sim starts ---
    # Two classes get pinned (ACTIVE flag cleared → solver skips them):
    #  (1) garment verts still stuck inside the body after inflation. Leaving
    #      them dynamic means the contact kernel sees them deep inside → huge
    #      push-out forces → NaN cascade to neighbors via stretch/bending.
    #  (2) particles with mass=0. Happens when ALL triangles referencing a
    #      particle were dropped as degenerate by cloth.py:270. Zero mass means
    #      infinite inverse mass → any force produces inf velocity → NaN.
    n_cloth_particles = len(clean_garment_verts)
    flags_np = model.particle_flags.numpy().copy()
    mass_np = model.particle_mass.numpy().copy()
    inv_mass_np = model.particle_inv_mass.numpy().copy()

    # stuck_mask_orig is indexed by original garment vert. Remap to clean.
    stuck_mask_clean = stuck_mask_orig[clean_to_orig]
    n_pin_stuck = int(stuck_mask_clean.sum())

    # Zero-mass particles (orphans after Newton's internal tri drop).
    cloth_mass_slice = mass_np[:n_cloth_particles]
    zero_mass_mask = cloth_mass_slice <= 0.0
    n_pin_orphan = int(zero_mass_mask.sum())

    pin_mask = stuck_mask_clean | zero_mass_mask
    n_pinned = int(pin_mask.sum())
    if n_pinned > 0:
        pin_idx = np.nonzero(pin_mask)[0]
        flags_np[pin_idx] = flags_np[pin_idx] & ~np.uint32(ParticleFlags.ACTIVE)
        mass_np[pin_idx] = 0.0
        inv_mass_np[pin_idx] = 0.0
        model.particle_flags = wp.array(flags_np, dtype=wp.uint32, device=device)
        model.particle_mass = wp.array(mass_np, dtype=wp.float32, device=device)
        model.particle_inv_mass = wp.array(inv_mass_np, dtype=wp.float32, device=device)
    print(f"[Newton] Pinned {n_pinned} particles "
          f"({n_pin_stuck} body-stuck, {n_pin_orphan} zero-mass orphans)")
    # Contact params copied 1:1 from canonical example_cloth_style3d.py. Newton's
    # defaults (ke=1e3, kd=1e3, mu=0.5) are rigid-body defaults that explode cloth.
    # The canonical values are the only published-safe combination for Style3D.
    #
    # IMPORTANT: kd=1e-6 (not 1.0!). Cloth particle masses are tiny (density×area ≈
    # 3e-5 kg per particle). With kd=1.0 and any contact velocity, the damping force
    # is 1,000,000× the mass — F/m blows past 1e6 m/s² in one step → NaN in <1 frame.
    # kd=1e-6 matches the canonical and keeps the contact spring critically-ish damped
    # without overpowering the mass. (Prior kd=1.0 was the primary NaN trigger.)
    #
    # mu=0.0: matches our prior choice. PR #1500 documents a friction sign-flip NaN
    # at near-zero tangential velocity. Canonical uses 0.2, but 0.0 is safer until
    # we pick up the fix.
    model.soft_contact_radius = 0.2e-2
    model.soft_contact_margin = 0.35e-2
    model.soft_contact_ke = 1.0e1
    model.soft_contact_kd = 1.0e-6
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
        # collide() once per frame, outside the substep loop — matches canonical
        # example_cloth_style3d.py (static avatar). H1 example moves collide() inside
        # the substep loop but that's because its avatar is animated per-substep; ours
        # is static so once per frame is sufficient and avoids per-substep BVH rebuild.
        model.collide(state_0, contacts)
        for _ in range(sim_substeps):
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
        final_verts_welded = final_verts_m / garment_unit_scale
    else:
        final_verts_welded = final_verts_m

    # UN-WELD: `final_verts_welded` is indexed by the welded vert table
    # (~26k entries). The original OBJ has ~27.7k `v` lines and its `f`
    # lines reference those original indices — `write_obj_with_new_verts`
    # iterates and substitutes positions in original order. Map every
    # original vert back to the position of its welded canonical vert.
    final_verts = final_verts_welded[orig_to_welded]

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


HANDLER_BUILD = "drape-handler 2026-04-20/v9-weld-seams (weld CLO3D seam-split verts at 1mm → 1 topological component; cloth can actually hold together)"

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
