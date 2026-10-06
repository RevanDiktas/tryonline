# Self-serve brands and the Shopify App Store (plan, 2026-10-06)

Goal: a fashion brand finds TryOn, installs it from the Shopify App Store, and has Find my
size live on every product the same day, with no help from us. Paid plans run through
Shopify's billing. 3D garments stay a done-for-you service inside the Try-On and Scale plans.

## Where we are (researched 2026-10-06)

- Rejected twice:
  1. §4.5.5, test credentials (March 2026): the test accounts used Google sign-in.
  2. §1.2.1/1.2.2, off-platform billing (2026-05-08): the listing said free, the app showed paid plans.
  The 2026-05-09 resubmit (tryon-13) has no recorded outcome. Find that last reviewer email first.
- After install, the merchant must create a separate TryOn email/password account inside
  Shopify admin (two logins). That is the root of the §4.5.5 risk.
- App Bridge loads only on the /app shell; session tokens are fetched but never verified.
- No Shopify Billing / Managed Pricing; nothing enforces plans.
- GDPR compliance webhooks answer 200 but delete nothing; working deletion code exists at
  other URLs that no config points to.
- No theme-editor deep link; the in-app "Getting started" step 3 is plain text.
- tryon-cart.js and tryon-size.js are ~14 KB each; the 10 KB theme-check rule is switched off.
- `brand/register` links any signed-up user to an unclaimed store by typed domain (takeover risk).
- `orders/paid` and `refunds/create` on the public app need an approved protected-customer-data request.

## The plan

### Step 1: one login (Shopify session tokens)
- On install and on every admin load, App Bridge gives a session token; the backend verifies it
  (HS256 with the app secret, `aud` = client id, `dest` = shop) and exchanges it for an access
  token (Shopify token exchange). No TryOn password inside Shopify, ever.
- The brand row is created or linked from the *verified* shop, never from a typed domain. This
  removes the store-claim takeover.
- App Bridge on every embedded page (not only /app), so navigation, toasts and the title bar work.
- Website sign-in for brands stays (email/password) for people who are not in Shopify admin.
- Result: the reviewer only needs a Shopify login to the dev store. §4.5.5 can no longer fail on our side.

### Step 2: billing through Shopify (Managed Pricing)
- Plans in the Partner dashboard as Managed Pricing: Free, Size Pro $29, Try-On $109 (+ usage
  for extra avatars), Scale $279; 30-day trial. Shopify hosts the plan page; we read the active
  subscription and gate features.
- Gates: Free = 500 size recommendations a month + badge; Size Pro = unlimited + fit passport +
  full analytics; Try-On/Scale = 3D try-on, avatar allowance, garment limits.
- Usage charges for extra avatars via a capped usage line item.
- The listing text and plan names match the app exactly (the §1.2.1 failure).

### Step 3: guided setup inside Shopify admin
- Home screen checklist that ticks itself: "Add the TryOn button" (deep link
  `/admin/themes/current/editor?template=product&addAppBlockId={client_id}/tryon-button&target=mainSection`),
  "Turn on the cart helper" (app embed deep link), "Upload a size chart" (optional), "Pick a plan".
- Detect that the block is placed (needs `read_themes`) so the step turns green.
- Size charts per product type, not per garment, so one upload covers a catalogue.

### Step 4: compliance and quality
- Point the compliance topics at real deletion logic (customers/redact, shop/redact,
  customers/data_request) and test them.
- `frame-ancestors https://admin.shopify.com https://{shop}` CSP on embedded pages.
- Uninstall: deactivate without losing data; check the `is_active` column bug.
- Trim tryon-cart.js and tryon-size.js below 10 KB and re-enable the theme-check rule.
- Either file the protected-customer-data request for orders/refunds (justification: return
  analytics) or drop those webhooks from the public app until approved.
- Update API versions (2024-01 / 2024-10 → current).

### Step 5: listing and submission (run the shopify-app-review-prep checklist)
- Listing: icon, 3-6 screenshots at 1600x900, a short screencast, description that promises
  only what ships, privacy URL, support email.
- Test store tryon-9626 with a seeded product; test instructions with the exact click path.
- Minutes before submitting: install fresh in incognito, use the main feature, uninstall.

## Order and size

| Step | Size | Depends on |
|---|---|---|
| 1. One login | 2-3 days | - |
| 2. Billing | 2 days | 1 |
| 3. Guided setup | 1-2 days | 1 |
| 4. Compliance | 1-2 days | - (parallel) |
| 5. Listing + submit | 1 day + review time | 1-4 |

About 1.5-2 weeks of work, then Shopify's review time.

## Decisions for Revan
1. Find and share the last reviewer email (after the 2026-05-09 resubmit).
2. Free plan badge: show "Powered by TryOn" on Free (helps growth) — yes/no.
3. Orders/refunds webhooks on the public app: file the data request now, or launch without return analytics and add it later.
