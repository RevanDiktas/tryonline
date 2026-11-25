"""Street pipeline for the worker: photo bytes -> 14 measurements, the same steps as
.local_prototype/measure_ml/measure_street.py (written by hand; the numeric parts live in the generated street_model.py).

    photo  -> parse_photos.parse          person outline (preprocess.py, DeepLabV3) + clothing label map (SegFormer)
    pair   -> parse_photos.reconcile_side the side view takes garment types and hem from the front
           -> street_model.pack           row widths, cloth-edge flags
           -> limbfeat.from_labels        bare-limb widths of the front view
           -> street_model.features       part locator profiles (zeros when it cannot read the outline)
    pairs  -> every network in weights/street_models.json, averaged over networks; pairs averaged
           -> optional typed sizes (weights/stage2_sizes.npz)
           -> street_model.to_tape        chest, waist, hip, thigh re-anchored on how a tape measures them
Front i goes with side i; the last side is reused when there are fewer sides.

The model file names are read from weights/street_models.json and nowhere else. To change them run
`.local_prototype/measure_ml/make_street_worker.py <version> a.pt b.pt ...`, which copies the files and rewrites that json.
"""
import copy
import hashlib
import json
from pathlib import Path

import numpy as np

CLOTH_LABELS = (8, 9, 11, 12)          # parse_photos labels: upper garment, lower garment, dress, accessory
FOUR = ("chest", "waist", "hip", "thigh")


class StreetPipeline:
    def __init__(self, weights_dir, parser_weights=None, segmenter=None):
        import torch
        from . import street_model as SM, parse_photos as PPH, limbfeat as LF
        self.SM, self.PPH, self.LF = SM, PPH, LF
        wd = Path(weights_dir); self.cfg = cfg = json.loads((wd / "street_models.json").read_text()); self.version = cfg["version"]
        if list(cfg["measurements"]) != list(SM.MEASUREMENTS):
            raise RuntimeError("weights/street_models.json lists other measurements than street_model.py")
        self.measurements = list(SM.MEASUREMENTS); self.mismatch = []

        def checked(entry):
            p = wd / entry["file"]
            if not p.exists():
                raise FileNotFoundError(f"{p} is listed in street_models.json but is not in weights/")
            if hashlib.sha256(p.read_bytes()).hexdigest() != entry["sha256"]:
                self.mismatch.append(entry["file"])
            return p

        self.models = []
        for e in cfg["models"]:
            ck = torch.load(checked(e), map_location="cpu", weights_only=False); st = ck["state"]
            kind = "both" if any(k.startswith("seq.") for k in st) else "seq"
            if kind != e["kind"] or str(ck.get("data", "street4")) != "street4":
                raise RuntimeError(f"{e['file']}: not the kind of network the sidecar says (street4 '{e['kind']}')")
            net = (SM.make_both if kind == "both" else SM.make_seq)(int(ck["n_meta"]), len(self.measurements), int(ck["options"].get("swidth", 64)))
            net.load_state_dict(st)
            self.models.append((e["file"], {"kind": kind, "net": net.eval(), "coef": ck["coef"], "rstd": ck["rstd"], "n_meta": int(ck["n_meta"])}))
        if not self.models:
            raise RuntimeError("street_models.json lists no models")
        SM.TAPE_PRIOR = checked(cfg["tape_prior"]); np.load(SM.TAPE_PRIOR)["C"]
        z = np.load(checked(cfg["stage2_sizes"]))
        if [str(x) for x in z["measurements"]] != self.measurements:
            raise RuntimeError("stage2_sizes.npz was fitted for a different measurement list")
        self.stage2 = {k: z[k] for k in ("trouser_waist", "chest_size", "waist_and_chest")}
        self.parser_weights = Path(parser_weights) if parser_weights else PPH.WEIGHTS
        if not self.parser_weights.exists():
            raise FileNotFoundError(f"clothing parser weights not found: {self.parser_weights} (the Dockerfile downloads them; locally set MEASURE_PARSER_WEIGHTS)")
        self._segmenter = segmenter; self._nets = None

    # ---------------------------------------------------------------- photos
    def nets(self):
        if self._nets is None:
            seg = self._segmenter() if callable(self._segmenter) else (self._segmenter or self.PPH.PP.load_segmenter())
            self._nets = (seg, self.PPH.load_parser(self.parser_weights))
        return self._nets

    def parse(self, photo_bytes, view, height_cm, fast=False):
        """One photo -> what parse_photos.parse returns (labels, mask_960x720, check, outfit, seconds)."""
        return self.PPH.parse(photo_bytes, view, height_cm, self.nets(), self.PPH.FAST_PASSES if fast else None)

    def pair_features(self, front, side, height_cm):
        """Two parse() results -> model inputs for one front/side pair, or (None, why)."""
        SM = self.SM
        if front["labels"] is None or side["labels"] is None:
            return None, "no person found"
        pr = self.PPH.reconcile_side(front, copy.deepcopy(side))            # a side photo reused for a second front must not carry the first front's hem
        fm, sm = pr["front"]["mask_960x720"] > 127, pr["side"]["mask_960x720"] > 127
        cf, cs = np.isin(pr["front"]["labels"], CLOTH_LABELS), np.isin(pr["side"]["labels"], CLOTH_LABELS)
        rows, cover, _small = SM.pack(fm, sm, cf, cs, height_cm)
        if not rows.reshape(-1)[: len(rows.reshape(-1)) // 6].max() > 0:
            return None, "the outline gave no row widths"
        limb = self.LF.from_labels(pr["front"]["labels"], "front", height_cm)[0]
        try:
            q = SM.features(fm, sm, height_cm)
        except Exception:  # noqa: BLE001  the locator is optional input: measure_street.py does the same
            q = None
        located = q is not None
        if q is None:
            q = (np.zeros(SM.N_PROFILE, np.float32), np.full(len(SM.SCALARS), -1, np.float32))
        return {"rows": rows, "cover": cover, "limb": limb, "prof": q[0], "sca": q[1], "located": located,
                "outfit": {k: pr["front"]["outfit"].get(k) for k in ("top_type", "lower_type", "top_hem_frac", "trouser_end_frac", "shoe_present")}}, None

    # ---------------------------------------------------------------- numbers
    def predict(self, feats, male, height_cm, weight_kg, trouser_waist_cm=None, chest_size_cm=None):
        """feats: list of pair_features() dicts. Returns arrays over the 14 measurements, in cm:
        tape (final, tape definition), photo_tape (before typed sizes), model (training definition), base_tape
        (height + weight + gender only, tape definition), spread (sd between pairs), per_model {file: tape definition}."""
        SM = self.SM; n = len(feats); g = lambda k: np.stack([f[k] for f in feats])
        p = {"rows": g("rows"), "cover": g("cover"), "limb": g("limb"), "prof": g("prof"), "sca": g("sca"),
             "male": np.full(n, float(male)), "h": np.full(n, float(height_cm)), "w": np.full(n, float(weight_kg))}
        per, per_tape, base = {}, {}, None
        for name, m in self.models:
            pred, b = SM.predict(m, p); per[name] = pred; per_tape[name] = SM.to_tape(pred, b, p); base = b if base is None else base
        pred = np.mean(list(per.values()), 0); photo_tape = np.mean(list(per_tape.values()), 0); tape = photo_tape; typed = None
        if trouser_waist_cm is not None or chest_size_cm is not None:
            typed, pred = self._typed(pred, base, p, trouser_waist_cm, chest_size_cm); tape = SM.to_tape(pred, base, p)
        return {"tape": tape.mean(0), "photo_tape": photo_tape.mean(0), "model": pred.mean(0), "base_tape": SM.to_tape(base, base, p).mean(0),
                "spread": tape.std(0) if n > 1 else np.zeros(len(self.measurements)), "per_model": {k: v.mean(0) for k, v in per_tape.items()}, "typed": typed}

    def _typed(self, pred, base, p, waist, chest):
        """measure_street.apply_typed: the typed tape value is moved into the training definition (typed - tape-definition
        height+weight estimate + training-definition height+weight estimate), then corrected = prediction + X @ W with
        X = [prediction - height+weight estimate (14), typed - predicted column(s), 1], per person (pairs averaged)."""
        SM = self.SM; M = self.measurements; jw, jc = M.index("waist"), M.index("chest")
        f, b = pred.mean(0), base.mean(0); tp = SM.tape_prior(p["male"][:1], p["h"][:1], p["w"][:1])[0]              # chest, waist, hip, thigh
        cols = []
        if waist is not None: cols.append(waist - tp[1] + b[jw] - f[jw])
        if chest is not None: cols.append(chest - tp[0] + b[jc] - f[jc])
        key = "waist_and_chest" if len(cols) == 2 else ("trouser_waist" if waist is not None else "chest_size")
        W = self.stage2[key]; x = np.r_[f - b, cols, 1.0]
        if W.shape != (len(x), len(M)):
            raise RuntimeError(f"stage2_sizes.npz[{key}] has shape {W.shape}, expected {(len(x), len(M))}")
        shift = x @ W
        return {"matrix": key, "shift_cm": {k: round(float(s), 2) for k, s in zip(M, shift)}}, pred + shift[None]
