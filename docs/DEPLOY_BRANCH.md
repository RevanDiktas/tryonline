# Deploy branch

**Railway (backend) and Vercel (frontend) deploy from `feature/analytics`.**

- **Do not push directly to `main`** for deployable changes.
- Workflow: merge or cherry-pick from `main` into `feature/analytics`, then **push to `feature/analytics`** to trigger deploys.
- Or do all new work on `feature/analytics` and push there.

```bash
# After making changes (on main or feature/analytics):
git checkout feature/analytics
git pull origin feature/analytics
git merge main   # if you did the work on main
git push origin feature/analytics
```

Railway is connected to **feature/analytics**; pushing there redeploys the backend.
