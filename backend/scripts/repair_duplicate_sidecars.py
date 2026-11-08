"""
Repair garments duplicated before the sidecar fix: copy the .mtl / texture files from the
source folder into each copy's folder, then re-queue that copy's failed drape jobs.

Run on the backend host (needs the service-role env):
    python -m scripts.repair_duplicate_sidecars            # dry run
    python -m scripts.repair_duplicate_sidecars --apply
"""
import sys
from app.services.supabase import SupabaseService
from app.api.routes.garments import _copy_sidecar_files, _storage_product_folder

apply = "--apply" in sys.argv
sb = SupabaseService()
bucket = sb.client.storage.from_("garments")

# Copies share content_hash with their source; find pairs inside one brand.
rows = sb.client.table("garments").select("id,brand_id,name,content_hash,shopify_product_id,shopify_product_handle,obj_sizes,created_at").not_.is_("content_hash", "null").order("created_at").execute().data or []
by_hash: dict = {}
for r in rows:
    by_hash.setdefault((r["brand_id"], r["content_hash"]), []).append(r)

for (brand_id, _h), group in by_hash.items():
    if len(group) < 2:
        continue
    src, copies = group[0], group[1:]
    for c in copies:
        failed = sb.client.table("drape_jobs").select("id", count="exact").eq("garment_id", c["id"]).eq("status", "failed").execute()
        n_failed = failed.count or 0
        print(f"{c['name']!r} <- {src['name']!r}: {n_failed} failed jobs")
        if not apply:
            continue
        n = _copy_sidecar_files(bucket, brand_id, _storage_product_folder(src), _storage_product_folder(c))
        print(f"  copied {n} sidecar files")
        if n and n_failed:
            sb.client.table("drape_jobs").update({"status": "queued", "attempts": 0, "error_message": None, "runpod_job_id": None, "dispatched_at": None}).eq("garment_id", c["id"]).eq("status", "failed").execute()
            print(f"  re-queued {n_failed} jobs")
print("done" + ("" if apply else " (dry run; add --apply)"))
