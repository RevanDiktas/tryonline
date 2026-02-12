# Backend & Frontend Setup — Steps 2 & 3

## Prerequisites

- **Python 3.10+** (for backend)
- **Node.js 18+** (for frontend)
- **Supabase** (once restored: URL + Service Role key from Project Settings → API)

---

## Backend Setup

### 1. Go to backend folder
```bash
cd /Volumes/Expansion/mvp_pipeline/backend
```

### 2. Create virtual environment (optional but recommended)
```bash
python3 -m venv venv
source venv/bin/activate   # Mac/Linux
# On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment variables
Create a file named `.env` in the `backend` folder (copy from `env.example`):

```bash
cp env.example .env
```

Edit `.env` and set:
- `SUPABASE_URL` — from Supabase Dashboard → Project Settings → API → Project URL
- `SUPABASE_SERVICE_KEY` — from Project Settings → API → `service_role` key (secret!)

When Supabase is restoring, these calls will fail, but the server will still start.

### 5. Start the backend
```bash
uvicorn app.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Test: open http://localhost:8000 — you should get `{"name":"TryOn API",...}`

---

## Frontend Setup

### 1. Go to frontend folder
```bash
cd /Volumes/Expansion/mvp_pipeline/frontend
```

### 2. Install dependencies
```bash
npm install
```

### 3. Environment variables (optional)
The frontend defaults to `http://localhost:8000` for the API. To override, create `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Start the frontend
```bash
npm run dev
```

You should see:
```
▲ Next.js 14.0.4
- Local: http://localhost:3000
```

---

## Test the embed (once Supabase is back)

1. Backend running on port 8000
2. Frontend running on port 3000
3. Open the TryOn widget: http://localhost:3000/test-viewer.html?product_id=demo-npc-tshirt&shop=demo.myshopify.com
4. Widget loads → creates session → tracks events
5. In Supabase: Table Editor → `analytics_events` and `tryon_sessions` should have new rows

---

## While Supabase is restoring

You can still:
- Start both servers
- Visit http://localhost:3000/test-viewer.html (full widget with TRY ON button)
- API calls to create session / track events will fail (no DB), but the UI works

Run the migration in Supabase SQL Editor once the project is back online.
