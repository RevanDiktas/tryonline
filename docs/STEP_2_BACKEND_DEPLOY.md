# Step 2: Deploy the backend (Railway or Render)

**Goal:** Get the FastAPI backend live on a public URL so the frontend (and later the widget) can call it.  
**No domain needed** — you’ll get a default URL like `https://yourapp.up.railway.app` or `https://yourapp.onrender.com`.

---

## Why we don’t deploy the backend on RunPod

**Short answer:** RunPod is for **GPU workloads** (your avatar pipeline). The backend is a **long‑running API server** that should run on a normal host (Railway/Render). RunPod is the right place only for the 4D-Humans container.

| | RunPod Serverless | Railway / Render |
|---|------------------|-------------------|
| **Purpose** | Run a **GPU job** (e.g. 4D-Humans), return result, then stop | Run a **web server** 24/7 that handles many small requests |
| **Billing** | Per **GPU-second** (expensive if you leave a server running) | Per **compute time** for a small API (cheap for health checks, sessions, webhooks) |
| **What runs there** | Your avatar pipeline container (triggered by the backend) | FastAPI: `/health`, `/api/events`, `/api/avatar`, webhooks, and it **calls** RunPod when it needs a GPU job |

So: **Backend** = Railway or Render (API + orchestration). **RunPod** = only the avatar GPU job. The backend **calls** RunPod; it doesn’t **run on** RunPod. Putting the FastAPI app on RunPod would mean paying GPU rates for every tiny API request and using the wrong tool for a long‑running server.

---

## Why the backend is separate from the frontend

- **Supabase** — Already in the cloud. You don’t deploy it; the frontend and backend both connect to it via env vars.
- **Backend (this step)** — Your API, RunPod calls, avatar pipeline orchestration, webhooks. Deploy to **Railway** or **Render**.
- **Frontend (Step 3)** — Deploy to **Vercel** separately. It serves the dashboard and the GLB viewer page; the viewer calls **your backend API** for sessions, avatar, products, etc. So: viewer is served by Vercel, data/GLBs come from your backend + Supabase.

---

## Step-by-step: Deploy on Railway

Do these in order. Total time ~10–15 min.

### 1. Open Railway and create a project

- Go to [railway.app](https://railway.app) and sign in (e.g. **Login with GitHub**).
- Click **New Project**.

### 2. Connect the repo

- Choose **Deploy from GitHub repo**.
- If asked, authorize Railway to access your GitHub.
- Select the repo (e.g. `RevanDiktas/tryonline`).
- Select the branch you want to deploy (e.g. **feature/analytics**).
- Railway may create a service automatically; we’ll point it at the backend next.

### 3. Set the root directory to `backend`

- Click the new **service** (the deployment).
- Go to **Settings** (or the service’s **Settings** tab).
- Find **Root Directory** (or **Source** → Root Directory).
- Set it to: **`backend`** (so only the `backend/` folder is built and run).
- Save if there’s a Save button.

### 4. Configure build and start (if needed)

- In **Settings**, check **Build** and **Start** (or **Deploy**).
- **Build command:**  
  Either leave empty (Railway may detect Python) or set:  
  `pip install -r requirements.txt`
- **Start command:**  
  `sh -c 'uvicorn app.main:app --host 0.0.0.0 --port $PORT'`  
  (Use the shell so Railway expands `$PORT`; otherwise you get `'$PORT' is not a valid integer`.)
- If you prefer Docker: set **Dockerfile path** to `backend/Dockerfile` and leave start command empty so the Dockerfile CMD runs.

### 5. Add environment variables

- Open the **Variables** tab for this service.
- Add each variable (names must match exactly). Use the **same values** as in your local `backend/.env`:

| Variable | Example / note |
|----------|----------------|
| `SUPABASE_URL` | `https://xxxxx.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Your **service_role** key from Supabase (secret) |
| `SUPABASE_JWT_SECRET` | JWT Secret from Supabase → Project Settings → API |
| `RUNPOD_API_KEY` | Your RunPod API key |
| `RUNPOD_ENDPOINT_ID` | Your RunPod endpoint ID |
| `PHOTOS_BUCKET` | `photos` |
| `AVATARS_BUCKET` | `avatars` |
| `CORS_ORIGINS` | For now: `http://localhost:3000`. After Vercel deploy, add e.g. `https://yourapp.vercel.app` (or both, comma-separated) |
| `SHOPIFY_WEBHOOK_SECRET` | Optional; leave empty or set when you add webhooks |

- **Do not** set `PORT` unless Railway doesn’t set it; they usually do.

### 6. Deploy and get the URL

- Trigger a deploy: **Deploy** (or push a commit to the same branch if you have auto-deploy).
- Wait until the build and deploy finish (logs should show uvicorn starting).
- In **Settings** (or the **Networking** / **Public Networking** section), click **Generate Domain** (or **Add public URL**). Railway will give you a URL like `https://your-service.up.railway.app`.
- Copy that URL — this is your **backend URL**.

### 7. Test the backend

- In the browser or with curl:  
  `https://<your-railway-url>/health`  
  You should get a healthy response (e.g. JSON with status).
- Optional:  
  `https://<your-railway-url>/`  
  Should return something like `{"name":"TryOn API", ...}`.

If both work, **Step 2 is done.** Use this backend URL as `NEXT_PUBLIC_API_URL` when you deploy the frontend (Step 3), and add the frontend URL to `CORS_ORIGINS` and redeploy the backend.

---

## Railway checklist (quick reference)

1. [ ] railway.app → New Project → Deploy from GitHub repo.  
2. [ ] Repo + branch (e.g. `feature/analytics`). Root directory: **backend**.  
3. [ ] Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.  
4. [ ] Variables: SUPABASE_*, RUNPOD_*, PHOTOS_BUCKET, AVATARS_BUCKET, CORS_ORIGINS.  
5. [ ] Generate domain; test `/health`.

---

## Option B: Render

1. Go to [render.com](https://render.com) and sign in (e.g. with GitHub).
2. **New** → **Web Service**.
3. Connect your repo and select the branch (e.g. `feature/analytics`).
4. **Root directory:** `backend`.
5. **Build command:** `pip install -r requirements.txt`  
   **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Or use **Docker** and set Dockerfile path to `backend/Dockerfile`.
6. **Environment:** Add the same variables as in the table above (Supabase, RunPod, CORS_ORIGINS, etc.). Render sets `PORT` for you.
7. Deploy. Render will assign a URL like `https://yourapp.onrender.com`.
8. Test: open `https://<your-render-url>/health`.

---

## After deploy

- **Note the backend URL** — you’ll need it for the frontend (`NEXT_PUBLIC_API_URL`) and for CORS.
- When you deploy the frontend (Step 3), come back and add your **Vercel frontend URL** to `CORS_ORIGINS` in the backend (e.g. `https://yourapp.vercel.app`) and redeploy the backend if needed.

Next: **Step 3 — Frontend deploy (Vercel)**. There you’ll set `NEXT_PUBLIC_API_URL` to this backend URL and `NEXT_PUBLIC_SUPABASE_*` so the app and GLB viewer talk to your API and Supabase.
