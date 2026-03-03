# Add to cart — instant cart update (research)

## Goal

When the Try On widget adds an item via the Shopify Cart API, the store’s cart (drawer, icon, count) must update **without a full page refresh**.

## Official Shopify behavior

- **Endpoint:** `POST /{locale}/cart/add.js`  
  [Cart API reference](https://shopify.dev/docs/api/ajax/reference/cart)
- **Bundled section rendering:** You can request re-rendered HTML for specific sections in the **same** request:
  - Request body: `items`, `sections` (comma-separated or array), and optionally `sections_url`.
  - Response: in addition to cart/items data, a `sections` object with HTML for each requested section (same keys as in the request).
- **sections_url:** Default is current page (from Referer). Can be set to e.g. `window.location.pathname` or `/cart` to control which template context is used for rendering.
- **Important:** “Each section can be identified by the same ID that was passed in the request.” So the section IDs we **send** must be the ones we use to **find and update** the DOM. Sections that fail to render are returned as `null`.

## How Dawn theme does it

(Dawn is the reference theme; cart refresh is implemented in `assets/cart.js`.)

1. **getSectionsToRender()**  
   Returns an array of `{ id, section, selector }`:
   - `id`: DOM element id (e.g. `'main-cart-items'`, `'cart-icon-bubble'`).
   - `section`: **Section ID to send in the API** — from `document.getElementById(id).dataset.id` when present (dynamic section id, e.g. `template--21946272514334__main-cart-items`), otherwise fallback (e.g. `'cart-icon-bubble'`).
   - `selector`: inner part to replace (e.g. `.js-contents`, `.shopify-section`).

2. **Request**  
   `sections: this.getSectionsToRender().map((section) => section.section)` and `sections_url: window.location.pathname`.

3. **Update DOM**  
   Dawn does **not** replace the whole section node. It finds the section wrapper and updates only its **inner content**:
   - `elementToReplace = document.getElementById(section.id).querySelector(section.selector) || document.getElementById(section.id)`
   - `elementToReplace.innerHTML = getSectionInnerHTML(parsedState.sections[section.section], section.selector)`

So: **innerHTML update only**, not `replaceChild(wholeNode)`. That keeps the section wrapper and avoids breaking custom elements (e.g. `<cart-drawer>`).

References:
- [How Dawn Theme Uses Section Rendering API for Cart Refresh](https://nickdrishinski.com/blogs/shopify/how-dawn-theme-uses-section-rendering-api-for-cart-refresh)
- [Shopify Cart API bundled section rendering (Stack Overflow)](https://stackoverflow.com/questions/69784149/shopify-cart-api-bundled-section-rendering-in-dawn)

## What we had vs what we changed

| Aspect | Before | After (aligned with Dawn + docs) |
|--------|--------|-----------------------------------|
| Section IDs in request | From DOM `shopify-section-*` ids + fallback list | Unchanged (already correct). |
| sections_url | `window.location.pathname` | Unchanged (correct). |
| **Applying response HTML** | `replaceChild(newEl, existing)` (whole node replace) | **`existing.innerHTML = newEl.innerHTML`** only. Preserves section wrapper and avoids breaking basket/custom elements. |
| Matching existing node | getElementById + querySelector by slug; previously also broad `[id*="keySlug"]` (removed earlier to fix “basket disappeared”) | Only `shopify-section-*` wrappers; innerHTML update only. |

## Takeaways

1. **Use the section IDs that exist on the current page** (from `[id^="shopify-section-"]` or `data-id`). On product pages, only cart-drawer and cart-icon-bubble may be present; main-cart-items is often only on `/cart`.
2. **Always send `sections_url`** (e.g. current path) so section HTML is rendered in the right context.
3. **Update only inner HTML** of the section wrapper; do not replace the whole section node. That matches Dawn and avoids breaking the cart UI and custom elements.
4. **Fallback:** If the add response has no sections or they’re null, we still run `refreshCartDrawerDawn()` (fetch `?section_id=cart-drawer` and `?section_id=cart-icon-bubble` and update drawer parts + bubble) and then update count and open the drawer.
