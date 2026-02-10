# Avatar TryOn Viewer — Root Cause & Fix

## Problem
- Avatar appeared untextured (white/beige)
- T-shirt huge, avatar tiny (wrong mapping)
- All sizes wrong

## Root Causes

### 1. Material Override
- **TryOnViewer.tsx** (embed): Was replacing avatar material with solid skin color → stripped texture
- **prepareGarment**: Was mutating materials in place; now clones before setting DoubleSide

### 2. Renderer Settings
- Aggressive tone mapping / exposure could wash out textures → removed to match dashboard

### 3. Garment URLs
- Relative paths in DB not resolved → backend now constructs full Supabase storage URLs

### 4. Unit Mismatch
- Avatar (meters) vs garment (mm) → scale avatar to match garment when ratio < 0.1

## Fixes Applied

### Backend
- `GET /api/avatar/{user_id}`: Always returns canonical GLB URL
- `GET /api/products/{id}/tryon-config`: Resolves relative garment paths to full Supabase URLs

### Frontend (test-viewer.html)
- Avatar: Fresh GLTFLoader per load, no material modification
- Garment: Clone materials before setting DoubleSide (preserves texture refs)
- Renderer: Removed tone mapping to match dashboard
- Unit correction: Scale avatar to match garment when height ratio < 0.1

### Frontend (TryOnViewer.tsx)
- AvatarModel: No longer replaces material — preserves texture
- GarmentModel: Clone material before setting DoubleSide

## Verification
1. Hard refresh (Cmd+Shift+R)
2. Restart backend
3. Console: `[TryOn] Loading avatar_textured.glb from: https://...`
4. Avatar should show skin texture; garment should fit
