"""Bare-limb features (2026-11-25): widths of arms, legs and neck where the outline IS the body.

    feats, names = limbfeat(mask, bare_arm_left, bare_arm_right, bare_leg_left, bare_leg_right, height_cm)
    feats, names = from_labels(labels_uint8, view, height_cm)        # real photos: parse_photos label map

All maps are bool, same frame (960 x 720 in practice, any size works). left / right = side of the IMAGE.
bare_* = bare skin of that limb only; may be all False. Pure numpy, no model. 4 to 12 ms per call on this laptop
(the higher figure with three other jobs running).
Scale, as in street_build.rowfeat: cm per pixel = height_cm / (rows from the outline's top to its bottom), where
the outline's rows are those with at least 3 pixels.

WHAT IS MEASURED (all in cm; a width is across the limb = row width x cos of the limb's local slant, the rule of
pipe_profiles.limb: centre line smoothed over 21 rows)

  Arm (hanging; the far end of the bare stretch is taken to be the fingertips). Positions are distances ALONG the
  arm from the fingertip end, as fractions of body height, so they mean the same place whatever the sleeve length:
    arm_bare_len          length of the bare stretch
    arm_wrist_w           narrowest width between 7% and 13% of height up from the fingertips (the hand is below it)
    arm_forearm_max_w     widest width from 3% to 12.5% of height above the wrist     (needs bare skin to 10.5% above it)
    arm_above_elbow_w     width 17.5% of height above the wrist, a few cm above the elbow (needs bare skin to 18.5%)
    arm_top_w             width near the top of the bare stretch (0.8% to 2.5% of height below its top edge);
                          the stretch is cut at 24% of height above the wrist (about armpit level), so a bare shoulder is not counted
    arm_top_above_wrist   how far that top edge is above the wrist (tells the model WHERE arm_top_w was taken)
  Leg. Positions are heights above the FLOOR (the outline's bottom row) as fractions of body height:
    leg_bare_len          length of the bare stretch
    leg_ankle_min_w       narrowest width between 3.5% and 8.5% of height
    leg_calf_max_w        widest width between 14% and 24%
    leg_knee_w            width at 28.5% (+-1%)
    leg_thigh_w           width at 40% (+-1%)
    a leg value needs bare skin on at least 70% of the rows of its band
  A width under 1.8% of height (arm) or 3% of height (leg) is rejected as a sliver of skin (a strip between trouser
  and shoe), not a limb.
  From the outline alone:
    neck_w                narrowest outline row between 9% and 19% of height below the head top
    head_w                widest outline row above that
  Each arm / leg value is the mean of left and right where both exist, else the one that exists.

Output: 13 values, then 13 flags "<name>_ok" (1 = measured, 0 = not; the value is then 0). 26 numbers.
limbfeat(..., detail=True) also returns a dict with the per-side values and the rows used (for overlays).

from_labels: arms are labels 4 and 5 as the parser gave them. LEGS ARE RE-SPLIT: labels 6 and 7 are merged and cut
at the body midline (centre of the outline between 62% and 90% of height from the top), because the parser hands
touching bare legs to one side as a single piece. Do the same on training outlines if legs can touch there.
In a side view every bare arm pixel is "left" and every bare leg pixel is "left"; widths are then of whatever
overlaps (both legs), so keep front and side features apart.

Limits seen on the 24 real people are listed at the bottom of this file.
"""
import numpy as np

NAMES = ["arm_bare_len", "arm_wrist_w", "arm_forearm_max_w", "arm_above_elbow_w", "arm_top_w", "arm_top_above_wrist",
         "leg_bare_len", "leg_ankle_min_w", "leg_calf_max_w", "leg_knee_w", "leg_thigh_w", "neck_w", "head_w"]
ARM, LEG = NAMES[:6], NAMES[6:11]
FEATURE_NAMES = NAMES + [n + "_ok" for n in NAMES]
MIN_RUN = 3
# fractions of body height
HAND_LO, HAND_HI = 0.07, 0.13            # the wrist is searched this far up from the fingertips
FOREARM_LO, FOREARM_HI, FOREARM_NEED = 0.03, 0.125, 0.105    # the elbow is about 14.6% of height above the wrist
ELBOW_AT, ELBOW_NEED = 0.175, 0.185
ARM_CAP = 0.24                           # higher than this above the wrist is armpit and shoulder, not arm (sleeveless tops)
MIN_ARM_W, MIN_LEG_W = 0.018, 0.03       # narrower than this (x height) is a sliver of skin, not a limb
TOP_LO, TOP_HI = 0.008, 0.025
ANKLE, CALF, KNEE, THIGH = (0.035, 0.085), (0.14, 0.24), (0.275, 0.295), (0.39, 0.41)
NECK = (0.09, 0.19)
MAX_SLOPE = 1.0                          # a limb lying flatter than 45 degrees cannot be read row by row


def largest_runs(m):
    """Per row of a bool map: start and end column of its longest run of True (at least MIN_RUN long).
    Returns (rows, start, end) for the rows that have one."""
    d = np.diff(np.pad(m, ((0, 0), (1, 1))).view(np.int8), axis=1)
    ys, xs = np.nonzero(d == 1); ye, xe = np.nonzero(d == -1)             # row-major, so starts and ends pair up
    ln = xe - xs; k = ln >= MIN_RUN
    ys, xs, xe, ln = ys[k], xs[k], xe[k] - 1, ln[k]
    if len(ys) == 0:
        return ys, xs, xe
    order = np.lexsort((ln, ys)); ys, xs, xe = ys[order], xs[order], xe[order]
    last = np.r_[ys[1:] != ys[:-1], True]
    return ys[last], xs[last], xe[last]


def _stretch(y, max_gap):
    """Indices of the longest stretch of rows with gaps of at most max_gap."""
    if len(y) == 0:
        return slice(0, 0)
    br = np.flatnonzero(np.diff(y) > max_gap + 1); st = np.r_[0, br + 1]; en = np.r_[br, len(y) - 1]
    k = int(np.argmax(y[en] - y[st])); return slice(int(st[k]), int(en[k]) + 1)


def _track(bare, cm, H):
    """Bare limb -> rows, width across the limb (cm), distance along the limb from its lower end (cm), slope."""
    if bare is None or not bare.any():
        return None
    rr = np.flatnonzero(bare.any(1)); y, x0, x1 = largest_runs(bare[rr[0]:rr[-1] + 1]); y = y + rr[0]
    sl = _stretch(y, max(2, int(0.01 * H))); y, x0, x1 = y[sl], x0[sl], x1[sl]
    if len(y) < 12:
        return None
    c = (x0 + x1) / 2.0; w = (x1 - x0 + 1).astype(float); k = 21
    cs = np.convolve(np.pad(c, k // 2, mode="edge"), np.ones(k) / k, "valid")
    slope = np.gradient(cs, y.astype(float)); cos = 1 / np.sqrt(1 + slope ** 2)
    step = np.r_[np.diff(y), 1] / cos                                     # px along the limb per row
    along = (np.cumsum(step[::-1])[::-1] - step) * cm                     # 0 at the lowest row, growing upwards
    wc = w * cos * cm; n = max(3, int(round(2.0 / cm)) | 1)               # smooth over about 2 cm
    ws = np.convolve(np.pad(wc, n // 2, mode="edge"), np.ones(n) / n, "valid")
    return {"y": y, "w": ws, "along": along, "slope": np.abs(slope), "len": float(step.sum() * cm), "c": c}


def _arm(bare, cm, H, hcm):
    out = dict.fromkeys(ARM); rows = {}
    t = _track(bare, cm, H)
    if t is None:
        return out, rows
    y, w, s, L = t["y"], t["w"], t["along"], t["len"]; out["arm_bare_len"] = L
    win = (s >= HAND_LO * hcm) & (s <= min(HAND_HI * hcm, L - 1.0))
    if L < 0.085 * hcm or win.sum() < 3:
        return out, rows                                                  # only a hand is bare (long sleeve), or less
    i = int(np.flatnonzero(win)[np.argmin(w[win])]); sw = s[i]
    arm = s >= sw
    if t["slope"][arm].max() > MAX_SLOPE:
        return out, rows                                                  # bent or lifted arm (hand on hip): not readable by rows
    if w[i] < MIN_ARM_W * hcm:
        return out, rows
    out["arm_wrist_w"] = float(w[i]); rows["wrist"] = int(y[i]); reach = min(L - sw, ARM_CAP * hcm); L = sw + reach
    out["arm_top_above_wrist"] = float(reach)
    if reach >= FOREARM_NEED * hcm:
        k = (s >= sw + FOREARM_LO * hcm) & (s <= sw + FOREARM_HI * hcm); j = int(np.flatnonzero(k)[np.argmax(w[k])])
        out["arm_forearm_max_w"] = float(w[j]); rows["forearm"] = int(y[j])
    if reach >= ELBOW_NEED * hcm:
        k = np.abs(s - (sw + ELBOW_AT * hcm)) <= 1.0
        if k.any():
            out["arm_above_elbow_w"] = float(np.median(w[k])); rows["above_elbow"] = int(y[k][len(y[k]) // 2])
    if reach >= 0.05 * hcm:
        k = (s <= L - TOP_LO * hcm) & (s >= L - TOP_HI * hcm)
        if k.any():
            out["arm_top_w"] = float(np.median(w[k])); rows["top"] = int(y[k][len(y[k]) // 2])
    return out, rows


def _leg(bare, cm, H, hcm, bot):
    out = dict.fromkeys(LEG); rows = {}
    t = _track(bare, cm, H)
    if t is None:
        return out, rows
    y, w = t["y"], t["w"]; out["leg_bare_len"] = t["len"]; above = (bot - y) * cm; ok_slope = t["slope"] <= MAX_SLOPE
    for name, (lo, hi), how in (("leg_ankle_min_w", ANKLE, "min"), ("leg_calf_max_w", CALF, "max"), ("leg_knee_w", KNEE, "med"), ("leg_thigh_w", THIGH, "med")):
        k = (above >= lo * hcm) & (above <= hi * hcm) & ok_slope; need = 0.7 * (hi - lo) * hcm / cm
        if k.sum() < max(3, need):
            continue
        j = np.flatnonzero(k)
        if how == "med":
            out[name] = float(np.median(w[k])); rows[name] = int(y[j[len(j) // 2]])
        else:
            q = j[np.argmin(w[k])] if how == "min" else j[np.argmax(w[k])]; out[name] = float(w[q]); rows[name] = int(y[q])
        if out[name] < MIN_LEG_W * hcm:
            out[name] = None; rows.pop(name, None)
    return out, rows


def _neck(mask, cm, top, H):
    y, x0, x1 = largest_runs(mask[top: top + int(0.25 * H) + 1]); out = {"neck_w": None, "head_w": None}; rows = {}
    if len(y) < 10:
        return out, rows
    w = (x1 - x0 + 1).astype(float); n = 5; ws = np.convolve(np.pad(w, n // 2, mode="edge"), np.ones(n) / n, "valid")
    k = np.flatnonzero((y >= NECK[0] * H) & (y <= NECK[1] * H))
    if len(k) < 5:
        return out, rows
    i = int(k[np.argmin(ws[k])]); head = float(ws[:i].max()) if i > 0 else 0.0
    # a neck is a waist in the outline: narrower than the head above it and than the shoulders below it
    below = ws[i:].max() if i < len(ws) - 1 else 0
    if k[0] < i < k[-1] and ws[i] < 0.92 * head and ws[i] < 0.8 * below:
        out["neck_w"] = float(ws[i] * cm); out["head_w"] = head * cm; rows["neck"] = int(top + y[i]); rows["head"] = int(top + y[int(np.argmax(ws[:i]))])
    return out, rows


def limbfeat(mask, bare_arm_left, bare_arm_right, bare_leg_left, bare_leg_right, height_cm, detail=False):
    feats = np.zeros(2 * len(NAMES), np.float32); info = {}
    rr = np.flatnonzero(mask.sum(1) >= 3)
    if len(rr) < 200:
        return (feats, FEATURE_NAMES, info) if detail else (feats, FEATURE_NAMES)
    top, bot = int(rr[0]), int(rr[-1]); H = bot - top + 1; cm = height_cm / H
    aL, rL = _arm(bare_arm_left, cm, H, height_cm); aR, rR = _arm(bare_arm_right, cm, H, height_cm)
    lL, sL = _leg(bare_leg_left, cm, H, height_cm, bot); lR, sR = _leg(bare_leg_right, cm, H, height_cm, bot)
    nk, rN = _neck(mask, cm, top, H)
    for j, name in enumerate(NAMES):
        vals = [d[name] for d in (aL, aR, lL, lR, nk) if d.get(name) is not None]
        if vals:
            feats[j] = float(np.mean(vals)); feats[len(NAMES) + j] = 1.0
    if detail:
        info = {"cm_per_px": cm, "arm_left": aL, "arm_right": aR, "leg_left": lL, "leg_right": lR, "neck": nk,
                "rows": {"arm_left": rL, "arm_right": rR, "leg_left": sL, "leg_right": sR, "neck": rN}}
        return feats, FEATURE_NAMES, info
    return feats, FEATURE_NAMES


def bare_maps(labels, view="front"):
    """parse_photos label map -> (mask, arm_left, arm_right, leg_left, leg_right). Legs are re-split at the midline."""
    mask = labels > 0; none = np.zeros(labels.shape, bool)
    if view != "front":
        return mask, (labels == 4) | (labels == 5), none, (labels == 6) | (labels == 7), none
    legs = (labels == 6) | (labels == 7); rr = np.flatnonzero(mask.sum(1) >= 3)
    if len(rr) < 200 or not legs.any():
        return mask, labels == 4, labels == 5, none, none
    top, H = int(rr[0]), int(rr[-1] - rr[0] + 1); band = mask[top + int(0.62 * H): top + int(0.90 * H)]
    cols = np.flatnonzero(band.any(0)); mid = int(round((cols[0] + cols[-1]) / 2)) if len(cols) else labels.shape[1] // 2
    left = legs.copy(); left[:, mid + 1:] = False; right = legs.copy(); right[:, :mid + 1] = False
    return mask, labels == 4, labels == 5, left, right


def from_labels(labels, view, height_cm, detail=False):
    return limbfeat(*bare_maps(np.asarray(labels), view), height_cm, detail=detail)


# LIMITS SEEN ON THE 24 REAL PEOPLE (21 uniquedata + 3 new udbio), front views, 2026-11-25: see the report sent to the
# measurement session; the short version is kept in limbfeat_report.txt next to this file.
