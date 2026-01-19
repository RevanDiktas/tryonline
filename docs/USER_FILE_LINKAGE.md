# User File Linkage Verification

## How Files Are Organized

### Storage Structure
All avatar files are stored in Supabase Storage under the `avatars` bucket, organized by `user_id`:

```
avatars/
  ├── {user_id_1}/
  │   ├── avatar_textured.glb
  │   ├── skin_texture.png
  │   ├── measurements.json
  │   └── ... (other pipeline files)
  ├── {user_id_2}/
  │   ├── avatar_textured.glb
  │   └── ...
  └── ...
```

**Example:**
- User ID: `694af2e0-4b22-4cdf-801f-24dc8a731d8f`
- Storage path: `avatars/694af2e0-4b22-4cdf-801f-24dc8a731d8f/avatar_textured.glb`
- Public URL: `https://{project}.supabase.co/storage/v1/object/public/avatars/694af2e0-4b22-4cdf-801f-24dc8a731d8f/avatar_textured.glb`

### Database Linkage

The `fit_passports` table links users to their avatar files:

```sql
fit_passports
  ├── user_id (UUID) → Links to users.id
  ├── avatar_url (TEXT) → Points to storage URL
  └── pipeline_files (JSONB) → All file URLs
      {
        "avatar_glb": "https://.../avatars/{user_id}/avatar_textured.glb",
        "skin_texture": "https://.../avatars/{user_id}/skin_texture.png",
        ...
      }
```

## How to Verify User Linkage

### 1. Check Storage Folder Name
The folder name in the `avatars` bucket **IS** the `user_id`:
- Folder: `694af2e0-4b22-4cdf-801f-24dc8a731d8f`
- This is the same UUID stored in `fit_passports.user_id`

### 2. Check Database Record
Query the database to verify:

```sql
SELECT 
  user_id,
  avatar_url,
  pipeline_files,
  status
FROM fit_passports
WHERE user_id = '694af2e0-4b22-4cdf-801f-24dc8a731d8f';
```

The `avatar_url` should contain the `user_id` in the path.

### 3. Verify in Code
The backend automatically verifies linkage after upload:
- Checks that `avatar_url` contains `user_id`
- Verifies all `pipeline_files` URLs contain `user_id`
- Logs verification results

## Security & Isolation

### User Isolation
- Each user's files are in a separate folder named after their `user_id`
- No user can access another user's files (unless they know the exact UUID)
- The `avatars` bucket is PUBLIC, but files are organized by UUID (hard to guess)

### Future Improvements
For better security, consider:
1. **Private bucket with signed URLs**: Make bucket private, generate time-limited signed URLs
2. **Row Level Security (RLS)**: Add RLS policies to restrict access
3. **Access tokens**: Require authentication to access avatar files

## Troubleshooting

### Files Not Linked to User
If files appear in storage but aren't linked:
1. Check `fit_passports` table for the `user_id`
2. Verify `avatar_url` contains the correct `user_id`
3. Check backend logs for upload verification messages

### Multiple Users' Files Mixed
This should never happen because:
- Each upload uses `{user_id}/{filename}` path
- The `user_id` comes from authenticated request
- Backend verifies linkage after upload

If you see mixed files, check:
1. Backend logs for the upload process
2. Verify `user_id` is correctly passed to upload function
3. Check for any path manipulation in the code
