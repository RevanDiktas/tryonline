"""
Rewrite draped_meshes.body_hash and drape_jobs.body_hash from the legacy measurement
hash to the avatar-based hash (app/services/body_clustering.py), for EVERY user.

Why: the legacy hash was sha256(user_id + editable measurements), so a dashboard edit
orphaned every drape. The new hash identifies the avatar mesh. Lookups already try the
new hash first and fall back to the legacy one, so this can run any time after the
backend deploy; it just makes the fallback unnecessary.

Per user (passport with a body mesh):
  new    = compute_body_hash(...)            avatar mesh path + processing_completed_at
  source = legacy hash from today's measurements + every body_hash on the user's jobs
           (older measurement edits left older hashes behind)
  1. collect draped_meshes rows under {new} + source
  2. drop from consideration rows finished BEFORE the current avatar existed
     (drape time < processing_completed_at): they were draped on a previous avatar and
     must not be re-labelled as this one. They are left untouched and reported.
     Drape time = the linked job's completed_at (the callback upserts, so a row's
     created_at is its FIRST drape, not its latest), else the row's created_at.
  3. per (garment_id, size) keep the newest row; delete the rest (draped_meshes is unique
     on (garment_id, size, body_hash), so two rows can't both carry the new hash)
  4. set the kept row's body_hash = new
  5. drape_jobs: body_hash = new; draped_mesh_id repointed to the kept row (or null)
     idx_drape_jobs_unique is (user_id, garment_id, size, garment_version_hash) and
     does not include body_hash, so rewriting body_hash can never collide.

Default is a dry run that changes nothing.

    cd backend && python3 scripts/migrate_body_hash.py              # dry run, all users
    cd backend && python3 scripts/migrate_body_hash.py --users <uuid> ...
    cd backend && python3 scripts/migrate_body_hash.py --apply
"""
import argparse
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.body_clustering import (  # noqa: E402
    PASSPORT_BODY_COLUMNS,
    compute_body_hash,
    compute_legacy_body_hash,
)
from app.services.supabase import supabase_service  # noqa: E402

db = supabase_service.client


def fetch_all(table: str, columns: str) -> list[dict]:
    rows, off = [], 0
    while True:
        batch = db.table(table).select(columns).order("id").range(off, off + 999).execute().data or []
        if not batch:
            return rows
        rows += batch
        off += len(batch)


def ts(value) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--users", nargs="*", help="limit to these user_ids")
    args = ap.parse_args()

    passports = db.table("fit_passports").select(PASSPORT_BODY_COLUMNS).execute().data or []
    if args.users:
        passports = [p for p in passports if p["user_id"] in set(args.users)]
    jobs = fetch_all("drape_jobs", "id,user_id,garment_id,size,body_hash,draped_mesh_id,completed_at,status")
    meshes = fetch_all("draped_meshes", "id,garment_id,size,body_hash,created_at")

    jobs_by_user = defaultdict(list)
    for j in jobs:
        jobs_by_user[j["user_id"]].append(j)
    meshes_by_hash = defaultdict(list)
    for m in meshes:
        meshes_by_hash[m["body_hash"]].append(m)
    job_by_mesh = {j["draped_mesh_id"]: j for j in jobs if j.get("draped_mesh_id")}

    totals = Counter()
    claimed_hashes = set()
    print(f"{'APPLY' if args.apply else 'DRY RUN'}: {len(passports)} passport(s), "
          f"{len(meshes)} draped_meshes, {len(jobs)} drape_jobs")

    for p in passports:
        uid = p["user_id"]
        new = compute_body_hash(uid, p)
        if not new:
            totals["users_without_body"] += 1
            continue
        legacy = compute_legacy_body_hash(uid, p)
        user_jobs = jobs_by_user.get(uid, [])
        source = ({legacy} | {j["body_hash"] for j in user_jobs if j.get("body_hash")}) - {new}
        claimed_hashes |= source | {new}
        avatar_done = ts(p.get("processing_completed_at"))

        rows = [m for h in (source | {new}) for m in meshes_by_hash.get(h, [])]
        if not rows and not any(j.get("body_hash") != new for j in user_jobs):
            totals["users_nothing_to_do"] += 1
            continue

        def drape_time(m):
            j = job_by_mesh.get(m["id"])
            return max(ts(m.get("created_at")), ts(j.get("completed_at")) if j else ts(None))

        current, older_avatar = [], []
        for m in rows:
            (older_avatar if m["body_hash"] != new and drape_time(m) < avatar_done else current).append(m)

        keep, delete = {}, []
        groups = defaultdict(list)
        for m in current:
            groups[(m["garment_id"], m["size"])].append(m)
        for key, ms in groups.items():
            ms.sort(key=lambda m: (drape_time(m), m["body_hash"] == new), reverse=True)
            keep[key] = ms[0]
            delete += ms[1:]
        relabel = [m for m in keep.values() if m["body_hash"] != new]
        job_updates = [j for j in user_jobs if j.get("body_hash") != new]
        deleted_ids = {m["id"] for m in delete}

        totals["users_migrated"] += 1
        totals["meshes_relabelled"] += len(relabel)
        totals["meshes_already_new"] += sum(1 for m in keep.values() if m["body_hash"] == new)
        totals["meshes_deleted_collision"] += len(delete)
        totals["meshes_left_older_avatar"] += len(older_avatar)
        totals["jobs_relabelled"] += len(job_updates)
        print(f"  {uid}  new={new} legacy={legacy} sources={sorted(source)}  "
              f"relabel={len(relabel)} keep_new={len(keep) - len(relabel)} "
              f"delete_collision={len(delete)} older_avatar={len(older_avatar)} jobs={len(job_updates)}")

        if not args.apply:
            continue
        for m in delete:
            db.table("draped_meshes").delete().eq("id", m["id"]).execute()
        for m in relabel:
            db.table("draped_meshes").update({"body_hash": new}).eq("id", m["id"]).execute()
        for j in user_jobs:
            upd = {}
            if j.get("body_hash") != new:
                upd["body_hash"] = new
            if j.get("draped_mesh_id") in deleted_ids:
                k = keep.get((j["garment_id"], j["size"]))
                upd["draped_mesh_id"] = k["id"] if k else None
            if upd:
                db.table("drape_jobs").update(upd).eq("id", j["id"]).execute()

    orphan = sum(len(v) for h, v in meshes_by_hash.items() if h not in claimed_hashes)
    print("\nTOTALS:", dict(totals), f"| draped_meshes under no user's hash (left as-is): {orphan}")
    if not args.apply:
        print("Nothing changed. Re-run with --apply after the backend with the new hash is deployed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
