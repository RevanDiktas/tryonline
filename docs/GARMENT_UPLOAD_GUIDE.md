# Garment Upload Guide — Supabase Storage + Mapping

How to upload garment GLBs and map them correctly so the widget loads the right models per product.

---

## 1. Folder structure in the `garments` bucket

Use **product_id** (same as `shopify_product_id`) as the folder name:

```
garments/
  demo-npc-tshirt/
    xs.glb
    s.glb
    m.glb
    l.glb
    xl.glb
  your-shopify-product-id/
    xs.glb
    s.glb
    ...
```

**Convention:** `garments/{product_id}/{size}.glb` (lowercase size: xs, s, m, l, xl)

---

## 2. Public storage URLs

For bucket `garments`, public URL pattern:

```
https://{project_ref}.supabase.co/storage/v1/object/public/garments/{product_id}/{size}.glb
```

Example (project `cykwthsbrylonconqlfz`):

```
https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/demo-npc-tshirt/xs.glb
https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/demo-npc-tshirt/s.glb
...
```

---

## 3. Add/update row in `garments` table

The products API looks up by `shopify_product_id`. Each product needs one row:

| Column | Value |
|--------|-------|
| `name` | Product name (e.g. "NPC Oversized T-Shirt") |
| `category` | tops, bottoms, outerwear, dresses, accessories |
| `shopify_product_id` | Product ID — **must match** folder name and URL param |
| `sizes` | JSONB with size → full URL |
| `size_chart` | JSONB with size → {chest, waist, hips} in cm |
| `model_type` | `"garment_only"` (optional column; if missing, defaults to garment_only) |

**Example `sizes` (full URLs):**

```json
{
  "xs": "https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/demo-npc-tshirt/xs.glb",
  "s": "https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/demo-npc-tshirt/s.glb",
  "m": "https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/demo-npc-tshirt/m.glb",
  "l": "https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/demo-npc-tshirt/l.glb",
  "xl": "https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/demo-npc-tshirt/xl.glb"
}
```

**Example `size_chart`:**

```json
{
  "xs": {"chest": 88, "waist": 72, "hips": 86},
  "s": {"chest": 92, "waist": 76, "hips": 90},
  "m": {"chest": 100, "waist": 84, "hips": 98},
  "l": {"chest": 108, "waist": 92, "hips": 106},
  "xl": {"chest": 116, "waist": 100, "hips": 114}
}
```

---

## 4. SQL to insert/update

```sql
-- Replace {PROJECT_REF} with your Supabase project ref (e.g. cykwthsbrylonconqlfz)
INSERT INTO public.garments (name, category, shopify_product_id, sizes, size_chart)
VALUES (
  'NPC Oversized T-Shirt',
  'tops',
  'demo-npc-tshirt',
  '{
    "xs": "https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/demo-npc-tshirt/xs.glb",
    "s": "https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/demo-npc-tshirt/s.glb",
    "m": "https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/demo-npc-tshirt/m.glb",
    "l": "https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/demo-npc-tshirt/l.glb",
    "xl": "https://cykwthsbrylonconqlfz.supabase.co/storage/v1/object/public/garments/demo-npc-tshirt/xl.glb"
  }'::jsonb,
  '{
    "xs": {"chest": 88, "waist": 72, "hips": 86},
    "s": {"chest": 92, "waist": 76, "hips": 90},
    "m": {"chest": 100, "waist": 84, "hips": 98},
    "l": {"chest": 108, "waist": 92, "hips": 106},
    "xl": {"chest": 116, "waist": 100, "hips": 114}
  }'::jsonb
);

-- If row already exists, update instead:
-- UPDATE public.garments SET sizes = '{...}'::jsonb, size_chart = '{...}'::jsonb WHERE shopify_product_id = 'demo-npc-tshirt';
```

---

## 5. Steps summary

1. Create folder `{product_id}` in the `garments` bucket.
2. Upload `xs.glb`, `s.glb`, `m.glb`, `l.glb`, `xl.glb` (garment-only meshes).
3. Copy the public URL of each file from Supabase.
4. Insert/update a row in `garments` with `shopify_product_id = {product_id}` and the `sizes` JSON.
5. Use `?product_id={product_id}` in the widget URL — it will fetch from the API and load these URLs.

---

## 6. Mapping flow

| Step | What happens |
|------|--------------|
| Widget opens with `product_id=demo-npc-tshirt` | Fetches `GET /api/products/demo-npc-tshirt/tryon-config` |
| API | Looks up `garments` where `shopify_product_id = 'demo-npc-tshirt'` |
| API returns | `model_urls` (from `sizes`), `size_chart`, `model_type: garment_only` |
| Widget | Loads user avatar + all garment URLs, maps them, preloads for instant switching |
