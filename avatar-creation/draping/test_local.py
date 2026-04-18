"""
Local test script for the cloth draping service.
Tests the handler without RunPod, using local file:// URLs.

Usage:
    python test_local.py --body-obj /path/to/body_tpose.obj --garment-obj /path/to/garment.obj
    python test_local.py --help
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from handler import handler


def main():
    parser = argparse.ArgumentParser(description="Test cloth draping locally")
    parser.add_argument("--body-obj", required=True, help="Body T-pose OBJ file")
    parser.add_argument("--garment-obj", required=True, help="Garment OBJ file")
    parser.add_argument("--smpl-params", default=None, help="SMPL params .npz file")
    parser.add_argument("--mode", default="swift", choices=["swift", "quality"])
    parser.add_argument("--output-dir", default="./test_output", help="Output directory")
    parser.add_argument("--fabric-preset", default=None,
                        help="Fabric preset name from default_fabric.json")
    args = parser.parse_args()

    body_path = Path(args.body_obj).resolve()
    garment_path = Path(args.garment_obj).resolve()

    if not body_path.exists():
        print(f"Error: Body OBJ not found: {body_path}")
        sys.exit(1)
    if not garment_path.exists():
        print(f"Error: Garment OBJ not found: {garment_path}")
        sys.exit(1)

    fabric_config = {}
    if args.fabric_preset:
        fabric_cfg_path = Path(__file__).parent / "configs" / "default_fabric.json"
        if fabric_cfg_path.exists():
            with open(fabric_cfg_path) as f:
                presets = json.load(f).get("presets", {})
            if args.fabric_preset in presets:
                fabric_config = presets[args.fabric_preset]
                print(f"Using fabric preset: {args.fabric_preset}")
            else:
                print(f"Warning: preset '{args.fabric_preset}' not found. Available: {list(presets.keys())}")

    event = {
        "input": {
            "body_obj_url": f"file://{body_path}",
            "garment_obj_url": f"file://{garment_path}",
            "smpl_params_url": f"file://{Path(args.smpl_params).resolve()}" if args.smpl_params else None,
            "fabric_config": fabric_config,
            "simulation_mode": args.mode,
            "garment_id": "test-garment",
            "size": "m",
            "user_id": "test-local",
        }
    }

    print(f"\n{'='*60}")
    print("Cloth Draping Local Test")
    print(f"{'='*60}")
    print(f"  Body:    {body_path.name} ({body_path.stat().st_size / 1024:.0f} KB)")
    print(f"  Garment: {garment_path.name} ({garment_path.stat().st_size / 1024:.0f} KB)")
    print(f"  Mode:    {args.mode}")
    print(f"{'='*60}\n")

    result = handler(event)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if result.get("success"):
        print(f"\n{'='*60}")
        print(f"  SUCCESS — {result['simulation_method']}")
        print(f"  Vertices:    {result['vertex_count']}")
        print(f"  OBJ size:    {result['obj_size_bytes'] / 1024:.1f} KB")
        print(f"  GLB size:    {result['glb_size_bytes'] / 1024:.1f} KB")
        print(f"  Time:        {result['processing_time_seconds']}s")
        print(f"{'='*60}")

        if result.get("draped_obj_base64"):
            obj_out = out_dir / "draped.obj"
            obj_out.write_bytes(base64.b64decode(result["draped_obj_base64"]))
            print(f"  Saved: {obj_out}")

        if result.get("draped_glb_base64"):
            glb_out = out_dir / "draped.glb"
            glb_out.write_bytes(base64.b64decode(result["draped_glb_base64"]))
            print(f"  Saved: {glb_out}")

        meta_out = out_dir / "result.json"
        safe = {k: v for k, v in result.items() if not k.endswith("_base64")}
        meta_out.write_text(json.dumps(safe, indent=2))
        print(f"  Saved: {meta_out}")
    else:
        print(f"\n  FAILED: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
