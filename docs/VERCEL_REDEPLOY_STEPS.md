# Deploy (or redeploy) the frontend on Vercel — step-by-step

**Current state:** Code is pushed to the **`feature/analytics`** branch. Use these steps so Vercel builds and deploys that branch.

---

## If Vercel is already connected to your repo

### Option A: Vercel is set to deploy from `feature/analytics`

- **Nothing to pull.** Vercel pulls from GitHub automatically when you push.
- **What to do:**
  1. Go to [vercel.com](https://vercel.com) → your project (e.g. **tryonline** or the name you gave it).
  2. Open the **Deployments** tab.
  3. You should see a new deployment for the latest push (commit `fix: Vercel build — …`). If it’s already **Building** or **Ready**, wait for it to finish.
  4. If you don’t see a new deployment, click **Redeploy** on the latest deployment and choose **Redeploy with existing Build Cache** or **Redeploy** (full rebuild).

### Option B: Vercel is set to deploy from `main` (or another branch)

- **Either:**
  - **Trigger a deploy from the branch:**
    1. Vercel dashboard → your project → **Deployments**.
    2. Click **Create Deployment** (or **Deploy**).
    3. Select branch **`feature/analytics`** and deploy.
  - **Or** merge `feature/analytics` into `main` and push; then Vercel will auto-deploy `main` (if that’s the production branch).

---

## If you haven’t set up the Vercel project yet

1. Go to [vercel.com](https://vercel.com) → **Add New…** → **Project**.
2. **Import** the repo **RevanDiktas/tryonline** (GitHub).
3. **Configure:**
   - **Root Directory:** set to **`frontend`** (required).
   - **Framework:** Next.js (auto-detected).
   - **Build / Install:** leave defaults.
4. **Environment variables** (add before first deploy):
   - `NEXT_PUBLIC_API_URL` = `https://heroic-celebration-production-9f72.up.railway.app`
   - `NEXT_PUBLIC_SUPABASE_URL` = your Supabase project URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = your Supabase anon (public) key
5. Click **Deploy**.
6. After deploy, in **Railway** set **CORS_ORIGINS** to include your Vercel URL (e.g. `http://localhost:3000,https://<your-app>.vercel.app`) and redeploy the backend.

---

## Checklist for this redeploy

- [ ] Code is pushed to **feature/analytics** (already done).
- [ ] In Vercel, either a new deployment appeared or you triggered a deploy from **feature/analytics**.
- [ ] **Root Directory** is **frontend** (in Project Settings → General).
- [ ] Env vars are set: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- [ ] After a successful deploy, add the Vercel URL to Railway **CORS_ORIGINS** and redeploy the backend.

---

## Summary

- **You do not need to “pull” on your machine for Vercel.** Vercel pulls from GitHub. Your push to `feature/analytics` is enough.
- If the project is already connected and deploys from `feature/analytics`, the push should have started a new deployment automatically. Check the **Deployments** tab.
- If it deploys from `main`, use **Create Deployment** and choose branch **feature/analytics**, or merge to `main` and push.
