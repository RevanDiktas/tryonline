"""Measurement-only RunPod worker: photos + height + weight + gender -> body measurements in cm.

    photo(s) -> preprocess (segment the person, check the photo, frame like BodyM)
             -> silhouette model (averaged over the accepted shots)  -> measurements
    height + weight -> SMPL-X body for display (not used for the measurements)

INPUT  {"input": {
    "front_url": str,                    required
    "side_url": str | null,
    "front_extra_urls": [str], "side_extra_urls": [str],      more shots of the same view (the page takes 3)
    "height_cm": number,                 required, 120 to 230
    "weight_kg": number,                 required, 30 to 250 (the model cannot run without it)
    "gender": "male" | "female" | "neutral",                  required
    "age": int | null, "front_pitch_deg": number | null, "side_pitch_deg": number | null,
    "body": bool                         default true; false skips the display body
    "ping": true                         -> selftest instead of a measurement
}}
OUTPUT (JSON only)  {
    "measurements": {key: cm} | absent when refused,
    "method": "front_and_side" | "front_only",
    "height_weight_only": {key: cm},     what height + weight alone would say, to show how far the photo moved it
    "checks": {"front": [{ok, reason, message, numbers}, ...], "side": [...]},      one entry per photo sent
    "body": {"tpose_obj_base64": str | null, ...},
    "model_version": str, "notes": [str], "timings": {...},
    "error": str, "reason": str          only on failure; "reason" is the check code when a photo was refused
}
Photos are read into memory, measured and dropped. Nothing is written to disk or sent anywhere.
"""
import base64
import io
import json
import os
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

BUILD = os.environ.get("MEASURE_BUILD", "dev")
CNN_PATH = Path(os.environ.get("MEASURE_CNN_PATH", HERE / "weights" / "measure_cnn.pt"))
HUMAN_MODELS = Path(os.environ.get("MEASURE_HUMAN_MODELS", HERE / "human_model_files"))     # holds smplx/SMPLX_*.npz
DEEPLAB_WEIGHTS = os.environ.get("MEASURE_DEEPLAB_WEIGHTS") or None                         # else torchvision's cache
ALLOW_LOCAL_FILES = os.environ.get("MEASURE_ALLOW_LOCAL_FILES") == "1"                      # local harness only

MAX_PHOTO_BYTES = 15 * 1024 * 1024
MAX_SHOTS_PER_VIEW = 4
DOWNLOAD_TIMEOUT_S = 30.0
HEIGHT_RANGE, WEIGHT_RANGE = (120.0, 230.0), (30.0, 250.0)
BODY_HEIGHT_RANGE, BODY_BMI_RANGE = (140.0, 210.0), (15.0, 45.0)      # where measure_core/test_fit.py checked the fit
TILT_WARN_DEG = 10.0            # beyond this a tilted phone starts to cost accuracy (robustness tables, measure_ml)

# BodyM column -> our API key. See README.md for what each one measures.
KEYS = {"ankle": "ankle", "arm-length": "arm_length", "bicep": "bicep", "calf": "calf", "chest": "chest", "forearm": "forearm",
        "height": "height_from_photo", "hip": "hips", "leg-length": "leg_length", "shoulder-breadth": "shoulder_width",
        "shoulder-to-crotch": "torso_length", "thigh": "thigh", "waist": "waist", "wrist": "wrist"}

_STATE = {}


class BadInput(Exception):
    def __init__(self, message, reason="bad_input"):
        super().__init__(message); self.reason = reason


# ---------------------------------------------------------------- loading (once per warm worker)
def _device():
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def _segmenter():
    if "segmenter" not in _STATE:
        import preprocess
        _STATE["segmenter"] = preprocess.load_segmenter(device=_device(), weights_path=DEEPLAB_WEIGHTS)
    return _STATE["segmenter"]


def _cnn():
    if "cnn" not in _STATE:
        from model import SilhouetteModel
        _STATE["cnn"] = SilhouetteModel(CNN_PATH, device=_device())
    return _STATE["cnn"]


def _smplx_layer(gender):
    key = "smplx_" + gender
    if key not in _STATE:
        import smplx
        _STATE[key] = smplx.create(str(HUMAN_MODELS), model_type="smplx", gender=gender, use_pca=False, flat_hand_mean=True, num_betas=10).eval()
    return _STATE[key]


# ---------------------------------------------------------------- pieces
def _fetch(url):
    """Photo bytes from an https URL. Local paths only when the harness asks for them."""
    if not isinstance(url, str) or not url.strip():
        raise BadInput("A photo URL is empty.")
    if url.startswith(("http://", "https://")):
        import httpx
        with httpx.Client(timeout=DOWNLOAD_TIMEOUT_S, follow_redirects=True) as c, c.stream("GET", url) as r:
            r.raise_for_status()
            buf = io.BytesIO()
            for chunk in r.iter_bytes():
                buf.write(chunk)
                if buf.tell() > MAX_PHOTO_BYTES:
                    raise BadInput("A photo is larger than 15 MB.", "photo_too_large")
            return buf.getvalue()
    if ALLOW_LOCAL_FILES:
        data = Path(url[7:] if url.startswith("file://") else url).read_bytes()
        if len(data) > MAX_PHOTO_BYTES:
            raise BadInput("A photo is larger than 15 MB.", "photo_too_large")
        return data
    raise BadInput("Photo URLs must start with https://.")


def _number(inp, key, lo, hi, required=True):
    v = inp.get(key)
    if v is None or v == "":
        if required:
            raise BadInput(f"{key} is required.", "missing_" + key)
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        raise BadInput(f"{key} must be a number.")
    if not (lo <= v <= hi):
        raise BadInput(f"{key} must be between {lo:g} and {hi:g}.")
    return v


def _view(urls, view, timings):
    """Preprocess every photo of one view. Returns (accepted framed masks, one check dict per photo)."""
    import preprocess
    masks, checks = [], []
    for i, url in enumerate(urls):
        t = time.time()
        try:
            out = preprocess.preprocess(_fetch(url), view, _segmenter())
            c = out["check"]
            if c["ok"] and out["mask_960x720"] is not None:
                masks.append(out["mask_960x720"])
            for k, v in out["seconds"].items():
                timings[f"{view}_{k}"] = round(timings.get(f"{view}_{k}", 0.0) + v, 3)
        except BadInput:
            raise
        except Exception as e:  # noqa: BLE001  a photo that cannot be fetched or decoded is a refused photo, not a crash
            c = {"ok": False, "reason": "unreadable", "message": "This photo could not be read. Please send a JPEG or PNG.",
                 "failed": ["unreadable"], "numbers": {"detail": repr(e)[:200]}}
        checks.append({"ok": c["ok"], "reason": c["reason"], "message": c["message"], "numbers": c["numbers"]})
        timings[f"{view}_photos_s"] = round(timings.get(f"{view}_photos_s", 0.0) + time.time() - t, 3)
    return masks, checks


def extras(height_cm, weight_kg, age, gender, measurements):
    """Tailoring measurements the silhouette model does not give (neck, sleeve, back length, shoulder
    seams...), from a height + weight + age regression fitted on ANSUR II tape measurements
    (weights/ansur_extras.json, typical error 0.8 to 1.9 cm). The photo does not enter these. Merged into
    "measurements"; keys already produced by the silhouette model are never overwritten."""
    if "extras" not in _STATE:
        f = Path(__file__).resolve().parent / "weights" / "ansur_extras.json"
        _STATE["extras"] = json.loads(f.read_text())["models"] if f.exists() else {}
    models = _STATE["extras"]
    if not models:
        return {}
    age = 35.0 if age is None else float(age)
    x = [1.0, height_cm, weight_kg, age, height_cm ** 2 / 100, weight_kg ** 2 / 100, height_cm * weight_kg / 100]
    genders = ["male", "female"] if gender == "neutral" else [gender]
    out = {}
    for name in models[genders[0]]:
        if name in measurements:
            continue
        vals = [sum(c * v for c, v in zip(models[g][name]["coef"], x)) for g in genders if name in models[g]]
        out[name] = sum(vals) / len(vals)
    return out


def _body(gender, height_cm, weight_kg):
    """SMPL-X fitted to the stated height and weight, T-pose, feet on y = 0, millimetres, as OBJ text.
    For display only. Returns (dict for the output, note or None)."""
    bmi = weight_kg / (height_cm / 100) ** 2
    if not (BODY_HEIGHT_RANGE[0] <= height_cm <= BODY_HEIGHT_RANGE[1] and BODY_BMI_RANGE[0] <= bmi <= BODY_BMI_RANGE[1]):
        return {"tpose_obj_base64": None, "reason": "outside_fit_range"}, "No display body: height or BMI is outside the range the body fit was checked for."
    import numpy as np
    import torch
    from fit import fit_to_height_weight, tpose_vertices
    layer = _smplx_layer(gender)
    betas, info = fit_to_height_weight(layer, np.zeros(10, dtype=np.float32), height_cm, weight_kg)
    if abs(info["height_cm"] - height_cm) > 0.5 or abs(info["mass_kg"] - weight_kg) > 1.0 or info["max_abs_beta"] >= 3.99:
        return {"tpose_obj_base64": None, "reason": "fit_did_not_converge", "fit": {k: round(v, 3) for k, v in info.items()}}, "No display body: the body fit did not reach the stated height and weight."
    with torch.no_grad():
        v = tpose_vertices(layer, torch.as_tensor(betas[None])).numpy() * 1000.0
    v[:, 1] -= v[:, 1].min()                                   # feet on the floor, like the avatar endpoint
    lines = ["# SMPL-X, mm"] + [f"v {x:.2f} {y:.2f} {z:.2f}" for x, y, z in v] + [f"f {a + 1} {b + 1} {c + 1}" for a, b, c in layer.faces.astype(int)]
    obj = ("\n".join(lines) + "\n").encode()
    return {"tpose_obj_base64": base64.b64encode(obj).decode(), "format": "obj", "units": "mm", "vertices": int(len(v)),
            "gender_model": gender, "fit": {k: round(v_, 3) for k, v_ in info.items()}, "betas": [round(float(b), 4) for b in betas]}, None


# ---------------------------------------------------------------- commands
def selftest():
    """What is loaded and whether each part runs. Never raises. "ok" is true only if everything passed."""
    r, ok = {"build": BUILD}, True
    def step(name, fn):
        nonlocal ok
        t = time.time()
        try:
            r[name] = fn(); r[name + "_s"] = round(time.time() - t, 2)
        except Exception as e:  # noqa: BLE001
            r[name] = "FAIL: " + repr(e)[:300]; ok = False
    def torch_info():
        import torch, torchvision
        return {"torch": torch.__version__, "torchvision": torchvision.__version__, "cuda": torch.cuda.is_available(),
                "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}
    def seg():
        import numpy as np, preprocess
        p = preprocess.segment_person(np.full((640, 480, 3), 128, np.uint8), _segmenter())
        return {"blank_photo_reason": preprocess.check(p, "front")["reason"]}
    def cnn():
        import numpy as np
        m = _cnn(); blank = np.zeros((960, 720), np.uint8)
        out = m.predict([blank], [], 1.0, 175.0, 75.0)
        if len(out) != 14 or not all(np.isfinite(list(out.values()))): raise RuntimeError("bad output")
        if not m.sidecar_matches: raise RuntimeError("weights/measure_cnn.json sha256 does not match measure_cnn.pt")
        return {"version": m.version, "measurements": len(out), "note": m.info.get("note")}
    def body():
        b, note = _body("neutral", 175.0, 75.0)
        if b["tpose_obj_base64"] is None: raise RuntimeError(note)
        return {"vertices": b["vertices"], "fit": b["fit"], "models": sorted(p.name for p in (HUMAN_MODELS / "smplx").glob("SMPLX_*.npz"))}
    step("torch", torch_info); step("segmenter", seg); step("cnn", cnn); step("body", body)
    r["ok"] = ok
    return r


def measure(inp):
    t0 = time.time(); timings, notes = {}, []
    front_url = inp.get("front_url")
    if not front_url:
        raise BadInput("front_url is required.", "missing_front_url")
    height = _number(inp, "height_cm", *HEIGHT_RANGE)
    try:
        weight = _number(inp, "weight_kg", *WEIGHT_RANGE)
    except BadInput as e:
        if e.reason == "missing_weight_kg":
            raise BadInput("weight_kg is required: the measurement model needs height and weight together.", "missing_weight_kg")
        raise
    gender = str(inp.get("gender") or "").lower()
    if gender not in ("male", "female", "neutral"):
        raise BadInput("gender must be male, female or neutral.", "missing_gender")
    age = _number(inp, "age", 0, 120, required=False)
    as_list = lambda v: [u for u in (v or []) if u] if isinstance(v, (list, tuple)) else []
    front_urls = ([front_url] + as_list(inp.get("front_extra_urls")))[:MAX_SHOTS_PER_VIEW]
    side_urls = (([inp["side_url"]] if inp.get("side_url") else []) + as_list(inp.get("side_extra_urls")))[:MAX_SHOTS_PER_VIEW]

    model = _cnn()
    out = {"model_version": model.version, "build": BUILD, "checks": {}, "notes": notes, "timings": timings,
           "input": {"height_cm": height, "weight_kg": weight, "gender": gender, "age": age,
                     "front_photos": len(front_urls), "side_photos": len(side_urls)}}
    if model.version.startswith("wiring"):
        notes.append("WIRING-TEST MODEL: the numbers are not real measurements.")

    front_masks, out["checks"]["front"] = _view(front_urls, "front", timings)
    if not front_masks:
        first = out["checks"]["front"][0]
        out.update(error=first["message"], reason=first["reason"])
        timings["total_s"] = round(time.time() - t0, 3)
        return out
    side_masks, out["checks"]["side"] = _view(side_urls, "side", timings) if side_urls else ([], [])
    if side_urls and not side_masks:
        notes.append("Side photo not used: " + out["checks"]["side"][0]["message"])
    out["method"] = "front_and_side" if side_masks else "front_only"
    out["shots_used"] = {"front": len(front_masks), "side": len(side_masks)}

    t = time.time()
    males = {"male": [1.0], "female": [0.0], "neutral": [1.0, 0.0]}[gender]
    if gender == "neutral":
        notes.append("Gender neutral: the model knows only male and female, so this is the mean of the two predictions.")
    preds = [model.predict(front_masks, side_masks, m, height, weight) for m in males]
    priors = [model.prior(m, height, weight) for m in males]
    mean = lambda ds: {KEYS.get(k, k): round(sum(d[k] for d in ds) / len(ds), 1) for k in ds[0]}
    meas, prior = mean(preds), mean(priors)
    out["height_from_photo_cm"] = meas.pop("height_from_photo"); prior.pop("height_from_photo")
    meas["height"] = round(height, 1); prior["height"] = round(height, 1)         # height is what the person told us
    extra = extras(height, weight, age, gender, dict(meas)) or {}
    meas.update({k: round(float(v), 1) for k, v in extra.items()})
    out.update(measurements=meas, height_weight_only=prior, extras_keys=sorted(extra))
    timings["model_s"] = round(time.time() - t, 3)

    for view in ("front", "side"):
        p = _number(inp, view + "_pitch_deg", -90, 90, required=False)
        out["input"][view + "_pitch_deg"] = p
        if p is not None and abs(p) > TILT_WARN_DEG:
            notes.append(f"The phone was tilted {abs(p):.0f} degrees for the {view} photo; upright gives better results.")

    if inp.get("body", True):
        t = time.time()
        try:
            out["body"], note = _body(gender, height, weight)
        except Exception as e:  # noqa: BLE001  the body is for display: never lose the measurements over it
            out["body"], note = {"tpose_obj_base64": None, "reason": "error", "detail": repr(e)[:300]}, "No display body: " + repr(e)[:120]
        if note:
            notes.append(note)
        timings["body_s"] = round(time.time() - t, 3)
    else:
        out["body"] = {"tpose_obj_base64": None, "reason": "not_requested"}
    timings["total_s"] = round(time.time() - t0, 3)
    return out


def handler(event):
    """RunPod serverless entry. Always returns a JSON-serialisable dict; failures carry "error"."""
    inp = (event or {}).get("input") or {}
    if inp.get("ping"):
        return {"status": "measure endpoint alive", "build": BUILD, "selftest": selftest()}
    try:
        return measure(inp)
    except BadInput as e:
        return {"error": str(e), "reason": e.reason, "build": BUILD}
    except Exception as e:  # noqa: BLE001
        return {"error": f"measure failed: {e!r}"[:500], "reason": "internal_error", "traceback": traceback.format_exc()[-2000:], "build": BUILD}


if __name__ == "__main__":
    import runpod
    try:
        print(f"[boot] runpod {runpod.__version__} build={BUILD} - loading models", flush=True)
        print("[boot] selftest", selftest(), flush=True)          # loads everything once, so the first job is warm
        runpod.serverless.start({"handler": handler})
    except Exception:  # noqa: BLE001
        print("[boot] FATAL: worker failed to start", flush=True)
        traceback.print_exc(); sys.stdout.flush(); sys.stderr.flush()
        raise
