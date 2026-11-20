"""Photo -> BodyM-style silhouette, with the checks that decide whether the photo can be measured at all.

    from preprocess import load_segmenter, preprocess
    model = load_segmenter()                      # once per warm worker
    out = preprocess("front.jpg", "front", model)
    if out["check"]["ok"]:  use out["mask_960x720"]      # uint8, 0 / 255, framed like BodyM
    else:                   show out["check"]["message"] to the tester

Depends on torch, torchvision, numpy, Pillow and cv2 only. Nothing here uploads or downloads a photo.

Segmenter: torchvision DeepLabV3-ResNet101, weights COCO_WITH_VOC_LABELS_V1.
    file   deeplabv3_resnet101_coco-586e9e4e.pth, 233 MB
    from   https://download.pytorch.org/models/deeplabv3_resnet101_coco-586e9e4e.pth
    cached under $TORCH_HOME/hub/checkpoints/ (bake it into the image there, or pass weights_path).
Chosen over U2Net-human and Mask R-CNN on real photos, see measure_ml/RESULTS_real_photos.md.

Thresholds were set on BodyM's own masks (8,978 known-good front and side captures), see
measure_core/GATES.md for the refusal rates; the ones set by judgement say so.
"""
import io
import time

import cv2
import numpy as np
from PIL import Image, ImageOps

# ---------------------------------------------------------------- constants
MAX_SIDE = 1600                 # longest side of the working photo, px (judgement: DeepLab runs at 640 anyway)
SEG_SHORT_SIDE = 640            # DeepLab input size on the short side (the size used for every result so far)
PERSON_CLASS = 15               # "person" in the VOC label set

OUT_W, OUT_H = 720, 960         # BodyM mask size
FRAME = {"front": {"top": 66, "height": 835, "cx": 362},      # BodyM medians, 400 random masks per split
         "side": {"top": 50, "height": 875, "cx": 361}}

MIN_PERSON_AREA = 0.01          # of the image; under this there is no person worth the name (judgement)
SECOND_PIECE_MAX = 0.05         # second-largest piece / largest; BodyM masks above it: 0.07 to 0.12% front, up to 1.2% side (GATES.md)
MIN_HEIGHT_FRAC = 0.40          # person height / image height (judgement; BodyM sits at 0.80 to 0.97)
MIN_HEIGHT_PX = 400             # person height in the working photo, px (judgement: BodyM masks are 835 px)
EDGE_MARGIN_PX = 2              # closer than this to an image edge counts as cut off
MIN_BBOX_ASPECT = 1.2           # person height / width; BodyM front 0.5th percentile is 1.27 to 1.29 (arms out), side is above 2.2
MIN_SIDE_ASPECT = 3.0           # side view: person height / width. BodyM side masks under it: 0.1% (Train), 0% (Test-A),
                                # 0.3% (Test-B); over 99% of BodyM FRONT masks are under it, so it catches a front photo sent as side
ARMS_CLEAR_MIN_PCT = 12.0       # front view: % of body rows where the outline splits into 3+ runs.
                                # BodyM front: 1st percentile 18.9 (Train), 19.1 (Test-A), 18.2 (Test-B), so 12 refuses
                                # under 0.2% of them; arms against the body or a raised arm scores near 0 (GATES.md).

MESSAGES = {
    "ok": "Photo accepted.",
    "no_person": "We could not find a person in this photo. Stand in front of a plain background with your whole body in the picture.",
    "landscape": "This photo is wider than it is tall. Hold the phone upright and retake it.",
    "several_people": "There seems to be more than one person, or a mirror, in this photo. Retake it with only you in the picture.",
    "too_small": "You are too small in this photo. Step closer so your body fills most of the picture, head to feet.",
    "cut_off_top": "Your head is cut off at the top of the photo. Step back or lower the phone so your whole body is in the picture.",
    "cut_off_bottom": "Your feet are cut off at the bottom of the photo. Step back so your whole body is in the picture, head to feet.",
    "cut_off_side": "Part of you is cut off at the side of the photo. Stand in the middle and step back a little.",
    "not_standing": "We could not see you standing upright. Retake the photo standing straight, with the phone upright.",
    "not_side_view": "This does not look like a side view. Turn 90 degrees so your side faces the camera, arms down by your sides.",
    "arms_not_clear": "Stand with your arms slightly away from your body and your legs slightly apart, facing the camera, hands empty.",
}

_MODELS = {}


# ---------------------------------------------------------------- photo and model
def load_photo(path_or_bytes, max_side=MAX_SIDE):
    """Upright RGB numpy array (EXIF orientation applied), longest side at most max_side."""
    src = io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, (bytes, bytearray)) else path_or_bytes
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    s = max_side / max(img.size)
    if s < 1:
        img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    return np.asarray(img)


def load_segmenter(device=None, weights_path=None):
    """DeepLabV3-R101 in eval mode, loaded once per (device, weights_path) and reused."""
    import torch
    import torchvision
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    key = (str(device), weights_path)
    if key not in _MODELS:
        seg = torchvision.models.segmentation
        if weights_path:
            net = seg.deeplabv3_resnet101(weights=None, weights_backbone=None, aux_loss=True)
            net.load_state_dict(torch.load(weights_path, map_location="cpu"))
        else:
            net = seg.deeplabv3_resnet101(weights=seg.DeepLabV3_ResNet101_Weights.COCO_WITH_VOC_LABELS_V1)
        _MODELS[key] = net.eval().to(device)
    return _MODELS[key]


def segment_person(rgb, model):
    """Probability (float32, 0..1) that each pixel of `rgb` is a person, at the photo's own resolution."""
    import torch
    h, w = rgb.shape[:2]
    s = SEG_SHORT_SIDE / min(h, w)
    small = cv2.resize(rgb, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_LINEAR)
    x = torch.from_numpy(small).permute(2, 0, 1).float().div(255)
    mean, std = torch.tensor([0.485, 0.456, 0.406])[:, None, None], torch.tensor([0.229, 0.224, 0.225])[:, None, None]
    x = ((x - mean) / std)[None].to(next(model.parameters()).device)
    with torch.no_grad():
        p = model(x)["out"].softmax(1)[:, PERSON_CLASS:PERSON_CLASS + 1]
        p = torch.nn.functional.interpolate(p, size=(h, w), mode="bilinear", align_corners=False)
    return p[0, 0].float().cpu().numpy()


# ---------------------------------------------------------------- mask handling
def _as_prob(mask_or_prob):
    m = np.asarray(mask_or_prob, dtype=np.float32)
    return m / 255.0 if m.max() > 1.5 else m


def pieces(mask_or_prob):
    """(labels, areas sorted largest first as [(label, area), ...]) of the connected pieces of the mask."""
    m = (_as_prob(mask_or_prob) > 0.5).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    return lab, sorted(((i, int(stats[i, cv2.CC_STAT_AREA])) for i in range(1, n)), key=lambda t: -t[1])


def clean_mask(mask_or_prob):
    """Keep the largest piece and close enclosed holes smaller than 0.1% of it. Returns a 0..1 float map
    (soft where the input was soft, so framing can still smooth the outline), or None if there is no piece."""
    p = _as_prob(mask_or_prob)
    lab, order = pieces(p)
    if not order:
        return None
    body = lab == order[0][0]
    n, holes, stats, _ = cv2.connectedComponentsWithStats((~body).astype(np.uint8), connectivity=4)
    border = set(np.unique(np.r_[holes[0], holes[-1], holes[:, 0], holes[:, -1]]).tolist())
    small = [i for i in range(1, n) if i not in border and stats[i, cv2.CC_STAT_AREA] < 0.001 * order[0][1] and not body[holes == i].any()]
    filled = body | np.isin(holes, small) if small else body
    return np.where(filled, np.maximum(p, 0.51), np.minimum(p, 0.49)).astype(np.float32)


def bbox(mask_or_prob):
    """(top, bottom, left, right) of the person; rows and columns with fewer than 3 pixels are specks."""
    m = _as_prob(mask_or_prob) > 0.5
    rows, cols = np.flatnonzero(m.sum(1) >= 3), np.flatnonzero(m.sum(0) >= 3)
    if len(rows) == 0 or len(cols) == 0:
        return None
    return int(rows[0]), int(rows[-1]), int(cols[0]), int(cols[-1])


def arms_clear_pct(mask_or_prob):
    """% of body rows where the silhouette is in three or more separate runs (arm, torso, arm; or leg gaps
    plus an arm). High when the arms hang clear of the body, about 0 when they rest against it."""
    m = _as_prob(mask_or_prob) > 0.5
    b = bbox(m)
    if b is None:
        return 0.0
    body = m[b[0]:b[1] + 1]
    starts = (body[:, 1:] & ~body[:, :-1]).sum(1) + body[:, 0]
    return float(100.0 * np.mean(starts >= 3))


def frame(mask_or_prob, view="front"):
    """Scale and place the person as BodyM does: uint8 (960, 720), 0 / 255. Same as measure_ml/bodym_framing."""
    t = FRAME[view]
    p = _as_prob(mask_or_prob)
    b = bbox(p)
    if b is None:
        raise ValueError("no person in mask")
    y0, y1, x0, x1 = b
    s = t["height"] / (y1 - y0 + 1)
    new_w = max(1, int(round((x1 - x0 + 1) * s)))
    crop = Image.fromarray((p[y0:y1 + 1, x0:x1 + 1] * 255).astype(np.uint8)).resize((new_w, t["height"]), Image.BILINEAR)
    crop = np.asarray(crop)
    out = np.zeros((OUT_H, OUT_W), np.uint8)
    left, top = int(round(t["cx"] - new_w / 2)), t["top"]
    ys, xs = slice(max(0, top), min(OUT_H, top + t["height"])), slice(max(0, left), min(OUT_W, left + new_w))
    out[ys, xs] = crop[ys.start - top: ys.stop - top, xs.start - left: xs.stop - left]
    return np.where(out > 127, 255, 0).astype(np.uint8)


# ---------------------------------------------------------------- gates
def check(mask_or_prob, view="front"):
    """Can this silhouette be measured? `mask_or_prob` is the segmentation of the WHOLE photo (so that
    edges mean image edges), before cleaning or framing.

    Returns {"ok", "reason", "message", "failed": [every reason that failed], "numbers": {...}}.
    Side view: the feet must be inside the picture too. BodyM's own side masks are cut at the bottom
    in a quarter to a third of cases, but a cut-off silhouette cannot be scaled by the person's height,
    and a tester can simply step back; drop or keep those BodyM masks in training as you see fit.
    """
    p = _as_prob(mask_or_prob)
    H, W = p.shape
    lab, order = pieces(p)
    numbers = {"image_w": W, "image_h": H, "pieces": len(order)}
    failed = []
    if not order or order[0][1] < MIN_PERSON_AREA * H * W:
        failed.append("no_person")
    else:
        body = lab == order[0][0]
        y0, y1, x0, x1 = bbox(body) or (0, H - 1, 0, W - 1)
        ph, pw = y1 - y0 + 1, x1 - x0 + 1
        numbers.update(person_area_frac=round(order[0][1] / (H * W), 4),
                       second_piece_ratio=round(order[1][1] / order[0][1], 4) if len(order) > 1 else 0.0,
                       person_height_frac=round(ph / H, 3), person_height_px=ph, bbox_aspect=round(ph / pw, 3),
                       gap_top_px=y0, gap_bottom_px=H - 1 - y1, gap_left_px=x0, gap_right_px=W - 1 - x1,
                       arms_clear_pct=round(arms_clear_pct(body), 1))
        if W > H: failed.append("landscape")
        if numbers["second_piece_ratio"] > SECOND_PIECE_MAX: failed.append("several_people")
        if ph / H < MIN_HEIGHT_FRAC or ph < MIN_HEIGHT_PX: failed.append("too_small")
        if y0 < EDGE_MARGIN_PX: failed.append("cut_off_top")
        if H - 1 - y1 < EDGE_MARGIN_PX: failed.append("cut_off_bottom")
        if x0 < EDGE_MARGIN_PX or W - 1 - x1 < EDGE_MARGIN_PX: failed.append("cut_off_side")
        if ph / pw < MIN_BBOX_ASPECT: failed.append("not_standing")
        if view == "front" and numbers["arms_clear_pct"] < ARMS_CLEAR_MIN_PCT: failed.append("arms_not_clear")
        if view == "side" and MIN_BBOX_ASPECT <= ph / pw < MIN_SIDE_ASPECT: failed.append("not_side_view")
    reason = failed[0] if failed else "ok"
    return {"ok": not failed, "reason": reason, "message": MESSAGES[reason], "failed": failed, "numbers": numbers}


def preprocess(path_or_bytes, view="front", model=None):
    """Photo -> {"mask_960x720": uint8 or None, "check": {...}, "seconds": {...}}. The mask is returned
    whenever a person was found, also when a gate failed, so a caller can log or show it."""
    t0 = time.time()
    rgb = load_photo(path_or_bytes)
    t1 = time.time()
    prob = segment_person(rgb, model or load_segmenter())
    t2 = time.time()
    result = check(prob, view)
    soft = clean_mask(prob)
    mask = frame(soft, view) if soft is not None and bbox(soft) is not None else None
    t3 = time.time()
    return {"mask_960x720": mask, "check": result,
            "seconds": {"load": round(t1 - t0, 3), "segment": round(t2 - t1, 3), "check_and_frame": round(t3 - t2, 3), "total": round(t3 - t0, 3)}}
