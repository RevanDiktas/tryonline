# How to Set Dropbox URLs in RunPod Environment Variables

## Quick Answer: YES - Paste the FULL link!

---

## Step-by-Step

### 1. Get Dropbox Share Links

For each file in Dropbox:
1. Right-click the file → **Share** → **Copy link**
2. You'll get a link like: `https://www.dropbox.com/s/XXXXX/filename.pkl?dl=0`

### 2. Convert to Direct Download

Change `?dl=0` to `?dl=1` at the end:

**Before:** `https://www.dropbox.com/s/XXXXX/filename.pkl?dl=0`  
**After:** `https://www.dropbox.com/s/XXXXX/filename.pkl?dl=1`

**OR** use this format (also works):
`https://dl.dropboxusercontent.com/s/XXXXX/filename.pkl`

### 3. Paste FULL URL in RunPod

Go to RunPod → Your Endpoint → Settings → Environment Variables

Add these 6 variables with the **FULL URLs**:

```
DROPBOX_CHECKPOINT_URL=https://www.dropbox.com/s/XXXXX/epoch=35-step=1000000.ckpt?dl=1
DROPBOX_SMPL_NEUTRAL_URL=https://www.dropbox.com/s/XXXXX/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl?dl=1
DROPBOX_SMPL_MALE_URL=https://www.dropbox.com/s/XXXXX/basicmodel_m_lbs_10_207_0_v1.1.0.pkl?dl=1
DROPBOX_SMPL_FEMALE_URL=https://www.dropbox.com/s/XXXXX/basicmodel_f_lbs_10_207_0_v1.1.0.pkl?dl=1
DROPBOX_MEAN_PARAMS_URL=https://www.dropbox.com/s/XXXXX/smpl_mean_params.npz?dl=1
DROPBOX_JOINT_REGRESSOR_URL=https://www.dropbox.com/s/XXXXX/SMPL_to_J19.pkl?dl=1
```

---

## Example

**Full example of what to paste:**

```
DROPBOX_CHECKPOINT_URL=https://www.dropbox.com/s/abc123xyz456/epoch%3D35-step%3D1000000.ckpt?dl=1
```

**Note:** If the filename has special characters (like `=` in `epoch=35-step=1000000.ckpt`), Dropbox might encode them as `%3D`. That's fine - use the link exactly as Dropbox gives it, just change `?dl=0` to `?dl=1`.

---

## Quick Checklist

- [ ] Uploaded all 6 files to Dropbox
- [ ] Got share link for each file
- [ ] Changed `?dl=0` to `?dl=1` in each link
- [ ] Pasted FULL URL (including `https://...`) into RunPod env vars
- [ ] Set all 6 environment variables
- [ ] Triggered Docker build

---

## Important Notes

✅ **DO:** Paste the complete URL starting with `https://`  
✅ **DO:** Include `?dl=1` at the end  
✅ **DO:** Use the exact link Dropbox gives you (even if it has encoded characters)

❌ **DON'T:** Just paste the file ID  
❌ **DON'T:** Remove the `https://` part  
❌ **DON'T:** Forget the `?dl=1` at the end

---

That's it! The build script will download directly from these Dropbox URLs. 🚀
