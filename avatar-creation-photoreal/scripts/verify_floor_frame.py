#!/usr/bin/env python3
"""
Local proof for the photoreal floor-frame fix.

Does NOT mock the thing under test. It imports `_zero_to_floor` from the real
patched handler, and it execs `_is_prefitted` + `align_meshes` verbatim out of
the `drape` branch's handler source, so both sides of the contract are the
actual shipping code.

Question it answers: does dropping the body to the floor flip the drape
handler's decision from "rescale this garment" to "leave it alone"?
"""
import ast
import subprocess
import sys
import types
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SAMPLE = HERE.parent / "test_outputs/v0.9-stage2b__neutral_h178__4e6e2edf"
DRAPE_REF = "drape:avatar-creation/draping/handler.py"


# --- import _zero_to_floor from the REAL patched handler ---------------------
# The module imports `runpod` at top level, which is not installed here and is
# irrelevant to the function under test. Stub it rather than copy the function.
for name in ("runpod", "runpod.serverless"):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules["runpod"].__version__ = "stub"
sys.modules["runpod"].serverless = types.SimpleNamespace(start=lambda *a, **k: None)
sys.path.insert(0, str(REPO / "avatar-creation-photoreal"))

src = (REPO / "avatar-creation-photoreal/handler.py").read_text()
tree = ast.parse(src)
ns_photo: dict = {"np": np}
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == "_zero_to_floor":
        exec(compile(ast.Module([node], []), "handler.py", "exec"), ns_photo)
_zero_to_floor = ns_photo["_zero_to_floor"]
print("loaded _zero_to_floor from the patched handler")


# --- exec _is_prefitted + align_meshes verbatim from the drape branch --------
# Pull the drape handler out of the `drape` branch so this always tests
# against what is actually deployed, not against a stale working copy.
drape_src = subprocess.run(
    ["git", "show", DRAPE_REF], cwd=REPO, capture_output=True, text=True, check=True
).stdout
dtree = ast.parse(drape_src)
ns_drape: dict = {"np": np}
wanted = {"_is_prefitted", "align_meshes"}
found = set()
for node in dtree.body:
    if isinstance(node, ast.FunctionDef) and node.name in wanted:
        exec(compile(ast.Module([node], []), "drape_handler.py", "exec"), ns_drape)
        found.add(node.name)
assert found == wanted, f"missing {wanted - found}"
_is_prefitted = ns_drape["_is_prefitted"]
align_meshes = ns_drape["align_meshes"]
print(f"loaded _is_prefitted + align_meshes verbatim from {DRAPE_REF}\n")


def load_obj_verts(path: Path) -> np.ndarray:
    out = []
    for line in path.read_text().splitlines():
        if line.startswith("v "):
            _, x, y, z = line.split()[:4]
            out.append((float(x), float(y), float(z)))
    return np.asarray(out, dtype=np.float64)


def span(v, axis=1):
    return v[:, axis].min(), v[:, axis].max()


# --- the real Stage 2b artifact ---------------------------------------------
body_raw_mm = load_obj_verts(SAMPLE / "body_apose.obj")
body_fixed_mm, offset = _zero_to_floor(body_raw_mm)
body_fixed_mm = np.asarray(body_fixed_mm, dtype=np.float64)

print("BODY, as the endpoint ships it today")
print(f"  Y [{span(body_raw_mm)[0]:9.1f} .. {span(body_raw_mm)[1]:8.1f}] mm   span {np.ptp(body_raw_mm[:,1]):.1f}")
print("BODY, after _zero_to_floor")
print(f"  Y [{span(body_fixed_mm)[0]:9.1f} .. {span(body_fixed_mm)[1]:8.1f}] mm   span {np.ptp(body_fixed_mm[:,1]):.1f}")
print(f"  offset removed: {offset:.1f} mm")

assert abs(body_fixed_mm[:, 1].min()) < 1e-3, "feet not on the floor"
assert abs(np.ptp(body_fixed_mm[:, 1]) - np.ptp(body_raw_mm[:, 1])) < 1e-3, "height changed"
for ax, nm in ((0, "X"), (2, "Z")):
    assert np.allclose(body_fixed_mm[:, ax], body_raw_mm[:, ax]), f"{nm} moved"
print("  height preserved, X and Z untouched\n")


# --- a floor-relative garment, the way CLO3D authors them -------------------
# Torso band of the floored body, pushed 8 mm outward from the vertical axis.
# By construction this genuinely hugs the body, so a correct pipeline must
# leave it alone.
band = (body_fixed_mm[:, 1] >= 900.0) & (body_fixed_mm[:, 1] <= 1350.0)
garment_mm = body_fixed_mm[band].copy()
cx, cz = garment_mm[:, 0].mean(), garment_mm[:, 2].mean()
d = np.stack([garment_mm[:, 0] - cx, garment_mm[:, 2] - cz], axis=1)
n = np.linalg.norm(d, axis=1, keepdims=True)
d = d / np.maximum(n, 1e-6)
garment_mm[:, 0] += d[:, 0] * 8.0
garment_mm[:, 2] += d[:, 1] * 8.0

print(f"GARMENT (floor-relative, {len(garment_mm)} verts)")
print(f"  Y [{span(garment_mm)[0]:9.1f} .. {span(garment_mm)[1]:8.1f}] mm   span {np.ptp(garment_mm[:,1]):.1f}\n")


# --- run the real drape decision against both body frames -------------------
# _normalize_to_meters keys off height span only, which is translation
# invariant, so both frames arrive in meters the same way.
g_m = garment_mm / 1000.0
results = {}
for label, body_mm in (("pelvis-centred (today)", body_raw_mm),
                       ("floor frame (fixed)", body_fixed_mm)):
    b_m = body_mm / 1000.0
    prefit = _is_prefitted(b_m, g_m)
    aligned, scale, translation = align_meshes(b_m, g_m)
    grew = np.ptp(aligned[:, 1]) / np.ptp(g_m[:, 1])
    results[label] = (prefit, scale, grew)
    print(f"--- {label} ---")
    print(f"  _is_prefitted : {prefit}")
    print(f"  scale applied : {scale:.6f}")
    print(f"  garment height {np.ptp(g_m[:,1]):.3f} m -> {np.ptp(aligned[:,1]):.3f} m  ({grew:.3f}x)")
    print()


# --- verdict ----------------------------------------------------------------
bad_prefit, bad_scale, bad_grew = results["pelvis-centred (today)"]
ok_prefit, ok_scale, ok_grew = results["floor frame (fixed)"]

ok = True
if bad_prefit or abs(bad_scale - 1.0) < 0.01:
    print("UNEXPECTED: the pelvis-centred frame did NOT reproduce the bug.")
    ok = False
else:
    print(f"REPRODUCED: pelvis-centred body inflates the garment {bad_grew:.3f}x")

if not ok_prefit or abs(ok_scale - 1.0) > 1e-9:
    print("FAILED: the floor frame did not produce an identity transform.")
    ok = False
else:
    print("FIXED:      floor frame is detected as pre-fitted, identity transform")

sys.exit(0 if ok else 1)
