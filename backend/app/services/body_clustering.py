"""
Body Shape Clustering for Draping Pre-computation
==================================================

Clusters users into body shape buckets based on their measurements.
This allows pre-computing draped meshes for ~50 representative body shapes
per garment+size, so most users get an instant cache hit.

Bucket key = quantized measurements hash (e.g., chest rounded to nearest 4cm).
"""

import hashlib
from typing import Optional


# Quantization step sizes (cm) — controls bucket granularity
# Smaller = more buckets (better fit, more compute)
# Larger = fewer buckets (faster cache hits, slightly less precise)
QUANT_STEPS = {
    "height": 5,
    "chest": 4,
    "waist": 4,
    "hips": 4,
    "weight": 5,
}

# Gender multiplier for separation
GENDER_MAP = {"male": "M", "female": "F", "other": "N", "neutral": "N"}


def quantize_measurement(value: float, step: int) -> int:
    """Round a measurement to the nearest step."""
    return round(value / step) * step


def compute_body_bucket(
    height: Optional[int],
    chest: Optional[int],
    waist: Optional[int],
    hips: Optional[int],
    gender: Optional[str] = None,
    weight: Optional[int] = None,
) -> str:
    """
    Compute a body shape bucket hash from measurements.

    Returns a 16-char hex string that groups similar body shapes together.
    Two users with similar measurements will get the same bucket hash,
    enabling shared draping cache.
    """
    parts = []

    g = GENDER_MAP.get((gender or "").lower(), "N")
    parts.append(f"g:{g}")

    for key, step in QUANT_STEPS.items():
        val = {"height": height, "chest": chest, "waist": waist, "hips": hips, "weight": weight}.get(key)
        if val is not None and val > 0:
            q = quantize_measurement(float(val), step)
            parts.append(f"{key[0]}:{q}")

    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def compute_body_bucket_from_passport(passport: dict) -> str:
    """Compute body bucket from a fit_passports row dict."""
    return compute_body_bucket(
        height=passport.get("height"),
        chest=passport.get("chest"),
        waist=passport.get("waist"),
        hips=passport.get("hips"),
        gender=passport.get("gender"),
        weight=passport.get("weight"),
    )


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
