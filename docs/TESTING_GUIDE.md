# TryOn MVP - Testing Guide

## Overview

Testing happens in layers, from local development to full integration.

---

## 1. Avatar Creation Pipeline (GPU Required)

### Test on Google Colab (Free)

```python
# Use the COLAB_BATTLE_TESTED.md guide in /Volumes/Expansion/persona/
# This runs 4D Humans and outputs SMPL params + mesh
```

### Test on RunPod (Production)

```bash
# Deploy the gpu-worker container
# Send a test image via API
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT/run \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"image_url": "https://example.com/test.jpg"}}'
```

### Expected Output
```
body_person0_params.npz  # Contains: betas, body_pose, global_orient
body_person0_neutral.obj # A-pose mesh (6890 vertices for SMPL)
```

### Verify SMPL Output
```python
import numpy as np
params = np.load('body_person0_params.npz')
print(f"Betas shape: {params['betas'].shape}")      # Should be (10,) or (16,)
print(f"Body pose shape: {params['body_pose'].shape}")  # Should be (69,) or (63,)
```

---

## 2. Measurement Extraction

### Local Test (No GPU needed)

```bash
cd /Volumes/Expansion/mvp_pipeline/avatar-creation-measurements

# Install dependencies
pip install numpy smplx trimesh

# Run measurement extraction
python measure.py --input ../avatar-creation/4D-Humans-clean/outputs/body_person0_params.npz
```

### Expected Output
```json
{
  "chest_circumference_cm": 98.5,
  "waist_circumference_cm": 82.3,
  "hip_circumference_cm": 96.1,
  "inseam_cm": 81.2,
  "shoulder_width_cm": 45.8,
  "height_cm": 178.0
}
```

### Validate Against Known Measurements
1. Take a photo of yourself
2. Run avatar creation
3. Run measurement extraction
4. Compare to your actual measurements (tape measure)
5. Calibrate if needed (scale factors)

---

## 3. GLB Combination / Viewer

### Test GLB Export Locally

```bash
cd /Volumes/Expansion/mvp_pipeline/avatar-creation

# Requires: trimesh, pygltflib
python combine_avatar_pants_tshirt_glb.py \
  --avatar outputs/body_textured.obj \
  --pants garments/pants_M.obj \
  --tshirt garments/tshirt_M.obj \
  --output combined.glb
```

### Test in Three.js Viewer

```html
<!-- Quick local test: create test.html -->
<!DOCTYPE html>
<html>
<head>
  <script type="importmap">
    { "imports": { "three": "https://unpkg.com/three@0.160.0/build/three.module.js" } }
  </script>
</head>
<body>
  <script type="module">
    import * as THREE from 'three';
    import { GLTFLoader } from 'https://unpkg.com/three@0.160.0/examples/jsm/loaders/GLTFLoader.js';
    import { OrbitControls } from 'https://unpkg.com/three@0.160.0/examples/jsm/controls/OrbitControls.js';
    
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f0f0);
    
    const camera = new THREE.PerspectiveCamera(50, window.innerWidth/window.innerHeight, 0.1, 100);
    camera.position.set(0, 1, 3);
    
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderer.domElement);
    
    const controls = new OrbitControls(camera, renderer.domElement);
    
    // Lighting
    scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const dirLight = new THREE.DirectionalLight(0xffffff, 1);
    dirLight.position.set(5, 5, 5);
    scene.add(dirLight);
    
    // Load GLB
    new GLTFLoader().load('combined.glb', (gltf) => {
      scene.add(gltf.scene);
    });
    
    function animate() {
      requestAnimationFrame(animate);
      renderer.render(scene, camera);
    }
    animate();
  </script>
</body>
</html>
```

Then run:
```bash
cd /Volumes/Expansion/mvp_pipeline/avatar-creation
python -m http.server 8000
# Open http://localhost:8000/test.html
```

---

## 4. Fit Logic

### Test Size Recommendation

```python
# test_fit_logic.py
def recommend_size(user_measurements: dict, size_chart: dict) -> dict:
    """
    Returns recommended size and fit assessment per garment area.
    """
    recommendations = {}
    
    for size, chart in size_chart.items():
        fit_score = 0
        fit_details = {}
        
        # Chest
        chest_diff = user_measurements['chest_cm'] - chart['chest_cm']
        if chest_diff < -2:
            fit_details['chest'] = 'too_tight'
        elif chest_diff > 6:
            fit_details['chest'] = 'loose'
        else:
            fit_details['chest'] = 'recommended'
            fit_score += 1
        
        # Waist
        waist_diff = user_measurements['waist_cm'] - chart['waist_cm']
        if waist_diff < -2:
            fit_details['waist'] = 'too_tight'
        elif waist_diff > 6:
            fit_details['waist'] = 'loose'
        else:
            fit_details['waist'] = 'recommended'
            fit_score += 1
        
        recommendations[size] = {
            'score': fit_score,
            'details': fit_details
        }
    
    # Find best size
    best_size = max(recommendations, key=lambda s: recommendations[s]['score'])
    return {'recommended_size': best_size, 'all_sizes': recommendations}


# Test
user = {'chest_cm': 100, 'waist_cm': 84}
size_chart = {
    'S': {'chest_cm': 92, 'waist_cm': 76},
    'M': {'chest_cm': 100, 'waist_cm': 84},
    'L': {'chest_cm': 108, 'waist_cm': 92},
}

result = recommend_size(user, size_chart)
print(result)
# Expected: {'recommended_size': 'M', 'all_sizes': {...}}
```

---

## 5. Backend API (FastAPI)

### Run Locally

```bash
cd /Volumes/Expansion/mvp_pipeline/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Create avatar (mock)
curl -X POST http://localhost:8000/api/avatars \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test123", "image_url": "https://example.com/photo.jpg"}'

# Get measurements
curl http://localhost:8000/api/avatars/test123/measurements

# Try-on session
curl -X POST http://localhost:8000/api/tryon \
  -H "Content-Type: application/json" \
  -d '{"avatar_id": "av_123", "garment_id": "gar_456", "size": "M"}'
```

---

## 6. Frontend (Next.js)

### Run Locally

```bash
cd /Volumes/Expansion/mvp_pipeline/frontend
npm install
npm run dev
# Open http://localhost:3000
```

### Test Checklist
- [ ] Photo upload works
- [ ] Avatar creation shows loading state
- [ ] 3D viewer loads avatar GLB
- [ ] Size selector switches garment GLBs
- [ ] Fit indicator shows correct recommendation
- [ ] Body masking hides poke-through

---

## 7. End-to-End Integration Test

### Flow Test Checklist

1. **Upload Photo**
   - [ ] Photo accepted (JPG/PNG, <10MB)
   - [ ] Progress indicator shows
   - [ ] Avatar created in <30s

2. **View Avatar**
   - [ ] 3D model loads in viewer
   - [ ] Can rotate/zoom
   - [ ] Skin texture visible

3. **Try On Garment**
   - [ ] Garment loads on avatar
   - [ ] No major poke-through visible
   - [ ] Size selector works

4. **Size Recommendation**
   - [ ] Shows "Recommended" badge on best size
   - [ ] Shows "Too tight" / "Loose" on others
   - [ ] Measurements displayed

5. **Shopify Embed**
   - [ ] Iframe loads on product page
   - [ ] "Try On" button visible
   - [ ] Session persists across page navigation

---

## 8. Performance Benchmarks

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Avatar creation | <30s | Time from upload to GLB ready |
| GLB load time | <1.5s | DevTools Network tab |
| Viewer FPS | >30 | Three.js stats panel |
| API response | <200ms | curl timing |
| Iframe load | <2s | DevTools Performance |

---

## Quick Test Commands Summary

```bash
# 1. Measurement extraction (local)
cd avatar-creation-measurements && python measure.py --help

# 2. GLB viewer (local)
cd avatar-creation && python -m http.server 8000

# 3. Backend API (local)
cd backend && uvicorn app.main:app --reload

# 4. Frontend (local)
cd frontend && npm run dev

# 5. Full stack (docker-compose)
docker-compose up
```
