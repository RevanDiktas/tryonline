"""The silhouette model: front mask + optional side mask + height + weight + gender -> 14 BodyM measurements.

Copied from .local_prototype/measure_ml/cnn_bodym_v2.py (Net, Encoder, meta) so this folder builds on its
own. Keep the two in step: a checkpoint only loads into the architecture it was trained with.

Checkpoint (torch.save): {"state", "coef" [10 x 14], "rstd" [14], "measurements" [14 names], "img" [160, 120]}
    prediction = [meta, 1] @ coef  +  net(front, side, has_side, meta) * rstd
The first term is the height + weight + gender regression; the network adds what the photo shows.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image


def meta(male, h, w):
    """9 features from gender (1 = male, 0 = female), height in cm, weight in kg. Arrays of equal length."""
    male, h, w = (np.asarray(x, dtype=np.float64) for x in (male, h, w))
    bmi = w / (h / 100) ** 2
    return np.stack([male, (h - 170) / 10, (w - 75) / 15, (bmi - 25) / 5, male * (h - 170) / 10, male * (w - 75) / 15,
                     ((h - 170) / 10) ** 2, ((w - 75) / 15) ** 2, (h - 170) / 10 * (w - 75) / 15], 1).astype(np.float32)


class Encoder(nn.Module):
    def __init__(self, out=192):
        super().__init__()
        chans, layers, c_in = [24, 48, 96, 144, out], [], 1
        for c in chans:
            layers += [nn.Conv2d(c_in, c, 3, stride=2, padding=1, bias=False), nn.BatchNorm2d(c), nn.ReLU(inplace=True),
                       nn.Conv2d(c, c, 3, padding=1, bias=False), nn.BatchNorm2d(c), nn.ReLU(inplace=True)]
            c_in = c
        self.net = nn.Sequential(*layers)
        self.head = nn.Linear(out * 5, out)          # pool over width only: where on the body a width sits is kept

    def forward(self, x):
        f = self.net(x)                               # B, C, 5, 4
        return F.relu(self.head(f.mean(3).flatten(1)))


class Net(nn.Module):
    def __init__(self, n_meta, n_out):
        super().__init__()
        self.front, self.side = Encoder(), Encoder()
        self.mlp = nn.Sequential(nn.Linear(192 * 2 + n_meta + 1, 256), nn.ReLU(inplace=True), nn.Dropout(0.1), nn.Linear(256, n_out))

    def forward(self, front, side, has_side, m):
        fs = self.side(side) * has_side[:, None]
        return self.mlp(torch.cat([self.front(front), fs, m, has_side[:, None]], 1))


def _frame_bbox(a, out_h, out_w, fill=0.90):
    """Copy of frame_mask() in cnn_bodym.py. a: bool HxW. Returns uint8 out_h x out_w."""
    rows = np.flatnonzero(a.sum(1) >= 3)
    cols = np.flatnonzero(a.sum(0) >= 3)
    if len(rows) < 50 or len(cols) < 10:
        return np.zeros((out_h, out_w), np.uint8)
    top, bot, left, right = rows[0], rows[-1], cols[0], cols[-1]
    hp = bot - top + 1
    scale = fill * out_h / hp
    crop = Image.fromarray((a[top:bot + 1, left:right + 1] * 255).astype(np.uint8))
    nw, nh = max(1, round(crop.width * scale)), max(1, round(hp * scale))
    crop = crop.resize((nw, nh), Image.BILINEAR)
    canvas = Image.new("L", (out_w, out_h), 0)
    canvas.paste(crop, ((out_w - nw) // 2, (out_h - nh) // 2))
    return np.asarray(canvas)


class SilhouetteModel:
    """A loaded checkpoint. predict() takes framed 960 x 720 masks (uint8 0/255) and returns cm."""

    def __init__(self, checkpoint_path, device="cpu"):
        p = Path(checkpoint_path)
        ck = torch.load(p, map_location="cpu")
        self.measurements = list(ck["measurements"])
        self.img_h, self.img_w = (int(v) for v in ck["img"])
        self.coef = np.asarray(ck["coef"], dtype=np.float64)          # [n_meta + 1, n_out]
        self.rstd = np.asarray(ck["rstd"], dtype=np.float64)          # [n_out]
        self.net = Net(self.coef.shape[0] - 1, len(self.measurements))
        self.net.load_state_dict(ck["state"])
        self.net.eval().to(device)
        self.device = device
        self.sha256 = hashlib.sha256(p.read_bytes()).hexdigest()
        side = p.with_suffix(".json")
        self.info = json.loads(side.read_text()) if side.exists() else {}
        self.version = self.info.get("version", "unknown") + "@" + self.sha256[:12]
        self.sidecar_matches = self.info.get("sha256") in (None, self.sha256)

    def _image(self, mask):
        """960 x 720 framed mask -> 1 x 160 x 120 float 0..1, exactly as in training (PIL bilinear).

        The sidecar's "framing" says how the checkpoint was trained: "bbox" (cnn_bodym.py: crop to the
        person, person height = 90% of the frame, centred) or "native" (cnn_bodym_v2.py: plain downscale).
        """
        a = np.asarray(mask, dtype=np.uint8)
        if self.info.get("framing", "native") == "bbox":
            return torch.from_numpy(_frame_bbox(a > 127, self.img_h, self.img_w).astype(np.float32) / 255.0)[None]
        small = Image.fromarray(a).resize((self.img_w, self.img_h), Image.BILINEAR)
        return torch.from_numpy(np.asarray(small, dtype=np.float32) / 255.0)[None]

    def prior(self, male, height_cm, weight_kg):
        """Height + weight + gender only: dict name -> cm."""
        m = meta([male], [height_cm], [weight_kg])
        return dict(zip(self.measurements, (np.c_[m, np.ones(1)] @ self.coef)[0].tolist()))

    def predict(self, front_masks, side_masks, male, height_cm, weight_kg):
        """Mean prediction over every accepted front shot (paired with every accepted side shot when
        there are any). Returns dict name -> cm."""
        fronts = [self._image(f) for f in front_masks]
        if not fronts:
            raise ValueError("at least one front mask is needed")
        sides = [self._image(s) for s in side_masks]
        pairs = [(f, s) for f in fronts for s in sides] if sides else [(f, torch.zeros_like(f)) for f in fronts]
        n = len(pairs)
        m = meta([male] * n, [height_cm] * n, [weight_kg] * n)
        with torch.no_grad():
            out = self.net(torch.stack([p[0] for p in pairs]).to(self.device), torch.stack([p[1] for p in pairs]).to(self.device),
                           torch.full((n,), 1.0 if sides else 0.0, device=self.device), torch.from_numpy(m).to(self.device)).cpu().numpy()
        pred = np.c_[m, np.ones(n)] @ self.coef + out.astype(np.float64) * self.rstd
        return dict(zip(self.measurements, pred.mean(0).tolist()))
