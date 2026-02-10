# Skin Showing Through Garment — Diagnosis & Fix

## Cause: Z-Fighting

When the garment is draped on the body in CLO, its surface sits **very close** to the avatar surface. In the viewer, both meshes are composited at nearly the same depth. The GPU depth buffer can't reliably decide which is in front → **z-fighting** → patches where skin shows through.

## Fixes Applied

### 1. Render Order
- Avatar: `renderOrder = 0` (drawn first)
- Garment: `renderOrder = 1` (drawn last)
- When depths are similar, the last-drawn (garment) wins.

### 2. Polygon Offset
On the garment material:
```javascript
material.polygonOffset = true;
material.polygonOffsetFactor = 2;
material.polygonOffsetUnits = 2;
```
This biases the garment's depth slightly *forward*, so it reliably appears in front of the avatar.

## Test with Local GLBs

To verify the issue is viewer-related (not asset-related):

1. Download avatar and garment from Supabase:
   - Avatar: `avatars/{user_id}/avatar_textured.glb`
   - Garment: `garments/demo-npc-tshirt/l.glb`

2. Place in `frontend/public/models/local/`:
   ```
   avatar.glb
   tshirt_l.glb
   ```

3. Test in viewer with local paths (temporarily change product config to use `/models/local/tshirt_l.glb` and avatar to `/models/local/avatar.glb`).

4. If skin still shows with local files → likely asset/export issue. If it fixes → was loading/network related.

## Future: Body Masking Shader

For a more robust solution, the `BodyMaskingShader` can hide body fragments where the garment is in front (depth pre-pass). This would require a custom render setup and is more complex.
