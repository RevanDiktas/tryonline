#!/usr/bin/env python3
"""Decode a photoreal-endpoint job result into a tidy test_outputs/ run folder.

Usage:
    python decode_result.py <result.json> [--photo <url_or_path>]

<result.json> is the raw RunPod /status response (must contain
output.files_base64). Writes the 5 artifacts + result.json (base64 stripped)
into avatar-creation-photoreal/test_outputs/<build>__<gender>_h<h>__<jobid>/.
Prints the run folder path.
"""
import argparse
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

# test_outputs/ sits one level up from this script's dir (scripts/).
TEST_OUTPUTS = Path(__file__).resolve().parent.parent / "test_outputs"

FILE_KEY_TO_NAME = {
    "apose_mesh": "body_apose.obj",
    "tpose_mesh": "body_tpose.obj",
    "avatar_glb": "avatar_textured.glb",
    "skin_texture": "skin_texture.png",
    "smpl_params": "smpl_params.npz",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result_json")
    ap.add_argument("--photo", default=None, help="source photo url/path to copy in")
    args = ap.parse_args()

    d = json.loads(Path(args.result_json).read_text())
    out = d.get("output") or {}
    files_b64 = out.get("files_base64") or {}
    if not files_b64:
        print(f"ERROR: no output.files_base64 in {args.result_json} "
              f"(status={d.get('status')}, error={d.get('error') or out.get('error')})")
        return 1

    build = out.get("build", "unknown")
    gender = out.get("gender", "na")
    height = out.get("height_cm") or "na"
    jobid = (d.get("id") or "job")[:8]
    run_dir = TEST_OUTPUTS / f"{build}__{gender}_h{height}__{jobid}"
    run_dir.mkdir(parents=True, exist_ok=True)

    for key, b64 in files_b64.items():
        name = FILE_KEY_TO_NAME.get(key, f"{key}.bin")
        (run_dir / name).write_bytes(base64.b64decode(b64))

    # result.json without the bulky base64 blobs
    slim = dict(d)
    if "output" in slim and isinstance(slim["output"], dict):
        slim["output"] = {k: v for k, v in slim["output"].items() if k != "files_base64"}
    (run_dir / "result.json").write_text(json.dumps(slim, indent=2))

    photo = args.photo or out.get("photo_url")
    if photo:
        try:
            dst = run_dir / "input_photo.jpg"
            if photo.startswith(("http://", "https://")):
                urllib.request.urlretrieve(photo, dst)
            elif os.path.exists(photo):
                dst.write_bytes(Path(photo).read_bytes())
        except Exception as e:  # noqa: BLE001
            print(f"(could not fetch source photo: {e})")

    print(str(run_dir))
    for p in sorted(run_dir.iterdir()):
        print(f"  {p.stat().st_size:>9} bytes  {p.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
