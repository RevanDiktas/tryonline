# Brand dashboard: one brand, their data only

**Rule:** When a brand (e.g. Moncler) logs in to the brand dashboard, they see **only their own** KPIs and TryOn widget performance. They do **not** see other brands’ data, and there is **no** UI to choose or switch to another brand.

---

## How it works

1. **Events are attributed to a brand**  
   Each analytics event has `brand_id` (and `shop_domain`) set when we track it. So we know “this event belongs to brand X.”

2. **Dashboard is scoped by the logged-in brand**  
   When the brand user is authenticated:
   - We know **who they are** (their brand, e.g. from session: `brand_id` or `shop_domain`).
   - **Every** analytics API call (Category A, B, C) is made with that brand’s `brand_id` (or `shop_domain`) as a filter.
   - The UI shows only those metrics. No dropdown like “Which brand do you want to see?” — they only see their own dashboard.

3. **No cross-brand visibility**  
   Moncler never sees Zara’s data. The dashboard is “your KPIs,” not “pick any brand.”

---

## Current vs intended state

- **Today:** The brand page may still have a **shop selector** (e.g. “All shops” / “demo.myshopify.com”) for **demo or internal** use. That is not intended for production with real brand partners.
- **Intended:** Once brand login exists, the dashboard should:
  - Derive the current brand from the **session** (e.g. `brand_id` or `shopify_domain` linked to the logged-in brand account).
  - Pass that **single** brand to all analytics calls.
  - **Remove** any “view as another shop/brand” selector so brands cannot see each other’s data.

---

## Summary

- **brand_id on events** = correct: it ties each event to the right brand.
- **Brand dashboard** = that brand’s data only, based on who is logged in. No list of brand IDs, no picking another brand — just “your” dashboard.
