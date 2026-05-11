"""
Fire ONE drape job at the deployed RunPod endpoint and dump every byte
of the response to disk for offline inspection. No webhook, no DB writes.

Use this when production drapes look broken but local sims look clean: it
isolates the deployed handler as the variable, since the inputs are the
exact URLs the dispatcher would have used.

  python -m backend.scripts.test_runpod_drape_oneshot \
      [--user-id <uuid>]   # default ca5808a9
      [--garment <id>]     # default rs bow zipup
      [--size s|m|l]       # default s
      [--out <dir>]        # default /tmp/v45_3_diag/runpod_<ts>/

Saves under <out>/:
    body_source.obj            (downloaded from Supabase, for reference)
    garment_source.obj         (downloaded from Supabase, for reference)
    draped.obj                 (handler output)
    draped.mtl                 (handler output, if returned)
    draped.glb                 (handler output, if returned)
    textures/<basename>        (handler output, if any)
    response_meta.json         (response minus base64 fields)
    job_meta.json              (input payload + RunPod job_id + timing)

Then prints a comparison of edge stats: source vs draped, per material
group, with the 05-07 baseline (S sleeves max edge 16.1mm, n>20mm = 0)
called out so we can see the deployed regression at a glance.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

THIS_DIR = Path(__file__).resolve().parent
REPO_BACKEND = THIS_DIR.parent
sys.path.insert(0, str(REPO_BACKEND))

from dotenv import load_dotenv
load_dotenv(REPO_BACKEND / ".env")

from supabase import create_client


DEFAULT_USER = "ca5808a9-99bd-45a2-86ec-f3f0f90db831"
DEFAULT_GARMENT = "2663d739-664e-4b61-bc0a-0eeaf6448eb5"
DEFAULT_SIZE = "s"
DRAPE_ENDPOINT = os.environ.get("RUNPOD_DRAPING_ENDPOINT_ID") or "e86juazm1b4mig"
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")


def _resolve(path_or_url: str) -> str:
    if not path_or_url:
        return ""
    if path_or_url.startswith("http"):
        return path_or_url
    base = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/public"
    return f"{base}/{path_or_url.lstrip('/')}"


def _resolve_inputs(user_id: str, garment_id: str, size: str) -> dict:
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    fp = sb.table("fit_passports").select(
        "pipeline_files,status"
    ).eq("user_id", user_id).limit(1).execute().data
    if not fp:
        sys.exit(f"no fit_passport for user {user_id}")
    pf = fp[0].get("pipeline_files") or {}
    body_obj = pf.get("apose_mesh") or pf.get("tpose_mesh") or pf.get("original_mesh")
    if not body_obj:
        sys.exit(f"no body OBJ in pipeline_files for user {user_id}: keys={list(pf)}")
    smpl_params = pf.get("smpl_params") or ""

    g = sb.table("garments").select(
        "id,name,obj_sizes,fabric_config,content_hash"
    ).eq("id", garment_id).limit(1).execute().data
    if not g:
        sys.exit(f"no garment row for id {garment_id}")
    grow = g[0]
    obj_sizes = grow.get("obj_sizes") or {}
    if size not in obj_sizes:
        sys.exit(f"size {size!r} not in obj_sizes={list(obj_sizes)}")
    garment_obj = obj_sizes[size]

    return {
        "body_obj_url": _resolve(body_obj),
        "garment_obj_url": _resolve(garment_obj),
        "smpl_params_url": _resolve(smpl_params) or None,
        "fabric_config": grow.get("fabric_config") or {},
        "garment_id": garment_id,
        "garment_name": grow.get("name"),
        "garment_content_hash": grow.get("content_hash"),
        "size": size,
        "user_id": user_id,
    }


def _download_to(url: str, dest: Path) -> int:
    with httpx.Client(timeout=120) as c:
        r = c.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest.stat().st_size


def _runpod_run(payload: dict) -> str:
    url = f"https://api.runpod.ai/v2/{DRAPE_ENDPOINT}/run"
    h = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    r = httpx.post(url, json=payload, headers=h, timeout=30.0)
    r.raise_for_status()
    j = r.json()
    if not j.get("id"):
        sys.exit(f"RunPod /run returned no id: {j}")
    return j["id"]


def _runpod_poll(job_id: str, timeout_s: int = 600) -> dict:
    url = f"https://api.runpod.ai/v2/{DRAPE_ENDPOINT}/status/{job_id}"
    h = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    started = time.time()
    last = None
    while True:
        r = httpx.get(url, headers=h, timeout=120.0)
        r.raise_for_status()
        j = r.json()
        st = j.get("status")
        if st != last:
            print(f"  [{int(time.time()-started):4d}s] status={st}")
            last = st
        if st in ("COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"):
            return j
        if time.time() - started > timeout_s:
            sys.exit(f"timeout after {timeout_s}s, last status={st}")
        time.sleep(5)


def _save_artifacts(out: Path, output: dict) -> dict:
    """Persist whatever the handler returned. v45.12+: prefer URL fields,
    fall back to *_base64 fields if URLs were not produced."""
    saved = {}

    def _download(url: str, dest: Path) -> int:
        with httpx.Client(timeout=120.0) as c:
            r = c.get(url)
            r.raise_for_status()
            dest.write_bytes(r.content)
        return dest.stat().st_size

    # OBJ
    if output.get("draped_obj_url"):
        p = out / "draped.obj"
        saved["draped.obj"] = _download(output["draped_obj_url"], p)
    elif output.get("draped_obj_base64"):
        p = out / "draped.obj"
        p.write_bytes(base64.b64decode(output["draped_obj_base64"]))
        saved["draped.obj"] = p.stat().st_size

    # MTL
    if output.get("draped_mtl_url"):
        p = out / "draped.mtl"
        saved["draped.mtl"] = _download(output["draped_mtl_url"], p)
    elif output.get("draped_mtl_base64"):
        p = out / "draped.mtl"
        p.write_bytes(base64.b64decode(output["draped_mtl_base64"]))
        saved["draped.mtl"] = p.stat().st_size

    # GLB
    if output.get("draped_glb_url"):
        p = out / "draped.glb"
        saved["draped.glb"] = _download(output["draped_glb_url"], p)
    elif output.get("draped_glb_base64"):
        p = out / "draped.glb"
        p.write_bytes(base64.b64decode(output["draped_glb_base64"]))
        saved["draped.glb"] = p.stat().st_size

    # Textures
    tex_urls = output.get("draped_textures_urls") or {}
    if tex_urls:
        td = out / "textures"
        td.mkdir(exist_ok=True)
        for name, url in tex_urls.items():
            saved[f"textures/{name}"] = _download(url, td / name)
    else:
        textures = output.get("draped_textures_base64") or {}
        if textures:
            td = out / "textures"
            td.mkdir(exist_ok=True)
            for name, b64 in textures.items():
                p = td / name
                p.write_bytes(base64.b64decode(b64))
                saved[f"textures/{name}"] = p.stat().st_size

    return saved


def _edge_stats_per_material(obj_path: Path) -> list[dict]:
    """Manual OBJ parse: per usemtl, gather faces and compute edge length stats.
    Mirrors the handler's own parser so we are measuring like-for-like."""
    if not obj_path.exists():
        return []
    verts: list[tuple] = []
    active = "UNASSIGNED"
    faces_by_mtl: dict[str, list] = defaultdict(list)
    txt = obj_path.read_text(encoding="utf-8", errors="replace")
    for line in txt.split("\n"):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("v "):
            parts = s.split()
            verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif s.startswith("usemtl "):
            active = s.split(None, 1)[1].strip()
        elif s.startswith("f "):
            parts = s.split()[1:]
            idx = []
            for p in parts:
                v = p.split("/")[0]
                if v:
                    idx.append(int(v) - 1)
            if len(idx) >= 3:
                # triangulate fan
                for i in range(1, len(idx) - 1):
                    faces_by_mtl[active].append((idx[0], idx[i], idx[i + 1]))

    import math
    out = []
    for mtl, faces in faces_by_mtl.items():
        edges = []
        for a, b, c in faces:
            for u, v in ((a, b), (b, c), (a, c)):
                if u >= len(verts) or v >= len(verts):
                    continue
                pu, pv = verts[u], verts[v]
                d = math.sqrt(sum((pu[i] - pv[i]) ** 2 for i in range(3))) * 1000  # m -> mm
                edges.append(d)
        if not edges:
            continue
        edges.sort()
        n20 = sum(1 for e in edges if e > 20)
        n30 = sum(1 for e in edges if e > 30)
        med = edges[len(edges) // 2]
        out.append({
            "mtl": mtl,
            "n_edges": len(edges),
            "median_mm": round(med, 2),
            "max_mm": round(edges[-1], 2),
            "n_gt_20mm": n20,
            "n_gt_30mm": n30,
        })
    out.sort(key=lambda x: -x["max_mm"])
    return out


def _print_stats_table(label: str, rows: list[dict]) -> None:
    print(f"\n=== {label} ===")
    if not rows:
        print("  (no faces parsed)")
        return
    print(f"  {'mtl':32s}  {'edges':>7s}  {'med':>7s}  {'max':>8s}  {'>20mm':>7s}  {'>30mm':>7s}")
    for r in rows[:25]:
        flag = " <-- BAD" if r["max_mm"] > 30 else ("  warn" if r["max_mm"] > 20 else "")
        print(f"  {r['mtl'][:32]:32s}  {r['n_edges']:7d}  {r['median_mm']:7.2f}  {r['max_mm']:8.2f}  {r['n_gt_20mm']:7d}  {r['n_gt_30mm']:7d}{flag}")


def main() -> int:
    if not RUNPOD_API_KEY:
        sys.exit("RUNPOD_API_KEY not set in backend/.env")
    if not SUPABASE_URL or not SUPABASE_KEY:
        sys.exit("SUPABASE_URL or SUPABASE_SERVICE_KEY not set")

    p = argparse.ArgumentParser()
    p.add_argument("--user-id", default=DEFAULT_USER)
    p.add_argument("--garment", default=DEFAULT_GARMENT)
    p.add_argument("--size", default=DEFAULT_SIZE, choices=("s", "m", "l"))
    p.add_argument("--out", default=None)
    args = p.parse_args()

    ts = time.strftime("%Y%m%d_%H%M%S")
    out = Path(args.out or f"/tmp/v45_3_diag/runpod_{ts}_{args.size}").resolve()
    out.mkdir(parents=True, exist_ok=True)
    print(f"out dir: {out}")
    print(f"endpoint: {DRAPE_ENDPOINT}")

    inputs = _resolve_inputs(args.user_id, args.garment, args.size)
    print(f"\nresolved inputs:")
    for k, v in inputs.items():
        print(f"  {k}: {v}")

    print(f"\ndownloading source files for offline reference...")
    body_src = out / "body_source.obj"
    g_src = out / "garment_source.obj"
    print(f"  body  -> {body_src.name}: {_download_to(inputs['body_obj_url'], body_src)/1024:.1f} KB")
    print(f"  garm  -> {g_src.name}: {_download_to(inputs['garment_obj_url'], g_src)/1024:.1f} KB")

    payload_input = {
        "body_obj_url": inputs["body_obj_url"],
        "garment_obj_url": inputs["garment_obj_url"],
        "smpl_params_url": inputs["smpl_params_url"],
        "fabric_config": inputs["fabric_config"],
        "simulation_mode": "swift",
        "garment_id": inputs["garment_id"],
        "size": inputs["size"],
        "user_id": inputs["user_id"],
        "drape_job_id": f"oneshot-{ts}",
        "garment_version_hash": inputs["garment_content_hash"],
        "body_hash": "oneshot",
        # v45.12: forward the service key so the handler uploads draped
        # artifacts to the draped-artifacts bucket and returns URLs.
        "supabase_service_key": SUPABASE_KEY,
    }
    payload = {"input": payload_input}

    (out / "job_meta.json").write_text(json.dumps({
        "ts": ts,
        "endpoint": DRAPE_ENDPOINT,
        "input": payload_input,
    }, indent=2))

    print(f"\nfiring /run on endpoint {DRAPE_ENDPOINT}...")
    job_id = _runpod_run(payload)
    print(f"  job_id={job_id}")
    print(f"\npolling /status...")
    t0 = time.time()
    final = _runpod_poll(job_id)
    elapsed = time.time() - t0
    print(f"\nterminal status after {elapsed:.1f}s: {final.get('status')}")

    output = final.get("output") or {}
    err = final.get("error") or output.get("error")
    if err:
        print(f"  RunPod error: {err}")

    saved = _save_artifacts(out, output) if isinstance(output, dict) else {}
    print(f"\nsaved artifacts:")
    for k, sz in saved.items():
        print(f"  {k}: {sz/1024:.1f} KB")

    redacted_output = {}
    if isinstance(output, dict):
        for k, v in output.items():
            if k.endswith("_base64") or k.endswith("textures_base64"):
                if isinstance(v, str):
                    redacted_output[k] = f"<base64:{len(v)} chars>"
                elif isinstance(v, dict):
                    redacted_output[k] = {kk: f"<base64:{len(vv)} chars>" for kk, vv in v.items()}
                else:
                    redacted_output[k] = "<base64>"
            else:
                redacted_output[k] = v

    (out / "response_meta.json").write_text(json.dumps({
        "status": final.get("status"),
        "elapsed_seconds": round(elapsed, 1),
        "delayTime": final.get("delayTime"),
        "executionTime": final.get("executionTime"),
        "error": err,
        "output_meta": redacted_output,
    }, indent=2))

    print(f"\n--- edge stats: source garment OBJ (input to handler) ---")
    src_rows = _edge_stats_per_material(g_src)
    _print_stats_table("garment_source.obj", src_rows)

    print(f"\n--- edge stats: draped OBJ (output from handler v45.3) ---")
    drape_rows = _edge_stats_per_material(out / "draped.obj")
    _print_stats_table("draped.obj", drape_rows)

    print("\n--- 05-07 BASELINE (clean local sim) ---")
    print("  S Sleeves: max 16.1mm, edges>20mm = 0, edges>30mm = 0")
    print("  M Sleeves: max 17.0mm, edges>20mm = 0, edges>30mm = 0")
    print("  L Sleeves: max 15.7mm, edges>20mm = 0, edges>30mm = 0")

    print(f"\nall artifacts under: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
