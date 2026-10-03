"""
Body Hash for Draping Cache
============================

Per-user body hash. Each shopper gets their own drape, never shared.

The hash identifies the AVATAR MESH that was draped, not the editable numbers:

    sha256("u:{user_id}|avatar:{body mesh path}|{avatar version}")[:16]

  - body mesh path: pipeline_files.apose_mesh (falling back to tpose/original), the
    exact file the drape dispatcher sends to the sim and the pose the widget shows.
  - avatar version: fit_passports.processing_completed_at, written only when an avatar
    is (re)generated (supabase.update_processing_status / update_fit_passport_with_results).
    Dashboard measurement edits (frontend updateFitPassport, measurements route) never
    touch it.

So a measurement edit keeps every cached drape (the drape body did not change), and a
regenerated avatar gets a new hash and is re-draped.

Until 2026-10 the hash was sha256(user_id + canonical measurements); an edit orphaned
every drape. `compute_legacy_body_hash` keeps that formula so lookups can fall back to
it while rows are migrated (scripts/migrate_body_hash.py).

Schema (`draped_meshes.body_hash`, `drape_jobs.body_hash`) is unchanged.

The legacy quantized-cluster function is kept below as `compute_shape_cluster`
in case we ever want shape-clustering for cost reduction. It is not used by the
live pipeline.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import NamedTuple, Optional


GENDER_MAP = {"male": "M", "female": "F", "other": "N", "neutral": "N"}


def _canonical_measurements(passport: dict) -> str:
    """Stable string representation of the measurements that drive a drape.
    Any change here invalidates every cached row. Keep keys sorted."""
    keys = ("height", "weight", "chest", "waist", "hips", "inseam",
            "shoulder_width", "arm_length", "neck", "thigh", "torso_length")
    payload = {k: passport.get(k) for k in keys if passport.get(k) is not None}
    payload["gender"] = GENDER_MAP.get((passport.get("gender") or "").lower(), "N")
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


# Columns a fit_passports select must include for compute_body_hash / lookup hashes.
PASSPORT_BODY_COLUMNS = (
    "user_id,pipeline_files,processing_completed_at,"
    "chest,waist,hips,height,weight,gender,inseam,shoulder_width,arm_length,neck,thigh,torso_length"
)


def body_mesh_path(passport: dict) -> Optional[str]:
    """The body OBJ that gets draped: A-pose first (what the widget displays and what
    the queue has always sent), then T-pose, then the original mesh."""
    pf = passport.get("pipeline_files") or {}
    return pf.get("apose_mesh") or pf.get("tpose_mesh") or pf.get("original_mesh") or None


def avatar_version(passport: dict) -> str:
    """processing_completed_at, normalised to UTC ISO so formatting differences between
    clients can't change the hash. Empty string when the avatar never completed."""
    raw = passport.get("processing_completed_at")
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="microseconds")
    except ValueError:
        return str(raw)


def compute_body_hash(user_id: str, passport: dict) -> Optional[str]:
    """
    Per-user, per-avatar body hash. 16 hex chars. Unchanged by measurement edits;
    changes when the avatar mesh is regenerated or repointed. None when the passport
    has no body mesh yet (nothing to drape).
    """
    path = body_mesh_path(passport)
    if not path:
        return None
    raw = f"u:{user_id}|avatar:{path}|{avatar_version(passport)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def compute_legacy_body_hash(user_id: str, passport: dict) -> str:
    """Pre-2026-10 hash: sha256(user_id + canonical measurements). Read-side fallback
    only; never write new rows with it."""
    raw = f"u:{user_id}|{_canonical_measurements(passport)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class BodyIdentity(NamedTuple):
    body_hash: Optional[str]      # write key (new)
    lookup_hashes: list           # read keys, preferred first: [new, legacy]
    mesh_path: Optional[str]


def body_identity(user_id: str, passport: dict) -> BodyIdentity:
    new = compute_body_hash(user_id, passport)
    legacy = compute_legacy_body_hash(user_id, passport)
    lookup = [h for h in (new, legacy) if h]
    return BodyIdentity(new, list(dict.fromkeys(lookup)), body_mesh_path(passport))


def body_identity_for_user(user_id: str) -> Optional[BodyIdentity]:
    """One passport read -> the user's body identity. None if no passport."""
    from app.services.supabase import supabase_service
    try:
        r = supabase_service.client.table("fit_passports").select(
            PASSPORT_BODY_COLUMNS
        ).eq("user_id", user_id).limit(1).execute()
    except Exception:
        return None
    if not r.data:
        return None
    return body_identity(user_id, r.data[0])


def pick_by_hash_preference(rows: list, lookup_hashes: list, key: str = "size") -> dict:
    """Given draped_meshes rows for several body hashes, keep one row per `key`,
    preferring the earliest hash in lookup_hashes (new over legacy)."""
    rank = {h: i for i, h in enumerate(lookup_hashes)}
    best: dict = {}
    for row in rows:
        k = row.get(key)
        r = rank.get(row.get("body_hash"), len(rank))
        if k is not None and (k not in best or r < rank.get(best[k].get("body_hash"), len(rank))):
            best[k] = row
    return best


def compute_body_bucket_from_passport(passport: dict, user_id: Optional[str] = None) -> str:
    """
    Backwards-compatible name. Returns the per-user body hash.
    `user_id` is required for per-user keying; if not supplied we fall back to a
    measurements-only hash (legacy path; only used by tooling that pre-dates
    per-user keying).
    """
    if user_id:
        return compute_legacy_body_hash(user_id, passport)
    raw = _canonical_measurements(passport)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Legacy: quantized shape clustering. Not used by the live pipeline. Kept here
# so a future cost-reduction pass can swap it back in by flipping one call.
# ---------------------------------------------------------------------------

QUANT_STEPS = {"height": 5, "chest": 4, "waist": 4, "hips": 4, "weight": 5}


def quantize_measurement(value: float, step: int) -> int:
    return round(value / step) * step


def compute_shape_cluster(
    height: Optional[int],
    chest: Optional[int],
    waist: Optional[int],
    hips: Optional[int],
    gender: Optional[str] = None,
    weight: Optional[int] = None,
) -> str:
    """Quantized cluster hash. Multiple users may collide. Currently unused."""
    parts = []
    g = GENDER_MAP.get((gender or "").lower(), "N")
    parts.append(f"g:{g}")
    for key, step in QUANT_STEPS.items():
        val = {"height": height, "chest": chest, "waist": waist, "hips": hips, "weight": weight}.get(key)
        if val is not None and val > 0:
            parts.append(f"{key[0]}:{quantize_measurement(float(val), step)}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


# Old name kept as alias so callers don't break.
compute_body_bucket = compute_shape_cluster


def compute_body_bucket_from_smpl(smpl_betas: list[float]) -> str:
    """
    Compute body bucket from SMPL beta parameters.
    Quantizes the first 4 betas to nearest 0.5.
    """
    quantized = [round(b * 2) / 2 for b in smpl_betas[:4]]
    raw = ",".join(f"{b:.1f}" for b in quantized)
    return hashlib.sha256(f"smpl:{raw}".encode()).hexdigest()[:16]


def generate_representative_bodies(n_buckets: int = 50) -> list[dict]:
    """
    Generate a grid of representative body shapes for pre-computation.
    Returns list of measurement dicts covering the most common body shapes.
    """
    bodies = []

    height_range = range(155, 196, 5)
    chest_ranges = {
        "M": range(84, 121, 4),
        "F": range(76, 109, 4),
    }
    waist_ranges = {
        "M": range(68, 105, 4),
        "F": range(60, 93, 4),
    }
    hips_ranges = {
        "M": range(84, 113, 4),
        "F": range(84, 117, 4),
    }

    for gender in ["M", "F"]:
        chests = list(chest_ranges[gender])
        waists = list(waist_ranges[gender])
        hipses = list(hips_ranges[gender])

        n_per_gender = n_buckets // 2
        step = max(1, (len(chests) * len(waists)) // n_per_gender)

        count = 0
        for ci, chest in enumerate(chests):
            for wi, waist in enumerate(waists):
                if (ci * len(waists) + wi) % step != 0:
                    continue
                hip = hipses[min(ci, len(hipses) - 1)]
                height = 170 if gender == "M" else 165
                bodies.append({
                    "height": height,
                    "chest": chest,
                    "waist": waist,
                    "hips": hip,
                    "gender": "male" if gender == "M" else "female",
                    "bucket": compute_body_bucket(height, chest, waist, hip, "male" if gender == "M" else "female"),
                })
                count += 1
                if count >= n_per_gender:
                    break
            if count >= n_per_gender:
                break

    return bodies
