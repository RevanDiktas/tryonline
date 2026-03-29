# Roadmap: Heatmaps first, then PERSONA (garment automation deferred)

**Purpose:** Structure the next three big product moves while Shopify review is in flight.  
**Explicitly out of scope for this plan:** Automated garment construction (hardest; revisit after heatmaps + PERSONA are anchored).

**Strategic order (why):**

1. **Fit heatmap procedure** — Hardest *product* decision: where computation runs, what you store, how you show it per shopper per try-on without exploding cost. Locking this avoids rework when PERSONA changes the body mesh.
2. **PERSONA in the pipeline** — Largely an engineering swap: new RunPod worker, iterate until SMPL-X body matches the user; same downstream contracts if you define them now.
3. **Wire heatmaps to the live try-on path** — Once (1) and (2) are clear, implementation is execution.

Related context: `docs/GARMENT_AUTOMATION_RESEARCH.md` (shopper-first: realism → heatmaps → automation).

---

## Part A — Fit heatmap: define the procedure first

### What a “heatmap” means here

A **per try-on** artifact that encodes *where the garment is tight, loose, or stressed* on **that** avatar in **that** pose for **that** garment variant (and optionally size). It is not the same as aggregate analytics; it is **session-scoped fit feedback**.

Outputs that merchants and shoppers can understand:

- **2D map** (texture or UV-mapped overlay on the garment) — shareable, light, works in widget and email.
- **Scalar summary** (e.g. “chest: moderate tension”) — cheap to store, good for analytics rollups.
- **3D vertex weights** (full sim mesh) — highest fidelity, heaviest; usually not sent to browser raw.

### The core tension you called out

| Approach | Pros | Cons |
|----------|------|------|
| **Compute in widget (browser)** | No server storage of every sim; instant feel | Heavy WASM/GPU assumptions; hard to match CLO-quality physics; large download per garment |
| **Compute on server after try-on request** | One job per try-on; quality tools (CLO API, custom sim) possible | **Storage**: N users × M try-ons × K garments; **latency**: user waits or sees “generating…” |
| **Precompute offline (brand-only)** | One heatmap per garment template per pose | **Not per user** — wrong for “your body”; only useful as generic merchandising |

**Conclusion for v1:** Per-user-per-try-on heatmaps almost certainly require **server-side** (or RunPod GPU) generation. The open design choice is **synchronous vs async** and **what you persist**.

### Recommended architecture (v1 target)

1. **Trigger:** When the shopper completes a meaningful try-on action (e.g. “size locked”, “add to cart”, or “view heatmap” button), enqueue **one** heatmap job keyed by:
   - `user_id` (or anonymous session id if allowed)
   - `tryon_session_id` (you already create sessions)
   - `garment_id` + `size` + `avatar_version` (hash or PERSONA/SMPL-X pipeline version)

2. **Compute:** Worker loads **avatar mesh** (GLB or internal sim format) + **garment asset** for that SKU/size. Runs a **lightweight** stress/tension pass first (e.g. simplified shell or proxy mesh); optionally upgrade to CLO-scripted batch later for hero SKUs.

3. **Persist (minimal):**
   - **Always:** JSON summary `{ regions: [...], scores: [...], computed_at, pipeline_version }` — small, queryable.
   - **Usually:** One **PNG/WebP** (fixed resolution) per try-on — bounded size (~50–300 KB with compression).
   - **Avoid until needed:** Full per-vertex float buffers in Supabase Storage (expensive at scale).

4. **Show in widget:**
   - **Not** full sim in the iframe on first paint.
   - **Pattern:** “Fit map” panel loads **summary + image URL** from your API after job completes (poll or WebSocket). Same pattern as avatar polling today.

5. **Retention / cost control:**
   - TTL on raw heatmap images (e.g. 90 days) or cap per user (last N try-ons).
   - Merchant dashboard sees **aggregates** derived from summaries, not every PNG.

### Steps you can take **now** (before Shopify feedback)

- [ ] Add a **heatmap job** placeholder type in backend (stub endpoint + DB row) tied to `tryon_session_id`.
- [ ] Define **API contract**: `GET /api/tryon/:session/heatmap` → `{ status, summary?, image_url? }`.
- [ ] In widget, add a **disabled / “Coming soon”** or internal-only flag for “Fit map” UI so product and design are scoped.
- [ ] Document **garment-side inputs** required for sim (per size: low-poly collision mesh? 2D pattern? — align with what you already export from CLO).

---

## Part B — PERSONA in the pipeline (after heatmap contract is sketched)

**Reference:** [PERSONA project page](https://mks0601.github.io/PERSONA/) (single-image personalized avatars; SMPL-X–centric).

### Role of PERSONA

- **Replaces or augments** the current “single photo → body mesh” stage on RunPod.
- **Downstream consumers** stay stable if you standardize outputs:
  - Same **SMPL-X** (or compatible) rig parameters where possible.
  - Same **export**: textured GLB + optional **neutral pose** mesh for simulation.

### Integration shape

1. New RunPod endpoint (or job type): `avatar_persona` vs current pipeline flag.
2. Version string in `fit_passports` or metadata: `avatar_pipeline_version` (for heatmap cache invalidation).
3. A/B or pilot: one internal user until quality bar is met; then migrate shoppers gradually.

### Steps you can take **now**

- [ ] Freeze **GLB schema**: which bones, scale, origin; document for sim team.
- [ ] Spin up **isolated** RunPod template with PERSONA deps; no production traffic.
- [ ] Output diff tool: side-by-side current avatar vs PERSONA for same photo set (subjective + measurement deltas).

### Dependency on Part A

Heatmap jobs should accept **`avatar_version`** so you do not mix sim results across pipeline generations.

---

## Part C — Order of execution (three big things)

| Phase | Focus | Outcome |
|-------|--------|---------|
| **1** | Heatmap **procedure** + API + storage rules | No ambiguity on “where it runs” and “what we save” |
| **2** | PERSONA **RunPod** path + quality bar | Better body fidelity; same contracts as today |
| **3** | Connect heatmap worker to **PERSONA** mesh + widget UI | Per-try-on fit map in production |

Garment automation (TailorNet/CLO batch/etc.) stays in `docs/GARMENT_AUTOMATION_RESEARCH.md` until Phase 1–3 are shipped or piloted.

---

## Part D — While Shopify review is pending

Low-risk, high-leverage:

- Heatmap **stub** API + DB migration (session link, status enum).
- Widget **feature flag** for fit map panel (off in production).
- PERSONA **RunPod skeleton** + one-photo regression set (not customer-facing).

Avoid: committing to CLO API costs at scale until heatmap storage and UX are validated on stub data.

---

## Open questions (resolve in Phase 1 design sessions)

1. **Merchant vs shopper visibility:** Is the heatmap shopper-facing, brand-only, or both?
2. **Legal/comfort:** Any copy or UI needed so tension maps are not read as medical advice?
3. **Anonymous try-ons:** Heatmap keyed by session only vs require Fit Passport?
4. **Minimum garment asset** for v1 sim: can every SKU provide a collision mesh, or only “Try On enabled” SKUs?

---

*Last updated: 2026-03-29 — aligns with Ramin Studios first deployment readiness (security, widget, avatar creation on main/feature split).*
