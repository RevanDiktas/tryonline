# TryOn MVP Pipeline - Folder Structure

```
mvp_pipeline/
├── docs/
│   ├── strategy/                    # Business & architecture docs
│   │   ├── MVP_LAUNCH_ROADMAP_JAN2026.md
│   │   ├── B2B_IMPLEMENTATION_GUIDE.md
│   │   ├── UNICORN_ROADMAP_1B.md
│   │   ├── SHOPIFY_DEPLOYMENT_STRATEGY.md
│   │   └── DEPLOYMENT_ARCHITECTURE.md
│   ├── FOLDER_STRUCTURE.md          # This file
│   ├── TESTING_GUIDE.md             # How to test each component
│   └── DEPLOYMENT_GUIDE.md          # How to deploy to production
│
├── avatar-creation/                 # Avatar pipeline (from main branch)
│   ├── pipelines/
│   │   └── run_4d_humans_only.sh    # Main avatar creation script
│   ├── utilities/
│   │   └── fix_pose_neutral.py      # A-pose conversion
│   ├── 4D-Humans-clean/
│   │   ├── hmr2/                    # HMR2 model code
│   │   ├── demo_yolo.py             # YOLO + HMR2 inference
│   │   └── data/                    # SMPL model files
│   ├── combine_avatar_pants_tshirt_glb.py  # GLB combination script
│   └── requirements.txt
│
├── avatar-creation-measurements/    # Measurement extraction (from body branch)
│   ├── measure.py                   # Main measurement script
│   ├── measurement_definitions.py   # Body measurement definitions
│   ├── joint_definitions.py         # SMPL joint positions
│   ├── landmark_definitions.py      # Body landmarks
│   ├── image_processor.py           # Image utilities
│   ├── utils.py                     # Helper functions
│   └── data/                        # Reference data
│
├── backend/                         # FastAPI backend (TO CREATE)
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry
│   │   ├── routers/
│   │   │   ├── avatars.py           # Avatar creation endpoints
│   │   │   ├── garments.py          # Garment management
│   │   │   ├── tryon.py             # Try-on session endpoints
│   │   │   └── analytics.py         # Brand dashboard data
│   │   ├── models/                  # Pydantic models
│   │   ├── services/
│   │   │   ├── avatar_service.py    # Orchestrates GPU jobs
│   │   │   ├── measurement_service.py
│   │   │   └── fit_service.py       # Size recommendations
│   │   └── db/
│   │       └── supabase.py          # Supabase client
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                        # Next.js frontend (TO CREATE)
│   ├── app/
│   │   ├── page.tsx                 # Landing page
│   │   ├── tryon/
│   │   │   └── [sessionId]/page.tsx # Try-on viewer page
│   │   ├── dashboard/               # Brand analytics dashboard
│   │   └── api/                     # Next.js API routes
│   ├── components/
│   │   ├── TryOnViewer.tsx          # Three.js 3D viewer
│   │   ├── PhotoUpload.tsx          # Avatar creation flow
│   │   ├── SizeSelector.tsx         # Size switching UI
│   │   └── FitIndicator.tsx         # "Too tight / Recommended / Loose"
│   ├── lib/
│   │   └── three/
│   │       └── BodyMasking.ts       # Body masking shader
│   ├── package.json
│   └── next.config.js
│
├── garments/                        # CLO3D garment exports (TO CREATE)
│   ├── brand_pilot/
│   │   ├── tshirt_basic/
│   │   │   ├── XS.glb
│   │   │   ├── S.glb
│   │   │   ├── M.glb
│   │   │   ├── L.glb
│   │   │   └── XL.glb
│   │   └── pants_slim/
│   │       ├── XS.glb
│   │       └── ...
│   └── size_charts/
│       └── brand_pilot.json         # Size chart with measurements
│
├── shopify/                         # Shopify integration (TO CREATE)
│   ├── theme-extension/
│   │   └── blocks/
│   │       └── tryon-button.liquid  # "Try On" button block
│   └── webhooks/
│       └── order_created.py         # Purchase attribution
│
└── gpu-worker/                      # RunPod/Modal worker (TO CREATE)
    ├── handler.py                   # Serverless handler
    ├── Dockerfile
    └── requirements.txt
```

## Key Folders Explained

### `avatar-creation/`
Contains the 4D Humans pipeline for creating SMPL avatars from photos.
- **Input**: User photo (JPG/PNG)
- **Output**: `body_person0_params.npz` (SMPL params), `body_person0_neutral.obj` (A-pose mesh)

### `avatar-creation-measurements/`
Contains measurement extraction code from SMPL parameters.
- **Input**: SMPL betas (shape parameters)
- **Output**: JSON with chest, waist, hips, inseam, etc. in cm

### `backend/`
FastAPI service that orchestrates everything:
- Receives photo uploads
- Dispatches GPU jobs to RunPod
- Stores results in Supabase
- Serves API for frontend

### `frontend/`
Next.js app with:
- TryOn platform website (tryon.com)
- Three.js viewer for avatar + garment rendering
- Embeddable iframe for Shopify stores

### `garments/`
CLO3D-exported garment GLBs, organized by brand and size.
Size charts stored as JSON for fit logic.

### `shopify/`
Minimal Shopify integration:
- Theme extension for "Try On" button
- Webhook handler for purchase attribution
