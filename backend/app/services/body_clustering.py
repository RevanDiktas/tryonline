"""
Body Hash for Draping Cache
============================

Per-user body hash. Each shopper gets their own drape, never shared.

The hash is sha256(user_id + canonical measurements). Two consequences:

  1. Privacy / fit fidelity: shopper A and shopper B never share a draped mesh
     even if their measurements happen to round to the same bucket. Bodies are
     genuinely different and the sim must reflect that.
  2. Auto-invalidation on re-measure: if the shopper updates their fit passport,
     the canonical measurement string changes, so the hash changes, so the
     existing cache row stops matching and the dispatcher re-drapes.

Schema (`draped_meshes.body_hash`, `drape_jobs.body_hash`) is unchanged. Only
the function that produces the hash flipped.

The legacy quantized-cluster function is kept below as `compute_shape_cluster`
in case we ever want shape-clustering for cost reduction. It is not used by the
live pipeline.
"""

import hashlib
import json
from typing import Optional


GENDER_MAP = {"male": "M", "female": "F", "other": "N", "neutral": "N"}


def _canonical_measurements(passport: dict) -> str:
    """Stable string representation of the measurements that drive a drape.
    Any change here invalidates every cached row. Keep keys sorted."""
    keys = ("height", "weight", "chest", "waist", "hips", "inseam",
            "shoulder_width", "arm_length", "neck", "thigh", "torso_length")
    payload = {k: passport.get(k) for k in keys if passport.get(k) is not None}
    payload["gender"] = GENDER_MAP.get((passport.get("gender") or "").lower(), "N")
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_body_hash(user_id: str, passport: dict) -> str:
    """
    Per-user body hash. 16 hex chars. Stable across calls as long as
    measurements don't change. Includes user_id so two shoppers with identical
    measurements still get distinct rows.
    """
    raw = f"u:{user_id}|{_canonical_measurements(passport)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def compute_body_bucket_from_passport(passport: dict, user_id: Optional[str] = None) -> str:
    """
    Backwards-compatible name. Returns the per-user body hash.
    `user_id` is required for per-user keying; if not supplied we fall back to a
    measurements-only hash (legacy path; only used by tooling that pre-dates
    per-user keying).
    """
    if user_id:
        return compute_body_hash(user_id, passport)
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
