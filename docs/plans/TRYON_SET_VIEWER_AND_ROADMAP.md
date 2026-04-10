# Try-on sets (zip-up + pants), UPT, and viewer roadmap

Planning doc for Ramin pilot work and later parity with the public TryOn Shopify app.

---

## 1. Product reality

- PDP may show a **set** (e.g. zip-up + sweatpants) while Shopify sells **one product** or a bundle.
- 3D can be authored as **matched sizes** (one GLB per size) or **independent top/bottom sizes**.

---

## 2. 3D asset strategies

### A) One GLB per (top, bottom) pair (matrix)

- Keys like `s-s`, `m-l` → URL (nine files for S/M/L × S/M/L).
- **Pros:** Matches “top S + bottom L” as a single authored asset; simplest Three.js (one load).
- **Cons:** File count grows as **n²** with more sizes.

### B) One GLB per slot (top vs bottom)

- e.g. `tops.m.glb` + `bottoms.l.glb`, composed in the scene.
- **Pros:** **2 × sizes** files; any combination.
- **Cons:** Alignment, clipping, skinning, z-fighting; pipeline must export consistent rest pose.

### C) Hybrid

- Default “matched” combo as one GLB; extra files only for hero mismatches.

**Pilot default:** (A) is fastest if you already export pairs. **Scale:** plan migration to (B) or cap allowed pairs.

---

## 3. Viewer UX

- Row 1: **Top** sizes (only sizes with assets in config).
- Row 2: **Bottom** sizes (same).
- Resolve asset: `key = f(top, bottom)` for matrix, or two loads for slots.
- Hide/disable pairs with no URL (same pattern as hiding XS/XL when no GLB).

---

## 4. API / `tryon-config` shape (freeze before public app)

Extend beyond flat `model_urls[size] → url`:

**Matrix (A):**

```json
{
  "model_urls": {
    "s-s": "https://...",
    "m-l": "https://..."
  }
}
```

**Slots (B):**

```json
{
  "slots": {
    "top": { "s": "...", "m": "..." },
    "bottom": { "s": "...", "m": "..." }
  }
}
```

Keep a single **product id** convention (handle vs Admin numeric) documented in the brand app and theme block so pilot and production match.

---

## 5. Merchandising / UPT / cart

- **“Includes sweatpants”**, bundle savings, and **UPT** are primarily **Shopify** concerns: product setup, discounts, bundle apps, or two line items.
- The iframe can carry **two variant ids** (or a bundle id) in the URL when you extend `TRYON_ADD_TO_CART` / `tryon-cart.js` to add multiple lines.
- Keep marketing copy in the **theme** or product description; keep the viewer focused on **fit visualization**.

**Phases:**

1. Pilot: matrix or single combined product; cart may stay **one variant** until flows are defined.
2. Before listing app: lock **config schema** + cart payload.
3. Scale: split meshes or bounded matrix + multi-add cart.

---

## 6. Console noise vs real TryOn bugs (2026-04)

When debugging the embedded viewer on `raminstudios.com`:

| Message | Typical cause |
|--------|----------------|
| `sessionStorage` + **sandbox** + `contentScript.js` | **Browser extension** (not TryOn). Filter console by `test-viewer` / `[TryOn]`. TryOn wraps `sessionStorage` in `try/catch` where needed. |
| **MetaMask** errors | Wallet extension; ignore for try-on. |
| **favicon 404** | Harmless. |
| **postMessage** target `null` / Shopify **web-pixels** “unsafe attempt to load URL” | Often **Shopify analytics / third-party** scripts in iframe context; not the Supabase GLB fetch. |
| **Garment URL** | Must be full `https://…supabase.co/storage/...` from `/api/products/.../tryon-config`. Avatar loading proves network/CORS to Supabase is generally OK for public buckets. |

**Sold out (`UITVERKOCHT`)** does not remove GLBs from the viewer; it only affects purchase UI.

**If the garment “flashes then disappears”:** see viewer fixes (scene ready + preload complete before first `displayModel`; garment `depthWrite` / small Z offset) in `frontend/public/test-viewer.html` commit history.

---

## 7. Next implementation tickets (suggested order)

1. Lock **tryon-config** JSON for **two dimensions** (matrix v1).
2. **test-viewer.html:** second size row + key resolver + Add to cart payload (size pair).
3. **tryon-cart.js** / parent: optional second variant or documented manual bundle step.
4. Theme block settings: optional **secondary product** metafield for pants (later).

This file is the working spec; revise when Shopify app review status or product taxonomy changes.
