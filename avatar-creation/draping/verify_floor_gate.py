#!/usr/bin/env python3
"""
Pre-build gate for the drape-handler body-frame fix: normalise the BODY (never the
garment) to feet at y=0 and a uniform scale to 1.8 m tall, the frame every La Fam /
Ramin garment is authored in and the frame the widget displays (d052c55).

Runs the REAL functions out of the WORKING-TREE handler (no copies, no mocks):
_normalize_to_meters, _is_prefitted, align_meshes, _belt_bottoms, _normalize_body_frame
and (if present) the file wrapper _normalize_body_obj, in handler.py's own order
(normalise units -> normalise body frame -> align -> prefit -> belt), against:

  - 9ede4581's real body_apose.obj (pelvis-centred, y = -1.316 .. 0.424 m, 1.74 m tall)
  - ca5808a9's real body_apose.obj (control: already feet-at-0 and exactly 1.8 m)
  - La Fam's real garment OBJs: diamond t-shirt blue XL, denim slogan jeans L

Asserts, per body:
  - body frame: min Y == 0, height == 1.8 m (+-1 mm), uniform scale (X/Z scale == Y scale),
    returned (offset, scale) match what was applied; a no-op on the control
  - file wrapper (if present): the OBJ it rewrites parses back to the same body, in the
    file's own units, with faces and every non-vertex line untouched
  - every garment: _is_prefitted True, align_meshes identity (scale 1, translation 0)
  - jeans: v48 belt holds the waistband at the waist line, sane lift (< 10 cm), hem unmoved
It also runs the un-normalised pelvis body and requires that it still REPRODUCES the bug,
so a passing gate can't be an artefact of the test.

Not covered: the SDF retarget and the PyGarment sim (need the GPU image).

    python3 verify_floor_gate.py
    python3 verify_floor_gate.py --frame-fn <name>     # if the helper is named differently
Exit 0 = safe to build. Needs numpy + scipy.
"""
import argparse
import ast
import contextlib
import io
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
HANDLER = HERE / "handler.py"
STORE = "https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public"
BODIES = {
    "9ede4581 (pelvis-centred, LHM)": f"{STORE}/avatars/9ede4581-7aea-4916-b680-d1346c8322ad/body_apose.obj",
    "ca5808a9 (feet-at-0 1.8 m control)": f"{STORE}/avatars/ca5808a9-99bd-45a2-86ec-f3f0f90db831/body_apose.obj",
}
LAFAM = f"{STORE}/garments/a3e127f6-d606-44ae-9d9d-779e8c82c2ec"
GARMENTS = [
    ("diamond t-shirt blue XL", "tops", f"{LAFAM}/diamond-t-shirt-blue/bldt_xl.obj"),
    ("denim slogan jeans L", "bottoms", f"{LAFAM}/denim-slogan-jeans/sj_l.obj"),
]
FRAME_FN = "_normalize_body_frame"   # (verts_m) -> (verts_m, offset_m, scale)
FILE_FN = "_normalize_body_obj"      # (path) -> rewrites the OBJ in place (optional)
NEEDED = ("_normalize_to_meters", "_is_prefitted", "align_meshes", "_belt_bottoms")
TARGET_H = 1.8
WAIST_FRAC, KNEE_FRAC = 0.575, 0.28  # must match _belt_bottoms

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("  PASS " if cond else "  FAIL ") + name + (f"   [{detail}]" if detail else ""))
    if not cond:
        failures.append(name)


def fetch(url: str) -> Path:
    cache = Path(tempfile.gettempdir()) / "tryon_floor_gate"
    cache.mkdir(exist_ok=True)
    dest = cache / url.rsplit("/", 2)[-2].replace(" ", "_") / url.rsplit("/", 1)[-1]
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:  # python.org macOS builds ship without a CA bundle; prefer certifi, else curl
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(url, context=ctx, timeout=120) as r:
                dest.write_bytes(r.read())
        except ImportError:
            subprocess.run(["curl", "-fsSL", "-o", str(dest), url], check=True)
    return dest


def load_verts(path: Path) -> np.ndarray:
    return np.asarray([[float(x) for x in ln.split()[1:4]]
                       for ln in path.read_text(errors="replace").splitlines() if ln.startswith("v ")],
                      dtype=np.float64)


def load_handler_functions(frame_fn: str):
    """Exec the named functions VERBATIM from handler.py, plus every top-level function and
    constant they reference (transitively), so helpers like load_obj_vertices or
    REFERENCE_BODY_HEIGHT_M come along without being listed by hand. Stdlib modules the
    handler imports at top level are provided in the namespace."""
    import json, math, os, re, shutil, struct, subprocess, time  # noqa: E401  (handler's own top-level imports)
    tree = ast.parse(HANDLER.read_text())
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    consts: dict = {}
    for n in tree.body:
        targets = n.targets if isinstance(n, ast.Assign) else [n.target] if isinstance(n, ast.AnnAssign) and n.value else []
        for t in targets:
            if isinstance(t, ast.Name):
                consts[t.id] = n
    missing = [n for n in NEEDED if n not in funcs]
    if missing:
        sys.exit(f"handler.py is missing {missing}")
    roots = list(NEEDED) + [n for n in (frame_fn, FILE_FN) if n in funcs]
    picked: dict = {}
    todo = list(roots)
    while todo:
        name = todo.pop()
        if name in picked:
            continue
        node = funcs.get(name) or consts.get(name)
        if node is None:
            continue
        picked[name] = node
        todo += [x.id for x in ast.walk(node) if isinstance(x, ast.Name)]
    ns: dict = {"np": np, "Path": Path, "os": os, "sys": sys, "time": time, "json": json,
                "shutil": shutil, "struct": struct, "tempfile": tempfile, "subprocess": subprocess,
                "math": math, "re": re, "USE_HTTPX": False}
    # constants first (in file order), then functions, so defaults resolve at def time
    ordered = sorted(picked.values(), key=lambda n: (isinstance(n, ast.FunctionDef), n.lineno))
    exec(compile(ast.Module(ordered, []), str(HANDLER), "exec"), ns)
    extra = sorted(k for k in picked if k not in roots)
    if extra:
        print(f"also exec'd (referenced): {', '.join(extra)}")
    return ns, (frame_fn if frame_fn in funcs else None), (FILE_FN if FILE_FN in funcs else None)


def quiet(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn(*a, **k)
    return out, buf.getvalue()


def waistband_tops(body: np.ndarray, garm: np.ndarray, n_bins: int = 36) -> np.ndarray:
    """Per-angle top of the garment above the knee, same binning idea as _belt_bottoms."""
    bmin, bh = body[:, 1].min(), np.ptp(body[:, 1])
    v = garm[garm[:, 1] > bmin + KNEE_FRAC * bh]
    top = v[:, 1].max()
    upper = v[v[:, 1] > top - 0.15]
    cx = 0.5 * (upper[:, 0].min() + upper[:, 0].max())
    cz = 0.5 * (upper[:, 2].min() + upper[:, 2].max())
    b = (((np.arctan2(v[:, 0] - cx, v[:, 2] - cz) + np.pi) / (2 * np.pi)) * n_bins).astype(int) % n_bins
    return np.array([v[b == i, 1].max() for i in range(n_bins) if (b == i).any()])


def garments_on(ns, body, garments):
    out = []
    for gname, cat, graw in garments:
        (g, _unit), _ = quiet(ns["_normalize_to_meters"], graw, "Garment")
        (aligned, scale, translation), _ = quiet(ns["align_meshes"], body, g, category=cat)
        prefit, _ = quiet(ns["_is_prefitted"], body, g)
        belted, blog = quiet(ns["_belt_bottoms"], body, aligned, category=cat)
        out.append(dict(name=gname, cat=cat, g=g, aligned=aligned, belted=belted, scale=float(scale),
                        translation=np.asarray(translation, dtype=float), prefit=bool(prefit),
                        belt_log=blog.strip()))
    return out


def check_body_frame(raw_m: np.ndarray, body: np.ndarray, offset: float, scale: float, control: bool):
    h_raw = float(np.ptp(raw_m[:, 1]))
    check("body min Y == 0", abs(body[:, 1].min()) < 1e-6, f"min={body[:,1].min():+.6f}")
    check("body height == 1.8 m (+-1 mm)", abs(np.ptp(body[:, 1]) - TARGET_H) < 1e-3,
          f"{h_raw:.4f} -> {np.ptp(body[:,1]):.4f} m")
    sy = np.ptp(body[:, 1]) / h_raw
    sx = np.ptp(body[:, 0]) / np.ptp(raw_m[:, 0])
    sz = np.ptp(body[:, 2]) / np.ptp(raw_m[:, 2])
    check("uniform scale (X and Z scaled exactly like Y)", abs(sx - sy) < 1e-6 and abs(sz - sy) < 1e-6,
          f"sx={sx:.6f} sy={sy:.6f} sz={sz:.6f}")
    check("returned scale matches the applied scale", abs(scale - sy) < 1e-6, f"returned {scale:.6f}")
    # Y must be exactly (y - min) * scale, i.e. the returned offset is the raw floor in metres
    floor = float(raw_m[:, 1].min())
    y_ok = np.allclose(body[:, 1], (raw_m[:, 1] - floor) * sy, atol=1e-6)
    # Sign convention is the helper's choice: offset may be the floor or its negation.
    off_ok = abs(offset - floor) < 1e-6 or abs(offset + floor) < 1e-6
    check("Y == (raw_y - floor) * scale, returned offset == raw floor", bool(y_ok and off_ok),
          f"offset={offset:+.4f} m, raw floor={floor:+.4f} m")
    check("shape preserved (no shear/rotation): pairwise distances scale uniformly",
          np.allclose(np.linalg.norm(body[1:200] - body[0], axis=1),
                      np.linalg.norm(raw_m[1:200] - raw_m[0], axis=1) * sy, atol=1e-6))
    if control:
        check("control body (already feet-at-0, 1.8 m): step is a no-op",
              abs(offset) < 1e-6 and abs(scale - 1.0) < 1e-6 and np.allclose(body, raw_m, atol=1e-9),
              f"offset={offset:+.6f} scale={scale:.6f}")


def check_file_wrapper(ns, file_fn, src: Path, body_frame_m: np.ndarray, unit_m: float):
    tmp = Path(tempfile.mkdtemp()) / src.name
    shutil.copy(src, tmp)
    before = tmp.read_text(errors="replace").splitlines()
    quiet(ns[file_fn], tmp)
    after = tmp.read_text(errors="replace").splitlines()
    v_after = load_verts(tmp)
    check(f"{file_fn}: rewritten OBJ == in-memory frame (file units preserved)",
          v_after.shape == body_frame_m.shape and np.allclose(v_after * unit_m, body_frame_m, atol=2e-6),
          f"units x{unit_m:g} -> m")
    non_v_before = [ln for ln in before if not ln.startswith("v ")]
    non_v_after = [ln for ln in after if not ln.startswith("v ")]
    check(f"{file_fn}: faces/normals/UVs/materials untouched", non_v_before == non_v_after,
          f"{len(non_v_before)} non-vertex lines")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame-fn", default=FRAME_FN, help="body-frame helper in handler.py")
    args = ap.parse_args()

    ns, frame_fn, file_fn = load_handler_functions(args.frame_fn)
    print(f"handler: {HANDLER}")
    print(f"loaded verbatim: {', '.join(NEEDED)}"
          + (f", {frame_fn}" if frame_fn else "") + (f", {file_fn}" if file_fn else ""))
    if not frame_fn:
        print(f"\nNO {args.frame_fn} IN handler.py. Running the un-normalised baseline only.\n")
    if not file_fn:
        print(f"(no {FILE_FN} yet: file-level wrapper not checked)")

    garments = [(n, c, load_verts(fetch(u))) for n, c, u in GARMENTS]
    for n, _, g in garments:
        print(f"garment {n}: {len(g)} verts, y=[{g[:,1].min():.3f}, {g[:,1].max():.3f}]")

    for label, url in BODIES.items():
        path = fetch(url)
        body_raw = load_verts(path)
        print(f"\n=== BODY {label}: {len(body_raw)} verts ===")
        (raw_m, unit_m), _ = quiet(ns["_normalize_to_meters"], body_raw, "Body")
        pelvis = raw_m[:, 1].min() < -0.5
        control = (not pelvis) and abs(np.ptp(raw_m[:, 1]) - TARGET_H) < 1e-3 and abs(raw_m[:, 1].min()) < 1e-6
        print(f"  raw y=[{raw_m[:,1].min():.3f}, {raw_m[:,1].max():.3f}] m, h={np.ptp(raw_m[:,1]):.4f} "
              f"({'PELVIS-CENTRED' if pelvis else 'feet-at-0'})")

        if pelvis:
            print("  -- un-normalised (today's behaviour), must reproduce the bug --")
            for r in garments_on(ns, raw_m, garments):
                print(f"     {r['name']}: prefit={r['prefit']} scale={r['scale']:.4f} dy={r['translation'][1]:+.3f}")
                if r["name"] == garments[0][0]:
                    check("baseline reproduces the bug (tee not prefitted / rescaled)",
                          (not r["prefit"]) or abs(r["scale"] - 1) > 0.01)

        if not frame_fn:
            failures.append(f"no {args.frame_fn}")
            continue

        print(f"  -- with {frame_fn} --")
        (out), _ = quiet(ns[frame_fn], raw_m.copy())
        body, offset, scale = np.asarray(out[0], dtype=np.float64), float(out[1]), float(out[2])
        check_body_frame(raw_m, body, offset, scale, control)
        if file_fn:
            check_file_wrapper(ns, file_fn, path, body, unit_m)

        bmin, bh = body[:, 1].min(), np.ptp(body[:, 1])
        waist_y = bmin + WAIST_FRAC * bh
        for r in garments_on(ns, body, garments):
            print(f"   {r['name']} ({r['cat']}): prefit={r['prefit']} scale={r['scale']:.6f} "
                  f"t=[{', '.join(f'{t:+.4f}' for t in r['translation'])}]")
            check(f"{r['name']}: _is_prefitted True", r["prefit"])
            check(f"{r['name']}: align is identity (scale 1, no translation)",
                  abs(r["scale"] - 1.0) < 1e-9 and np.allclose(r["translation"], 0.0)
                  and np.allclose(r["aligned"], r["g"]))
            check(f"{r['name']}: garment inside body's vertical span",
                  r["aligned"][:, 1].min() >= bmin - 0.05 and r["aligned"][:, 1].max() <= body[:, 1].max() + 0.05,
                  f"y=[{r['aligned'][:,1].min():.3f}, {r['aligned'][:,1].max():.3f}]")
            if r["cat"] == "bottoms":
                before = waistband_tops(body, r["aligned"])
                after = waistband_tops(body, r["belted"])
                lift = float((after - before).max()) if len(after) == len(before) else \
                    float(r["belted"][:, 1].max() - r["aligned"][:, 1].max())
                print(f"     waist line {waist_y:.3f} m | waistband top before [{before.min():.3f}, {before.max():.3f}]"
                      f" after [{after.min():.3f}, {after.max():.3f}] | "
                      f"{r['belt_log'].splitlines()[0] if r['belt_log'] else 'no belt log'}")
                check(f"{r['name']}: belt ran (logged a lift)", "belt lift" in r["belt_log"])
                check(f"{r['name']}: waistband held at the waist line (lowest angle >= waist - 1 cm)",
                      after.min() >= waist_y - 0.01, f"min top {after.min():.3f} vs waist {waist_y:.3f}")
                check(f"{r['name']}: sane lift (0 .. 10 cm)", -1e-6 <= lift <= 0.10, f"max lift {lift*100:.1f} cm")
                check(f"{r['name']}: hem unmoved (lift fades out by the knee)",
                      abs(r["belted"][:, 1].min() - r["aligned"][:, 1].min()) < 0.005,
                      f"hem {r['aligned'][:,1].min():.3f} -> {r['belted'][:,1].min():.3f}")

    print("\n" + ("GATE PASSED: safe to build" if not failures else f"GATE FAILED ({len(failures)}): " + "; ".join(failures)))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
