#!/usr/bin/env python3
"""Run the REAL handler on this machine before any build (the runpod-handler-rigor rule).

Imports handler.py from the folder above (not a copy) and calls handler(event) the way RunPod would,
with local photo paths. Model files are read from where they already are on this disk; nothing is
downloaded except what torchvision would fetch if the DeepLab weights are not cached.

    python scripts/local_invoke.py --front /path/full_body.jpg --refuse /path/mirror_selfie.jpg \
        [--side /path/side.jpg] [--height 192 --weight 83 --gender male] [--out result.json]

Paths to private photos are arguments on purpose: none are written into this repo.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROTO = ROOT.parent / ".local_prototype"

os.environ.setdefault("MEASURE_ALLOW_LOCAL_FILES", "1")
os.environ.setdefault("MEASURE_BUILD", "local")
if not (ROOT / "human_model_files" / "smplx").exists():
    os.environ.setdefault("MEASURE_HUMAN_MODELS", str(PROTO / "measure_models" / "human_model_files"))
if (PROTO / "measure_ml" / "seg_models" / "torch").exists():
    os.environ.setdefault("TORCH_HOME", str(PROTO / "measure_ml" / "seg_models" / "torch"))
sys.path.insert(0, str(ROOT))
import handler as H  # noqa: E402


def trim(o):
    """The same structure with long strings cut, so the output can be read and pasted."""
    if isinstance(o, dict): return {k: trim(v) for k, v in o.items()}
    if isinstance(o, list): return [trim(v) for v in o]
    if isinstance(o, str) and len(o) > 200: return f"{o[:40]}... ({len(o)} chars)"
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--front", required=True, help="a good full-body front photo")
    ap.add_argument("--refuse", help="a photo that should be refused (e.g. a mirror selfie)")
    ap.add_argument("--side"); ap.add_argument("--height", type=float, default=178); ap.add_argument("--weight", type=float, default=75)
    ap.add_argument("--gender", default="male"); ap.add_argument("--out")
    a = ap.parse_args()
    person = {"height_cm": a.height, "weight_kg": a.weight, "gender": a.gender}
    cases = [("ping", {"ping": True}),
             ("good front photo", {"front_url": a.front, **person, "front_pitch_deg": 2.0}),
             ("same photo three times (averaging path), neutral gender, no body", {"front_url": a.front, "front_extra_urls": ["file://" + a.front, a.front], **person, "gender": "neutral", "body": False}),
             ("missing weight", {"front_url": a.front, "height_cm": a.height, "gender": a.gender}),
             ("missing front_url", dict(person)),
             ("http(s)-only rule with local files off is covered by the handler; bad gender", {"front_url": a.front, **person, "gender": "other"}),
             ("unreadable photo", {"front_url": str(Path(__file__)), **person})]
    if a.refuse: cases.insert(2, ("photo that must be refused", {"front_url": a.refuse, **person}))
    if a.side: cases.insert(2, ("front + side", {"front_url": a.front, "side_url": a.side, **person}))
    if a.refuse: cases.append(("good front, refused photo as side -> falls back to front only", {"front_url": a.front, "side_url": a.refuse, **person, "body": False}))
    results = {}
    for name, inp in cases:
        t = time.time(); out = H.handler({"input": inp}); dt = time.time() - t
        json.dumps(out)                                   # must be JSON-serialisable, or RunPod cannot return it
        results[name] = out
        print(f"\n=== {name}  ({dt:.1f} s) ===\n" + json.dumps(trim(out), indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(results, indent=1)); print("\nfull results written to", a.out)


if __name__ == "__main__":
    main()
