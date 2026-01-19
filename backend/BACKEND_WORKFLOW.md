# Backend Workflow & Architecture
## Complete Avatar Creation Flow

---

## 📋 Table of Contents
1. [Overview](#overview)
2. [API Endpoints](#api-endpoints)
3. [Complete Request Flow](#complete-request-flow)
4. [File Structure](#file-structure)
5. [Error Points & Diagnostics](#error-points--diagnostics)
6. [Configuration Required](#configuration-required)

---

## 🎯 Overview

**Backend Stack:**
- **Framework:** FastAPI (Python)
- **Database:** Supabase (PostgreSQL)
- **Storage:** Supabase Storage
- **GPU Processing:** RunPod Serverless
- **Port:** 8000

**Architecture:**
```
Frontend (Next.js) 
    ↓ HTTP POST
Backend API (/api/avatar/create)
    ↓ Background Task
RunPod Service → Submit Job
    ↓ Poll Status
RunPod GPU Worker → Process Avatar
    ↓ Returns Results
Backend → Upload to Supabase Storage
    ↓ Update Database
Frontend polls for completion
```

---

## 📡 API Endpoints

### 1. Health Check
- **URL:** `GET /health`
- **Purpose:** Verify backend is running
- **Response:** `{"status": "ok"}`

### 2. Create Avatar
- **URL:** `POST /api/avatar/create`
- **Request Body:**
```json
{
  "user_id": "uuid-string",
  "photo_url": "https://supabase.co/storage/...",
  "height": 175,
  "weight": 70,  // optional
  "gender": "male"  // male, female, other
}
```
- **Response:**
```json
{
  "job_id": "job-abc123",
  "user_id": "uuid-string",
  "status": "queued",
  "message": "Avatar creation started",
  "estimated_time_seconds": 120
}
```

### 3. Get Job Status
- **URL:** `GET /api/avatar/status/{job_id}`
- **Purpose:** Poll for job progress
- **Response:**
```json
{
  "job_id": "job-abc123",
  "status": "processing",  // queued, processing, completed, failed
  "progress": 45,
  "message": "Creating your 3D avatar...",
  "avatar_url": "https://...",  // when completed
  "measurements": {...},  // when completed
  "error": "..."  // if failed
}
```

---

## 🔄 Complete Request Flow

### Step 1: Frontend Calls Backend
**File:** `frontend/lib/api.ts` → `createAvatar()`

```
POST http://localhost:8000/api/avatar/create
Headers: Content-Type: application/json
Body: {
  user_id: "...",
  photo_url: "https://...",
  height: 175,
  gender: "male"
}
```

**Entry Point:** `backend/app/api/routes/avatar.py` → `create_avatar()`

---

### Step 2: Backend Receives Request
**File:** `backend/app/api/routes/avatar.py:26-79`

**What happens:**
1. ✅ Validates request (Pydantic model)
2. ✅ Generates unique `job_id` (e.g., `job-abc123def456`)
3. ✅ Updates Supabase `fit_passports` table:
   - Sets `status = "processing"`
   - Sets `processing_started_at = now()`
4. ✅ Stores job in memory: `jobs[job_id] = {...}`
5. ✅ Starts background task: `background_tasks.add_task(process_avatar_job, ...)`
6. ✅ **Immediately returns** `job_id` to frontend (doesn't wait for processing)

**Key Code:**
```python
# Line 44-64: Create job record
job_id = f"job-{uuid.uuid4().hex[:12]}"
jobs[job_id] = {
    "user_id": request.user_id,
    "status": ProcessingStatus.queued,
    "runpod_job_id": None,  # Will be set later
    ...
}

# Line 67-71: Start background processing
background_tasks.add_task(
    process_avatar_job,
    job_id=job_id,
    request=request
)

# Line 73-79: Return immediately
return AvatarCreateResponse(job_id=job_id, ...)
```

**⚠️ CRITICAL:** Backend returns **immediately** - processing happens in background!

---

### Step 3: Background Task Starts
**File:** `backend/app/api/routes/avatar.py:82-159`

**What happens:**

#### 3a. Prepare Photo URL
**Lines 103-117:**
- Extracts photo path from Supabase public URL
- Creates signed URL (valid for 1 hour) for RunPod to access
- **Why:** RunPod worker needs to download photo from Supabase

#### 3b. Check RunPod Service
**Lines 142-150:**
- Checks if using **Real RunPod Service** or **Mock Service**
- **If Mock:** ⚠️ Jobs will NOT be submitted to RunPod!
- **If Real:** Proceeds with actual RunPod API call

**Diagnostic Logs:**
```
[Avatar] RunPod service type: RunPodService or MockRunPodService
[RunPod Service] API Key: SET or NOT SET (using mock)
[RunPod Service] Endpoint ID: xxx or NOT SET (using mock)
```

#### 3c. Submit Job to RunPod
**File:** `backend/app/services/runpod.py:26-61`

**Lines 38-46:** Creates payload:
```json
{
  "input": {
    "photo_url": "https://...",
    "height": 175,
    "weight": 70,
    "gender": "male",
    "user_id": "uuid"
  }
}
```

**Lines 48-61:** POST to RunPod API
```
POST https://api.runpod.ai/v2/{ENDPOINT_ID}/run
Headers:
  Authorization: Bearer {RUNPOD_API_KEY}
  Content-Type: application/json
Body: {payload above}
```

**Response from RunPod:**
```json
{
  "id": "runpod-job-uuid",
  "status": "IN_QUEUE"  // or "IN_PROGRESS"
}
```

**Logs to check:**
```
[RunPod] Submitting job to: https://api.runpod.ai/v2/xxx/run
[RunPod] Response status: 200
[RunPod] ✅ Job submitted successfully: runpod-job-uuid
```

**⚠️ IF THIS FAILS:**
- Check: `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` in `.env`
- Check: RunPod API key is valid
- Check: Endpoint ID is correct
- Check: Endpoint has workers available

**Lines 130-132:** If `runpod_job_id` is `None`:
- Raises exception: `"Failed to submit job to GPU"`
- Job marked as `failed`
- Frontend will see error

---

### Step 4: Poll RunPod Job Status
**File:** `backend/app/api/routes/avatar.py:137-296`

**Lines 141-142:** Polls every 5 seconds (max 60 attempts = 5 minutes)

**Lines 144-145:** Gets job status from RunPod:
```
GET https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{runpod_job_id}
Headers: Authorization: Bearer {RUNPOD_API_KEY}
```

**File:** `backend/app/services/runpod.py:63-126`

**Status Flow:**
1. `IN_QUEUE` → Job waiting for worker
2. `IN_PROGRESS` → Job running on GPU
3. `COMPLETED` → Job finished successfully
4. `FAILED` / `CANCELLED` → Job failed

**When `COMPLETED` (Lines 154-293):**
- ✅ Extracts `output` from RunPod response
- ✅ Decodes base64 files: `files_bytes = {...}`
- ✅ Uploads all files to Supabase Storage
- ✅ Updates database with results

---

### Step 5: Upload Files to Supabase
**File:** `backend/app/services/supabase.py:180-224`

**What happens:**
- For each file in `files_bytes`:
  1. Determines filename from `file_key`
  2. Uploads to: `avatars/{user_id}/{filename}`
  3. Gets public URL
  4. Returns dict: `{file_key: public_url}`

**File Structure in Supabase:**
```
avatars/
  └── {user_id}/
      ├── avatar_textured.glb
      ├── skin_texture.png
      ├── body_original.obj
      ├── smpl_params.npz
      ├── body_tpose.obj
      ├── body_apose.obj
      ├── measurements.json
      └── ...
```

**Why organized by user_id:**
- Each user's files are isolated
- Easy to find user's files
- Prevents conflicts

---

### Step 6: Update Database
**File:** `backend/app/services/supabase.py:59-93`

**What happens:**
- Updates `fit_passports` table:
  - `avatar_url` → Main GLB file URL
  - `status` → `"completed"`
  - `measurements` → Individual columns (chest, waist, etc.)
  - `pipeline_files` → JSONB with all file URLs
  - `processing_completed_at` → Timestamp

**Verification (Lines 244-272):**
- Reads back from database
- Checks `avatar_url` contains `user_id`
- Verifies all pipeline files linked correctly

---

### Step 7: Frontend Polls for Completion
**File:** `frontend/lib/api.ts:164-187`

**What happens:**
- Frontend calls: `GET /api/avatar/status/{job_id}` every 2 seconds
- **File:** `backend/app/api/routes/avatar.py:313-336`
- Returns current job status and progress
- When `status === "completed"`, frontend stops polling
- Displays avatar and measurements

---

## 📁 File Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Settings (reads .env)
│   │
│   ├── api/
│   │   └── routes/
│   │       ├── avatar.py       # ⭐ MAIN AVATAR ENDPOINT
│   │       ├── health.py       # Health check
│   │       ├── measurements.py # Measurements update
│   │       └── events.py       # Analytics
│   │
│   ├── models/
│   │   ├── avatar.py           # Pydantic request/response models
│   │   ├── events.py
│   │   └── user.py
│   │
│   ├── services/
│   │   ├── runpod.py           # ⭐ RUNPOD API CLIENT
│   │   └── supabase.py         # ⭐ SUPABASE CLIENT
│   │
│   └── tasks/
│       ├── avatar_tasks.py     # Celery tasks (optional)
│       └── celery_app.py
│
├── requirements.txt            # Python dependencies
├── .env                        # ⚠️ Environment variables (NOT in git)
└── env.example                 # Template for .env
```

---

## 🔍 Error Points & Diagnostics

### ❌ Error 1: Backend Won't Start
**Symptom:** `ModuleNotFoundError: No module named 'pydantic_settings'`

**Fix:**
```bash
cd /Volumes/Expansion/mvp_pipeline/backend
pip install -r requirements.txt
```

**Check:** All dependencies installed
```bash
python3 -c "import fastapi, uvicorn, pydantic_settings, supabase, httpx; print('✅ All deps OK')"
```

---

### ❌ Error 2: Jobs Not Reaching RunPod Queue
**Symptom:** Dashboard shows 0 jobs, no jobs in queue

**Diagnostics to check:**

1. **Check if using Mock Service:**
   Look in backend logs:
   ```
   [RunPod Service] ⚠️  RunPod not configured - using MOCK service
   ```
   
   **If you see this:** RunPod credentials not set!

2. **Check .env file:**
   ```bash
   cd /Volumes/Expansion/mvp_pipeline/backend
   grep RUNPOD .env
   ```
   
   Should show:
   ```
   RUNPOD_API_KEY=rp_xxxxx...
   RUNPOD_ENDPOINT_ID=xxxxx...
   ```

3. **Check RunPod Service initialization:**
   Look for these logs when backend starts:
   ```
   [RunPod Service] Initializing...
   [RunPod Service] API Key: SET
   [RunPod Service] Endpoint ID: xxx
   [RunPod Service] ✅ Using real RunPod service
   [RunPod Service] Base URL: https://api.runpod.ai/v2/xxx
   ```

4. **Check job submission:**
   When avatar creation starts, look for:
   ```
   [Avatar] 🚀 Starting avatar job: job-abc123
   [Avatar] ✓ Using real RunPod service
   [RunPod] Submitting job to: https://api.runpod.ai/v2/xxx/run
   [RunPod] Response status: 200
   [RunPod] ✅ Job submitted successfully: runpod-job-uuid
   ```

**If you see:**
```
[RunPod] Response status: 401
```
→ **Invalid API key!**

```
[RunPod] Response status: 404
```
→ **Invalid endpoint ID!**

```
[RunPod] ❌ Submit error: 403
```
→ **Endpoint doesn't exist or no permission!**

---

### ❌ Error 3: Photo URL Issues
**Symptom:** RunPod job fails to download photo

**Check logs:**
```
[Avatar] ✓ Using signed URL for photo (path: user_id/file.jpg)
```

**If you see:**
```
[Avatar] ⚠️  Warning: Failed to create signed URL
```
→ Photo bucket might not be private, or Supabase key wrong

---

### ❌ Error 4: Job Stuck in Queue
**Symptom:** Job shows `IN_QUEUE` forever

**Possible causes:**
1. **No workers available** (dashboard warning: "Supply of your primary GPU choice is currently low")
2. **Worker crashed** (check RunPod worker logs)
3. **Endpoint not receiving jobs** (check endpoint settings)

**Fix:** Ensure workers are running in RunPod dashboard

---

### ❌ Error 5: Job Completes But No Files
**Symptom:** RunPod job completes, but `files_bytes` is empty

**Check RunPod handler logs:**
- Should show: `"files_base64": {...}` in output
- If missing, RunPod handler isn't returning files

**Check backend logs:**
```
[Avatar] Files to upload: 5
[Avatar] Files uploaded: 0
```
→ Upload failed or no files in response

---

## ⚙️ Configuration Required

### Backend `.env` File
**Location:** `/Volumes/Expansion/mvp_pipeline/backend/.env`

**Required variables:**
```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...  # Service role key (NOT anon key!)

# RunPod
RUNPOD_API_KEY=rp_xxxxx...  # ⚠️ REQUIRED - Get from RunPod dashboard
RUNPOD_ENDPOINT_ID=xxxxx...  # ⚠️ REQUIRED - Your endpoint ID

# Storage Buckets
PHOTOS_BUCKET=photos
AVATARS_BUCKET=avatars
```

**⚠️ CRITICAL:** Without `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`, backend uses **Mock Service** and jobs won't reach RunPod!

---

## 🔄 Complete Flow Diagram

```
┌─────────────┐
│   Frontend  │
│  (Next.js)  │
└──────┬──────┘
       │ 1. POST /api/avatar/create
       │    {user_id, photo_url, height, gender}
       ▼
┌─────────────────────────────────────┐
│     Backend API (FastAPI)           │
│  /api/avatar/create endpoint        │
│  - Validates request                │
│  - Creates job_id                   │
│  - Updates DB: status="processing"  │
│  - Starts background task           │
│  - Returns job_id immediately       │
└──────┬──────────────────────────────┘
       │
       │ 2. Background Task Starts
       ▼
┌─────────────────────────────────────┐
│  process_avatar_job()               │
│  - Prepares signed photo URL        │
│  - Checks RunPod service type       │
│  - Submits to RunPod                │
└──────┬──────────────────────────────┘
       │
       │ 3. POST to RunPod API
       ▼
┌─────────────────────────────────────┐
│     RunPod Service                  │
│  POST /v2/{endpoint_id}/run         │
│  - Validates API key                │
│  - Queues job                       │
│  - Returns runpod_job_id            │
└──────┬──────────────────────────────┘
       │
       │ 4. Job in Queue
       ▼
┌─────────────────────────────────────┐
│     RunPod GPU Worker               │
│  - Downloads photo                  │
│  - Runs avatar pipeline             │
│  - Returns base64 files             │
└──────┬──────────────────────────────┘
       │
       │ 5. Poll Status (every 5s)
       ▼
┌─────────────────────────────────────┐
│  Backend Polls RunPod               │
│  GET /v2/{endpoint_id}/status/{id}  │
│  - Checks status                    │
│  - When COMPLETED: gets output      │
└──────┬──────────────────────────────┘
       │
       │ 6. Upload Files
       ▼
┌─────────────────────────────────────┐
│  Supabase Storage                   │
│  - Uploads GLB, OBJ, PNG files      │
│  - Organizes by user_id             │
│  - Returns public URLs              │
└──────┬──────────────────────────────┘
       │
       │ 7. Update Database
       ▼
┌─────────────────────────────────────┐
│  Supabase Database                  │
│  fit_passports table                │
│  - avatar_url                       │
│  - measurements                     │
│  - pipeline_files (JSONB)           │
│  - status="completed"               │
└──────┬──────────────────────────────┘
       │
       │ 8. Frontend Polls Status
       ▼
┌─────────────────────────────────────┐
│  GET /api/avatar/status/{job_id}    │
│  - Returns job status               │
│  - When completed: returns results  │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────┐
│   Frontend  │
│  Displays   │
│  Avatar     │
└─────────────┘
```

---

## 🔍 How to Verify Errors

### 1. Check Backend Logs
**When backend starts, you should see:**
```
Starting TryOn API...
[RunPod Service] Initializing...
[RunPod Service] API Key: SET
[RunPod Service] Endpoint ID: xxx
[RunPod Service] ✅ Using real RunPod service
```

**If you see:**
```
[RunPod Service] ⚠️  RunPod not configured - using MOCK service
```
→ **Fix:** Set `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` in `.env`

---

### 2. Check When Avatar Creation Starts
**You should see:**
```
[Avatar] 🚀 Starting avatar job: job-abc123
[Avatar]   User ID: xxx
[Avatar]   Height: 175 cm
[Avatar] ✓ Using signed URL for photo
[Avatar] ✓ Using real RunPod service
[RunPod] Submitting job to: https://api.runpod.ai/v2/xxx/run
[RunPod] ✅ Job submitted successfully: runpod-job-uuid
[Avatar] ✅ Job submitted to RunPod: runpod-job-uuid
```

**If you see:**
```
[Avatar] ⚠️  WARNING: Using MOCK RunPod service
```
→ Jobs won't reach RunPod! Check `.env` file.

**If you see:**
```
[RunPod] ❌ Submit error: 401
```
→ Invalid API key! Check RunPod dashboard for correct key.

**If you see:**
```
[RunPod] ❌ Submit error: 404
```
→ Invalid endpoint ID! Check RunPod dashboard for correct endpoint.

---

### 3. Check RunPod Dashboard
**After job submission, you should see:**
- Job appears in RunPod queue
- Status: `IN_QUEUE` → `IN_PROGRESS` → `COMPLETED`

**If nothing appears:**
1. Check backend logs for errors
2. Verify RunPod credentials in `.env`
3. Check RunPod service type (Real vs Mock)

---

## 📝 Key Files to Check

### 1. Backend Configuration
**File:** `backend/.env`
- ✅ `RUNPOD_API_KEY` must be set
- ✅ `RUNPOD_ENDPOINT_ID` must be set
- ✅ `SUPABASE_URL` must be set
- ✅ `SUPABASE_SERVICE_KEY` must be set

### 2. RunPod Service
**File:** `backend/app/services/runpod.py`
- **Line 16-17:** Reads credentials from settings
- **Line 18:** Constructs API URL
- **Line 48-61:** Submits job to RunPod
- **Line 182-219:** Determines Real vs Mock service

### 3. Avatar Route
**File:** `backend/app/api/routes/avatar.py`
- **Line 26-79:** `create_avatar()` endpoint
- **Line 82-159:** `process_avatar_job()` background task
- **Line 122-131:** Submits to RunPod
- **Line 137-296:** Polls for completion

---

## 🚨 Common Issues & Fixes

### Issue: "Nothing in RunPod queue"
**Cause:** Using Mock Service (credentials not set)

**Fix:**
1. Check `.env` file has `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`
2. Restart backend after setting variables
3. Check logs show: `[RunPod Service] ✅ Using real RunPod service`

---

### Issue: "401 Unauthorized"
**Cause:** Invalid RunPod API key

**Fix:**
1. Go to RunPod Dashboard → Settings → API Keys
2. Generate new API key
3. Update `.env` file
4. Restart backend

---

### Issue: "404 Not Found"
**Cause:** Invalid endpoint ID

**Fix:**
1. Go to RunPod Dashboard → Serverless → Your Endpoint
2. Copy endpoint ID from URL or settings
3. Update `.env` file
4. Restart backend

---

### Issue: "Job submitted but never completes"
**Cause:** RunPod worker issues

**Fix:**
1. Check RunPod dashboard → Workers tab
2. Verify worker is running
3. Check worker logs for errors
4. Verify endpoint has workers available

---

## ✅ Verification Checklist

Before testing avatar creation:

- [ ] Backend starts without errors
- [ ] Backend logs show: `[RunPod Service] ✅ Using real RunPod service`
- [ ] `.env` file has all required variables
- [ ] RunPod endpoint has workers available
- [ ] RunPod API key is valid
- [ ] Frontend can reach backend: `curl http://localhost:8000/health`
- [ ] Frontend shows backend is available (not using mock mode)

---

**Last Updated:** January 19, 2026
**Status:** ✅ Complete workflow documentation
