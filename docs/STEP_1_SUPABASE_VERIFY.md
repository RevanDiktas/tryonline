# Step 1: Supabase verify (no domain needed)

**Goal:** Project exists, schema and migrations are applied, storage buckets exist, and you have the keys for backend + frontend.  
**Time:** ~10–15 min.

**If you’re already testing locally (frontend :3000, backend :8000) and data flows correctly** (e.g. brand dashboard, events, sessions) — **Step 1 is done.** Use the checklist below only if you spin up a new project or need to re-verify.

---

## 1.1 Confirm project and keys

1. Open [Supabase Dashboard](https://supabase.com/dashboard) and select your project (or create one).
2. Go to **Project Settings → API** and note:
   - **Project URL** (e.g. `https://xxxxx.supabase.co`) → backend `SUPABASE_URL` and frontend `NEXT_PUBLIC_SUPABASE_URL`
   - **anon public** key → frontend `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - **service_role** key (secret) → backend `SUPABASE_SERVICE_KEY` only
   - **JWT Secret** (Project Settings → API → JWT Secret) → backend `SUPABASE_JWT_SECRET`
3. Confirm your `backend/.env` has `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `SUPABASE_JWT_SECRET` set.  
   (Do not commit `.env`; it’s gitignored.)

---

## 1.2 Run SQL in order (Supabase SQL Editor)

Open **SQL Editor** in the dashboard and run these files **in this order**.  
Copy the contents of each file from your repo, paste into the editor, and run.

| Order | File | Purpose |
|-------|------|--------|
| 1 | `frontend/supabase-schema.sql` | Base tables, RLS, triggers |
| 2 | `frontend/supabase-schema-migration-add-pipeline-files.sql` | `pipeline_files` on fit_passports (safe if already there) |
| 3 | `frontend/supabase-migration-analytics-category-a.sql` | Analytics columns + `analytics_daily` |
| 4 | `frontend/supabase-migration-fit-passports-preferred-fit.sql` | `preferred_fit` on fit_passports if missing |
| 5 | `frontend/supabase-migration-user-addresses.sql` | `user_addresses` table |
| 6 | `frontend/supabase-migration-garments-demo.sql` | Optional: demo garment row (needs at least one brand in `brands`; skip if you don’t have one yet) |

If any statement errors with “already exists”, that’s fine — it means that part is already applied. Continue with the next file.

---

## 1.3 Create storage buckets

Go to **Storage** in the dashboard and create these buckets:

| Bucket | Public? | Used for |
|--------|--------|----------|
| **photos** | No (private) | User uploads; backend generates signed URLs |
| **avatars** | Yes | Avatar GLB/OBJ files |
| **garments** | Yes | CLO3D garment files (for product try-on) |

If you use a **brand-assets** bucket (e.g. for logos), create it and set public as needed.

---

## 1.4 Quick backend test (optional)

From the repo root:

```bash
cd backend
source venv/bin/activate   # if you use venv
python -c "
from app.config import get_settings
s = get_settings()
print('SUPABASE_URL:', s.supabase_url[:30] + '...' if s.supabase_url else 'MISSING')
print('SUPABASE_SERVICE_KEY:', 'set' if s.supabase_service_key else 'MISSING')
from app.services.supabase import supabase_service
r = supabase_service.client.table('tryon_sessions').select('id').limit(1).execute()
print('DB connection OK:', r.data is not None)
"
```

You should see `DB connection OK: True`. If you get “relation does not exist”, run the schema/migrations from 1.2.

---

## 1.5 Checklist

- [ ] Project exists; API URL and keys noted
- [ ] `backend/.env` has `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`
- [ ] Ran `supabase-schema.sql` in SQL Editor
- [ ] Ran migrations 2–5 (and optionally 6) in order
- [ ] Buckets **photos**, **avatars**, **garments** created
- [ ] (Optional) Backend test script prints `DB connection OK: True`

When all are done, **Step 1 is complete.** Next: Step 2 — Backend deploy (Railway or Render).
