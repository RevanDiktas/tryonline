"""
Drape job queue service
=======================

Owns the `drape_jobs` table. Two entry points:

  - `enqueue_full_drape(user_id, priority)` — fan out one user across every
    active garment x size. Called from the avatar onboarding hook and from the
    admin backfill route.
  - `compute_garment_content_hash(garment_id)` — lazy-compute and persist the
    content hash for a garment by fetching its OBJ files from storage. Called
    from enqueue when the column is NULL.

Dispatcher and webhook handler live in `drape_dispatcher.py` and the route
file. This module just deals with the data layer.
"""

from __future__ import annotations

import hashlib
from typing import Iterable, Optional

import httpx

from app.config import get_settings
from app.services.body_clustering import (
    PASSPORT_BODY_COLUMNS,
    avatar_version,
    compute_body_hash,
    compute_legacy_body_hash,
)
from app.services.supabase import supabase_service

settings = get_settings()


# ---------------------------------------------------------------------------
# Garment content hash
# ---------------------------------------------------------------------------


def _resolve_storage_url(path: str) -> str:
    if not path:
        return ""
    if path.startswith("http"):
        return path
    base = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public"
    return f"{base}/{path.lstrip('/')}"


def compute_garment_content_hash(garment_id: str) -> Optional[str]:
    """
    Hash all sized OBJ files for a garment. Persists the result on
    garments.content_hash and returns it. Returns None if the garment has no
    obj_sizes (caller should skip enqueue).
    """
    r = supabase_service.client.table("garments").select(
        "id,obj_sizes,content_hash"
    ).eq("id", garment_id).limit(1).execute()
    if not r.data:
        return None
    row = r.data[0]
    obj_sizes = row.get("obj_sizes") or {}
    if not obj_sizes:
        return None

    if row.get("content_hash"):
        return row["content_hash"]

    h = hashlib.sha256()
    fetched_any = False
    for size in sorted(obj_sizes.keys()):
        path = obj_sizes[size]
        if not path:
            continue
        url = _resolve_storage_url(path)
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url)
                resp.raise_for_status()
                h.update(size.encode())
                h.update(b"|")
                h.update(resp.content)
                h.update(b"||")
                fetched_any = True
        except Exception as e:
            print(f"[drape_queue] content-hash fetch failed for {garment_id}/{size}: {e}")
            return None

    if not fetched_any:
        return None

    content_hash = h.hexdigest()[:16]
    supabase_service.client.table("garments").update({
        "content_hash": content_hash
    }).eq("id", garment_id).execute()
    return content_hash


# ---------------------------------------------------------------------------
# Enqueue
# ---------------------------------------------------------------------------


def _get_passport(user_id: str) -> Optional[dict]:
    r = supabase_service.client.table("fit_passports").select(
        PASSPORT_BODY_COLUMNS + ",status"
    ).eq("user_id", user_id).limit(1).execute()
    if not r.data:
        return None
    return r.data[0]


def _list_active_garments(brand_ids: Optional[Iterable[str]] = None) -> list[dict]:
    q = supabase_service.client.table("garments").select(
        "id,brand_id,obj_sizes,content_hash"
    ).eq("is_active", True)
    if brand_ids is not None:
        ids = [b for b in brand_ids if b]
        if not ids:
            return []
        q = q.in_("brand_id", ids)
    r = q.execute()
    return r.data or []


# Job statuses that mean "work for this row is still pending"; anything else is terminal.
_IN_FLIGHT = ("queued", "dispatched", "running")


def _enqueue_one(
    user_id: str, garment_id: str, size: str, body_hash: str, version: str,
    priority: int, counts: dict, passport: Optional[dict] = None,
) -> None:
    """Make sure one (user, garment, size, version) is draped for `body_hash`.

    - a draped_meshes row for this body_hash + version exists -> cached, nothing to do
    - no job row yet                                          -> insert a queued job
    - a job row exists (idx_drape_jobs_unique is (user, garment, size, version) and does
      NOT include body_hash, so there is at most one):
        * same body_hash and still in flight                  -> already queued
        * same body_hash and completed but no cached mesh     -> reset (mesh was deleted)
        * same body_hash and failed                           -> leave it (no retry storm)
        * DIFFERENT body_hash (avatar regenerated)            -> stale: reset to queued
          with the new hash. Before this, the duplicate insert was counted as "already
          queued" and a regenerated avatar was silently never re-draped.

    Transition (until scripts/migrate_body_hash.py has run): a drape cached under the
    user's LEGACY measurement hash by a job that finished after the current avatar was
    built is this avatar's drape. Count it as cached instead of resetting it, so a garment
    upload or backfill between deploy and migration doesn't re-drape everyone.
    """
    legacy = compute_legacy_body_hash(user_id, passport) if passport else None
    hashes = [body_hash] + ([legacy] if legacy and legacy != body_hash else [])
    cached = supabase_service.client.table("draped_meshes").select("id,body_hash").eq(
        "garment_id", garment_id
    ).eq("size", size).in_("body_hash", hashes).eq(
        "garment_version_hash", version
    ).execute()
    cached_hashes = {row.get("body_hash") for row in (cached.data or [])}
    if body_hash in cached_hashes:
        counts["skipped_already_cached"] += 1
        return

    existing = supabase_service.client.table("drape_jobs").select(
        "id,status,body_hash,completed_at"
    ).eq("user_id", user_id).eq("garment_id", garment_id).eq("size", size).eq(
        "garment_version_hash", version
    ).limit(1).execute()
    job = existing.data[0] if existing.data else None

    if (job and legacy and legacy in cached_hashes and job.get("body_hash") == legacy
            and job.get("status") == "completed"
            and avatar_version({"processing_completed_at": job.get("completed_at")})
            >= avatar_version(passport)):
        counts["skipped_already_cached"] += 1
        return

    if job is None:
        try:
            supabase_service.client.table("drape_jobs").insert({
                "user_id": user_id,
                "garment_id": garment_id,
                "size": size,
                "body_hash": body_hash,
                "garment_version_hash": version,
                "priority": priority,
                "status": "queued",
            }).execute()
            counts["enqueued"] += 1
        except Exception as e:
            msg = str(e).lower()
            if "duplicate" in msg or "23505" in msg or "unique" in msg:
                counts["skipped_already_queued"] += 1  # raced with another enqueue
            else:
                print(f"[drape_queue] enqueue failed user={user_id} garment={garment_id} size={size}: {e}")
        return

    same_body = job.get("body_hash") == body_hash
    status = job.get("status")
    if same_body and status in _IN_FLIGHT:
        counts["skipped_already_queued"] += 1
        return
    if same_body and status == "failed":
        counts["skipped_already_queued"] += 1
        return

    supabase_service.client.table("drape_jobs").update({
        "status": "queued",
        "body_hash": body_hash,
        "priority": priority,
        "attempts": 0,
        "runpod_job_id": None,
        "draped_mesh_id": None,
        "error_message": None,
        "dispatched_at": None,
        "completed_at": None,
    }).eq("id", job["id"]).execute()
    counts["enqueued"] += 1
    counts["reset_stale"] = counts.get("reset_stale", 0) + 1


def enqueue_full_drape(
    user_id: str,
    priority: int = 100,
    brand_ids: Optional[Iterable[str]] = None,
) -> dict:
    """
    Fan a user out across every active garment x size.

    Idempotent: re-running for the same user/garment/size/version is a no-op.
    Returns counters: {enqueued, skipped_no_obj, skipped_already_cached,
                       skipped_already_queued, skipped_no_passport}.
    """
    counts = {
        "enqueued": 0,
        "skipped_no_obj": 0,
        "skipped_already_cached": 0,
        "skipped_already_queued": 0,
        "skipped_no_passport": 0,
    }

    passport = _get_passport(user_id)
    if not passport:
        counts["skipped_no_passport"] = 1
        return counts

    body_hash = compute_body_hash(user_id, passport)
    if not body_hash:  # no avatar mesh yet: nothing to drape against
        counts["skipped_no_passport"] = 1
        return counts
    garments = _list_active_garments(brand_ids)

    for g in garments:
        garment_id = g["id"]
        obj_sizes = g.get("obj_sizes") or {}
        if not obj_sizes:
            counts["skipped_no_obj"] += len(["x"])
            continue

        version = g.get("content_hash") or compute_garment_content_hash(garment_id)
        if not version:
            counts["skipped_no_obj"] += 1
            continue

        for size, path in obj_sizes.items():
            if not path:
                continue
            _enqueue_one(user_id, garment_id, size, body_hash, version, priority, counts, passport)

    return counts


def enqueue_for_garment(
    garment_id: str,
    priority: int = 200,
    user_ids: Optional[Iterable[str]] = None,
) -> dict:
    """
    Reverse fan-out: drape one garment across every existing avatar with a
    completed fit passport. Used when a brand uploads a new SKU.
    """
    counts = {
        "enqueued": 0,
        "skipped_no_obj": 0,
        "skipped_already_cached": 0,
        "skipped_already_queued": 0,
        "skipped_no_passport": 0,
    }

    g_row = supabase_service.client.table("garments").select(
        "id,obj_sizes,content_hash,is_active"
    ).eq("id", garment_id).limit(1).execute()
    if not g_row.data:
        return counts
    g = g_row.data[0]
    obj_sizes = g.get("obj_sizes") or {}
    if not obj_sizes:
        counts["skipped_no_obj"] = 1
        return counts

    version = g.get("content_hash") or compute_garment_content_hash(garment_id)
    if not version:
        counts["skipped_no_obj"] = 1
        return counts

    if user_ids is None:
        users_q = supabase_service.client.table("fit_passports").select("user_id").eq(
            "status", "completed"
        ).execute()
        user_ids = [u["user_id"] for u in (users_q.data or []) if u.get("user_id")]

    for uid in user_ids:
        passport = _get_passport(uid)
        if not passport:
            counts["skipped_no_passport"] += 1
            continue
        body_hash = compute_body_hash(uid, passport)
        if not body_hash:
            counts["skipped_no_passport"] += 1
            continue

        for size, path in obj_sizes.items():
            if not path:
                continue
            _enqueue_one(uid, garment_id, size, body_hash, version, priority, counts, passport)

    return counts


# Priorities: lower runs first. The fan-out after onboarding uses 10, backfills 100 and a
# new garment 200. A garment the shopper has open in the try-on goes ahead of all of them.
PRIORITY_ON_SCREEN = 0      # the size the shopper is looking at
PRIORITY_IN_VIEWER = 1      # the other sizes of the garment they have open


def prioritize_drape(user_id: str, garment_id: str, size: str, priority: int) -> Optional[dict]:
    """The try-on is showing this garment: make sure this shopper's drape for it exists and
    is first in line. Uses the same drape_jobs row as the fan-out (one job per user,
    garment, size and version), so nothing is draped twice.

    Returns the job row ({id, status, priority, error_message}), or None when the shopper
    has no avatar or the garment has no OBJ for this size.
    """
    passport = _get_passport(user_id)
    if not passport:
        return None
    body_hash = compute_body_hash(user_id, passport)
    if not body_hash:
        return None
    g = supabase_service.client.table("garments").select(
        "id,obj_sizes,content_hash"
    ).eq("id", garment_id).limit(1).execute()
    if not g.data or not (g.data[0].get("obj_sizes") or {}).get(size):
        return None
    version = g.data[0].get("content_hash") or compute_garment_content_hash(garment_id)
    if not version:
        return None

    counts = {"enqueued": 0, "skipped_already_cached": 0, "skipped_already_queued": 0}
    _enqueue_one(user_id, garment_id, size, body_hash, version, priority, counts, passport)

    r = supabase_service.client.table("drape_jobs").select(
        "id,status,priority,error_message"
    ).eq("user_id", user_id).eq("garment_id", garment_id).eq("size", size).eq(
        "garment_version_hash", version
    ).limit(1).execute()
    job = r.data[0] if r.data else None
    # Still waiting in our queue behind other work: move it up. (Once handed to RunPod
    # it is already next or running.)
    if job and job.get("status") == "queued" and (job.get("priority") is None or job["priority"] > priority):
        supabase_service.client.table("drape_jobs").update({"priority": priority}).eq("id", job["id"]).execute()
        job["priority"] = priority
    return job
