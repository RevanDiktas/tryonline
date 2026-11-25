#!/usr/bin/env python3
"""Run the REAL handler on this machine before any build (the runpod-handler-rigor rule).

Imports handler.py from the folder above (not a copy) and calls handler(event) the way RunPod would,
with local photo paths. Model files are read from where they already are on this disk; nothing is
downloaded except what torchvision would fetch if the DeepLab weights are not cached.

    python scripts/local_invoke.py --front /path/full_body.jpg --refuse /path/mirror_selfie.jpg \
        [--side /path/side.jpg] [--height 192 --weight 83 --gender male] [--out result.json]

Street pipeline (front + side, weights/street_models.json), compared with a measure_street.py result:

    python scripts/local_invoke.py --street --front f1.HEIC f2.HEIC --side s1.HEIC s2.HEIC --height 192 --weight 85 --gender male \
        --expect ../.local_prototype/measure_ml/street_test/revan_heic_avg3.json [--trouser-waist 89 --chest-size 110] [--tape tape.json]

It exits with an error when any measurement differs from --expect by more than 0.1 cm. One CPU thread unless
MEASURE_LOCAL_THREADS is set (other jobs share this laptop).

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
THREADS = os.environ.get("MEASURE_LOCAL_THREADS", "1")
os.environ.setdefault("PARSE_THREADS", THREADS)
if not (ROOT / "weights" / "segformer_b2_clothes.safetensors").exists():           # the Dockerfile downloads it; locally use the prototype's copy
    os.environ.setdefault("MEASURE_PARSER_WEIGHTS", str(PROTO / "measure_ml" / "seg_models" / "segformer_b2_clothes" / "model.safetensors"))
sys.path.insert(0, str(ROOT))
import handler as H  # noqa: E402

BACK = {v: k for k, v in H.KEYS.items()}            # API key -> the training code's name


def trim(o):
    """The same structure with long strings cut, so the output can be read and pasted."""
    if isinstance(o, dict): return {k: trim(v) for k, v in o.items()}
    if isinstance(o, list): return [trim(v) for v in o]
    if isinstance(o, str) and len(o) > 200: return f"{o[:40]}... ({len(o)} chars)"
    return o


def street(a):
    """The street pipeline through the real handler, beside a measure_street.py result and (optionally) a tape."""
    import torch
    torch.set_num_threads(int(THREADS))
    inp = {"front_url": a.front[0], "front_extra_urls": a.front[1:], "side_url": a.side[0], "side_extra_urls": a.side[1:],
           "height_cm": a.height, "weight_kg": a.weight, "gender": a.gender, "body": bool(a.body)}
    if a.trouser_waist is not None: inp["trouser_waist_cm"] = a.trouser_waist
    if a.chest_size is not None: inp["chest_size_cm"] = a.chest_size
    t = time.time(); out = H.handler({"input": inp}); dt = time.time() - t
    json.dumps(out)
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1))
    if "measurements" not in out or out.get("pipeline") != "street":
        print(json.dumps(trim(out), indent=1)); raise SystemExit("the street pipeline did not produce measurements")
    exp = json.load(open(a.expect)) if a.expect else {}; tape = json.load(open(a.tape)) if a.tape else {}
    for view in ("front", "side"):
        for i, c in enumerate(out["checks"][view]):
            print(f"  {view} photo {i + 1}: check {'ok' if c['ok'] else 'FAILED (' + str(c['reason']) + ')'}, {'used' if c['used'] else 'NOT used'}")
    print(f"\nmodel {out['model_version']}, pairs {out['pairs_used']}, wall clock {dt:.0f} s, timings {out['timings']}")
    print(f"{'measurement':16s} {'handler':>8s}" + (f" {'runner':>8s} {'gap':>6s}" if exp else "") + (f" {'photo only':>10s}" if "measurements_photo_only" in out else "") + (f" {'tape':>7s} {'diff':>6s}" if tape else ""))
    worst = 0.0
    for key, v in out["measurements"].items():
        k = BACK.get(key, key)
        if key in out["extras_keys"] or key == "height":
            continue
        line = f"{key:16s} {v:8.1f}"
        if exp:
            e = exp[k]["tape_def"]; worst = max(worst, abs(v - e)); line += f" {e:8.1f} {v - e:+6.1f}"
        if "measurements_photo_only" in out: line += f" {out['measurements_photo_only'][key]:10.1f}"
        if tape: line += (f" {float(tape[k]):7.1f} {v - float(tape[k]):+6.1f}" if k in tape else "")
        print(line)
    for n in out["notes"]: print("note:", n)
    if exp:
        print(f"\nlargest gap between the handler and {Path(a.expect).name}: {worst:.2f} cm (allowed 0.1; both are rounded to 0.1)")
        if worst > 0.1 + 1e-6: raise SystemExit("MISMATCH: the worker does not reproduce the runner")
        print("OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--street", action="store_true", help="street pipeline run: several --front / --side photos, compared with --expect")
    ap.add_argument("--expect", help="json written by measure_street.py --out"); ap.add_argument("--tape")
    ap.add_argument("--trouser-waist", type=float); ap.add_argument("--chest-size", type=float); ap.add_argument("--body", action="store_true")
    if "--street" in sys.argv:
        ap.add_argument("--front", nargs="+", required=True); ap.add_argument("--side", nargs="+", required=True)
        ap.add_argument("--height", type=float, required=True); ap.add_argument("--weight", type=float, required=True); ap.add_argument("--gender", required=True); ap.add_argument("--out")
        return street(ap.parse_args())
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
