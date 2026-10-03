"""
Invalidate and re-run drapes simulated against a body that was not in the reference frame
(feet at y=0, 1.8 m tall), which the drape handler now normalises every body to.

Since 2026-09-18 some avatars ship body_apose.obj in SMPL-X's native pelvis-centred frame
(min Y ~ -1.3 m) instead of feet-at-0. The drape handler's _is_prefitted/align path
mis-handles that frame, so every drape cached for those bodies is junk.

Run this ONLY AFTER the drape handler that floors the body is deployed to RunPod;
otherwise the re-drapes come back just as wrong.

What it does (per affected user):
  1. finds the user's body OBJ (same key order as drape_dispatcher: apose > tpose > original)
     and measures its Y range; affected = min Y not 0 or height not 1.8 m (+-1 mm)
  2. lists that user's draped_meshes rows (by every body_hash their drape_jobs used)
  3. --apply: deletes those draped_meshes rows, then resets the user's drape_jobs to
     status='queued' (attempts 0, runpod/draped ids cleared) so the EXISTING dispatcher
     loop re-runs them. Jobs are reset rather than re-inserted because
     idx_drape_jobs_unique (user_id, garment_id, size, garment_version_hash) would make
     enqueue_full_drape skip them as "already queued". Finally calls enqueue_full_drape
     so any active garment x size the user never had a job for is added too.

Default is a dry run that changes nothing.

    cd backend && python3 scripts/redrape_pelvis_avatars.py                 # dry run, all users
    cd backend && python3 scripts/redrape_pelvis_avatars.py --users 9ede4581-...  # dry run, some
    cd backend && python3 scripts/redrape_pelvis_avatars.py --apply         # do it
"""
import argparse
import os
import sys
from collections import Counter

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.body_clustering import compute_body_hash, compute_legacy_body_hash  # noqa: E402
from app.services.drape_dispatcher import _resolve_storage_url  # noqa: E402
from app.services.drape_queue import enqueue_full_drape  # noqa: E402
from app.services.supabase import supabase_service  # noqa: E402

# The drape handler now normalises every body to feet-at-0 and 1.8 m tall (the frame the
# garments are authored in and the widget displays). Any drape simulated against a body
# that was NOT already in that frame was made on a different body and must be redone:
# pelvis-centred LHM bodies, and feet-at-0 bodies at their real height (e.g. 1.73 m).
REFERENCE_HEIGHT_M = 1.8
TOL_M = 0.001
db = supabase_service.client


def body_y_range_m(http: httpx.Client, pipeline_files: dict):
    path = pipeline_files.get("apose_mesh") or pipeline_files.get("tpose_mesh") or pipeline_files.get("original_mesh")
    if not path:
        return None, None
    r = http.get(_resolve_storage_url(path))
    r.raise_for_status()
    ys = [float(line.split()[2]) for line in r.text.splitlines() if line.startswith("v ")]
    lo, hi = min(ys), max(ys)
    unit = 1000.0 if (hi - lo) > 10 else 1.0  # bodies are stored in mm
    return path, (lo / unit, hi / unit)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually delete + requeue (default: dry run)")
    ap.add_argument("--users", nargs="*", help="limit to these user_ids (full UUIDs)")
    args = ap.parse_args()

    q = db.table("fit_passports").select("*").eq("status", "completed")
    passports = q.execute().data or []
    if args.users:
        wanted = set(args.users)
        passports = [p for p in passports if p["user_id"] in wanted]

    affected = []
    with httpx.Client(timeout=120) as http:
        for p in passports:
            path, yr = body_y_range_m(http, p.get("pipeline_files") or {})
            if yr is None:
                continue
            off_floor = abs(yr[0]) > TOL_M
            off_height = abs((yr[1] - yr[0]) - REFERENCE_HEIGHT_M) > TOL_M
            if off_floor or off_height:
                affected.append((p, path, yr))

    print(f"{'APPLY' if args.apply else 'DRY RUN'}: {len(affected)} avatar(s) not in the "
          f"feet-at-0 / {REFERENCE_HEIGHT_M} m reference frame")
    total_rows = total_jobs = 0
    for p, path, (lo, hi) in affected:
        uid = p["user_id"]
        jobs = db.table("drape_jobs").select("id,body_hash,status,garment_id,size").eq("user_id", uid).execute().data or []
        # Re-drapes are written under the avatar-based hash (body_clustering.compute_body_hash),
        # the key the widget reads first. Delete under every hash this user's drapes may still
        # carry: the new one, the legacy measurement hash (if migrate_body_hash.py hasn't run
        # yet) and any older measurement hashes left on their jobs.
        current_hash = compute_body_hash(uid, p)
        hashes = sorted({j["body_hash"] for j in jobs if j.get("body_hash")}
                        | {current_hash, compute_legacy_body_hash(uid, p)})
        rows = []
        for h in hashes:
            rows += db.table("draped_meshes").select("id,garment_id,size").eq("body_hash", h).execute().data or []
        total_rows += len(rows)
        total_jobs += len(jobs)
        why = "pelvis-centred" if lo < -0.5 else f"h={hi - lo:.3f} m"
        print(f"  {uid}  created {p['created_at'][:10]}  body y=[{lo:.3f}, {hi:.3f}] m ({why})  "
              f"draped_meshes={len(rows)}  jobs={len(jobs)} {dict(Counter(j['status'] for j in jobs))}  "
              f"body_hashes={hashes} current={current_hash}")
        if not args.apply:
            continue
        for h in hashes:
            db.table("draped_meshes").delete().eq("body_hash", h).execute()
        db.table("drape_jobs").update({
            "status": "queued",
            "attempts": 0,
            "priority": 10,
            "body_hash": current_hash,
            "runpod_job_id": None,
            "draped_mesh_id": None,
            "error_message": None,
            "dispatched_at": None,
            "completed_at": None,
        }).eq("user_id", uid).execute()
        counts = enqueue_full_drape(uid, priority=10)
        print(f"    -> deleted draped_meshes for {len(hashes)} hash(es), reset {len(jobs)} job(s); "
              f"enqueue_full_drape: {counts}")

    print(f"TOTAL: draped_meshes rows {'deleted' if args.apply else 'to delete'}: {total_rows}; "
          f"jobs {'reset' if args.apply else 'to reset'}: {total_jobs}")
    if not args.apply:
        print("Nothing changed. Re-run with --apply after the floored drape handler is live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
