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
from app.services.body_clustering import compute_body_hash
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
        "user_id,chest,waist,hips,height,weight,gender,inseam,"
        "shoulder_width,arm_length,neck,thigh,torso_length,pipeline_files,status"
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

            cached = supabase_service.client.table("draped_meshes").select("id").eq(
                "garment_id", garment_id
            ).eq("size", size).eq("body_hash", body_hash).eq(
                "garment_version_hash", version
            ).limit(1).execute()
            if cached.data:
                counts["skipped_already_cached"] += 1
                continue

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
                    counts["skipped_already_queued"] += 1
                else:
                    print(f"[drape_queue] enqueue failed user={user_id} garment={garment_id} size={size}: {e}")

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

        for size, path in obj_sizes.items():
            if not path:
                continue
            cached = supabase_service.client.table("draped_meshes").select("id").eq(
                "garment_id", garment_id
            ).eq("size", size).eq("body_hash", body_hash).eq(
                "garment_version_hash", version
            ).limit(1).execute()
            if cached.data:
                counts["skipped_already_cached"] += 1
                continue
            try:
                supabase_service.client.table("drape_jobs").insert({
                    "user_id": uid,
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
                    counts["skipped_already_queued"] += 1
                else:
                    print(f"[drape_queue] enqueue failed user={uid} garment={garment_id} size={size}: {e}")

    return counts
