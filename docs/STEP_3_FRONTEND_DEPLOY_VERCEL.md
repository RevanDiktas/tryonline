# Step 3: Deploy the frontend to Vercel

**Goal:** Get the Next.js frontend live so the dashboard and widget (`test-viewer.html`) are reachable. You’ll get a default URL like `https://your-project.vercel.app`. Add your own domain later.

**Backend URL to use:** `https://heroic-celebration-production-9f72.up.railway.app`

---

## Step-by-step

### 1. Open Vercel and sign in

- Go to [vercel.com](https://vercel.com) and sign in (e.g. **Continue with GitHub**).
- If this is your first time, authorize Vercel to access your GitHub.

### 2. Add a new project

- Click **Add New…** → **Project** (or **Import Project**).
- You’ll see a list of GitHub repos. Select **RevanDiktas/tryonline** (or the repo that has your frontend).
- If you don’t see it, use **Configure GitHub App** and grant Vercel access to the repo (same idea as Railway).

### 3. Configure the project

- **Framework Preset:** Vercel should detect **Next.js**. Leave as is.
- **Root Directory:** Click **Edit** and set to **`frontend`**. (So only the `frontend/` folder is built and deployed.)
- **Build Command:** Leave default (`next build` or empty).
- **Output Directory:** Leave default (e.g. `.next`).
- **Install Command:** Leave default (`npm install` or `yarn install`).

### 4. Add environment variables

Before deploying, add these in the project config (or in the “Environment Variables” step):

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | `https://heroic-celebration-production-9f72.up.railway.app` |
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL (e.g. `https://xxxxx.supabase.co`) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Your Supabase **anon public** key (from Supabase → Project Settings → API) |

- Use **Production** (and optionally Preview) for each variable.
- Don’t add a trailing slash to the URLs.

### 5. Deploy

- Click **Deploy**.
- Wait for the build to finish. Vercel will show a URL like `https://tryon-frontend-xxx.vercel.app` or `https://your-project.vercel.app`.

### 6. Test the frontend

- Open the Vercel URL in the browser. You should see your app (e.g. home or dashboard).
- Open **`https://<your-vercel-url>/test-viewer.html`** and confirm the widget page loads. If it calls the API (e.g. session or events), those go to your Railway backend via `NEXT_PUBLIC_API_URL` and the rewrites in `next.config.js`.

### 7. Update backend CORS (important)

So the browser allows requests from your frontend to the backend:

- In **Railway** → **heroic-celebration** → **Variables**, edit **CORS_ORIGINS**.
- Set it to: `http://localhost:3000,https://<your-vercel-url>`  
  (e.g. `http://localhost:3000,https://tryon-frontend-xxx.vercel.app` — no trailing slash.)
- Redeploy the Railway service (or let it auto-redeploy if you have that on) so the new CORS value is applied.

After that, the widget on the Vercel URL can call the Railway API without CORS errors.

---

## Checklist

- [ ] Vercel project created from GitHub repo.
- [ ] Root directory set to **frontend**.
- [ ] `NEXT_PUBLIC_API_URL` = Railway backend URL.
- [ ] `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` set.
- [ ] Deploy succeeded; frontend URL works.
- [ ] `CORS_ORIGINS` on Railway includes the Vercel URL; backend redeployed.

---

## Domain later

When you have a domain, add it in Vercel: **Project → Settings → Domains → Add**. Then add that same origin to **CORS_ORIGINS** on Railway (e.g. `https://app.yourdomain.com`) and redeploy the backend.

---

*Backend URL (Railway):* `https://heroic-celebration-production-9f72.up.railway.app`
