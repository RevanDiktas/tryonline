"""Tests for preprocess.py that need neither the dataset nor the model weights: a drawn figure stands in
for a segmented person. Run with pytest, or directly:  python test_preprocess.py
(The segmenter itself is only exercised when MEASURE_TEST_SEGMENTER=1, since it needs the 233 MB weights.)
"""
import io
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preprocess as P  # noqa: E402


def figure(w=900, h=1200, top=120, height=950, cx=None, arms="clear", legs_apart=True):
    """A crude standing person as a 0/255 mask: head, torso, two arms, two legs."""
    m = np.zeros((h, w), np.uint8); cx = w // 2 if cx is None else cx; u = height / 100.0
    P_ = lambda x, y: (int(cx + x * u), int(top + y * u))
    cv2.circle(m, P_(0, 7), int(6.5 * u), 255, -1)                                   # head
    cv2.rectangle(m, P_(-3, 10), P_(3, 16), 255, -1)                                 # neck
    cv2.rectangle(m, P_(-11, 14), P_(11, 52), 255, -1)                               # torso
    gap = 5 if legs_apart else 0
    for s in (-1, 1):
        cv2.line(m, P_(s * (5 + gap / 2), 50), P_(s * (7 + gap), 99), 255, int(8 * u))              # leg
        hand = {"clear": (s * 26, 50), "down": (s * 13, 52), "wide": (s * 48, 20)}[arms]
        cv2.line(m, P_(s * 12, 17), P_(*hand), 255, int(4.5 * u))                                   # arm
    return m


def test_good_front_passes_and_is_framed_like_bodym():
    m = figure()
    r = P.check(m, "front")
    assert r["ok"] and r["reason"] == "ok" and r["failed"] == [], r
    assert r["numbers"]["arms_clear_pct"] > P.ARMS_CLEAR_MIN_PCT
    out = P.frame(P.clean_mask(m), "front")
    assert out.shape == (960, 720) and out.dtype == np.uint8 and set(np.unique(out)) == {0, 255}
    top, bottom, left, right = P.bbox(out)
    assert top == P.FRAME["front"]["top"] and bottom - top + 1 == P.FRAME["front"]["height"]
    assert abs((left + right) / 2 - P.FRAME["front"]["cx"]) <= 1.5


def test_side_framing_and_no_arm_gate_for_side():
    m = narrow_figure()
    assert P.check(m, "side")["ok"]
    out = P.frame(m, "side"); top, bottom, _, _ = P.bbox(out)
    assert top == P.FRAME["side"]["top"] and bottom - top + 1 == P.FRAME["side"]["height"]


def narrow_figure():
    """Seen from the side: one narrow column."""
    m = np.zeros((1200, 900), np.uint8); cv2.circle(m, (450, 185), 62, 255, -1); cv2.rectangle(m, (385, 230), (515, 1070), 255, -1)
    return m


def test_front_photo_sent_as_side_is_refused():
    assert P.check(narrow_figure(), "side")["ok"]
    r = P.check(figure(), "side")
    assert not r["ok"] and r["reason"] == "not_side_view" and "side" in r["message"]


def test_arms_against_the_body_are_refused_in_front_view():
    r = P.check(figure(arms="down", legs_apart=False), "front")
    assert not r["ok"] and r["reason"] == "arms_not_clear" and "arms" in r["message"]


def test_cut_off_head_feet_and_side():
    assert "cut_off_top" in P.check(figure(top=-30), "front")["failed"]
    assert "cut_off_bottom" in P.check(figure(top=300), "front")["failed"]
    assert "cut_off_bottom" in P.check(np.roll(narrow_figure(), 200, axis=0), "side")["failed"]   # side view: feet must be in too
    assert "cut_off_side" in P.check(figure(cx=200), "front")["failed"]


def test_no_person_small_person_two_people_landscape_lying():
    assert P.check(np.zeros((1200, 900), np.uint8), "front")["reason"] == "no_person"
    assert "too_small" in P.check(figure(top=400, height=300), "front")["failed"]
    two = np.maximum(figure(w=1400, cx=380), figure(w=1400, cx=1020, height=700, top=300))
    assert "several_people" in P.check(two[:, :1100], "front")["failed"] or "several_people" in P.check(two, "front")["failed"]
    assert "landscape" in P.check(figure(w=1600, h=1200), "front")["failed"]
    assert "not_standing" in P.check(figure(arms="wide"), "front")["failed"]
    assert P.check(figure(), "front")["message"] == P.MESSAGES["ok"]


def test_clean_mask_drops_specks_and_closes_small_holes():
    m = figure(); m[30:40, 30:40] = 255; m[600:604, 448:452] = 0
    c = P.clean_mask(m) > 0.5
    assert not c[35, 35] and c[602, 450] and P.clean_mask(np.zeros((50, 50))) is None
    assert P.check(m, "front")["ok"]                                             # a speck is not a second person


def test_probability_maps_and_masks_give_the_same_answer():
    m = figure(); p = cv2.GaussianBlur(m, (0, 0), 2).astype(np.float32) / 255
    assert P.check(p, "front")["ok"]
    a, b = P.frame(m, "front") > 0, P.frame(p, "front") > 0
    assert (a & b).sum() / (a | b).sum() > 0.98


def test_load_photo_applies_exif_and_caps_size():
    img = Image.fromarray(np.zeros((3000, 4000, 3), np.uint8)); ex = Image.Exif(); ex[0x0112] = 6
    buf = io.BytesIO(); img.save(buf, "JPEG", exif=ex)
    rgb = P.load_photo(buf.getvalue())
    assert rgb.shape == (1600, 1200, 3) and rgb.dtype == np.uint8                # rotated upright, longest side 1600


def test_segmenter_end_to_end_when_weights_are_available():
    if os.environ.get("MEASURE_TEST_SEGMENTER") != "1":
        return
    model = P.load_segmenter(); assert P.load_segmenter() is model               # cached
    rgb = np.full((800, 600, 3), 200, np.uint8)
    prob = P.segment_person(rgb, model)
    assert prob.shape == (800, 600) and 0 <= prob.min() and prob.max() <= 1
    assert P.check(prob, "front")["reason"] == "no_person"                        # a blank wall has nobody in it


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("ok  ", name)
    print("all passed")
