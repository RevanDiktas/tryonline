"""
Body measurements from photos for partners, with no shopper account.

A made-to-measure partner sends a front photo and, optionally, a side photo with the
person's height. Each photo runs as its own job on the avatar GPU endpoint (the same
endpoint and payload as /api/avatar/create, unchanged) and comes back as measurements in cm.
Nothing here creates a user, a fit passport or a drape.

Partner (X-API-Key header, or ?k= on the test page link):
- POST /api/measure               -- photos + height -> {id, status}
- GET  /api/measure               -- the partner's recent requests
- GET  /api/measure/{id}          -- status, per-photo and combined measurements, body mesh
- POST /api/measure/{id}/actual   -- the partner's own tape measurements, for comparison

There is no background worker: GET /{id} asks RunPod where each photo's job is and saves
the result the first time it is finished, so a backend restart loses nothing. RunPod keeps
a finished job for about half an hour; a request nobody polls in that time is marked failed.

GPU time per request is stored on the row (gpu_ms, gpu_cost_usd) for pricing; it is never
returned to the partner.
"""
import asyncio
import hmac
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from slowapi import Limiter

from app.api.rate_limit import client_key
from app.config import get_settings
from app.services.runpod import runpod_service
from app.services.supabase import supabase_service

settings = get_settings()
router = APIRouter()
limiter = Limiter(key_func=client_key)

TABLE = "measure_requests"
MAX_PHOTO_BYTES = 10 * 1024 * 1024
VIEW_TIMEOUT_SECONDS = 15 * 60       # a photo's job that is not done by then has failed
SIGNED_URL_SECONDS = 3600
GENDERS = ("male", "female", "neutral")
# What the avatar endpoint can return, in the order the page shows them.
MEASUREMENT_KEYS = (
    "height", "chest", "waist", "hips", "neck", "shoulder_width", "arm_length", "bicep",
    "forearm", "wrist", "inseam", "thigh", "calf", "ankle", "torso_length", "crotch_height",
    "head",
)
# Body meshes kept from the front photo's job: output key -> (file name, content type).
BODY_FILES = {
    "tpose_mesh": ("body_tpose.obj", "text/plain"),
    "avatar_glb": ("body_apose.glb", "model/gltf-binary"),
}

# RunPod serverless prices per GPU hour (runpod.io/pricing, read 2026-11-19), matched as a
# substring of the worker's GPU name. The avatar endpoint mostly lands on A40s, sometimes
# on an H100, which costs five times as much per second.
GPU_USD_PER_HOUR = {
    "H200": 6.99, "H100": 5.89, "A100": 2.99, "L40": 1.89, "6000 Ada": 1.89, "5090": 1.89,
    "A6000": 1.22, "A40": 1.22, "PRO 4500": 1.15,
}
# A worker stays up, and billed, this long after each job (the endpoint's idle timeout).
IDLE_BILLED_SECONDS = 5


def gpu_cost_usd(gpu_ms: Optional[int], gpu: Optional[str]) -> float:
    """What one job cost: its run time plus the idle tail, at its GPU's price.

    Not included: loading the models on a cold worker, which RunPod bills but only
    reports mixed in with queue time (queue_ms on the view is the upper bound).
    """
    per_hour = next(
        (price for name, price in GPU_USD_PER_HOUR.items() if gpu and name in gpu),
        settings.measure_gpu_usd_per_hour_default,
    )
    seconds = (gpu_ms or 0) / 1000 + IDLE_BILLED_SECONDS
    return round(seconds * per_hour / 3600, 5)


# Requests whose finished jobs are being saved right now, so two polls do not both do it.
_saving: set[str] = set()


def _partners() -> Dict[str, str]:
    """MEASURE_API_KEYS is 'partner:key,partner:key' -> {key: partner}."""
    out: Dict[str, str] = {}
    for item in (settings.measure_api_keys or "").split(","):
        name, _, key = item.strip().partition(":")
        if name.strip() and key.strip():
            out[key.strip()] = name.strip()
    return out


def require_partner(
    x_api_key: Optional[str] = Header(default=None),
    k: Optional[str] = Query(default=None),
) -> str:
    given = (x_api_key or k or "").strip()
    if given:
        for key, partner in _partners().items():
            if hmac.compare_digest(given.encode(), key.encode()):
                return partner
    raise HTTPException(status_code=401, detail="Missing or invalid API key")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db():
    return supabase_service.client.table(TABLE)


def _bucket():
    return supabase_service.client.storage.from_(settings.photos_bucket)


async def _load(request_id: str, partner: str) -> Dict[str, Any]:
    try:
        uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Request not found")
    res = await asyncio.to_thread(
        lambda: _db().select("*").eq("id", request_id).eq("partner", partner).limit(1).execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Request not found")
    return res.data[0]


async def _save(request_id: str, changes: Dict[str, Any]) -> None:
    changes = {**changes, "updated_at": _now()}
    await asyncio.to_thread(lambda: _db().update(changes).eq("id", request_id).execute())


async def _read_photo(upload: UploadFile, name: str) -> bytes:
    if not upload.content_type or not upload.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"The {name} photo must be an image")
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail=f"The {name} photo is empty")
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail=f"The {name} photo is too large (max 10 MB)")
    return data


def _extension(upload: UploadFile) -> str:
    ext = (upload.filename or "").rsplit(".", 1)[-1].lower() if "." in (upload.filename or "") else ""
    return ext if ext in ("jpg", "jpeg", "png", "webp", "heic") else "jpg"


def _clean(measurements: Any) -> Dict[str, float]:
    """Keep the numeric values, in cm, to one decimal."""
    out: Dict[str, float] = {}
    if not isinstance(measurements, dict):
        return out
    for key, value in measurements.items():
        try:
            number = round(float(value), 1)
        except (TypeError, ValueError):
            continue
        if number > 0:
            out[key] = number
    return out


def combine(views: Dict[str, Dict[str, Any]], height_cm: float) -> tuple[Optional[Dict[str, float]], Optional[str]]:
    """One result from the photos that worked.

    Each photo gives its own estimate of the same body. With both, a measurement is the
    mean of the two; with one, it is that one. Height is what the person told us.
    """
    done = {name: v["measurements"] for name, v in views.items() if v.get("measurements")}
    if not done:
        return None, None
    if len(done) == 1:
        (name, only), = done.items()
        combined = dict(only)
        method = f"{name}_only"
    else:
        keys = [k for k in MEASUREMENT_KEYS if any(k in m for m in done.values())]
        keys += sorted({k for m in done.values() for k in m} - set(keys))
        combined = {}
        for key in keys:
            values = [m[key] for m in done.values() if key in m]
            combined[key] = round(sum(values) / len(values), 1)
        method = "mean_of_views"
    combined["height"] = round(float(height_cm), 1)
    return combined, method


async def _advance_view(row: Dict[str, Any], name: str, view: Dict[str, Any]) -> bool:
    """Ask RunPod about one photo's job. Returns True when the view changed."""
    if view.get("status") in ("completed", "failed"):
        return False

    age = (datetime.now(timezone.utc) - datetime.fromisoformat(row["created_at"])).total_seconds()

    result = await runpod_service.get_job_status(view["runpod_job_id"])
    status = result.get("status") or ""
    timing = result.get("timing") or {}

    async def billed() -> Dict[str, Any]:
        gpu = await runpod_service.worker_gpu(timing.get("worker_id"))
        return {
            "gpu_ms": timing.get("gpu_ms"),
            "queue_ms": timing.get("queue_ms"),
            "gpu": gpu,
            "cost_usd": gpu_cost_usd(timing.get("gpu_ms"), gpu) if timing.get("gpu_ms") else 0,
        }

    async def fail(message: str) -> bool:
        view.update(status="failed", error=message, **(await billed()))
        return True

    if status == "COMPLETED":
        output = result.get("output") or {}
        if result.get("error") or output.get("error"):
            return await fail(str(result.get("error") or output.get("error")))
        measurements = _clean(output.get("measurements"))
        if not measurements:
            return await fail("No measurements came back for this photo")
        if name == "front":
            files = dict(row.get("files") or {})
            for key, (filename, content_type) in BODY_FILES.items():
                data = (output.get("files_bytes") or {}).get(key)
                if not data:
                    continue
                path = f"partners/{row['partner']}/{row['id']}/{filename}"
                try:
                    await asyncio.to_thread(
                        _bucket().upload, path, data, {"content-type": content_type, "x-upsert": "true"}
                    )
                    files[key] = path
                except Exception as e:
                    # The measurements are the product; the mesh only illustrates them.
                    print(f"[Measure] Could not store {filename} for {row['id']}: {e}")
            row["files"] = files
        view.update(
            status="completed",
            measurements=measurements,
            error=None,
            pipeline_s=output.get("processing_time"),
            **(await billed()),
        )
        return True

    if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
        return await fail(str(result.get("error") or "GPU processing failed"))

    if age > VIEW_TIMEOUT_SECONDS:
        return await fail("Timed out waiting for the GPU")

    new_status = "processing" if status == "IN_PROGRESS" else "queued"
    if new_status != view.get("status"):
        view["status"] = new_status
        return True
    return False


async def _advance(row: Dict[str, Any]) -> Dict[str, Any]:
    """Bring a processing request up to date with RunPod and save what changed."""
    if row["status"] != "processing" or row["id"] in _saving:
        return row
    _saving.add(row["id"])
    try:
        views = row.get("views") or {}
        changed = await asyncio.gather(*[_advance_view(row, name, view) for name, view in views.items()])
        if not any(changed):
            return row

        changes: Dict[str, Any] = {"views": views, "files": row.get("files") or {}}
        if all(v.get("status") in ("completed", "failed") for v in views.values()):
            combined, method = combine(views, float(row["height_cm"]))
            gpu_ms = sum(int(v.get("gpu_ms") or 0) for v in views.values())
            changes.update(
                status="completed" if combined else "failed",
                measurements=combined,
                method=method,
                error=None if combined else "; ".join(
                    f"{name}: {v.get('error')}" for name, v in views.items() if v.get("error")
                ) or "Measurement failed",
                gpu_ms=gpu_ms,
                gpu_cost_usd=round(sum(float(v.get("cost_usd") or 0) for v in views.values()), 5),
                completed_at=_now(),
            )
        await _save(row["id"], changes)
        row.update(changes)
        return row
    finally:
        _saving.discard(row["id"])


def _message(row: Dict[str, Any]) -> str:
    if row["status"] == "completed":
        return "Done"
    if row["status"] == "failed":
        return "We could not measure from these photos"
    statuses = [v.get("status") for v in (row.get("views") or {}).values()]
    if any(s == "processing" for s in statuses) or any(s == "completed" for s in statuses):
        return "Measuring..."
    return "Starting the measurement engine..."


async def _signed(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    url = await asyncio.to_thread(supabase_service.get_photo_signed_url, path, SIGNED_URL_SECONDS)
    return url or None


async def _public(row: Dict[str, Any], with_body: bool = True) -> Dict[str, Any]:
    """What the partner sees. GPU time and cost stay on our side."""
    files = row.get("files") or {}
    views = {
        name: {
            "status": v.get("status"),
            "measurements": v.get("measurements"),
            "error": v.get("error"),
        }
        for name, v in (row.get("views") or {}).items()
    }
    out = {
        "id": row["id"],
        "status": row["status"],
        "message": _message(row),
        "label": row.get("label"),
        "height_cm": row.get("height_cm"),
        "weight_kg": row.get("weight_kg"),
        "age": row.get("age"),
        "gender": row.get("gender"),
        "views": views,
        "measurements": row.get("measurements"),
        "method": row.get("method"),
        "actual": row.get("actual"),
        "actual_notes": row.get("actual_notes"),
        "error": row.get("error"),
        "created_at": row.get("created_at"),
        "completed_at": row.get("completed_at"),
    }
    if with_body:
        out["body"] = {
            "tpose_obj_url": await _signed(files.get("tpose_mesh")),
            "apose_glb_url": await _signed(files.get("avatar_glb")),
        }
    return out


@router.post("")
@limiter.limit("10/minute")
async def create_measurement(
    request: Request,
    front: UploadFile = File(...),
    side: Optional[UploadFile] = File(default=None),
    height_cm: float = Form(...),
    gender: str = Form(...),
    weight_kg: Optional[float] = Form(default=None),
    age: Optional[int] = Form(default=None),
    label: Optional[str] = Form(default=None),
    partner: str = Depends(require_partner),
):
    """Start a measurement from a front photo and an optional side photo."""
    if not 120 <= height_cm <= 230:
        raise HTTPException(status_code=400, detail="height_cm must be between 120 and 230")
    gender = (gender or "").strip().lower()
    if gender not in GENDERS:
        raise HTTPException(status_code=400, detail="gender must be male, female or neutral")
    if weight_kg is not None and not 30 <= weight_kg <= 300:
        raise HTTPException(status_code=400, detail="weight_kg must be between 30 and 300")
    if age is not None and not 14 <= age <= 100:
        raise HTTPException(status_code=400, detail="age must be between 14 and 100")

    photos = {"front": (front, await _read_photo(front, "front"))}
    if side is not None and side.filename:
        photos["side"] = (side, await _read_photo(side, "side"))

    request_id = str(uuid.uuid4())
    views: Dict[str, Dict[str, Any]] = {}
    for name, (upload, data) in photos.items():
        path = f"partners/{partner}/{request_id}/{name}.{_extension(upload)}"
        try:
            await asyncio.to_thread(
                _bucket().upload, path, data,
                {"content-type": upload.content_type or "image/jpeg", "x-upsert": "true"},
            )
        except Exception as e:
            print(f"[Measure] Photo upload failed for {request_id}/{name}: {e}")
            raise HTTPException(status_code=502, detail="Could not store the photo. Please try again.")
        views[name] = {"photo_path": path, "status": "queued"}

    async def submit(name: str) -> None:
        url = await _signed(views[name]["photo_path"])
        job_id = None
        if url:
            job_id = await runpod_service.submit_avatar_job(
                photo_url=url,
                height=int(round(height_cm)),
                weight=int(round(weight_kg)) if weight_kg is not None else None,
                gender=gender,
                user_id=f"measure-{request_id}-{name}",
            )
        if job_id:
            views[name]["runpod_job_id"] = job_id
        else:
            views[name].update(status="failed", error="Could not start the measurement")

    await asyncio.gather(*[submit(name) for name in views])
    started = any(v.get("runpod_job_id") for v in views.values())

    row = {
        "id": request_id,
        "partner": partner,
        "label": (label or "").strip()[:80] or None,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "age": age,
        "gender": gender,
        "status": "processing" if started else "failed",
        "views": views,
        "error": None if started else "Could not start the measurement",
    }
    try:
        await asyncio.to_thread(lambda: _db().insert(row).execute())
    except Exception as e:
        print(f"[Measure] Could not save request {request_id}: {e}")
        raise HTTPException(status_code=502, detail="Could not save the request. Please try again.")
    if not started:
        raise HTTPException(status_code=502, detail="The measurement engine is unavailable. Please try again.")
    print(f"[Measure] {partner} request {request_id}: {list(views)} submitted")
    return {"id": request_id, "status": "processing"}


@router.get("")
async def list_measurements(partner: str = Depends(require_partner), limit: int = Query(default=50, ge=1, le=200)):
    """The partner's most recent requests, newest first."""
    res = await asyncio.to_thread(
        lambda: _db().select("*").eq("partner", partner).order("created_at", desc=True).limit(limit).execute()
    )
    return {"requests": [await _public(row, with_body=False) for row in (res.data or [])]}


@router.get("/{request_id}")
async def get_measurement(request_id: str, partner: str = Depends(require_partner)):
    """Status and results. Poll this until status is completed or failed."""
    row = await _load(request_id, partner)
    row = await _advance(row)
    return await _public(row)


class ActualMeasurements(BaseModel):
    actual: Dict[str, float] = Field(default_factory=dict)
    notes: Optional[str] = Field(default=None, max_length=2000)


@router.post("/{request_id}/actual")
async def save_actual(request_id: str, body: ActualMeasurements, partner: str = Depends(require_partner)):
    """Store the partner's tape measurements (cm) next to ours."""
    row = await _load(request_id, partner)
    actual = {k[:40]: round(float(v), 1) for k, v in body.actual.items() if 0 < float(v) < 400}
    changes = {"actual": actual or None, "actual_notes": (body.notes or "").strip() or None}
    await _save(request_id, changes)
    row.update(changes)
    return await _public(row)
