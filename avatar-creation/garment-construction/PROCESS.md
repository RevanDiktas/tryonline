# Garment Construction — Process & Runbook

Branch: `feature/garment-construction`. New isolated RunPod serverless endpoint
(`tryonline-garment`, to be created). Does NOT touch tryonline / tryonline-lhm /
tryonline-drape. Full audit: `../../docs/research/GARMENT_PIPELINE_VERIFICATION_2026-05-31.md`.

## Files here
| File | Role |
|---|---|
| `Dockerfile.base` | BASE image: compiles all heavy deps (build once on GPU pod) |
| `build_base.sh` | build+push helper for the base image |
| `Dockerfile` | thin SERVERLESS image: FROM base + handler (fast build) |
| `handler.py` | the pipeline: STEP0 bootstrap -> 1 ChatGarment -> 2 GarmentCodeRC -> 3 texture -> upload |
| `BUILD_SPEC.md` | verified commands, dep pins, path patches, output contract |
| `REFERENCE_*.{py,sh}` | upstream source copies the handler is built against |
| `weights/` | gitignored; local mirror of the checkpoint download |

## Pipeline (verified)
```
photo(s) -> ChatGarment (LLaVA-7B, 2-step) -> GarmentCodeRC JSON
         -> run_garmentcode_sim.py (Warp XPBD drape on 'mean_all') -> garment OBJ+UV
         -> texture extraction -> {size}.obj + {size}.mtl + {size}_texture.png
         -> Supabase garments/{garment_id}/{size}/  -> hand to EXISTING drape svc
```

## Status (2026-05-31)
- [x] Research verified against primary sources (all 3 biansy000 repos real)
- [x] handler.py written (426 lines, compiles), grounded in REFERENCE_* source
- [x] Dockerfile.base + Dockerfile + build_base.sh written
- [~] Checkpoint downloading to weights/chatgarment/ (~14 GB, in progress)
- [ ] Mirror checkpoint to a bucket -> set CHATGARMENT_CKPT_URL
- [ ] Build base image on a GPU pod -> push to registry
- [ ] Build + deploy serverless image -> create endpoint
- [ ] Test one real garment end-to-end

## Runbook: build the BASE image (on a GPU pod, NOT the Mac)
1. RunPod -> GPU pod (A6000/L40S, "PyTorch 2.1" template, Docker enabled).
2. Clone repo (or scp this folder). `cd avatar-creation/garment-construction`.
3. `docker login`
4. `bash build_base.sh push`   # compiles Warp fork etc (~30-60 min, no cap on a pod)
   - Watch the build-sanity `RUN python -c "import warp ..."` line passes.
5. Confirm `revandiktas/tryon-garment-base:latest` is in the registry.

## Runbook: mirror the checkpoint
1. Local file: `weights/chatgarment/pytorch_model.bin` (~14 GB).
2. Upload to a bucket we control (Supabase or S3), get a plain-GET URL.
3. That URL -> endpoint env var `CHATGARMENT_CKPT_URL`.
   (Upstream SharePoint link is auth-gated; RunPod cannot fetch it directly.)

## Runbook: serverless deploy
1. Push `feature/garment-construction` -> RunPod GitHub auto-build of `Dockerfile`
   (thin, fast) OR `docker build -t revandiktas/tryon-garment:latest . && push`.
2. New Serverless Endpoint: image above, 48 GB GPU, min 0 / max 1-2, network
   volume mounted at the weights cache path so the 14 GB checkpoint persists.
3. Env vars: CHATGARMENT_CKPT_URL, SUPABASE_URL, SUPABASE_SERVICE_KEY,
   GARMENT_BUCKET=garments. Optional: LLAVA_BASE, VISION_TOWER.
4. Test event:
   {"input":{"image_urls":["https://.../garment_front.jpg"],
             "garment_id":"test001","size":"m"}}

## Open risks (flagged, not yet hit)
- STEP-1 exact run-folder mapping + `deepspeed` vs `python` launcher: confirm on
  first GPU run (handler scans for vis_new/all_json_spec_files.json to be robust).
- STEP-2 output OBJ name: handler greps *_sim.obj then any UV'd .obj.
- Texture v1 = flat dominant-colour fill; logo/print placement is v2.
- LICENSE: Warp fork + SMPL-X non-commercial — prototype only, replace before paid.
