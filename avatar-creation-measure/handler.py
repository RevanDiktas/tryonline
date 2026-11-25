"""Measurement-only RunPod worker: photos + height + weight + gender -> body measurements in cm.

    front + side photo(s) -> street pipeline (street/pipeline.py): person outline + clothing labels -> row widths, cloth
                             flags, bare-limb widths, part locator -> the networks in weights/street_models.json, averaged
                             -> optional typed sizes -> chest / waist / hips / thigh as a tape measures them
    front photo only      -> the older silhouette CNN (model.py), training-set definitions ("pipeline": "silhouette_cnn")
    height + weight       -> SMPL-X body for display (not used for the measurements)

INPUT  {"input": {
    "front_url": str,                    required
    "side_url": str | null,
    "front_extra_urls": [str], "side_extra_urls": [str],      more shots of the same view (the page takes 3)
    "height_cm": number,                 required, 120 to 230
    "weight_kg": number,                 required, 30 to 250 (the model cannot run without it)
    "gender": "male" | "female" | "neutral",                  required
    "age": int | null, "front_pitch_deg": number | null, "side_pitch_deg": number | null,
    "trouser_waist_cm": number | null,   optional typed size, as a tape reads it (street pipeline only), 40 to 200
    "chest_size_cm": number | null,      optional typed size, as a tape reads it (street pipeline only), 50 to 200
    "body": bool                         default true; false skips the display body
    "ping": true                         -> selftest instead of a measurement
}}
OUTPUT (JSON only)  {
    "measurements": {key: cm} | absent when refused,
    "method": "front_and_side" | "front_only",
    "pipeline": "street" | "silhouette_cnn",   "definition": "tape" | "training_set"  (what chest / waist / hips / thigh mean)
    "measurements_photo_only": {key: cm}       only when a typed size was applied: the values before it
    "typed_sizes": {...}, "between_pairs_sd": {key: cm}, "per_model": {file: {chest, waist, hips, thigh}}, "outfits": [...]   street only
    "height_weight_only": {key: cm},     what height + weight alone would say, to show how far the photo moved it
    "checks": {"front": [{ok, reason, message, numbers, used}, ...], "side": [...]},      one entry per photo sent.
                                         Street pipeline: a failed check is REPORTED and the photo is still used (the networks
                                         are trained for hanging arms); only the reasons in STREET_BLOCKING drop a photo.
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
STREET_WEIGHTS = Path(os.environ.get("MEASURE_STREET_WEIGHTS", HERE / "weights"))           # holds street_models.json: THE list of model files
PARSER_WEIGHTS = os.environ.get("MEASURE_PARSER_WEIGHTS") or None                           # else weights/segformer_b2_clothes.safetensors
STREET_CUT = {"cut_off_top", "cut_off_bottom"}      # head or feet missing: scaling by the stated height would stretch the body, so ask for a new photo
STREET_BLOCKING = {"no_person", "unreadable"} | STREET_CUT       # photo checks that drop a photo from the street pipeline; every other failed check is only reported
STREET_IGNORED = {"arms_not_clear"}                 # not a fault in the street pipeline: hanging arms are the pose it is trained for, so no shopper is told to move them
os.environ.setdefault("PARSE_THREADS", str(len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 1)))   # the parser's CPU threads
ALLOW_LOCAL_FILES = os.environ.get("MEASURE_ALLOW_LOCAL_FILES") == "1"                      # local harness only

MAX_PHOTO_BYTES = 15 * 1024 * 1024
MAX_SHOTS_PER_VIEW = 4
DOWNLOAD_TIMEOUT_S = 30.0
HEIGHT_RANGE, WEIGHT_RANGE = (120.0, 230.0), (30.0, 250.0)
TYPED_WAIST_RANGE, TYPED_CHEST_RANGE = (40.0, 200.0), (50.0, 200.0)
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


def _street():
    if "street" not in _STATE:
        from street.pipeline import StreetPipeline
        _STATE["street"] = StreetPipeline(STREET_WEIGHTS, PARSER_WEIGHTS, segmenter=_segmenter)
    return _STATE["street"]


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


def _is_heif(data):
    return len(data) > 12 and data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1")


def _photo(url):
    """Photo bytes PIL can open. iPhone HEIC is decoded with pillow-heif (in the image); on a Mac without it, with `sips`
    (what measure_street.py does), so the local harness reads the same pixels as the scored runner."""
    data = _fetch(url)
    if not _is_heif(data):
        return data
    try:
        import pillow_heif
        if not _STATE.get("heif"):
            pillow_heif.register_heif_opener(); _STATE["heif"] = True
        return data
    except ImportError:
        pass
    import subprocess
    import tempfile
    if not Path("/usr/bin/sips").exists():
        raise RuntimeError("HEIC photo, and neither pillow-heif nor sips is available")
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "photo.heic", Path(tmp) / "photo.jpg"; src.write_bytes(data)
        r = subprocess.run(["/usr/bin/sips", "-s", "format", "jpeg", "-s", "formatOptions", "95", str(src), "--out", str(dst)], capture_output=True, text=True)
        if r.returncode != 0 or not dst.exists():
            raise RuntimeError("sips could not convert the HEIC photo: " + (r.stderr.strip() or r.stdout.strip())[:200])
        return dst.read_bytes()


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
            out = preprocess.preprocess(_photo(url), view, _segmenter())
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
        checks.append({"ok": c["ok"], "reason": c["reason"], "message": c["message"], "numbers": c["numbers"], "used": bool(c["ok"])})
        timings[f"{view}_photos_s"] = round(timings.get(f"{view}_photos_s", 0.0) + time.time() - t, 3)
    return masks, checks


def _street_measure(front_urls, side_urls, height, weight, gender, typed, timings, notes):
    """The street pipeline on every photo sent. Returns (result dict or None, checks). None = no usable front/side pair;
    the reason is added to notes and the caller falls back to the front-only model."""
    import numpy as np
    sp = _street(); parsed, checks = {"front": [], "side": []}, {"front": [], "side": []}
    for view, urls in (("front", front_urls), ("side", side_urls)):
        for url in urls:
            t = time.time()
            try:
                r = sp.parse(_photo(url), view, height); c = r["check"]
            except BadInput:
                raise
            except Exception as e:  # noqa: BLE001  a photo that cannot be fetched or decoded is a refused photo, not a crash
                r = None
                c = {"ok": False, "reason": "unreadable", "message": "This photo could not be read. Please send a JPEG, PNG or HEIC.",
                     "failed": ["unreadable"], "numbers": {"detail": repr(e)[:200]}}
            failed = [x for x in (c.get("failed") or []) if x not in STREET_IGNORED]
            if len(failed) != len(c.get("failed") or []):
                import preprocess
                c = {**c, "failed": failed, "ok": not failed, "reason": failed[0] if failed else "ok", "message": preprocess.MESSAGES[failed[0] if failed else "ok"]}
            usable = r is not None and r["labels"] is not None and not (set(c.get("failed") or []) & STREET_BLOCKING)
            parsed[view].append(r if usable else None)
            checks[view].append({"ok": c["ok"], "reason": c["reason"], "message": c["message"], "failed": list(c.get("failed") or []), "numbers": c["numbers"], "used": False})
            timings[f"{view}_photos_s"] = round(timings.get(f"{view}_photos_s", 0.0) + time.time() - t, 3)
    t = time.time(); feats, used = [], []
    for i, f in enumerate(parsed["front"]):
        j = min(i, len(parsed["side"]) - 1); s = parsed["side"][j]
        if f is None or s is None:
            continue
        ft, why = sp.pair_features(f, s, height)
        if ft is None:
            notes.append(f"Front photo {i + 1} with side photo {j + 1} not used: {why}."); continue
        feats.append(ft); used.append((i, j)); checks["front"][i]["used"] = True; checks["side"][j]["used"] = True
    if not feats:
        notes.append("No usable front + side pair for the street pipeline; measured from the front photo alone with the older model.")
        return None, checks
    for view in ("front", "side"):
        for k, c in enumerate(checks[view]):
            if c["used"] and not c["ok"]:
                notes.append(f"{view.capitalize()} photo {k + 1} failed a photo check ({c['reason']}) and was used anyway: {c['message']}")
    if not all(ft["located"] for ft in feats):
        notes.append("The part locator could not read a front outline; the networks ran without it for that pair.")
    males = {"male": [1.0], "female": [0.0], "neutral": [1.0, 0.0]}[gender]
    if gender == "neutral":
        notes.append("Gender neutral: the model knows only male and female, so this is the mean of the two predictions.")
    runs = [sp.predict(feats, m, height, weight, typed.get("trouser_waist_cm"), typed.get("chest_size_cm")) for m in males]
    avg = lambda k: np.mean([r[k] for r in runs], 0)
    named = lambda a: {KEYS.get(k, k): round(float(v), 1) for k, v in zip(sp.measurements, a)}
    res = {"measurements": named(avg("tape")), "height_weight_only": named(avg("base_tape")), "between_pairs_sd": {KEYS.get(k, k): round(float(v), 2) for k, v in zip(sp.measurements, avg("spread"))},
           "per_model": {name: {KEYS.get(k, k): round(float(np.mean([r["per_model"][name][sp.measurements.index(k)] for r in runs])), 1) for k in ("chest", "waist", "hip", "thigh")} for name in runs[0]["per_model"]},
           "outfits": [ft["outfit"] for ft in feats], "pairs_used": [{"front": i + 1, "side": j + 1} for i, j in used], "model_version": sp.version}
    if runs[0]["typed"]:
        res["measurements_photo_only"] = named(avg("photo_tape"))
        res["typed_sizes"] = {**typed, "matrix": runs[0]["typed"]["matrix"],
                              "shift_cm": {KEYS.get(k, k): round(float(np.mean([r["typed"]["shift_cm"][k] for r in runs])), 2) for k in sp.measurements}}
    timings["model_s"] = round(time.time() - t, 3)
    return res, checks


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
    def street():
        import numpy as np
        sp = _street(); sp.nets()                                   # loads the clothing parser too
        if sp.mismatch: raise RuntimeError("SHA-256 differs from weights/street_models.json: " + ", ".join(sp.mismatch))
        SM = sp.SM; front = np.zeros((960, 720), bool); side = np.zeros((960, 720), bool)      # a drawn figure: only "does every part run"
        front[66:170, 320:404] = 1; front[170:480, 270:454] = 1; front[480:900, 275:355] = 1; front[480:900, 369:449] = 1; side[50:925, 300:420] = 1
        cloth = np.zeros_like(front); rows, cover, _ = SM.pack(front, side, cloth, cloth, 175.0)
        labels = np.where(front, 8, 0).astype(np.uint8); limb = sp.LF.from_labels(labels, "front", 175.0)[0]
        ft = {"rows": rows, "cover": cover, "limb": limb, "prof": np.zeros(SM.N_PROFILE, np.float32), "sca": np.full(len(SM.SCALARS), -1, np.float32)}
        r = sp.predict([ft], 1.0, 175.0, 75.0, 85.0, 100.0)
        if not all(np.isfinite(r[k]).all() for k in ("tape", "photo_tape", "base_tape")): raise RuntimeError("bad output")
        return {"version": sp.version, "models": [n for n, _ in sp.models], "parser": sp.parser_weights.name, "parser_threads": os.environ.get("PARSE_THREADS"),
                "parser_device": sp.PPH.DEVICE, "typed_sizes": r["typed"]["matrix"]}
    step("torch", torch_info); step("segmenter", seg); step("cnn", cnn); step("street", street); step("body", body)
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

    typed = {k: v for k, v in (("trouser_waist_cm", _number(inp, "trouser_waist_cm", *TYPED_WAIST_RANGE, required=False)),
                               ("chest_size_cm", _number(inp, "chest_size_cm", *TYPED_CHEST_RANGE, required=False))) if v is not None}
    out = {"build": BUILD, "checks": {}, "notes": notes, "timings": timings,
           "input": {"height_cm": height, "weight_kg": weight, "gender": gender, "age": age, **typed,
                     "front_photos": len(front_urls), "side_photos": len(side_urls)}}

    street = None
    if side_urls:
        street, street_checks = _street_measure(front_urls, side_urls, height, weight, gender, typed, timings, notes)
        if street is None:                               # never answer with the older model when the only problem is a cut-off photo
            cut = [(v, x) for v in ("front", "side") for c in street_checks[v] for x in c["failed"] if x in STREET_CUT]
            if cut:
                import preprocess
                view, why = cut[0]
                out["checks"] = street_checks
                out.update(error=f"{view.capitalize()} photo: {preprocess.MESSAGES[why]}", reason=why)
                timings["total_s"] = round(time.time() - t0, 3)
                return out
    if street is not None:
        out["checks"] = street_checks; meas, prior = street.pop("measurements"), street.pop("height_weight_only")
        out.update(street, pipeline="street", definition="tape", method="front_and_side")
        out["shots_used"] = {v: sum(c["used"] for c in street_checks[v]) for v in ("front", "side")}
        if "measurements_photo_only" in out:
            out["measurements_photo_only"].pop("height_from_photo", None); out["measurements_photo_only"]["height"] = round(height, 1)
        out["between_pairs_sd"].pop("height_from_photo", None)
    else:
        model = _cnn(); out.update(model_version=model.version, pipeline="silhouette_cnn", definition="training_set")
        if typed:
            notes.append("Typed sizes were not applied: they need the street pipeline (a usable front + side pair).")
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
        timings["model_s"] = round(time.time() - t, 3)
    out["height_from_photo_cm"] = meas.pop("height_from_photo"); prior.pop("height_from_photo")
    meas["height"] = round(height, 1); prior["height"] = round(height, 1)         # height is what the person told us
    extra = extras(height, weight, age, gender, dict(meas)) or {}
    meas.update({k: round(float(v), 1) for k, v in extra.items()})
    out.update(measurements=meas, height_weight_only=prior, extras_keys=sorted(extra))

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
