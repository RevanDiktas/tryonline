# Pipeline Files Storage in Supabase

## Overview

All pipeline output files are stored in Supabase Storage under each user's folder:
```
avatars/
  └── {user_id}/
      ├── avatar_textured.glb        # Main 3D avatar (GLB)
      ├── body_original.obj          # Original mesh from 4D-Humans
      ├── body_tpose.obj             # T-pose mesh (for measurements)
      ├── body_apose.obj             # A-pose mesh (for visualization)
      ├── smpl_params.npz            # SMPL parameters
      ├── measurements.json          # Body measurements
      ├── skin_texture.png           # Extracted skin texture
      ├── avatar_texture.png         # Applied texture for GLB
      ├── face_crop.png              # Cropped face image
      └── skin_detection_mask.png    # Skin detection visualization
```

## Database Schema

The `fit_passports` table stores:
- `avatar_url` - Main GLB file URL (for 3D viewer)
- `pipeline_files` (JSONB, optional) - All file URLs as JSON:
  ```json
  {
    "avatar_glb": "https://.../avatar_textured.glb",
    "original_mesh": "https://.../body_original.obj",
    "tpose_mesh": "https://.../body_tpose.obj",
    "apose_mesh": "https://.../body_apose.obj",
    "smpl_params": "https://.../smpl_params.npz",
    "measurements": "https://.../measurements.json",
    "skin_texture": "https://.../skin_texture.png",
    "avatar_texture": "https://.../avatar_texture.png",
    "face_crop": "https://.../face_crop.png",
    "skin_detection_mask": "https://.../skin_detection_mask.png"
  }
  ```

## Schema Migration (Optional)

To store all file URLs in database, run this SQL:

```sql
-- Add pipeline_files JSONB column to fit_passports
ALTER TABLE public.fit_passports
ADD COLUMN IF NOT EXISTS pipeline_files JSONB;

-- Create index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_fit_passports_pipeline_files 
ON public.fit_passports USING GIN (pipeline_files);
```

## File Mapping

| Pipeline Output | Storage Filename | Content Type |
|----------------|------------------|--------------|
| `avatar_glb` | `avatar_textured.glb` | `model/gltf-binary` |
| `original_mesh` | `body_original.obj` | `model/obj` |
| `tpose_mesh` | `body_tpose.obj` | `model/obj` |
| `apose_mesh` | `body_apose.obj` | `model/obj` |
| `smpl_params` | `smpl_params.npz` | `application/octet-stream` |
| `measurements` | `measurements.json` | `application/json` |
| `skin_texture` | `skin_texture.png` | `image/png` |
| `avatar_texture` | `avatar_texture.png` | `image/png` |
| `face_crop` | `face_crop.png` | `image/png` |
| `skin_detection_mask` | `skin_detection_mask.png` | `image/png` |

## Retrieval

To get all files for a user:

```typescript
// Frontend
const { data } = await supabase
  .storage
  .from('avatars')
  .list(`${userId}/`, { limit: 100 })

// Or construct URLs directly:
const baseUrl = 'https://your-project.supabase.co/storage/v1/object/public/avatars'
const fileUrl = `${baseUrl}/${userId}/avatar_textured.glb`
```

## Benefits

1. **All files preserved** - Complete pipeline output available for:
   - Debugging and troubleshooting
   - Future reprocessing
   - Research and analysis
   - User data export

2. **Organized per user** - Easy to:
   - List all files for a user
   - Clean up user data (delete folder)
   - Backup per user

3. **Public access** - Files are public URLs (CDN-cached) for fast loading in 3D viewer
