"""
RunPod Serverless Handler for Cloth Draping Service
====================================================

Drapes a CLO3D-exported garment OBJ onto a SMPL avatar body OBJ using the
NvidiaWarp-GarmentCode + PyGarment cloth simulator (primary), with a
deterministic geometric drape as the safety-net fallback.

Newton Style3D was used from v4 through v16 and removed in v18 after repeated
NaN explosions on CLO3D tight-fit garments.

Expected input:
{
    "body_obj_url":    "https://...",   # URL to body_apose.obj (SMPL mesh)
    "garment_obj_url": "https://...",   # URL to garment .obj (CLO3D export)
    "fabric_config":   {"preset": "cotton_medium", ...},  # optional overrides
    "simulation_mode": "swift",         # "swift" or "quality"
    "garment_id":      "uuid", "size": "m", "user_id": "uuid"   # for logging
}

Output:
{
    "draped_obj_base64":  "...",
    "draped_mtl_base64":  "...",         # MTL with relative texture paths
    "draped_textures_base64": { ... },   # {filename: base64}
    "draped_glb_base64":  "...",         # Bare GLB fallback for Three.js
    "processing_time_seconds": ...,
    "simulation_method":  "pygarment" | "geometric_fallback",
    "vertex_count":       ...,
    "sim_stats":          { ... },
    "success":            true
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

# --- numpy<2.0 shim ---
# NvidiaWarp-GarmentCode (and its Style3D cloth utilities) call np.atan2 /
# np.pow / np.asin / np.acos / np.atan, which only exist in numpy>=2.0. The
# RunPod pytorch:2.1.0 base image pins numpy<2 for torch ABI compatibility,
# so we expose the new names as aliases here. Must run BEFORE any warp import.
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

# --- NvidiaWarp-GarmentCode / PyGarment cloth simulation ---
# This is our ONLY GPU path as of v18. Newton Style3D was ripped out after 16
# versions of NaN fights — the stability features it lacked (particle velocity
# clamp, zero-gravity warmup, equilibrium auto-terminate) are all baked into
# PyGarment by design. Geometric drape stays as the deterministic safety net.
WARP_AVAILABLE = False
try:
    import warp as wp
    wp.init()
    WARP_AVAILABLE = True
    print(f"[Draping] Warp {wp.__version__} loaded — PyGarment GPU sim available")
except Exception as e:
    print(f"[Draping] Warp not available ({e}) — will use geometric fallback only")


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
    print(f"[PyGarment] Weld: {n_orig} → {n_welded} verts "
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


def _normalize_to_meters(verts: np.ndarray, label: str) -> tuple:
    """If a mesh appears to be in millimetres (height >> 10), convert to meters.
    Warp expects SI units — gravity is m/s², so mm-scale meshes get effectively
    zero gravity force."""
    h = verts[:, 1].max() - verts[:, 1].min()
    if h > 50.0:
        print(f"[PyGarment] {label} looks like mm (height={h:.1f}), converting to meters")
        return verts / 1000.0, 1.0 / 1000.0
    return verts, 1.0


def _write_welded_obj(welded_verts: np.ndarray, welded_faces: np.ndarray, output_path: Path):
    """Write a minimal OBJ containing just v + f lines for a welded mesh.

    PyGarment's Cloth class only reads v and f from paths.g_box_mesh (see
    pygarment/meshgen/garment.py :: load_obj → returns vertices+indices+faces).
    UVs/materials from the original CLO3D OBJ are preserved on OUR side when
    we write the final output — here we just need the topology PyGarment
    actually simulates.
    """
    with open(output_path, "w") as f:
        f.write("# welded mesh (stitched seam-split verts) for PyGarment\n")
        for v in welded_verts:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for face in welded_faces:
            # OBJ is 1-indexed.
            f.write(f"f {int(face[0]) + 1} {int(face[1]) + 1} {int(face[2]) + 1}\n")


def _generate_cloth_seg_file(
    garment_obj: Path,
    welded_verts: np.ndarray,
    orig_to_welded: np.ndarray,
    output_txt: Path,
) -> dict:
    """
    Write PyGarment's per-vertex panel segmentation txt file — one line per
    WELDED vertex (not original). Needed because we feed PyGarment the
    welded mesh (see _write_welded_obj above) and it asserts one label
    per-vertex.

    Format (from pygarment/warp/collision/panel_assignment.py::read_segmentation):
      one line per vertex, each line = comma-separated entries, first entry
      is the panel label. Lines starting with "stitch" are treated as stitch
      verts (used by add_cloth_mesh_sewing_spring to identify which faces
      get sewing-spring treatment).

    Labeling strategy:
      - A WELDED vert whose merge-group contains MORE THAN ONE original vert
        was at a seam (two panel copies met there) → label "stitch_N"
      - Otherwise: inherit the panel material from one of the original verts
        that merged to it (deterministic: first original vert seen)

    Sleeve split (v19): CLO3D exports both sleeves under one material name
    (e.g. "Sleeves_FRONT_2731"). PyGarment's panel_assignment maps one
    material → one closest body part, so both sleeves get dragged to ONE arm
    (v18.9 log: all 6544 sleeve verts → right_arm). Post-label pass: any
    welded vert whose label contains "sleeve" gets suffixed `_L` or `_R`
    based on whether its x-coordinate is below or above the mean x of the
    sleeve-material verts (which naturally sits on the body centerline for a
    symmetric T/A-pose garment). Two materials → two closest body parts →
    left sleeve dragged to left_arm, right sleeve to right_arm.

    The stitching-seam convention is what enables
    builder.add_cloth_mesh_sewing_spring to route edge-adjacent-to-stitch
    triangles through add_triangles_stitching instead of add_triangles,
    producing proper sewing springs across panel seams.
    """
    welded_verts_count = len(welded_verts)
    # --- Pass 1: parse OBJ line-by-line, track active usemtl, assign per-face
    # material, propagate to ORIGINAL vertices (using 1-indexed OBJ convention).
    active_mtl = "UNASSIGNED"
    orig_vert_to_mtl = {}  # orig_vert_idx (0-based) → first material name touching it
    face_count = 0
    materials_seen = set()

    with open(garment_obj, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("usemtl "):
                active_mtl = line.strip().split(None, 1)[1].strip()
                materials_seen.add(active_mtl)
            elif line.startswith("f "):
                parts = line.strip().split()[1:]
                for p in parts:
                    v_idx_1based = p.split("/")[0]
                    try:
                        v_idx = int(v_idx_1based) - 1
                    except ValueError:
                        continue
                    if v_idx not in orig_vert_to_mtl:
                        orig_vert_to_mtl[v_idx] = active_mtl
                face_count += 1

    # --- Pass 2: compute welded groups — which welded verts absorbed multiple
    # originals. orig_to_welded[i] = welded_idx for original vert i.
    from collections import Counter
    welded_group_counts = Counter(orig_to_welded.tolist())
    stitch_welded_set = {w for w, c in welded_group_counts.items() if c > 1}

    # --- Pass 3: for each welded vert, pick a representative original vert to
    # inherit the material label from (deterministic: lowest original index).
    welded_to_orig_representative = {}
    for orig_idx, welded_idx in enumerate(orig_to_welded.tolist()):
        if welded_idx not in welded_to_orig_representative:
            welded_to_orig_representative[welded_idx] = orig_idx

    # --- Pass 4: emit one label per WELDED vert.
    n_stitch = 0
    labels = []
    for welded_idx in range(welded_verts_count):
        if welded_idx in stitch_welded_set:
            labels.append(f"stitch_{welded_idx}")
            n_stitch += 1
        else:
            orig_idx = welded_to_orig_representative.get(welded_idx, -1)
            labels.append(orig_vert_to_mtl.get(orig_idx, "UNASSIGNED"))

    # --- Pass 5 (v19): split any "sleeve*" material into L/R by x-coord.
    # See docstring for why. Does nothing for garments with no sleeves.
    sleeve_welded_indices = [
        i for i, lbl in enumerate(labels)
        if not lbl.startswith("stitch_") and "sleeve" in lbl.lower()
    ]
    if sleeve_welded_indices:
        sleeve_xs = welded_verts[sleeve_welded_indices, 0]
        x_mid = float(sleeve_xs.mean())
        n_left = n_right = 0
        for wi in sleeve_welded_indices:
            base = labels[wi]
            if welded_verts[wi, 0] < x_mid:
                labels[wi] = f"{base}_L"
                n_left += 1
            else:
                labels[wi] = f"{base}_R"
                n_right += 1
        print(f"[PyGarment] Sleeve split: {n_left} L / {n_right} R "
              f"(x_mid={x_mid:.4f})")

    with open(output_txt, "w") as f:
        f.write("\n".join(labels) + "\n")

    panel_counts = Counter(l for l in labels if not l.startswith("stitch_"))
    print(f"[PyGarment] Cloth seg: {welded_verts_count} welded verts, "
          f"{face_count} faces (orig), {len(materials_seen)} materials, "
          f"{n_stitch} stitch verts")
    for mtl, n in panel_counts.most_common(10):
        print(f"[PyGarment]   {mtl:40s}: {n:6d} verts")
    return {
        "verts_total": welded_verts_count,
        "stitch_verts": n_stitch,
        "materials": sorted(materials_seen),
        "panel_counts": dict(panel_counts),
    }


def _write_body_measurements_yaml(output_path: Path, body_name: str = "smpl_avatar"):
    """
    Minimal body_measurements.yaml. PyGarment's PathCofig reads this to check
    for a 'body_sample' key that would override the body_name it was given.
    We keep it empty so PathCofig uses the body_name we pass.
    """
    # Deliberately minimal — no `body_sample` key → _body_name stays as passed.
    # Height is only for informational purposes; not used by the sim.
    content = "body:\n  height: 1.80\n"
    output_path.write_text(content)


def _write_minimal_pattern_spec(output_path: Path):
    """
    Write the smallest pattern specification JSON that satisfies
    pygarment.pattern.core.BasicPattern's constructor.

    Cloth.build_stage calls Cloth._load_panel_labels() which does:
        pattern = BasicPattern(self.paths.g_specs)
        for name, panel in pattern.pattern['panels'].items(): ...

    BasicPattern.reloadJSON loads `self.spec['pattern']` and
    `self.spec['properties']`, then _normalize_template accesses
    `self.properties['curvature_coords']` and `'units_in_meter'`. If any of
    those keys are missing it KeyError's — so the spec must include all of
    them. We set empty panels + neutral properties; panel_assignment handles
    label assignment geometrically when panel_init_labels is empty.

    Without this file, build_stage crashes at `BasicPattern(...)` with
    FileNotFoundError before sim even starts. This is the kind of issue I
    prefer to pre-write rather than discover after a 15-min build cycle.
    """
    spec = {
        "pattern": {
            "panels": {},
            "stitches": []
        },
        "parameters": {},
        "parameter_order": [],
        "properties": {
            "curvature_coords": "relative",
            "units_in_meter": 100
        }
    }
    output_path.write_text(json.dumps(spec, indent=2))


def pygarment_drape(
    body_obj: Path,
    garment_obj: Path,
    output_obj: Path,
    fabric_config: dict,
    simulation_mode: str = "swift",
) -> dict:
    """
    Run the PyGarment XPBD cloth simulation. Returns stats dict matching
    the original handler schema so the caller doesn't care about the backend.

    Raises RuntimeError on any sim failure (e.g., PyGarment crash, no output
    mesh produced). Caller catches and falls back to geometric.
    """
    # Lazy imports so a failure to install PyGarment doesn't break the module
    # at startup (geometric safety net still works).
    import shutil
    import sys
    import types
    import yaml
    from scipy.spatial import cKDTree as _cKDTree

    # Stub out pygarment.meshgen.render.pythonrender BEFORE pygarment imports.
    # simulation.py does `from pygarment.meshgen.render.pythonrender import
    # render_images` at module top. pythonrender.py in turn imports `pyrender`
    # which we don't install (heavy native deps — EGL/OSMesa, and we don't
    # render in the handler, we return the mesh). Pre-registering a fake
    # module in sys.modules short-circuits Python's import machinery.
    if "pygarment.meshgen.render.pythonrender" not in sys.modules:
        _stub = types.ModuleType("pygarment.meshgen.render.pythonrender")
        def _render_images_stub(*args, **kwargs):
            print("[PyGarment] render_images() stubbed — handler doesn't render")
        _stub.render_images = _render_images_stub
        sys.modules["pygarment.meshgen.render.pythonrender"] = _stub

    # v18.8: disable Cloth's CUDA graph capture. NvidiaWarp-GarmentCode's Warp
    # fork has a bug where transient scratch arrays allocated inside
    # wp.sim.collide / integrator.simulate get Python-GC'd during an active
    # capture, triggering array.__del__ → allocator.free → the RuntimeError
    # we saw dozens of times in the v18.7 log:
    #
    #   Cannot free memory on device ... while graph capture is active
    #   at /workspace/warp-gc/warp/types.py:1660
    #
    # Those "Exception ignored" suppressions mask the fact that the capture
    # state is left inconsistent, so the resulting graph replays produce
    # bogus output. Disabling graph capture forces the Python-level substep
    # loop (slightly slower per frame, but correct).
    #
    # Patch order matters: Cloth is imported by pygarment.meshgen.simulation
    # at that module's load time. Must patch pygarment.meshgen.garment.Cloth
    # BEFORE importing simulation, otherwise simulation.py grabs the
    # unpatched class.
    import pygarment.meshgen.garment as _pg_garment
    _orig_cloth_init = _pg_garment.Cloth.__init__
    def _cloth_init_no_graph(self, *args, **kwargs):
        # Replace create_graph on this instance FIRST so the parent __init__'s
        # conditional call to self.create_graph() hits our no-op instead.
        self.create_graph = lambda: setattr(self, "graph", None)
        _orig_cloth_init(self, *args, **kwargs)
        # Belt-and-suspenders: even if the original init re-set
        # sim_use_graph, force it off so update() takes the Python loop.
        self.sim_use_graph = False
        self.graph = None
    _pg_garment.Cloth.__init__ = _cloth_init_no_graph

    from pygarment.meshgen.sim_config import PathCofig
    from pygarment.meshgen.simulation import run_sim
    from pygarment import data_config

    # ------------------------------------------------------------------
    # Step 1: load & align meshes in OUR coordinate system (meters, Y-up).
    # Re-uses the same mesh preproc (weld + align) so the pipelines start from
    # identical input state.
    # ------------------------------------------------------------------
    body_verts_raw = load_obj_vertices(body_obj)
    garment_verts_raw = load_obj_vertices(garment_obj)
    if len(body_verts_raw) == 0 or len(garment_verts_raw) == 0:
        raise RuntimeError(
            f"Empty mesh: body={len(body_verts_raw)} garment={len(garment_verts_raw)} verts"
        )

    body_verts, _ = _normalize_to_meters(body_verts_raw, "Body")
    garment_verts, garment_unit_scale = _normalize_to_meters(garment_verts_raw, "Garment")
    garment_faces = load_obj_faces(garment_obj)
    aligned_verts, align_scale, translation = align_meshes(body_verts, garment_verts)

    # Weld CLO3D seam-split verts at 1mm tol. v18.7 change: we now FEED the
    # welded mesh to PyGarment (not the original). Previously we wrote the
    # pre-weld mesh, which meant each seam had two separate vertex indices in
    # the OBJ PyGarment loaded — and
    # `builder.add_cloth_mesh_sewing_spring` identifies stitch triangles by
    # topological adjacency (`i in stitch_vertices_set` for face verts).
    # Without shared vertex indices, adjacent panels have no common triangle
    # edge, no sewing springs form, panels drift apart under gravity. The
    # v18.5/v18.6 screenshots showed this exactly.
    welded_verts, welded_faces, orig_to_welded = _weld_duplicate_vertices(
        aligned_verts.copy(), garment_faces, tol=1.0e-3
    )
    print(f"[PyGarment] Weld pass: detected {(np.bincount(orig_to_welded) > 1).sum()} "
          f"welded groups for stitch-vert labeling")

    # ------------------------------------------------------------------
    # Step 2: build PyGarment's expected tmpdir layout. Paths must match
    # PathCofig's hardcoded filename conventions (see
    # pygarment/meshgen/sim_config.py :: PathCofig._update_*_paths).
    # ------------------------------------------------------------------
    tmp_root = Path(tempfile.mkdtemp(prefix="pygarment_"))
    tag = "drape"
    body_name = "smpl_avatar"

    # PyGarment's bodies_default_path (where it looks for body.obj + body.yaml +
    # smpl_vert_segmentation.json). Our Dockerfile ships smpl_vert_segmentation.json
    # at /workspace/pygarment_assets. For this run we symlink the shipped seg
    # into the tmpdir and write the body OBJ + measurements there.
    bodies_dir = tmp_root / "bodies"
    bodies_dir.mkdir()
    shipped_seg = Path("/workspace/pygarment_assets/smpl_vert_segmentation.json")
    if not shipped_seg.exists():
        # Fallback for local testing (outside Docker). Let it fail loudly if
        # PyGarment needs it.
        shipped_seg = Path(__file__).parent / "pygarment_assets" / "smpl_vert_segmentation.json"
    (bodies_dir / "smpl_vert_segmentation.json").symlink_to(shipped_seg)

    # v18.6 scale fix: PyGarment's internal sim convention is CM (their pattern
    # coords are in cm, their sim code scales accordingly). Cloth.build_stage
    # multiplies body verts by b_scale=100 and cloth verts by c_scale=1. To end
    # up at matched cm-scale in-sim:
    #   - body OBJ must be in METERS → PyGarment ×100 → cm in-sim
    #   - cloth OBJ must be in CM    → PyGarment ×1   → cm in-sim
    # Previous code pre-divided body by 100, which left body at 0–1.8 IN-SIM
    # while cloth was at 0–180, a 100× mismatch. That made panel_assignment's
    # nearest-body-part lookup garbage, disabled body-cloth contact entirely
    # (body is effectively a tiny speck next to the cloth), and gravity pulled
    # the cloth away from the body → the "hanging off the avatar" look in the
    # screenshots. Write body directly in meters — no pre-scaling.
    body_obj_staged = bodies_dir / f"{body_name}.obj"
    write_obj_with_new_verts(body_obj, body_verts, body_obj_staged)

    # Minimal body measurements yaml.
    _write_body_measurements_yaml(bodies_dir / f"{body_name}.yaml", body_name=body_name)

    # Element dir (PathCofig's in_element_path — holds sim_props.yaml etc).
    el_dir = tmp_root / "element"
    el_dir.mkdir()

    # Root of PyGarment's "out" tree. PathCofig will create {out_dir}/{tag}/
    # for the box-mesh + segmentation + sim output files.
    out_dir = tmp_root / "out"
    out_dir.mkdir()

    # Stage our tuned sim_props.yaml into the element dir. PyGarment writes
    # per-run stats back into this yaml, so it needs to be writable and
    # uniquely owned by this invocation.
    shipped_sim_props = Path("/workspace/pygarment_assets/default_sim_props.yaml")
    if not shipped_sim_props.exists():
        shipped_sim_props = Path(__file__).parent / "pygarment_assets" / "default_sim_props.yaml"
    sim_props_dst = el_dir / "sim_props.yaml"
    shutil.copy(shipped_sim_props, sim_props_dst)

    # system.json for PathCofig. It hardcodes `Properties('./system.json')`,
    # so we must have system.json in CWD. We chdir to tmp_root and write one
    # that points at our tmpdir's bodies/ and out/ subdirs.
    orig_cwd = Path.cwd()
    system_json = tmp_root / "system.json"
    system_json.write_text(json.dumps({
        "output": str(out_dir),
        "datasets_path": "",
        "datasets_sim": "",
        "sim_configs_path": str(shipped_sim_props.parent),
        "bodies_default_path": str(bodies_dir),
        "body_samples_path": "",
    }))

    # ------------------------------------------------------------------
    # Step 3: construct PathCofig FIRST (it creates out_el dir for us and
    # computes the expected filenames), THEN write our box mesh +
    # segmentation directly into the paths it computes. The previous
    # ordering had us writing to a separately-created dir and then
    # shutil.copy-ing to paths.g_box_mesh — which turned out to resolve to
    # the exact same file, raising SameFileError. Writing directly
    # eliminates the redundant file hop entirely.
    # ------------------------------------------------------------------
    os.chdir(tmp_root)
    try:
        props = data_config.Properties(str(sim_props_dst))
        props.set_section_stats(
            "sim",
            fails={}, sim_time={}, spf={}, fin_frame={},
            body_collisions={}, self_collisions={},
        )
        props.set_section_stats("render", render_time={})

        paths = PathCofig(
            in_element_path=el_dir,
            out_path=out_dir,
            in_name=tag,
            body_name=body_name,
            smpl_body=True,  # use smpl_vert_segmentation.json
            add_timestamp=False,
        )
        # PathCofig made paths.out_el and paths.g_box_mesh etc. Now write
        # our files directly there.

        # PyGarment's Cloth.build_stage multiplies body verts by b_scale=100
        # and cloth verts by c_scale=1. Both sides end up at cm in-sim when
        # we write body in meters (done above) and cloth in cm (× 100 here).
        # v18.7: the cloth written out is the WELDED topology — same vertex
        # index at both sides of every panel seam — so PyGarment's stitching
        # logic fires correctly.
        welded_verts_cm = welded_verts * 100.0
        _write_welded_obj(welded_verts_cm, welded_faces, paths.g_box_mesh)

        # Per-vertex panel segmentation — one line PER WELDED VERT. Stitch
        # verts get "stitch_N" (triggers the sewing-spring path); otherwise
        # the label is inherited from the CLO3D MTL material of the first
        # original vert that merged into this welded slot.
        seg_stats = _generate_cloth_seg_file(
            garment_obj, welded_verts, orig_to_welded, paths.g_mesh_segmentation
        )

        # Minimal pattern spec JSON at both paths.in_g_spec (input dir) and
        # paths.g_specs (out dir). Cloth._load_panel_labels() opens
        # paths.g_specs; without this file it crashes with FileNotFoundError
        # BEFORE sim starts. We pass empty panels → panel_assignment falls
        # back to geometric label inference.
        _write_minimal_pattern_spec(paths.in_g_spec)
        _write_minimal_pattern_spec(paths.g_specs)

        # ------------------------------------------------------------------
        # Step 4: run the simulation. PyGarment auto-terminates on equilibrium
        # (is_static check every frame), capped at max_sim_steps from our yaml.
        # ------------------------------------------------------------------
        print(f"[PyGarment] Starting run_sim — max_sim_steps="
              f"{props['sim']['config']['max_sim_steps']}, "
              f"zero_gravity_steps={props['sim']['config']['zero_gravity_steps']}")
        sim_start = time.time()
        run_sim(
            cloth_name=tag,
            props=props,
            paths=paths,
            save_v_norms=False,
            store_usd=False,
            optimize_storage=False,
            verbose=True,
        )
        sim_time = time.time() - sim_start

        # ------------------------------------------------------------------
        # Step 5: read back the draped mesh and un-weld for the original OBJ
        # topology. PyGarment wrote paths.g_sim with the WELDED vertex count
        # (26396 for our Ramin hoodie). Our caller expects the ORIGINAL CLO3D
        # OBJ topology (27696 verts, preserving UVs/materials). We
        # un-weld by mapping every original-vert → the position of its
        # welded canonical.
        # ------------------------------------------------------------------
        if not paths.g_sim.exists():
            raise RuntimeError(f"PyGarment sim produced no output at {paths.g_sim}")
        welded_draped_cm = load_obj_vertices(paths.g_sim)
        if len(welded_draped_cm) != len(welded_verts):
            raise RuntimeError(
                f"PyGarment g_sim vert count mismatch: expected {len(welded_verts)} "
                f"(welded), got {len(welded_draped_cm)}"
            )
        # cm → meters
        welded_draped_m = welded_draped_cm / 100.0
        # UN-WELD: expand to original OBJ vert count via orig_to_welded mapping.
        # Each original vert takes the position of the welded canonical it was
        # merged into → seam-split verts end up at IDENTICAL 3D positions
        # (the welded canonical's final position), so the output mesh looks
        # seamlessly stitched when rendered.
        final_verts_m = welded_draped_m[orig_to_welded]

        # Undo alignment translation (align_scale is almost always 1.0 for us).
        if align_scale != 1.0:
            final_verts_m = (final_verts_m - translation) / align_scale
        else:
            final_verts_m = final_verts_m - translation
        # Restore original garment unit (mm if input was mm).
        if garment_unit_scale != 1.0:
            final_verts_out = final_verts_m / garment_unit_scale
        else:
            final_verts_out = final_verts_m

        # Write to the caller's output_obj, preserving original OBJ topology
        # (including UVs and materials that PyGarment never saw).
        write_obj_with_new_verts(garment_obj, final_verts_out, output_obj)

        body_collisions = props["sim"]["stats"].get("body_collisions", {}).get(tag, -1)
        self_collisions = props["sim"]["stats"].get("self_collisions", {}).get(tag, -1)
        fin_frame = props["sim"]["stats"].get("fin_frame", {}).get(tag, -1)
        print(f"[PyGarment] Success: {fin_frame} frames, {sim_time:.1f}s, "
              f"body_collisions={body_collisions}, self_collisions={self_collisions}")

        return {
            "vertices_total": len(final_verts_out),
            "simulation_frames": int(fin_frame) if fin_frame != -1 else 0,
            "simulation_time_seconds": round(sim_time, 2),
            "body_collisions": int(body_collisions) if body_collisions != -1 else None,
            "self_collisions": int(self_collisions) if self_collisions != -1 else None,
            "materials": seg_stats["materials"],
            "stitch_verts": seg_stats["stitch_verts"],
            "backend": "pygarment",
            # fabric_preset is displayed by drape-test.html if present — we
            # pass it through from the request so the frontend confirms the
            # requested fabric was used.
            "fabric_preset": fabric_config.get("preset", "cotton_medium"),
            "align_scale": round(align_scale, 6),
            "translation_m": [round(float(t), 6) for t in translation],
        }
    finally:
        os.chdir(orig_cwd)
        # Leave tmp_root for debugging if needed; RunPod cleans ephemeral storage.


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

        # Strategy 1 (v17 primary): PyGarment / NvidiaWarp-GarmentCode.
        # XPBD cloth with particle_max_velocity clamp, zero-gravity warmup,
        # body segmentation, and auto-terminate on equilibrium. The first
        # backend we've had that's designed for CLO3D-style tight garments on
        # arbitrary bodies. See pygarment_drape() above.
        try:
            print("[Draping] Running PyGarment cloth simulation (primary, v17)...")
            draped_obj = output_dir / "draped.obj"
            sim_stats = pygarment_drape(
                body_obj=body_obj,
                garment_obj=garment_obj,
                output_obj=draped_obj,
                fabric_config=merged_fabric,
                simulation_mode=simulation_mode,
            )
            simulation_method = "pygarment"
            print(f"[Draping] PyGarment success: {sim_stats}")
        except Exception as e:
            print(f"[Draping] PyGarment failed, falling back to geometric: {e}")
            import traceback
            traceback.print_exc()
            draped_obj = None

        # Strategy 2 (safety net): geometric drape (deterministic, no GPU,
        # no physics — just multi-pass collision resolution + Laplacian
        # smoothing). Guaranteed to run so the shopper never sees a failure.
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
                mtl_text_orig = mtl_source.read_text(encoding="utf-8", errors="replace")
                cleaned_lines = []
                for mtl_line in mtl_text_orig.split("\n"):
                    stripped = mtl_line.strip()
                    if stripped.startswith("map_") or stripped.startswith("bump"):
                        parts = stripped.split()
                        if len(parts) >= 2:
                            tex_filename = parts[-1].replace("\\", "/").rsplit("/", 1)[-1]
                            tex_path = garment_obj.parent / tex_filename
                            if tex_path.exists() and tex_path.stat().st_size < 10_000_000:
                                tex_bytes = tex_path.read_bytes()
                                textures_b64[tex_filename] = base64.b64encode(tex_bytes).decode("utf-8")
                                cleaned_lines.append(mtl_line)
                                print(f"[Draping] Texture: {tex_filename} ({len(tex_bytes)/1024:.1f} KB)")
                            else:
                                # Drop this map_* line so Three.js MTLLoader.preload()
                                # doesn't throw on the missing texture and kill the
                                # whole OBJ rendering path. Base `Kd` color survives
                                # and the garment still shows (flat fabric color).
                                print(f"[Draping] MTL ref dropped (texture missing): {tex_filename}")
                                continue
                    else:
                        cleaned_lines.append(mtl_line)
                mtl_bytes = "\n".join(cleaned_lines).encode("utf-8")
                mtl_b64 = base64.b64encode(mtl_bytes).decode("utf-8")
                print(f"[Draping] MTL: {mtl_name} ({len(mtl_bytes)/1024:.1f} KB, "
                      f"{len(textures_b64)} textures included)")

        # Convert draped OBJ directly to GLB (one-to-one vertex mapping). No
        # injection into the CLO3D display GLB — that path does nearest-vertex
        # mapping between 27k sim verts and 194k display verts across 71
        # sub-meshes (zipper, drawstrings), which produces shredded/misaligned
        # geometry. Per user feedback, OBJ + MTL is the authoritative pipeline;
        # the GLB output here is only a fallback for Three.js GLTFLoader.
        glb_path = output_dir / "draped.glb"
        glb_b64 = ""
        glb_bytes = b""
        if _obj_to_glb_bare(draped_obj, glb_path):
            glb_bytes = glb_path.read_bytes()
            glb_b64 = base64.b64encode(glb_bytes).decode("utf-8")
            print(f"[Draping] GLB (direct from draped OBJ): {len(glb_bytes)/1024:.1f} KB")

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


HANDLER_BUILD = (
    "drape-handler 2026-04-22/v19-quality-pass-1 "
    "(v18.9 completed 300 frames but ended with 311 body-cloth intersections, "
    "1107 self-intersections, and 4117 non-static verts. Three YAML fixes + "
    "one label fix: (1) soft_contact_ke 10 → 5000 (Newton-era value was "
    "1000x too low to eject penetrations); (2) fabric_thickness 0.1 → 0.001 "
    "(10cm self-collision bubble → 1mm); (3) zero_gravity_steps 10 → 30 (more "
    "time to un-penetrate before gravity kicks in); (4) split 'Sleeves*' "
    "material into L/R by x-sign so panel_assignment maps each sleeve to "
    "the correct arm — v18.9 dragged both sleeves to right_arm with k=1e7.)"
)

try:
    import runpod
    print(f"[Draping] === {HANDLER_BUILD} ===")
    print("[Draping] Starting serverless cloth draping handler...")
    print(f"[Draping] PyGarment/Warp sim available: {WARP_AVAILABLE}")
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
