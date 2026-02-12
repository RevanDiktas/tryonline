# Analytics Fork Workflow

**Why:** RunPod is connected to the main repo. We develop analytics (Categories A, B, C) in a fork so we don't disturb the avatar pipeline.

## Setup (one-time)

1. **Create fork** on GitHub:
   - Go to the original repo → Fork
   - Creates `YOUR_USER/mvp_pipeline` (or whatever the fork name is)

2. **Add fork as remote:**
   ```bash
   git remote add analytics https://github.com/YOUR_USER/mvp_pipeline.git
   # Or with SSH:
   git remote add analytics git@github.com:YOUR_USER/mvp_pipeline.git
   ```

3. **Check remotes:**
   ```bash
   git remote -v
   # origin     -> original repo (RunPod pulls from here)
   # analytics  -> your fork (we push here)
   ```

## Daily workflow

```bash
# Work on analytics branch
git checkout feature/analytics

# ... make changes ...

# Push to fork only (NOT origin)
git add .
git commit -m "Category A: schema migration"
git push analytics feature/analytics
```

**Never** `git push origin` while on `feature/analytics` — that could affect RunPod.

## When ready to merge

Options:
- Open PR from fork → original repo (when you want to integrate)
- Or keep separate until you have a dedicated analytics deployment
