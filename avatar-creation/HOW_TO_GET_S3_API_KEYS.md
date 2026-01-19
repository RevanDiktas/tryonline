# How to Get RunPod S3 API Keys

## Step-by-Step Guide

### Step 1: Go to RunPod Settings

1. **Visit:** https://www.runpod.io/console/user/settings
2. **Log in** to your RunPod account

### Step 2: Find S3 API Keys Section

1. Scroll down to find **"S3 API Keys"** section
2. It should be near other API/security settings

### Step 3: Generate S3 API Key

1. Click **"Generate New Key"** or **"Create S3 API Key"** button
2. You'll get:
   - **Access Key ID** (this is your **User ID**, usually `user_XXXXX`)
   - **Secret Access Key** (this is the S3 API secret - **save this immediately!**)

⚠️ **Important:** The secret key is only shown once! Copy it immediately.

### Step 4: Get Your User ID

If you don't see your User ID:
1. Look at the top of the settings page
2. Or check your account/profile page
3. It's usually in format: `user_XXXXX` or just `XXXXX`

---

## Alternative: Check Your Network Volume Page

Sometimes the S3 API credentials are shown on the Network Volume page:

1. Go to: https://www.runpod.io/console/storage
2. Click on your Network Volume
3. Look for "S3 API Access" section
4. It might show the credentials there

---

## What You Need

After getting the keys, you need:

1. **AWS_ACCESS_KEY_ID** = Your RunPod User ID (e.g., `user_XXXXX`)
2. **AWS_SECRET_ACCESS_KEY** = The S3 API Secret Key you generated

---

## Set Environment Variables

Once you have both:

```bash
export AWS_ACCESS_KEY_ID="your-user-id"
export AWS_SECRET_ACCESS_KEY="your-s3-api-secret"
```

Then run the upload script:

```bash
cd /Volumes/Expansion/mvp_pipeline
python3 upload_models_to_volume.py --models-dir ~/models_4dhumans
```

---

## Can't Find It?

If you can't find the S3 API Keys section:

1. **Check if you have the right permissions** - Some accounts might need to enable this feature
2. **Try the Network Volume page** - Sometimes credentials are shown there
3. **Contact RunPod support** - They can help you generate S3 API keys

---

## Quick Links

- **Settings:** https://www.runpod.io/console/user/settings
- **Storage/Volumes:** https://www.runpod.io/console/storage
- **RunPod Docs:** https://docs.runpod.io/serverless/storage/s3-api
