# Status Report — 2026-02-25 (Afternoon)

## What Was Done Today

### Brand Onboarding — COMPLETE
- **Brand signup form**: Brand/Company Name, Contact Person, Business Email, Phone, Country, Password, optional Shopify Store URL
- **Shopper signup** unchanged and working (name, DOB, city, height, gender, photo, avatar)
- **Login routing**: brands → `/brand` (analytics dashboard), shoppers → `/dashboard` or `/onboarding`
- **Dashboard isolation**: shoppers cannot see brand dashboard, brands cannot see shopper dashboard. Both redirect if wrong user type.
- **Brand record created** in `brands` table on signup, linked to `users` table via `user_id`
- **Garments folder** automatically created in Supabase Storage (`garments/{brand_id}/`) on brand signup
- **Cascade delete** SQL added: deleting a user auto-deletes their brand record

### APP_MODE Environment Variable
- `NEXT_PUBLIC_APP_MODE=website` (default) — shows both shopper and brand signup
- `NEXT_PUBLIC_APP_MODE=shopify` — shows brand-only signup (no shopper noise)
- Ready for the Shopify-specific Vercel deployment

### Homepage Redesign
- **No more auto-redirect**: clicking the TryOn logo always goes to the homepage
- **Logged out**: two CTAs — "Create Your Fit Passport" (shopper) and "Launch Your Brand" (brand)
- **Logged in**: shows brand name (for brands) or user name (for shoppers) + dashboard button
- After signup: brands go directly to `/brand`, shoppers go to `/onboarding`

### Shopper Dashboard Cleanup
- Removed "Brand analytics →" link from header
- Removed "Test TryOn Widget" section
- Clean: avatar, measurements, addresses, fit preference only

### Backend Changes
- `POST /api/brand/register` — creates brand record linked to user + garments folder
- `GET /api/brand/me` — returns brand data for authenticated user
- `_create_brand_folder()` — creates `garments/{brand_id}/` in Supabase Storage
- Brand creation works for both website signup and Shopify OAuth install flow

### SQL Migrations Run Today
```sql
-- Add user_id to brands table
ALTER TABLE public.brands ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id);
CREATE INDEX IF NOT EXISTS idx_brands_user_id ON public.brands(user_id);

-- Cascade delete (deleting user deletes their brand)
ALTER TABLE public.brands
  DROP CONSTRAINT IF EXISTS brands_user_id_fkey,
  ADD CONSTRAINT brands_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
```

### Files Changed Today
| File | Change |
|------|--------|
| `frontend/app/page.tsx` | Homepage: no auto-redirect, two CTAs, logged-in state with brand name |
| `frontend/app/signup/page.tsx` | Separate brand/shopper forms, APP_MODE support, direct routing after signup |
| `frontend/app/login/page.tsx` | Routes brands to /brand, shoppers to /dashboard or /onboarding |
| `frontend/app/brand/page.tsx` | Auth-gated: only brand users, sign out button, email display |
| `frontend/app/dashboard/page.tsx` | Removed brand analytics link + test widget, gates brand users out |
| `frontend/app/onboarding/page.tsx` | Logo links to homepage properly |
| `frontend/lib/app-mode.ts` | NEW: APP_MODE helper (website vs shopify) |
| `frontend/lib/api.ts` | Added registerBrand(), getMyBrand() API calls |
| `backend/app/api/routes/brand.py` | NEW: /api/brand/register + /api/brand/me endpoints |
| `backend/app/main.py` | Registered brand router |
| `backend/app/services/supabase.py` | create_brand_for_user(), get_brand_by_user_id(), _create_brand_folder() |
| `frontend/supabase-migration-brands-user-id.sql` | Migration: user_id column on brands |

### Vercel Production Branch
Changed from `main` to `feature/analytics` — auto-deploys on every push now.

---

## Current State of Services

| Service | Status | Branch | URL |
|---------|--------|--------|-----|
| **RunPod (GPU)** | WORKING | `main` | RunPod serverless endpoint |
| **Backend (Railway)** | WORKING | `feature/analytics` | https://heroic-celebration-production-9f72.up.railway.app |
| **Frontend (Vercel)** | WORKING | `feature/analytics` | https://tryonline.vercel.app |
| **Supabase** | WORKING | — | https://cykwthsbrylonconqlfz.supabase.co |

---

## What Still Needs to Be Done Tonight

### Priority 1: Deploy Shopify App (brand-only version)

#### Step 1: Create Second Vercel Project
- Go to vercel.com/new → import same repo (RevanDiktas/tryonline)
- Name: `tryon-shopify` or `tryon-brands`
- Root Directory: `frontend`
- Production Branch: `feature/analytics`
- Environment Variables:
  - `NEXT_PUBLIC_APP_MODE` = `shopify`
  - `NEXT_PUBLIC_SUPABASE_URL` = (same as main)
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = (same as main)
  - `NEXT_PUBLIC_API_URL` = `https://heroic-celebration-production-9f72.up.railway.app`

#### Step 2: Update shopify.app.toml
- Change `application_url` to the new Shopify Vercel URL
- Update `redirect_urls` to include the new URL

#### Step 3: Deploy to Shopify
- Run `shopify app deploy` from `shopify_app/` directory
- This pushes the updated config + widget extension to Shopify

#### Step 4: Test Full Flow
- Install the app on a test Shopify store
- Verify brand-only signup (no shopper option)
- Check brand record + garments folder created
- Verify the Try On widget works on product pages

### Priority 2: Garment Management (later — not needed for launch)
- Add garment upload section to brand dashboard
- Upload GLB/OBJ files to `garments/{brand_id}/{product_id}/`
- Categorize by collections
- For now: garments can be manually uploaded to the Storage bucket

### Priority 3: Shopper Dashboard Polish (later)
- Any remaining cleanup for the shopper experience
- Ensure widget ↔ shopper flow is seamless when brands have the app installed
