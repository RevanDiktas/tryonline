# Status Report. 2026-06-27

Headline: **Website hardening + booking pass before Web Summit, and Lafam sent the SKUs.**
Six commits shipped to `feature/analytics` (Vercel + Railway): brand-spelling consistency end to
end, three navigation/state bug fixes, only-facts copy, and a real Calendly booking flow replacing
the book-a-call mailtos. Separately: Tryon was accepted as a Web Summit 2026 alpha startup, and
Lafam delivered the pilot SKUs, so that critical path moves from "waiting on Lafam" to "build them."

Branch context: everything shipped to `feature/analytics`. Day-to-day work stays on
`feature/garment-construction`. This report is the only change committed here today.

---

## WHAT SHIPPED TODAY (all on feature/analytics)

### Brand consistency
- **Spelling sweep, public + logged-in** (`d11bb7f`, `8e90377`). "TryOn" -> "Tryon" across the
  marketing site (home, pricing, demo, page title, nav, signup) and the logged-in dashboard
  (brand + shopper dashboards, cohorts, garments, onboarding, widget sign-in, saved items),
  including alt/aria/title text. Code identifiers (`TryOnViewer`, `DashboardTryOnModal`, `onTryOn`)
  left untouched via a word-boundary regex. Also killed an em-dash in the hero eyebrow.

### Bug fixes (`dd70a7b`)
- **Hero avatar clothing disappeared** navigating dashboard -> home. Root cause: `useGLTF` returns a
  shared cached scene we scale in place, so on remount the garment kept its prior scale, unit
  auto-detection mis-read it, and the group-fit shrank the garment to ~2mm while the body stayed
  correct. Fix: reset group + meshes to identity and update the world matrix before measuring.
- **Google/Apple sign in missing on the website.** `shopifyMode` was `isShopifyMode() ||
  !!resolvedShop`, so a stale sessionStorage shop context from a brand's Shopify session forced
  brand-only mode (which hides SSO) on the public site. Brand-only is now strictly the
  Shopify-embedded surface (host/env). The website always shows shopper SSO.
- **Shopify surface could land on the shopper dashboard.** The embedded home redirect now sends any
  signed-in user to `/brand`. Shopify only ever shows the brand dashboard.

### Only-facts copy (`d11bb7f`, `0faa81e`)
- Home return-reduction figure 40% -> 20% to match the conservative, source-cited number the
  pricing ROI math is built on (was self-contradicting).
- Competitor price now "Reportedly $10K to $50K/mo" (True Fit does not publish pricing).
- Scale tier says "security documentation" instead of implying a SOC2 certification we do not hold.
- Removed the live Shopify widget code snippet (CDN URL + data attributes) from the home page.
- Sign-in heading is now a neutral "Welcome back."

### Booking flow (`0faa81e`, `c2f6d30`, `c82fb58`)
- Website brand onboarding now routes to a booked call (high-touch: size charts, 3D garment build,
  widget install; no self-serve billing yet). The Shopify-embedded install path stays self-serve.
- New **`/book`** page embeds the Calendly scheduler (`calendly.com/revan-tryon/30min`, connected to
  `revan@tryon.global` so bookings land in Outlook). Every "Book a call" touchpoint routes there:
  the four pricing-tier CTAs, the pricing final CTA, the pricing nav, and the brand-onboarding
  button. Added a "Book a call" link to the home + demo nav.
- Privacy contact email moved to `revan@tryon.global` (was an off-domain `privacy@tryonline.app`).

---

## STRATEGY

- **Web Summit 2026: accepted as alpha startup.** Decision: go to market as **Tryon**, sell the
  product first, and only rebrand under **Fravash** after traction + MRR + validation justify the
  umbrella. Fravash stays the quiet parent/legal entity. Do not stand up the umbrella while there is
  one product.

---

## VERIFICATION STATUS
- `tsc` clean on every commit; all pushes via isolated worktrees so the dev branch was never
  disturbed.
- **Pending live eyeball (cannot prove from tsc):**
  1. `/book` Calendly embed renders at tryon.global/book and a test booking lands in Outlook. If it
     renders blank, check the event slug and Calendly's embed/domain settings.
  2. Avatar clothing persists across dashboard -> home in a real browser.
  3. Carryover from 2026-06-17: live Shopify spot-check (iframe one-time sign in, `&country=`,
     region recommendation) on raministudios.com.

## LAFAM (status changed today)
- **SKUs received 2026-06-27.** Critical path moves to "Revan builds the garments" (CLO3D / our
  construction pipeline). This is now the active Lafam work item, no longer blocked on Lafam.
- Still pending from Lafam: `.myshopify.com` handle (-> `SHOPIFY_PILOT_SHOPS` + webhook/CORS), and
  confirm the SKU sizing data is in hand.

## NEXT SESSION
1. **Live verification** of the three pending items above once Vercel redeploys.
2. **Lafam: build the received SKUs** into 3D garments; confirm jacket + pants categories end to end.
3. Then the non-Lafam backlog: tall-person length flag for bottoms, elastic waistbands, or the v2
   universal mesh-measurement matching.

## OPEN / DEFERRED (non-Lafam)
- Tall-person length flag for bottoms; elastic waistbands.
- v2 universal mesh-measurement matching (reduces reliance on hardcoded bands).
- Garment construction: elastic cuffs; flared sleeves; length floor; on-model face-bake; grading;
  multi-photo.
