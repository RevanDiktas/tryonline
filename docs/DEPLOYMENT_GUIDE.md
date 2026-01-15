# TryOn MVP - Deployment Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION STACK                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐   │
│  │   Vercel    │     │  Railway/   │     │      RunPod         │   │
│  │  (Frontend) │────▶│   Render    │────▶│   (GPU Worker)      │   │
│  │  Next.js    │     │  (Backend)  │     │   4D Humans         │   │
│  └─────────────┘     └─────────────┘     └─────────────────────┘   │
│         │                   │                      │               │
│         │                   ▼                      │               │
│         │            ┌─────────────┐               │               │
│         └───────────▶│  Supabase   │◀──────────────┘               │
│                      │  (DB + S3)  │                               │
│                      └─────────────┘                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Supabase Setup (Database + Storage)

### Create Project
1. Go to [supabase.com](https://supabase.com)
2. Create new project: `tryon-mvp`
3. Note: `Project URL` and `anon key`

### Database Schema

```sql
-- Users (shoppers)
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Avatars
CREATE TABLE avatars (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  photo_url TEXT,
  glb_url TEXT,
  measurements JSONB,
  smpl_params_url TEXT,
  status TEXT DEFAULT 'pending', -- pending, processing, ready, failed
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Brands (B2B clients)
CREATE TABLE brands (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  shopify_shop_domain TEXT,
  api_key TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Garments
CREATE TABLE garments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID REFERENCES brands(id),
  name TEXT NOT NULL,
  shopify_product_id TEXT,
  sizes JSONB, -- {"XS": "url_to_xs.glb", "S": "url_to_s.glb", ...}
  size_chart JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Try-on sessions
CREATE TABLE tryon_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  brand_id UUID REFERENCES brands(id),
  avatar_id UUID REFERENCES avatars(id),
  garment_id UUID REFERENCES garments(id),
  selected_size TEXT,
  fit_result JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Events (analytics)
CREATE TABLE events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID REFERENCES brands(id),
  user_id UUID,
  session_id UUID,
  event_type TEXT NOT NULL, -- avatar_created, tryon_started, size_switched, purchase_completed
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_avatars_user ON avatars(user_id);
CREATE INDEX idx_events_brand ON events(brand_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_garments_brand ON garments(brand_id);
```

### Storage Buckets

Create these buckets in Supabase Storage:
- `avatars` - User avatar GLBs and photos (private)
- `garments` - Garment GLBs (public, CDN-cached)
- `photos` - Original upload photos (private)

```sql
-- Storage policies
-- Allow authenticated users to upload to avatars bucket
CREATE POLICY "Users can upload avatars"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'avatars' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Allow public read of garments
CREATE POLICY "Public garment access"
ON storage.objects FOR SELECT
USING (bucket_id = 'garments');
```

---

## 2. GPU Worker (RunPod)

### Create Serverless Endpoint

1. Go to [runpod.io](https://runpod.io)
2. Create new Serverless Endpoint
3. Use custom Docker image

### Dockerfile

```dockerfile
# gpu-worker/Dockerfile
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y git wget unzip && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy 4D Humans code
COPY 4D-Humans-clean/ ./4D-Humans-clean/
COPY utilities/ ./utilities/
COPY pipelines/ ./pipelines/

# Download HMR2 model weights
RUN python 4D-Humans-clean/download_models.py

# Copy handler
COPY handler.py .

# RunPod handler
CMD ["python", "-u", "handler.py"]
```

### Handler

```python
# gpu-worker/handler.py
import runpod
import subprocess
import json
import os
from supabase import create_client

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_SERVICE_KEY']
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def handler(event):
    """
    RunPod serverless handler for avatar creation.
    Input: {"avatar_id": "uuid", "image_url": "https://..."}
    Output: {"status": "success", "measurements": {...}}
    """
    try:
        avatar_id = event['input']['avatar_id']
        image_url = event['input']['image_url']
        
        # Download image
        os.makedirs('/tmp/input', exist_ok=True)
        subprocess.run(['wget', '-O', '/tmp/input/photo.jpg', image_url], check=True)
        
        # Run 4D Humans pipeline
        subprocess.run([
            'bash', 'pipelines/run_4d_humans_only.sh',
            '/tmp/input/photo.jpg',
            '/tmp/output'
        ], check=True)
        
        # Extract measurements
        from measure import extract_measurements
        measurements = extract_measurements('/tmp/output/body_person0_params.npz')
        
        # Upload results to Supabase
        with open('/tmp/output/body_person0_neutral.glb', 'rb') as f:
            supabase.storage.from_('avatars').upload(
                f'{avatar_id}/avatar.glb', f
            )
        
        # Update database
        supabase.table('avatars').update({
            'status': 'ready',
            'glb_url': f'{SUPABASE_URL}/storage/v1/object/public/avatars/{avatar_id}/avatar.glb',
            'measurements': measurements
        }).eq('id', avatar_id).execute()
        
        return {
            'status': 'success',
            'avatar_id': avatar_id,
            'measurements': measurements
        }
        
    except Exception as e:
        # Update status to failed
        supabase.table('avatars').update({
            'status': 'failed'
        }).eq('id', avatar_id).execute()
        
        return {'status': 'error', 'message': str(e)}

runpod.serverless.start({'handler': handler})
```

### Deploy to RunPod

```bash
# Build and push Docker image
docker build -t your-dockerhub/tryon-gpu-worker:latest ./gpu-worker
docker push your-dockerhub/tryon-gpu-worker:latest

# In RunPod dashboard:
# 1. Create new Serverless Endpoint
# 2. Set Docker image: your-dockerhub/tryon-gpu-worker:latest
# 3. Set GPU: RTX 3090 or A10G (cheapest with enough VRAM)
# 4. Set environment variables: SUPABASE_URL, SUPABASE_SERVICE_KEY
# 5. Note the endpoint URL
```

---

## 3. Backend API (Railway/Render)

### Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and init
railway login
cd /Volumes/Expansion/mvp_pipeline/backend
railway init

# Set environment variables
railway variables set SUPABASE_URL=https://xxx.supabase.co
railway variables set SUPABASE_KEY=eyJ...
railway variables set RUNPOD_API_KEY=xxx
railway variables set RUNPOD_ENDPOINT_ID=xxx

# Deploy
railway up
```

### Or Deploy to Render

1. Create new Web Service on [render.com](https://render.com)
2. Connect GitHub repo
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables

### Environment Variables

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
RUNPOD_API_KEY=rp_xxxxxxxxxxxxxxx
RUNPOD_ENDPOINT_ID=xxxxxxxxxx
JWT_SECRET=your-random-secret-key
CORS_ORIGINS=https://tryon.com,https://your-brand.myshopify.com
```

---

## 4. Frontend (Vercel)

### Deploy to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd /Volumes/Expansion/mvp_pipeline/frontend
vercel

# Set environment variables in Vercel dashboard:
# NEXT_PUBLIC_API_URL=https://your-backend.railway.app
# NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
# NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

### Custom Domain

1. In Vercel dashboard → Domains
2. Add `tryon.com` (or your domain)
3. Update DNS records as instructed

---

## 5. Shopify Integration

### Create Private App

1. Go to Shopify Partners → Apps → Create app
2. Choose "Custom app" for a specific store
3. Set App URL: `https://tryon.com`
4. Set Allowed redirection URLs: `https://tryon.com/callback`
5. Request scopes:
   - `read_products`
   - `read_orders` (for purchase attribution)

### Theme App Extension

Create `shopify/theme-extension/blocks/tryon-button.liquid`:

```liquid
{% comment %}
  TryOn Button - Embeds on Product Page
{% endcomment %}

<div id="tryon-widget" 
     data-product-id="{{ product.id }}"
     data-variant-id="{{ product.selected_or_first_available_variant.id }}"
     data-shop="{{ shop.permanent_domain }}">
</div>

<script>
  (function() {
    const widget = document.getElementById('tryon-widget');
    const iframe = document.createElement('iframe');
    iframe.src = 'https://tryon.com/embed?' + new URLSearchParams({
      product_id: widget.dataset.productId,
      variant_id: widget.dataset.variantId,
      shop: widget.dataset.shop
    });
    iframe.style.cssText = 'width:100%;height:600px;border:none;';
    widget.appendChild(iframe);
  })();
</script>

{% schema %}
{
  "name": "TryOn Virtual Fitting",
  "target": "section",
  "settings": []
}
{% endschema %}
```

### Install on Store

```bash
# Using Shopify CLI
shopify app deploy
```

Or manually:
1. In store admin → Online Store → Themes → Customize
2. Add "TryOn Virtual Fitting" block to product template
3. Save

---

## 6. Production Checklist

### Security
- [ ] All API keys in environment variables (not in code)
- [ ] CORS configured for allowed origins only
- [ ] Rate limiting on API endpoints
- [ ] Input validation on file uploads
- [ ] HTTPS everywhere

### Performance
- [ ] CDN enabled for Supabase Storage
- [ ] GLB files gzip compressed
- [ ] Database indexes created
- [ ] API response caching where appropriate

### Monitoring
- [ ] Error tracking (Sentry)
- [ ] Uptime monitoring (Better Uptime / Pingdom)
- [ ] Performance monitoring (Vercel Analytics)
- [ ] GPU worker logs in RunPod dashboard

### Backup
- [ ] Supabase automatic backups enabled
- [ ] Database export script ready

---

## 7. Cost Estimates (MVP Scale)

| Service | Plan | Monthly Cost |
|---------|------|--------------|
| Vercel | Hobby/Pro | $0-20 |
| Railway | Starter | $5-20 |
| Supabase | Free/Pro | $0-25 |
| RunPod | Pay-per-use | ~$0.05/avatar |
| Domain | Annual | ~$12/year |
| **Total** | | **~$30-70/mo + GPU** |

### GPU Cost Breakdown
- RunPod RTX 3090: ~$0.44/hr
- Avatar creation: ~30 seconds
- Cost per avatar: ~$0.01-0.02
- 1000 avatars/month: ~$15-20

---

## 8. Scaling Notes

### When to Scale

| Metric | Threshold | Action |
|--------|-----------|--------|
| API response time | >500ms | Upgrade Railway plan |
| DB connections | >50 concurrent | Upgrade Supabase |
| GPU queue time | >60s | Add more RunPod workers |
| Storage | >10GB | Review CDN caching |

### Future Scaling
- Move to dedicated GPU server if >10K avatars/month
- Add Redis for caching avatar/garment metadata
- Consider Cloudflare R2 for cheaper storage
- Multi-region deployment for global brands
