# Safe storage cleanup on your Mac (no projects or apps)

This guide only targets **caches, logs, and system junk**. It does **not** touch your projects or applications.

## Already done for you (from this session)

- **npm cache** – verified and garbage-collected
- **pip cache** – purged (~486 MB); pip will re-download packages when needed
- **Homebrew** – old formulae and logs cleaned (~70 MB freed)

## Safe steps you can do yourself

### 1. Empty Trash
- In Finder: **Finder → Empty Trash** (or right-click Trash → Empty Trash).
- Frees whatever is in Trash.

### 2. Clear user caches (optional, safe)
- **Finder → Go → Go to Folder…** (⇧⌘G) → type: `~/Library/Caches`
- You can **delete the contents** of this folder (or delete whole subfolders). Apps will recreate caches when needed. This can free **several GB** (e.g. 3+ GB is common).
- Do **not** delete the `Caches` folder itself, only its contents.

### 3. Reduce “System Data” in macOS
- **About This Mac → Storage → Manage** (or **System Settings → General → Storage**).
- Use the suggestions there, especially:
  - **Empty Trash**
  - **Remove old iOS backups** (if you don’t need them): list of backups with sizes; delete ones you don’t need.
  - **Delete Time Machine local snapshots** (if you use Time Machine): often labeled as “Local snapshots” or similar; removing them can free a lot of space. Your Time Machine backup on the external drive is not deleted.

### 4. Clear old logs (optional)
- **Go to Folder…** → `~/Library/Logs`
- You can delete old log files or entire app log folders you don’t care about. This can free hundreds of MB. Avoid deleting the `Logs` folder itself.

### 5. Docker (only if you use Docker)
- If you use Docker Desktop: **Docker → Preferences → Resources → Advanced → Disk image size**, and/or run:  
  `docker system prune -a`  
  (removes unused images/containers; you can re-pull images later.)

---

**Summary:** No projects or applications are removed. Only caches, Trash, old backups, snapshots, and logs are targeted. If in doubt, skip a step or only delete one cache/log folder at a time.
