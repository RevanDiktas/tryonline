"""WORKER COPY of .local_prototype/measure_ml/parse_photos.py, written by make_street_worker.py (changed lines: PARSE_PATCHES there).

Clothing parser for shopper photos (2026-11-24): WHAT the person wears and WHERE skin is bare, in the same
720 x 960 BodyM framing as measure_core/preprocess.py, so the label map lines up pixel for pixel with its
mask_960x720. Runs on this machine, CPU only; nothing here uploads a photo.

    from parse_photos import parse
    r = parse("front.jpg", "front", height_cm=192)        # height is optional (only adds cm values)
    r["labels"]        uint8 (960, 720), values = LABELS below; 0 exactly where r["mask_960x720"] is 0
    r["mask_960x720"]  the same array measure_core.preprocess.preprocess() returns for this photo
    r["uncertain"]     bool (960, 720): inside the outline but the parser saw background; the label there is its second choice
    r["outfit"]        descriptor dict (top type, sleeve ends, hem, lower type, trouser ends, shoes, bare fractions)
    r["check"]         preprocess's photo check, unchanged
    r["seconds"]       timing per stage

    r = parse_pair("front.jpg", "side.jpg", height_cm=192)   # {"front": ..., "side": ...}; USE THIS when both exist:
                                                             # the side view takes garment types and hem from the front

    python parse_photos.py check <n>=<photo>:<front|side> [...] [--height 192]
        writes ~/Downloads/parse_check_<n>.png (photo | labels on photo | labels + descriptor) and prints the descriptors
    python parse_photos.py pair <nf>=<front photo> <ns>=<side photo> [--height 192]
        the same for one capture, side view reconciled with the front view
    python parse_photos.py selftest
        proves the torch SegFormer here equals the published ONNX export (needs onnxruntime: use segvenv/bin/python)

MODEL: mattmdjaga/segformer_b2_clothes (Hugging Face), SegFormer-B2 (MiT-B2 backbone) fine-tuned on the ATR
human-parsing dataset, 18 classes. File seg_models/segformer_b2_clothes/model.safetensors, 109,493,236 bytes,
sha256 8f86fd90c567afd4370b3cc3a7e81ed767a632b2832a738331af660acc0c4c68, from
https://huggingface.co/mattmdjaga/segformer_b2_clothes/resolve/main/model.safetensors
The network is written out below in plain torch (no `transformers` needed), checked against the repo's ONNX export.

LICENCE -- READ BEFORE THIS GOES NEAR A PAYING CUSTOMER. As found on 2026-11-24:
  * Model card: "license: other" and, under "License": "The license for this model can be found here"
    -> https://github.com/NVlabs/SegFormer/blob/master/LICENSE , the "NVIDIA Source Code License for SegFormer"
    (full copy next to the weights: seg_models/segformer_b2_clothes/LICENSE_NVIDIA_SegFormer.txt). Its clause 3.3:
      "Use Limitation. The Work and any derivative works thereof only may be used or intended for use
       non-commercially. Notwithstanding the foregoing, NVIDIA and its affiliates may use the Work and any
       derivative works commercially. As used herein, "non-commercially" means for research or evaluation
       purposes only."
    So these WEIGHTS ARE NON-COMMERCIAL (the MiT-B2 backbone they start from, nvidia/mit-b2, carries the same
    licence). Fine for validation (see CLAUDE.md, pre-seed licence posture); not for the shipped product.
  * Training data, ATR (github.com/lemondan/HumanParsing-Dataset; the HF copy is mattmdjaga/human_parsing_dataset):
    the repository has NO licence file. Its README's only usage sentence is: "Please cite our two papers if you
    use this dataset for  acadamic and commercial research." The HF dataset card says, under Licensing
    Information: "[More Information Needed]". The 17,706 images are fashion photos collected from the web;
    no statement about the rights in the images themselves. So: no explicit grant, citation requested.
  * Alternatives looked at for the commercial route (none is clean out of the box):
      - SCHP (GoGoDuck912/Self-Correction-Human-Parsing): code MIT ("Copyright (c) 2020 Peike Li"); weights trained
        on LIP / ATR / Pascal-Person-Part, whose terms are those datasets' own (LIP is published for
        non-commercial research); weights are on Google Drive only.
      - Sapiens-seg (facebookresearch/sapiens): LICENSE file is "Creative Commons Attribution-NonCommercial 4.0
        International". Non-commercial.
      - MediaPipe multi-class selfie segmenter: MediaPipe is Apache-2.0, the only clearly commercial-usable one,
        but its 6 classes (background, hair, body-skin, face-skin, clothes, others) do not separate upper from
        lower garment or shoes. It would give skin vs cloth; top/bottom would have to come from geometry.
    The commercial path is therefore: (a) MediaPipe skin/cloth + geometry, or (b) train our own small parser
    (architecture is free to re-implement; the constraint is the weights and the data), using this model's
    labels only as a reference to check against, not as training targets for a shipped model without legal sign-off.

Person outline: measure_core/preprocess.py (DeepLabV3-R101, torchvision COCO_WITH_VOC_LABELS_V1 weights), reused
unchanged: same photo loading, same person mask, same crop / scale / placement.

Everything marked "judgement" below is a threshold set by eye on the eight test photos of one man, not calibrated.

SEEN ON THE EIGHT TEST PHOTOS (revan/up_2112..2120; black T-shirt, black straight jeans, black socks, dim room),
overlays in ~/Downloads/parse_check_<n>.png:
  works   front views: skin / top / trousers split, sleeve end, top hem. Hem agrees to 0.2% of height across parser
          settings and to 1% between two shots of the same session. Bare arms, neck, face, hair are clean in all eight.
  works   side views after parse_pair: top / trouser split and bare arm.
  FAILS   side view alone, hem of a black top over black trousers: off by 6% of height in 2 of 4 (up_2115, up_2120),
          and before the whole-body dress decision the torso came back as "a dress". parse_pair repairs it from the front.
  FAILS   trouser end against socks of the same colour: no sock class, and the model drops or mislabels dark shins near
          a dark floor object. Wrong on one leg of up_2112 and up_2118 and on side up_2120 (reads 0.85 to 0.87 of height,
          truth about 0.94). Each case carries trouser_end_in_doubt = true; the outfit-level trouser_end_frac takes the
          leg that is not in doubt and was within 1% of height on all four front photos.
  FAILS   an object merged into the outline (the stand between the legs in up_2112): the parser calls most of it
          trousers, so r["uncertain"] does NOT flag it. What does flag it: crotch_suspect (legs join at 0.68 of height).
  untested  hoodie, long sleeves, shorts, bare legs, shoes, skirts, dresses, light clothes, women, other skin tones.
          The type rules for those are written but have not seen a photo.
Time per photo, one CPU thread, on this laptop (Intel i5-8257U) while three other jobs held the other cores:
  person outline (DeepLab, the same work preprocess.py does) 19 to 37 s; parser 13 to 20 s for three passes,
  4.6 s for one (FAST_PASSES); framing + descriptor 0.2 to 0.5 s.
"""
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))                                 # worker: preprocess.py is one folder up
import preprocess as PP  # noqa: E402

torch.set_num_threads(int(os.environ.get("PARSE_THREADS", "1")))      # other jobs own the remaining cores
cv2.setNumThreads(int(os.environ.get("PARSE_THREADS", "1")))

WEIGHTS = Path(os.environ.get("MEASURE_PARSER_WEIGHTS") or HERE.parent / "weights" / "segformer_b2_clothes.safetensors")
DEVICE = os.environ.get("MEASURE_PARSER_DEVICE", "cpu")                # "cuda" is NOT verified; cpu is what was scored
# Parser passes, averaged. One pass is NOT stable on side views of dark clothes: the same photo comes back as
# "T-shirt + trousers" or as "a dress down to the knee" depending on crop margin and input size (tested 2026-11-24,
# six settings x eight photos). Front views agree across settings to 0.2% of height. Each pass = (shape, margin):
#   "square": the person box, padded to 2:3 and squashed to 512 x 512, which is how the model saw ATR in training
#   "aspect": the person box at 768 px tall, shape kept
# margin = space around the person box as a fraction of person height.
PASSES = (("square", 0.06), ("square", 0.15), ("aspect", 0.15))
FAST_PASSES = (("square", 0.15),)                     # one pass, a third of the time; fine for front views

# ---------------------------------------------------------------- labels
LABELS = ["background", "hair", "face", "neck", "arm_left", "arm_right", "leg_left", "leg_right",
          "upper_garment", "lower_garment", "footwear", "dress", "accessory"]
# left / right = side of the IMAGE (not the person's own left / right). In a side view all bare arm skin is
# arm_left and all bare leg skin is leg_left (one visible limb; the split has no meaning there).
# neck is cut from the model's "Face" class by shape (the model has no neck class), see _split_neck.
# footwear = shoes AND socks: the model has no sock class.
# r["uncertain"] (bool map, same frame) marks pixels inside the outline that the parser called background in a solid
# blob: a piece of the person the parser missed (seen: a black trouser shin in front of a dark stand base) or an
# object merged into the outline. In r["labels"] those pixels carry the nearest body label, so there are no holes.
# It does NOT catch every merged object: the parser labelled most of a black stand between the legs as trousers.
L = {n: i for i, n in enumerate(LABELS)}
ATR = ["Background", "Hat", "Hair", "Sunglasses", "Upper-clothes", "Skirt", "Pants", "Dress", "Belt", "Left-shoe",
       "Right-shoe", "Face", "Left-leg", "Right-leg", "Left-arm", "Right-arm", "Bag", "Scarf"]
# merged groups, in this order: bg, hair, face(+neck), arm skin, leg skin, upper, lower, footwear, dress, accessory
GROUPS = [("background", [0]), ("hair", [2]), ("face", [11]), ("arm", [14, 15]), ("leg", [12, 13]),
          ("upper_garment", [4]), ("lower_garment", [6, 5, 8]), ("footwear", [9, 10]), ("dress", [7]),
          ("accessory", [1, 3, 16, 17])]
G = {n: i for i, (n, _) in enumerate(GROUPS)}
COLOURS = np.array([(0, 0, 0), (150, 90, 30), (255, 200, 160), (255, 140, 90), (255, 60, 60), (255, 150, 0),
                    (200, 60, 200), (255, 120, 220), (40, 150, 255), (40, 220, 120), (240, 240, 60), (0, 200, 200),
                    (180, 180, 180)], np.uint8)


# ---------------------------------------------------------------- SegFormer-B2 in plain torch
class _Attn(nn.Module):
    def __init__(self, dim, heads, sr):
        super().__init__()
        self.heads = heads
        self.self = nn.Module(); self.output = nn.Module()
        self.self.query, self.self.key, self.self.value = nn.Linear(dim, dim), nn.Linear(dim, dim), nn.Linear(dim, dim)
        self.sr = sr
        if sr > 1:
            self.self.sr = nn.Conv2d(dim, dim, sr, sr); self.self.layer_norm = nn.LayerNorm(dim)
        self.output.dense = nn.Linear(dim, dim)

    def forward(self, x, h, w):
        b, n, c = x.shape
        q = self.self.query(x).view(b, n, self.heads, c // self.heads).transpose(1, 2)
        kv = x
        if self.sr > 1:
            kv = self.self.layer_norm(self.self.sr(x.transpose(1, 2).reshape(b, c, h, w)).flatten(2).transpose(1, 2))
        k = self.self.key(kv).view(b, -1, self.heads, c // self.heads).transpose(1, 2)
        v = self.self.value(kv).view(b, -1, self.heads, c // self.heads).transpose(1, 2)
        a = (q @ k.transpose(-1, -2)) / (c // self.heads) ** 0.5
        return self.output.dense((a.softmax(-1) @ v).transpose(1, 2).reshape(b, n, c))


class _Mlp(nn.Module):
    def __init__(self, dim, ratio=4):
        super().__init__()
        self.dense1 = nn.Linear(dim, dim * ratio)
        self.dwconv = nn.Module(); self.dwconv.dwconv = nn.Conv2d(dim * ratio, dim * ratio, 3, 1, 1, groups=dim * ratio)
        self.dense2 = nn.Linear(dim * ratio, dim)

    def forward(self, x, h, w):
        x = self.dense1(x); b, n, c = x.shape
        x = self.dwconv.dwconv(x.transpose(1, 2).reshape(b, c, h, w)).flatten(2).transpose(1, 2)
        return self.dense2(F.gelu(x))


class _Block(nn.Module):
    def __init__(self, dim, heads, sr):
        super().__init__()
        self.layer_norm_1, self.attention = nn.LayerNorm(dim), _Attn(dim, heads, sr)
        self.layer_norm_2, self.mlp = nn.LayerNorm(dim), _Mlp(dim)

    def forward(self, x, h, w):
        x = x + self.attention(self.layer_norm_1(x), h, w)
        return x + self.mlp(self.layer_norm_2(x), h, w)


class _Patch(nn.Module):
    def __init__(self, cin, dim, k, stride):
        super().__init__()
        self.proj, self.layer_norm = nn.Conv2d(cin, dim, k, stride, k // 2), nn.LayerNorm(dim)

    def forward(self, x):
        x = self.proj(x); h, w = x.shape[2:]
        return self.layer_norm(x.flatten(2).transpose(1, 2)), h, w


class _LinearC(nn.Module):
    def __init__(self, cin, dim):
        super().__init__(); self.proj = nn.Linear(cin, dim)


class SegFormerB2(nn.Module):
    """Same parameter names as transformers.SegformerForSemanticSegmentation, so the checkpoint loads strictly."""
    DIMS, DEPTHS, HEADS, SR = (64, 128, 320, 512), (3, 4, 6, 3), (1, 2, 5, 8), (8, 4, 2, 1)

    def __init__(self, n_classes=18, dec=768):
        super().__init__()
        enc = nn.Module(); d = self.DIMS
        enc.patch_embeddings = nn.ModuleList([_Patch(3 if i == 0 else d[i - 1], d[i], 7 if i == 0 else 3, 4 if i == 0 else 2) for i in range(4)])
        enc.block = nn.ModuleList([nn.ModuleList([_Block(d[i], self.HEADS[i], self.SR[i]) for _ in range(self.DEPTHS[i])]) for i in range(4)])
        enc.layer_norm = nn.ModuleList([nn.LayerNorm(d[i]) for i in range(4)])
        self.segformer = nn.Module(); self.segformer.encoder = enc
        head = nn.Module()
        head.linear_c = nn.ModuleList([_LinearC(d[i], dec) for i in range(4)])
        head.linear_fuse = nn.Conv2d(4 * dec, dec, 1, bias=False)
        head.batch_norm = nn.BatchNorm2d(dec); head.classifier = nn.Conv2d(dec, n_classes, 1)
        self.decode_head = head

    def forward(self, x):
        enc, head, feats = self.segformer.encoder, self.decode_head, []
        for i in range(4):
            t, h, w = enc.patch_embeddings[i](x)
            for blk in enc.block[i]:
                t = blk(t, h, w)
            x = enc.layer_norm[i](t).transpose(1, 2).reshape(t.shape[0], -1, h, w)
            feats.append(x)
        size = feats[0].shape[2:]; ups = []
        for f, lc in zip(feats, head.linear_c):
            y = lc.proj(f.flatten(2).transpose(1, 2)).transpose(1, 2).reshape(f.shape[0], -1, *f.shape[2:])
            ups.append(F.interpolate(y, size=size, mode="bilinear", align_corners=False))
        y = F.relu(head.batch_norm(head.linear_fuse(torch.cat(ups[::-1], 1))))
        return head.classifier(y)                                    # logits at 1/4 of the input size


_PARSER = {}


def load_parser(weights=WEIGHTS):
    """SegFormer-B2 clothes parser in eval mode, loaded once."""
    key = str(weights)
    if key not in _PARSER:
        from safetensors.torch import load_file
        net = SegFormerB2(); net.load_state_dict(load_file(key), strict=True)
        _PARSER[key] = net.eval().to(DEVICE)
    return _PARSER[key]


def _one_pass(rgb, box, net, shape, margin):
    """18-class probabilities over the person box (y0..y1, x0..x1 of the working photo), one parser pass.
    Where the crop leaves the photo it is padded by repeating the edge."""
    y0, y1, x0, x1 = box; m = int(round(margin * (y1 - y0 + 1)))
    cy0, cy1 = y0 - m, y1 + 1 + m
    if shape == "square":
        want = int((cy1 - cy0) * 2 / 3); c = (x0 + x1) // 2; cx0, cx1 = c - want // 2, c + want // 2
        cx0, cx1 = min(cx0, x0), max(cx1, x1 + 1); size = (512, 512)            # never cut the person (arms held wide)
    else:
        cx0, cx1 = x0 - m, x1 + 1 + m; size = (max(32, int(round((cx1 - cx0) * 768 / (cy1 - cy0) / 32)) * 32), 768)
    pad = (max(0, -cy0), max(0, cy1 - rgb.shape[0]), max(0, -cx0), max(0, cx1 - rgb.shape[1]))
    crop = cv2.copyMakeBorder(rgb[max(0, cy0):cy1, max(0, cx0):cx1], *pad, cv2.BORDER_REPLICATE)
    x = torch.from_numpy(cv2.resize(crop, size, interpolation=cv2.INTER_AREA)).permute(2, 0, 1).float().div(255)
    x = ((x - torch.tensor([0.485, 0.456, 0.406])[:, None, None]) / torch.tensor([0.229, 0.224, 0.225])[:, None, None])[None]
    with torch.no_grad():
        lg = F.interpolate(net(x.to(DEVICE)), size=crop.shape[:2], mode="bilinear", align_corners=False)[0].cpu()
    return lg.softmax(0)[:, y0 - cy0:y1 + 1 - cy0, x0 - cx0:x1 + 1 - cx0]


def _fill_nearest(lab, unknown, inside):
    """Give every `unknown` pixel the label of the nearest known pixel inside the outline."""
    known = inside & ~unknown
    if not known.any() or not unknown.any():
        return lab
    _, idx = cv2.distanceTransformWithLabels((~known).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    table = np.zeros(int(idx.max()) + 1, lab.dtype); table[idx[known]] = lab[known]
    out = lab.copy(); out[unknown] = table[idx[unknown]]
    return out


# ---------------------------------------------------------------- photo -> framed label map
def _frame_geometry(soft, view):
    """The numbers measure_core.preprocess.frame() uses: person box in the photo, scale, placement."""
    t = PP.FRAME[view]; y0, y1, x0, x1 = PP.bbox(soft)
    s = t["height"] / (y1 - y0 + 1); new_w = max(1, int(round((x1 - x0 + 1) * s)))
    return {"box": (y0, y1, x0, x1), "scale": s, "new_w": new_w, "left": int(round(t["cx"] - new_w / 2)), "top": t["top"], "height": t["height"]}


def _to_frame(crop, geo, interp):
    """A crop of the person box (H x W [x C]) -> the 960 x 720 frame, placed as preprocess.frame() places the mask."""
    r = cv2.resize(crop, (geo["new_w"], geo["height"]), interpolation=interp)
    out = np.zeros((PP.OUT_H, PP.OUT_W) + r.shape[2:], r.dtype)
    left, top = geo["left"], geo["top"]
    ys, xs = slice(max(0, top), min(PP.OUT_H, top + geo["height"])), slice(max(0, left), min(PP.OUT_W, left + geo["new_w"]))
    out[ys, xs] = r[ys.start - top: ys.stop - top, xs.start - left: xs.stop - left]
    return out


def _photo_in_frame(rgb, geo):
    """The whole photo warped into the frame (person box lands where the mask is), for overlays."""
    y0, y1, x0, x1 = geo["box"]; sx = geo["new_w"] / (x1 - x0 + 1); sy = geo["height"] / (y1 - y0 + 1)
    M = np.float32([[sx, 0, geo["left"] - x0 * sx], [0, sy, geo["top"] - y0 * sy]])
    return cv2.warpAffine(rgb, M, (PP.OUT_W, PP.OUT_H), flags=cv2.INTER_AREA, borderValue=(30, 30, 30))


def _split_neck(lab, top, H):
    """Cut the neck off the model's Face class: below the row where the face region has narrowed to under 70% of
    its widest row, and never above 10% of body height from the head top (judgement)."""
    face = lab == L["face"]; rows = np.flatnonzero(face.sum(1) >= 3)
    if len(rows) < 10:
        return lab, None
    w = face.sum(1).astype(float); k = int(rows[0] + np.argmax(w[rows[0]:rows[-1] + 1])); chin = None
    for y in range(k, int(rows[-1]) + 1):
        if w[y] < 0.70 * w[k] and y >= top + 0.10 * H and np.all(w[y:y + 4] < 0.75 * w[k]):
            chin = y; break
    if chin is None:
        return lab, None
    lab = lab.copy(); sel = face.copy(); sel[:chin] = False; lab[sel] = L["neck"]
    return lab, chin


def parse(photo_path, view="front", height_cm=None, models=None, passes=None, keep_debug=False):
    """Photo -> label map + outfit descriptor in preprocess.py's 720 x 960 framing. See the module docstring.
    models: optional (deeplab, parser) pair to reuse; loaded once and cached otherwise.
    passes: PASSES (default, three parser passes) or FAST_PASSES (one), or set PARSE_FAST=1."""
    passes = passes or (FAST_PASSES if os.environ.get("PARSE_FAST") else PASSES)
    t0 = time.time()
    seg, net = models if models else (PP.load_segmenter(), load_parser())
    rgb = PP.load_photo(photo_path)
    t1 = time.time()
    prob = PP.segment_person(rgb, seg)
    chk = PP.check(prob, view); soft = PP.clean_mask(prob)
    t2 = time.time()
    out = {"view": view, "check": chk, "mask_960x720": None, "labels": None, "outfit": None, "label_names": LABELS}
    if soft is None or PP.bbox(soft) is None:
        out["seconds"] = {"load": round(t1 - t0, 2), "outline": round(t2 - t1, 2), "parse": 0.0, "total": round(time.time() - t0, 2)}
        return out
    mask = PP.frame(soft, view); geo = _frame_geometry(soft, view)
    y0, y1, x0, x1 = geo["box"]
    p = sum(_one_pass(rgb, geo["box"], net, shape, margin) for shape, margin in passes) / len(passes)
    # one decision for the whole body: a dress, or a top with trousers / skirt. Pixel by pixel the model mixes the
    # two (dark top over dark trousers reads as a knee-length dress in patches); the larger total wins outright.
    body = torch.from_numpy(soft[y0:y1 + 1, x0:x1 + 1] > 0.5)
    mass = lambda i: float(p[i][body].sum())
    dress_mass, two_piece_mass = mass(7), mass(4) + mass(6) + mass(5)
    if dress_mass < two_piece_mass:
        p[7] = 0
    grp = torch.stack([p[ids].sum(0) for _, ids in GROUPS], -1).numpy()            # (h, w, 10) merged probabilities
    t3 = time.time()
    gf = np.dstack([_to_frame(np.ascontiguousarray(grp[..., i]), geo, cv2.INTER_LINEAR) for i in range(grp.shape[2])])
    inside = mask > 0
    best = gf.argmax(2); best_fg = 1 + gf[..., 1:].argmax(2)
    # inside the outline the parser's "background" only stands where it forms a solid blob; edge slivers take the best body label
    bg_in = inside & (best == 0)
    blob = cv2.morphologyEx(bg_in.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))) > 0
    blob = cv2.dilate(blob.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))) > 0
    uncertain = bg_in & blob
    # No holes in the label map: a doubted pixel carries the parser's best BODY label (its second choice). On the test
    # photos that put the trouser end within 1% of height of the truth where a nearest-label fill was 7% off.
    g = best_fg
    rows = np.flatnonzero(inside.sum(1) >= 3); top, bot = int(rows[0]), int(rows[-1]); H = bot - top + 1
    cols = np.arange(PP.OUT_W)[None, :]
    band = inside[top + int(0.25 * H): top + int(0.50 * H)]
    mid = float(np.flatnonzero(band.sum(0)).mean()) if band.any() else PP.FRAME[view]["cx"]
    if view == "front":                                    # image-left / image-right of the body midline, limb by limb
        cc_side = _limb_sides(g, inside, mid)
    else:
        cc_side = np.zeros(g.shape, bool)
    lab = np.zeros(g.shape, np.uint8)
    lab[g == G["hair"]] = L["hair"]; lab[g == G["face"]] = L["face"]
    lab[g == G["arm"]] = L["arm_left"]; lab[(g == G["arm"]) & cc_side] = L["arm_right"]
    lab[g == G["leg"]] = L["leg_left"]; lab[(g == G["leg"]) & cc_side] = L["leg_right"]
    lab[g == G["upper_garment"]] = L["upper_garment"]; lab[g == G["lower_garment"]] = L["lower_garment"]
    lab[g == G["footwear"]] = L["footwear"]; lab[g == G["dress"]] = L["dress"]; lab[g == G["accessory"]] = L["accessory"]
    lab[~inside] = 0
    # footwear must reach the feet: a "shoe" patch that ends more than 5% of height above the floor is a mislabelled
    # piece of dark trouser leg (seen on black jeans + black socks); it takes the nearest other label
    n, cc, stats, _ = cv2.connectedComponentsWithStats((lab == L["footwear"]).astype(np.uint8), connectivity=8)
    stray = np.isin(cc, [i for i in range(1, n) if stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] - 1 < bot - 0.05 * H])
    if stray.any():
        lab = _fill_nearest(lab, stray, inside & (lab != L["footwear"]) | stray)      # nearest label that is not footwear
    lab, chin = _split_neck(lab, top, H)
    # how far outline and parser disagree: the parser's person outside the outline, and the outline's non-person inside
    parser_person = best != 0
    geo_px = {"top": top, "bot": bot, "H": H, "mid": mid, "chin": chin}
    outfit = describe(lab, mask, view, height_cm, geo_px, uncertain)
    outfit["dress_vs_two_piece_mass"] = [round(dress_mass / max(float(body.sum()), 1), 4), round(two_piece_mass / max(float(body.sum()), 1), 4)]
    outfit["outline_vs_parser"] = {
        "uncertain_inside_outline_frac": round(float(uncertain.sum() / max(inside.sum(), 1)), 4),
        "parser_person_outside_outline_frac": round(float((parser_person & ~inside).sum() / max(inside.sum(), 1)), 4)}
    t4 = time.time()
    out.update(mask_960x720=mask, labels=lab, uncertain=uncertain, outfit=outfit, passes=len(passes),
               seconds={"load": round(t1 - t0, 2), "outline": round(t2 - t1, 2), "parse": round(t3 - t2, 2),
                        "frame_and_describe": round(t4 - t3, 2), "total": round(t4 - t0, 2)})
    if keep_debug:
        out["_photo_in_frame"] = _photo_in_frame(rgb, geo); out["_geo"] = geo; out["_parser_person"] = parser_person
    return out


def _limb_sides(g, inside, mid):
    """True where a pixel belongs to the image-RIGHT half: each connected piece of bare arm / bare leg goes to the
    side its centre lies on (so a hand crossing the midline stays with its arm); other pixels by column."""
    right = np.zeros(g.shape, bool); right[:, int(round(mid)) + 1:] = True
    for grp in (G["arm"], G["leg"]):
        n, cc, stats, cent = cv2.connectedComponentsWithStats(((g == grp) & inside).astype(np.uint8), connectivity=8)
        for i in range(1, n):
            right[cc == i] = cent[i][0] > mid
    return right


# ---------------------------------------------------------------- outfit descriptor
def _runs_of_rows(flags, max_gap=6):
    """Longest stretch of True rows, allowing gaps of up to max_gap rows. Returns (first, last) or None."""
    ys = np.flatnonzero(flags)
    if len(ys) == 0:
        return None
    best, start, prev = None, ys[0], ys[0]
    for y in list(ys[1:]) + [None]:
        if y is None or y - prev > max_gap + 1:
            if best is None or prev - start > best[1] - best[0]:
                best = (int(start), int(prev))
            start = y
        prev = y
    return best


def describe(lab, mask, view, height_cm=None, geo=None, uncertain=None):
    """Outfit descriptor from a framed label map. Rows are frame rows (0..959); *_frac values are fractions of
    person height measured down from the head top (hair included, as the outline includes it)."""
    inside = mask > 0
    rows = np.flatnonzero(inside.sum(1) >= 3); top, bot = int(rows[0]), int(rows[-1]); H = bot - top + 1
    mid = geo["mid"] if geo else PP.FRAME[view]["cx"]
    fr = lambda y: None if y is None else round((y - top) / H, 4)
    cm = (height_cm / H) if height_cm else None
    area = float(inside.sum())
    cnt = {n: int((lab == i).sum()) for n, i in L.items()}
    d = {"view": view, "person_top_row": top, "person_bottom_row": bot, "person_height_px": H,
         "cm_per_px": round(cm, 5) if cm else None,
         "area_frac": {n: round(c / area, 4) for n, c in cnt.items() if n != "background"}}
    up = (lab == L["upper_garment"]) | (lab == L["dress"]); low = lab == L["lower_garment"]; foot = lab == L["footwear"]
    arm = {"left": lab == L["arm_left"], "right": lab == L["arm_right"]}
    leg = {"left": lab == L["leg_left"], "right": lab == L["leg_right"]}

    # --- landmarks from the outline: shoulder row, crotch row, limb tracks (front view only)
    P = None
    if view == "front":
        try:
            import pipe_profiles2 as P2
            P = P2.front_parts(inside)
        except Exception:
            P = None
    width = inside.sum(1).astype(float)
    if P and (P["pit"]["L"] or P["pit"]["R"]):
        pit = int(np.mean([v for v in P["pit"].values() if v]))
        ext = np.array([P["extent"][y][1] - P["extent"][y][0] + 1 if y in P["extent"] else 0 for y in range(top, bot + 1)], float)
        ys = np.flatnonzero(ext[: pit - top + 1] >= 0.85 * ext[pit - top])
        shoulder = top + int(ys[0]) if len(ys) else top + int(0.18 * H)
        shoulder_src = "outline (first row at 85% of the width at the armpits)"
        crotch = int(P["crotch"]); crotch_src = "outline (where the legs join)"
        if not 0.50 <= (crotch - top) / H <= 0.62:           # judgement: an object between the legs moves the join (seen: 0.675 with a stand)
            d["crotch_suspect"] = f"legs join at {round((crotch - top) / H, 3)} of height, outside 0.50 to 0.62: something fills the gap between the legs"
            crotch, crotch_src = top + int(round(0.56 * H)), "fixed 56% of height (outline value rejected)"
    else:
        shoulder, shoulder_src = top + int(round(0.18 * H)), "fixed 18% of height (judgement)"
        crotch, crotch_src = top + int(round(0.56 * H)), "fixed 56% of height (judgement; trouser crotch, hair included in height)"
    d["shoulder_row"], d["shoulder_frac"], d["shoulder_from"] = shoulder, fr(shoulder), shoulder_src
    d["crotch_row"], d["crotch_frac"], d["crotch_from"] = crotch, fr(crotch), crotch_src

    # --- arms: where bare skin starts (= sleeve end) and how much of shoulder-to-fingertip is bare
    sides = ("left", "right") if view == "front" else ("left",)
    arms = {}
    for k in sides:
        a = arm[k]; flags = a.sum(1) >= 3; flags[:shoulder - int(0.03 * H)] = False
        run = _runs_of_rows(flags, max_gap=int(0.02 * H))
        track_bot = None
        if P and P["arms"]["L" if k == "left" else "R"]:
            track_bot = int(P["arms"]["L" if k == "left" else "R"][-1][0])
        if run is None or run[1] - run[0] < 0.03 * H:
            arms[k] = {"bare_frac": 0.0, "sleeve_end_row": track_bot, "sleeve_end_frac": fr(track_bot), "arm_bottom_row": track_bot,
                       "arm_bottom_frac": fr(track_bot), "sleeve_len_frac_of_arm": 1.0 if track_bot else None,
                       "note": "no bare arm skin found: sleeve reaches the hand, or the arm is hidden"}
            continue
        end = max(run[1], track_bot or 0); length = max(end - shoulder + 1, 1)
        bare_rows = int(flags[run[0]:run[1] + 1].sum())
        arms[k] = {"sleeve_end_row": run[0], "sleeve_end_frac": fr(run[0]), "arm_bottom_row": end, "arm_bottom_frac": fr(end),
                   "bare_frac": round(min(bare_rows / length, 1.0), 3),
                   "sleeve_len_frac_of_arm": round(max(run[0] - shoulder, 0) / length, 3)}
        if cm:
            arms[k]["sleeve_end_cm_below_shoulder"] = round(max(run[0] - shoulder, 0) * cm, 1)
    d["arms"] = arms if view == "front" else {"near": arms["left"]}

    # --- top: hem row, type
    torso_cols = slice(int(mid - 0.07 * H), int(mid + 0.07 * H)) if view == "front" else slice(0, lab.shape[1])
    has_top = up.sum() >= 0.03 * area
    hem = None
    if has_top:
        sub = up[:, torso_cols]; colsum = sub.sum(0); ok = colsum >= 0.05 * H
        if ok.any():
            lowest = np.array([np.flatnonzero(sub[:, c])[-1] for c in np.flatnonzero(ok)])
            hem = int(np.median(lowest)); d["top_hem_row_spread"] = [int(np.percentile(lowest, 10)), int(np.percentile(lowest, 90))]
    d["top_hem_row"], d["top_hem_frac"] = hem, fr(hem)
    d["top_hem_minus_crotch_frac"] = round((hem - crotch) / H, 4) if hem is not None else None       # dress.py's "hem" number
    sl = [v["sleeve_len_frac_of_arm"] for v in arms.values() if v.get("sleeve_len_frac_of_arm") is not None]
    sleeve = float(np.mean(sl)) if sl else None
    hood = float((up[:max(shoulder - int(0.04 * H), 0)]).sum() / max(up.sum(), 1))        # cloth well above the shoulder line
    hairless = cnt["hair"] < 0.004 * area
    if not has_top:
        top_type = "none"
    elif sleeve is None:
        top_type = "tee"
    elif sleeve >= 0.55:                                    # judgement: the elbow is at about 0.42 of shoulder-to-fingertip
        top_type = "hoodie" if (hood > 0.03 or hairless) else "long"
    else:
        top_type = "tee"
    d["top_type"] = top_type
    d["top_evidence"] = {"upper_garment_area_frac": round(float(up.sum() / area), 4), "mean_sleeve_len_frac_of_arm": None if sleeve is None else round(sleeve, 3),
                         "sleeveless": bool(has_top and sleeve is not None and sleeve < 0.10),
                         "cloth_above_shoulder_frac": round(hood, 4), "is_dress": bool(cnt["dress"] > cnt["upper_garment"])}

    # --- legs: trouser end, bare skin, footwear
    floor = bot; leg_len = max(floor - crotch, 1); legs = {}
    half = {"left": cols_lt(lab.shape, mid), "right": ~cols_lt(lab.shape, mid)} if view == "front" else {"left": np.ones(lab.shape, bool)}
    for k in sides:
        lo = low & half[k]; lo_rows = lo.sum(1) >= 3
        run = _runs_of_rows(lo_rows, max_gap=int(0.02 * H)) if lo_rows.any() else None
        skin_rows = (leg[k].sum(1) >= 3); skin_rows[:crotch] = False
        ft = foot & half[k]; ft_rows = np.flatnonzero(ft.sum(1) >= 3)
        # the cloth's own lowest row. (Until 2026-11-24 night it had to start at the crotch row; with a low camera the
        # crotch row is a guess, and short shorts on people 0, 2, 6 of the real set came out as "none".)
        end = run[1] if run else None
        doubt = False
        if uncertain is not None and end is not None:
            band = (uncertain & half[k])[max(end - int(0.05 * H), 0): end + int(0.05 * H)]
            doubt = bool(band.sum() >= 0.0015 * area)
        legs[k] = {"trouser_end_row": end, "trouser_end_frac": fr(end), "trouser_end_in_doubt": doubt,
                   "covered_frac_of_leg": round(float(np.clip((end - crotch) / leg_len, 0, 1)), 3) if end is not None else 0.0,
                   "bare_frac": round(float(skin_rows.sum()) / leg_len, 3),
                   "footwear_top_row": int(ft_rows[0]) if len(ft_rows) else None, "footwear_top_frac": fr(int(ft_rows[0])) if len(ft_rows) else None,
                   "footwear_area_frac": round(float(ft.sum() / area), 4)}
    d["legs"] = legs if view == "front" else {"both": legs["left"]}
    # one trouser end for the outfit: a leg whose end is not in doubt wins; otherwise the lower end (dark cloth gets
    # MISSED near the floor, it is not invented, so the lower reading is the safer one)
    ends = [(v["trouser_end_in_doubt"], -v["trouser_end_row"]) for v in legs.values() if v["trouser_end_row"] is not None]
    d["trouser_end_row"] = -min(ends)[1] if ends else None
    d["trouser_end_frac"] = fr(d["trouser_end_row"]); d["trouser_end_in_doubt"] = bool(min(ends)[0]) if ends else None
    zone = slice(bot - int(0.06 * H), bot + 1)                         # the feet: bottom 6% of height (judgement)
    foot_px, skin_px = int(foot[zone].sum()), int((leg["left"] | leg["right"])[zone].sum())
    d["shoe_present"] = bool(foot_px >= 0.004 * area and foot_px > skin_px)   # a few "shoe" pixels on bare toes do not count
    d["foot_zone_px"] = {"footwear": foot_px, "bare_skin": skin_px}
    d["shoe_note"] = "footwear = shoes or socks; the model has no sock class and cannot tell them apart"

    # --- lower garment type from how far it reaches and how the leg width tapers (outline widths, per leg)
    cov = [v["covered_frac_of_leg"] for v in legs.values()]
    taper = _leg_taper(inside, low, P, crotch, floor, mid, view, legs)
    d["leg_width"] = taper
    if cm and taper:
        d["leg_width_cm"] = {k: round(v * H * cm, 1) for k, v in taper.items() if k.endswith("_w") and v is not None}
    has_low = low.sum() >= 0.02 * area
    is_dress = bool(cnt["dress"] > cnt["upper_garment"] and cnt["dress"] >= 0.05 * area)
    if is_dress and not has_low:
        lower = "dress"                                                # not in dress.py's LEGS list: a skirt-shaped outline below the hip
    elif not has_low:
        lower = "none"
    elif max(cov) < 0.72:                                              # judgement: cloth ends well above the ankle
        lower = "shorts"
    elif view != "front":
        lower = "long"                                                 # full-length; fit cannot be read from a side view (legs overlap)
    else:
        hw, kw = taper.get("hem_w"), taper.get("knee_w")
        if hw is None:
            lower = "straight"
        elif hw < 0.068:                                               # widths as fractions of person height (judgement)
            lower = "slim"
        elif hw < 0.105:
            lower = "straight"
        else:
            lower = "loose"
    d["lower_type"] = lower
    if is_dress:
        d["dress_hem_row"], d["dress_hem_frac"] = d["top_hem_row"], d["top_hem_frac"]
    d["lower_evidence"] = {"lower_garment_area_frac": round(float(low.sum() / area), 4), "max_covered_frac_of_leg": round(max(cov), 3),
                           "note": "front view: slim / straight / loose from hem width over height: under 0.068 slim, under 0.105 straight, else loose "
                                   "(judgement, uncalibrated). Side view: 'long' only, take the fit from the front photo (parse_pair does)."}
    return d


# ---------------------------------------------------------------- front + side together
HEM_AGREE = 0.025     # fraction of height: a side-view hem this close to the front-view hem is kept as it is (judgement)


def parse_pair(front_path, side_path, height_cm=None, models=None, passes=None, keep_debug=False):
    """Both photos of one capture. The front view reads the garments reliably; a side view of dark clothes does
    not (the top / trouser boundary moved by up to 8% of height between parser settings on the test photos).
    So the side view takes garment TYPES from the front, and where its own hem disagrees with the front's by more
    than HEM_AGREE its cloth pixels are re-split at the front's hem height. Rows carry over as fractions of person
    height from the head top. Returns {"front": ..., "side": ...}, each as parse() returns."""
    models = models or (PP.load_segmenter(), load_parser())
    f = parse(front_path, "front", height_cm, models, passes, keep_debug)
    s = parse(side_path, "side", height_cm, models, passes, keep_debug)
    return reconcile_side(f, s)


def reconcile_side(f, s):
    """The front-to-side step of parse_pair, on two parse() results (changes s in place)."""
    if f["labels"] is None or s["labels"] is None:
        return {"front": f, "side": s}
    fo, so = f["outfit"], s["outfit"]
    so["own"] = {k: so[k] for k in ("top_type", "lower_type", "top_hem_row", "top_hem_frac")}
    so["top_type"], so["lower_type"] = fo["top_type"], fo["lower_type"]
    so["types_from"] = "front view"
    fh, sh = fo["top_hem_frac"], so["top_hem_frac"]
    two_piece = fo["top_type"] != "none" and fo["lower_type"] not in ("none", "dress") and not fo["top_evidence"]["is_dress"]
    if two_piece and fh is not None and (sh is None or abs(sh - fh) > HEM_AGREE):
        lab = s["labels"]; row = so["person_top_row"] + int(round(fh * so["person_height_px"]))
        cloth = np.isin(lab, [L["upper_garment"], L["lower_garment"], L["dress"]])
        above = np.zeros(lab.shape, bool); above[:row] = True
        lab[cloth & above] = L["upper_garment"]; lab[cloth & ~above] = L["lower_garment"]
        so["top_hem_row"], so["top_hem_frac"], so["top_hem_from"] = row, round(fh, 4), "front view (side view's own hem disagreed)"
        so["top_hem_minus_crotch_frac"] = round((row - so["crotch_row"]) / so["person_height_px"], 4)
        so.pop("top_hem_row_spread", None)
    else:
        so["top_hem_from"] = "side view (agrees with the front view)" if sh is not None else "none"
    if so.get("trouser_end_in_doubt") and fo.get("trouser_end_frac") is not None and not fo.get("trouser_end_in_doubt"):
        so["own"]["trouser_end_frac"] = so["trouser_end_frac"]
        so["trouser_end_frac"] = fo["trouser_end_frac"]; so["trouser_end_row"] = so["person_top_row"] + int(round(fo["trouser_end_frac"] * so["person_height_px"]))
        so["trouser_end_in_doubt"] = False; so["trouser_end_from"] = "front view (side view's own was in doubt)"
    return {"front": f, "side": s}


def cols_lt(shape, mid):
    m = np.zeros(shape, bool); m[:, :int(round(mid)) + 1] = True
    return m


def _leg_taper(inside, low, P, crotch, floor, mid, view, legs):
    """Outline width of one leg at thigh, knee and hem, as fractions of person height (mean of the two legs in a
    front view where they are separate; in a side view the single silhouette width, both legs overlapping)."""
    H = inside.sum(1).nonzero()[0]; top, bot = int(H[0]), int(H[-1]); Hh = bot - top + 1
    L_ = max(floor - crotch, 1)
    ends = [v["trouser_end_row"] for v in legs.values() if v["trouser_end_row"] is not None]
    end = int(np.mean(ends)) if ends else floor - int(0.08 * L_)
    bands = {"thigh_w": (crotch + 0.12 * L_, crotch + 0.20 * L_), "knee_w": (crotch + 0.46 * L_, crotch + 0.54 * L_),
             "hem_w": (end - 0.09 * L_, end - 0.03 * L_)}
    out = {}
    for name, (a, b) in bands.items():
        ws = []
        for y in range(int(a), int(b) + 1):
            if not (0 <= y < inside.shape[0]):
                continue
            if view == "front":
                for side, sel in (("L", slice(0, int(round(mid)) + 1)), ("R", slice(int(round(mid)) + 1, inside.shape[1]))):
                    tr = None
                    if P:
                        tr = next((t for t in P["legs"][side] if t[0] == y), None)
                    if tr is not None:
                        ws.append(tr[2] - tr[1] + 1)
                    else:
                        r = inside[y, sel]; lw = int(r.sum())
                        # arms hanging beside the thigh would add to a plain count: keep the run touching the midline
                        idx = np.flatnonzero(r)
                        if len(idx):
                            brk = np.flatnonzero(np.diff(idx) > 1)
                            segs = np.split(idx, brk + 1)
                            seg = segs[-1] if side == "L" else segs[0]
                            ws.append(len(seg))
            else:
                idx = np.flatnonzero(inside[y])
                if len(idx):
                    segs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
                    ws.append(max(len(s) for s in segs))
        out[name] = round(float(np.median(ws)) / Hh, 4) if ws else None
    if out.get("hem_w") and out.get("knee_w"):
        out["hem_over_knee"] = round(out["hem_w"] / out["knee_w"], 3)
    if out.get("hem_w") and out.get("thigh_w"):
        out["hem_over_thigh"] = round(out["hem_w"] / out["thigh_w"], 3)
    out["legs_separate_in_outline"] = bool(P is not None) if view == "front" else None
    return out


# ---------------------------------------------------------------- bare-skin limb widths (second task)
def bare_widths(result, height_cm):
    """Widths in cm of limbs where the label map shows bare skin: neck, upper arm just below the sleeve, forearm,
    wrist. Width is measured across the limb (row width x cos of the limb's lean). Front view."""
    lab = result["labels"]; o = result["outfit"]; H = o["person_height_px"]; cm = height_cm / H
    out = {"cm_per_px": round(cm, 5), "note": "cm per px = stated height / outline height; the outline's top is the hair, not the skull, and the feet are in socks"}
    neck = (lab == L["neck"]).sum(1).astype(float); rows = np.flatnonzero(neck >= 3)
    if len(rows) >= 4:
        w = neck[rows]; out["neck_width_cm"] = round(float(np.percentile(w, 25)) * cm, 1); out["neck_rows"] = [int(rows[0]), int(rows[-1])]
    for k, name in (("left", "arm_left"), ("right", "arm_right")):
        a = o["arms"].get(k) if "arms" in o else None
        if not a or not a.get("bare_frac"):
            continue
        m = lab == L[name]; y0, y1 = a["sleeve_end_row"], a["arm_bottom_row"]
        ys, ws, cs = [], [], []
        for y in range(y0, y1 + 1):
            idx = np.flatnonzero(m[y])
            if len(idx) >= 3:
                segs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1); s = max(segs, key=len)
                ys.append(y); ws.append(len(s)); cs.append((s[0] + s[-1]) / 2)
        if len(ys) < 20:
            continue
        ys, ws, cs = np.array(ys), np.array(ws, float), np.array(cs)
        slope = np.polyfit(ys, cs, 1)[0]; cosv = 1 / np.sqrt(1 + slope ** 2); wc = ws * cosv * cm
        n = len(ys); shoulder = o["shoulder_row"]; arm_len = max(y1 - shoulder, 1)
        rel = (ys - shoulder) / arm_len                       # 0 shoulder .. 1 fingertip; elbow about 0.42, wrist about 0.75 (judgement)
        sm = np.convolve(wc, np.ones(9) / 9, mode="same")
        res = {"lean_deg": round(float(np.degrees(np.arctan(slope))), 1), "bare_rows": [int(ys[0]), int(ys[-1])]}
        up_sel = (rel < 0.40) & (ys >= y0 + 0.01 * H)
        if up_sel.sum() >= 5:
            res["upper_arm_below_sleeve_cm"] = round(float(np.median(sm[up_sel][: max(5, int(0.03 * H))])), 1)
            res["upper_arm_max_bare_cm"] = round(float(sm[up_sel].max()), 1)
        fo = (rel >= 0.45) & (rel <= 0.72)
        if fo.sum() >= 5:
            res["forearm_max_cm"] = round(float(sm[fo].max()), 1); res["forearm_max_row"] = int(ys[fo][np.argmax(sm[fo])])
            res["wrist_min_cm"] = round(float(sm[(rel >= 0.62) & (rel <= 0.80)].min()), 1) if ((rel >= 0.62) & (rel <= 0.80)).sum() >= 3 else None
        out[name] = res
    return out


# ---------------------------------------------------------------- overlay and command line
def overlay(result, path, title=""):
    """photo in frame | labels over the photo with the descriptor rows drawn | plain labels with the legend."""
    from PIL import Image, ImageDraw
    photo = result["_photo_in_frame"]; lab = result["labels"]; o = result["outfit"]
    col = COLOURS[lab]; mix = np.where((lab > 0)[..., None], (0.45 * photo + 0.55 * col).astype(np.uint8), (photo * 0.6).astype(np.uint8))
    edge = cv2.morphologyEx((result["mask_960x720"] > 0).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    a = photo.copy(); a[edge] = (255, 0, 160)
    mix[edge] = (255, 255, 255)
    unc = result.get("uncertain")
    plain = np.where((lab > 0)[..., None], col, 25).astype(np.uint8)
    if unc is not None and unc.any():                       # white hatching = parser saw background here, label is a fill-in
        yy, xx = np.indices(lab.shape); hatch = unc & ((yy + xx) % 6 < 2)
        mix[hatch] = (255, 255, 255); plain[hatch] = (255, 255, 255)
    sheet = Image.fromarray(np.hstack([a, mix, plain]))
    dr = ImageDraw.Draw(sheet); W = PP.OUT_W

    def line(y, text, colour, x0=W, x1=2 * W):
        if y is None:
            return
        dr.line([(x0, y), (x1, y)], fill=colour, width=1); dr.text((x0 + 4, y - 11), text, fill=colour)
    line(o["shoulder_row"], "shoulder", (255, 255, 255)); line(o["crotch_row"], "crotch", (255, 255, 255))
    line(o["top_hem_row"], f"top hem ({o['top_type']})" + (" [from front]" if "front view (" in str(o.get("top_hem_from")) else ""), (120, 200, 255), W + 200)
    for k, v in o["arms"].items():
        x0 = W if k in ("left", "near") else W + 480
        line(v.get("sleeve_end_row"), f"sleeve end {k}, bare {v['bare_frac']}", (255, 110, 110), x0, x0 + 240)
    for k, v in o["legs"].items():
        x0 = W if k in ("left", "both") else W + 480
        line(v.get("trouser_end_row"), f"trouser end {k}", (90, 255, 160), x0, x0 + 240)
        line(v.get("footwear_top_row"), "footwear top", (240, 240, 60), x0 + 60, x0 + 240)
    for i, n in enumerate(LABELS[1:] + ["hatched: parser unsure"], 1):
        dr.rectangle([2 * W + 8, 8 + 16 * (i - 1), 2 * W + 20, 20 + 16 * (i - 1)], fill=tuple(int(c) for c in COLOURS[i]) if i < len(LABELS) else (255, 255, 255)); dr.text((2 * W + 26, 8 + 16 * (i - 1)), n, fill=(255, 255, 255))
    dr.text((8, 8), f"{title}  {o['view']}  top={o['top_type']}  lower={o['lower_type']}  shoes={o['shoe_present']}  {result['seconds']['total']} s", fill=(255, 255, 0))
    sheet.save(path)


def _selftest():
    """The torch network here against the model's published ONNX export, on a real crop."""
    import onnxruntime as ort
    net = load_parser(); rgb = PP.load_photo(str(HERE / "revan" / "up_2117.jpg"))
    x = cv2.resize(rgb, (512, 512)); t = torch.from_numpy(x).permute(2, 0, 1).float().div(255)
    t = ((t - torch.tensor([0.485, 0.456, 0.406])[:, None, None]) / torch.tensor([0.229, 0.224, 0.225])[:, None, None])[None]
    with torch.no_grad():
        a = net(t).numpy()
    so = ort.SessionOptions(); so.intra_op_num_threads = 1
    sess = ort.InferenceSession(str(WEIGHTS.parent / "model.onnx"), so, providers=["CPUExecutionProvider"])
    b = sess.run(None, {sess.get_inputs()[0].name: t.numpy()})[0]
    print("torch", a.shape, "onnx", b.shape, "largest logit difference", float(np.abs(a - b).max()), "label agreement", float((a.argmax(1) == b.argmax(1)).mean()))


def _json(o):
    return json.dumps(o, indent=1, default=lambda v: v.item() if hasattr(v, "item") else str(v))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        _selftest(); sys.exit()
    if len(sys.argv) < 3 or sys.argv[1] not in ("check", "pair"):
        sys.exit(__doc__)
    args = sys.argv[2:]; height = None
    if "--height" in args:
        i = args.index("--height"); height = float(args[i + 1]); del args[i:i + 2]
    models = (PP.load_segmenter(), load_parser()); allout = {}; jobs = []
    if sys.argv[1] == "pair":
        (nf, pf), (ns, ps) = (a.split("=", 1) for a in args[:2])
        pr = parse_pair(pf, ps, height, models, keep_debug=True); jobs = [(nf, "front", pr["front"]), (ns, "side", pr["side"])]
    else:
        for spec in args:
            name, rest = spec.split("=", 1); path, view = rest.rsplit(":", 1)
            jobs.append((name, view, parse(path, view, height, models, keep_debug=True)))
    for name, view, r in jobs:
        dest = Path.home() / "Downloads" / f"parse_check_{name}.png"
        if r["labels"] is None:
            print(name, "no person found"); continue
        overlay(r, dest, name)
        np.save(HERE / "revan" / f"parse_{name}_labels.npy", r["labels"]) if os.environ.get("PARSE_SAVE") else None
        o = dict(r["outfit"]); o["seconds"] = r["seconds"]; o["check"] = r["check"]["reason"]
        if height and view == "front":
            o["bare_widths"] = bare_widths(r, height)
        allout[name] = o
        print(f"=== {name} ({view}) -> {dest}\n{_json(o)}", flush=True)
    if os.environ.get("PARSE_JSON"):
        Path(os.environ["PARSE_JSON"]).write_text(_json(allout))
