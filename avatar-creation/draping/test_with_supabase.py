"""
Test draping handler against real user data from Supabase.

Downloads your actual body OBJ from Supabase Storage, pairs it with
a sample garment OBJ, and runs the geometric draping locally.

Usage:
    # Set env vars (or put in .env):
    export SUPABASE_URL="https://xxx.supabase.co"
    export SUPABASE_SERVICE_KEY="eyJ..."
    export TEST_USER_ID="your-uuid"

    python test_with_supabase.py

    # Or pass user_id as argument:
    python test_with_supabase.py --user-id "your-uuid"
"""

import os
import sys
import json
import base64
import argparse
import tempfile
from pathlib import Path

# Allow running from the draping directory
sys.path.insert(0, str(Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(description="Test draping with real Supabase data")
    parser.add_argument("--user-id", default=os.environ.get("TEST_USER_ID"), help="User UUID")
    parser.add_argument("--garment-obj", default=None, help="Local garment OBJ (skip if you just want to test body download)")
    parser.add_argument("--output-dir", default="./test_output", help="Output directory")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not supabase_url or not supabase_key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
        print("  export SUPABASE_URL='https://xxx.supabase.co'")
        print("  export SUPABASE_SERVICE_KEY='eyJ...'")
        sys.exit(1)

    if not args.user_id:
        print("ERROR: Provide --user-id or set TEST_USER_ID env var")
        sys.exit(1)

    try:
        from supabase import create_client
    except ImportError:
        print("Installing supabase client...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "supabase"])
        from supabase import create_client

    print(f"\n{'='*60}")
    print(f"  Draping Test — Real Supabase Data")
    print(f"{'='*60}")
    print(f"  User:     {args.user_id}")
    print(f"  Supabase: {supabase_url[:40]}...")
    print(f"{'='*60}\n")

    client = create_client(supabase_url, supabase_key)

    # 1. Fetch user's fit passport
    print("[1/5] Fetching fit passport...")
    r = client.table("fit_passports").select(
        "pipeline_files,avatar_url,chest,waist,hips,height,gender"
    ).eq("user_id", args.user_id).limit(1).execute()

    if not r.data:
        print(f"  ERROR: No fit passport found for user {args.user_id}")
        sys.exit(1)

    passport = r.data[0]
    pf = passport.get("pipeline_files") or {}
    print(f"  Height: {passport.get('height')}cm")
    print(f"  Chest:  {passport.get('chest')}cm")
    print(f"  Gender: {passport.get('gender')}")
    print(f"  Pipeline files: {list(pf.keys())}")

    body_obj_url = pf.get("tpose_mesh") or pf.get("apose_mesh") or pf.get("original_mesh")
    if not body_obj_url:
        print("  ERROR: No body OBJ found in pipeline_files")
        print(f"  Available keys: {list(pf.keys())}")
        sys.exit(1)

    # Resolve relative URL
    if not body_obj_url.startswith("http"):
        body_obj_url = f"{supabase_url.rstrip('/')}/storage/v1/object/public/{body_obj_url.lstrip('/')}"

    print(f"  Body OBJ URL: {body_obj_url[:80]}...")

    # 2. Download body OBJ
    print("\n[2/5] Downloading body OBJ...")
    import httpx
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    body_path = out_dir / "body.obj"
    with httpx.Client(timeout=60) as http:
        resp = http.get(body_obj_url)
        if resp.status_code != 200:
            print(f"  ERROR: Download failed (HTTP {resp.status_code})")
            print(f"  URL: {body_obj_url}")
            sys.exit(1)
        body_path.write_bytes(resp.content)
    print(f"  Downloaded: {body_path} ({body_path.stat().st_size / 1024:.1f} KB)")

    # 3. Check body OBJ is valid
    print("\n[3/5] Validating body OBJ...")
    from handler import load_obj_vertices
    body_verts = load_obj_vertices(body_path)
    print(f"  Vertices: {len(body_verts)}")
    if len(body_verts) == 0:
        print("  ERROR: Body OBJ has 0 vertices — file may be corrupt or wrong format")
        sys.exit(1)
    print(f"  Bounds Y: {body_verts[:, 1].min():.4f} to {body_verts[:, 1].max():.4f}")
    print(f"  Body OBJ is valid!")

    # 4. Run geometric drape if garment OBJ provided
    if args.garment_obj:
        garment_path = Path(args.garment_obj)
        if not garment_path.exists():
            print(f"\n  ERROR: Garment OBJ not found: {garment_path}")
            sys.exit(1)

        print(f"\n[4/5] Running geometric drape...")
        print(f"  Garment: {garment_path} ({garment_path.stat().st_size / 1024:.1f} KB)")

        from handler import handler
        result = handler({
            "input": {
                "body_obj_url": f"file://{body_path.resolve()}",
                "garment_obj_url": f"file://{garment_path.resolve()}",
                "simulation_mode": "swift",
                "garment_id": "test",
                "size": "m",
                "user_id": args.user_id,
            }
        })

        if result.get("success"):
            print(f"\n[5/5] Results:")
            print(f"  Method:     {result['simulation_method']}")
            print(f"  Vertices:   {result['vertex_count']}")
            print(f"  OBJ size:   {result['obj_size_bytes'] / 1024:.1f} KB")
            print(f"  GLB size:   {result['glb_size_bytes'] / 1024:.1f} KB")
            print(f"  Time:       {result['processing_time_seconds']}s")

            if result.get("draped_glb_base64"):
                glb_out = out_dir / "draped.glb"
                glb_out.write_bytes(base64.b64decode(result["draped_glb_base64"]))
                print(f"\n  Saved GLB:  {glb_out}")

            if result.get("draped_obj_base64"):
                obj_out = out_dir / "draped.obj"
                obj_out.write_bytes(base64.b64decode(result["draped_obj_base64"]))
                print(f"  Saved OBJ:  {obj_out}")

            print(f"\n  SUCCESS — open {out_dir}/draped.glb in a 3D viewer to verify")
        else:
            print(f"\n  FAILED: {result.get('error')}")
            sys.exit(1)
    else:
        print(f"\n[4/5] Skipping drape (no --garment-obj provided)")
        print(f"  Body OBJ downloaded and validated successfully.")
        print(f"  To run full drape test:")
        print(f"    python test_with_supabase.py --user-id {args.user_id} --garment-obj /path/to/garment.obj")

    print(f"\n{'='*60}")
    print(f"  Test complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
