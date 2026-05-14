# Status report 2026-05-14 (Thu)

## Headline

Pitch deck pass: fixed the global slide-clipping bug (right side of every slide was cut off on any laptop narrower than 16:9) and rewrote the source citations on slides 12 / 13 / 14 after a structured audit. Two fabricated stats and four mis-attributions removed; two unverifiable NL stats on slide 14 swapped for CBS-sourced replacements. Two commits to `feature/analytics`, Vercel auto-deployed.

## What happened

### 1. Pitch-deck layout fix (commit `ccc69f9`)

User reported "text overwriting" and "pages not fitting the screen" on slides 12 / 13 / 14. Captured headless screenshots at 1920×1080 (all clean) then at 1440×900 (broken everywhere). Root cause was in `frontend/public/pitch-deck.html` `fit()` at line 1644-1645: scale was computed as `vh/1080` only, ignoring viewport width.

On a 1440×900 laptop:
- scale = 900/1080 = 0.833
- tile_w = 1920 × 0.833 = 1600 px (wider than the 1440 viewport)
- right ~160 px of every slide tile clipped off the visible viewport
- top-right chrome label, bottom-right chrome label, full right column of stat values, and right-column dark panel content all lost their right side

Fix: `const s = Math.min(vh / DESIGN_H, vw / DESIGN_W);`. Slide now fits both axes. Letterboxes appear top/bottom on shorter screens, which is the correct tradeoff. Verified clean at 1920×1080, 1440×900, 1366×768, and 2560×1440.

Diagnosis was slowed by headless Chrome not letting me jump to a target slide via `scrollLeft` — the assignment took (debug overlay confirmed `scrollLeft=19419` after assignment) but the rendered output stayed at the previous scroll position. Worked around by adding a temp `?s=N` URL param that just hides all non-target slides via `display: none`. Removed before commit.

### 2. Citation audit + rewrite (commit `3c11ba2`)

Spawned a research agent to verify all 13 citations on slides 12-14 in parallel. Results:

- 3 verified clean (kept): $3-5T McKinsey QB Oct 2025, $385B Morgan Stanley Dec 2025, 50M Aura Consortium 2024
- 2 fabricated (replaced):
  - Slide 12 "18% Salesforce US AI-comm 2025" → "20% AI-influenced Cyber Week orders, Salesforce Dec 2025" (verified)
  - Slide 13 "$590B counterfeit fashion" → "$467B global counterfeit trade, 62% apparel, OECD-EUIPO 2025"
- 4 close-but-mis-attributed (tightened):
  - Slide 12 4,700%: dropped "Similarweb · Adobe · State of Fashion 2026" attribution → "Adobe Analytics · July 2025"
  - Slide 13 $2.67T → $16.1T: low end was wrong → "$310B → $16.1T BCG · ADDX · 2022"
  - Slide 13 "EU DPP mandatory 2027" → "EU DPP textiles · delegated act 2027" (label clarified; mandatory enforcement is ~2028)
  - Slide 13 $227B resale → $205B (GlobalData 2024)
- 2 unverifiable NL stats on slide 14 (swapped for CBS-sourced replacements):
  - "21,000+ online fashion brands NL · Trustbonus.org" → "22,985 Dutch online clothing shops Q1 2024 · CBS · Thuiswinkel.org"
  - "60%+ Dutch brands · major production delays · FashionUnited 2024" → "+21% Dutch retail bankruptcies YoY 2024 · CBS via NL Times · Dec 2024"
- 1 verified but mis-attributed (corrected): slide 14 27% NL SME financing source line changed from "DNB Financial Stability Report · Basel III-F · SMEs 6.4x" to "DNB · Fintech Lending Stats · 2025"
- 1 reframed (Mordor fashion-NFT figure was unverifiable): slide 13 second stat changed from "$25B fashion NFT by 2030" to "$229B global NFT market by 2031" (Mordor's broader segment is verifiable)

### 3. Memory updates

- `project_pitch_deck_2026-05-12.md` — replaced the "best-effort, needs verification" section with the final audited citation list and a note on today's `fit()` layout fix.

## What did not happen today

- **No drape pipeline work.** v45.12.1 cache still source of truth.
- **PDP spot-check on live Ramin store** against the v45.12.1 drape cache — confirmed by user as "looks good", closing out.
- **Brand dashboard remake** — queued.
- **Shopper lobby v0.2** — queued.
- **mockPassport in /demo** — confirmed as fine.

## Lessons

1. The pitch-deck "text overwriting" report was misdiagnosed yesterday as a per-slide content overflow. It was a single global bug in `fit()` affecting every slide. Lesson: when the same symptom appears on multiple slides, look at shared layout code before tweaking individual slide markup.
2. Citation audits with a research-agent + structured table return are fast (≈50 sec for 13 claims) and produce a much higher-confidence rewrite than guessing. Worth doing before any investor-facing deck export.
3. Headless Chrome screenshot fidelity is finicky. `--window-size` doesn't give exactly that viewport (1920×1080 produced a 993 px logical inner height in our case); `scrollLeft` assignments to scroll-snap-less containers may not render at the expected position even when readback says they did. For slide-isolated screenshots, hide all other slides via `display: none` instead — bypasses scroll positioning entirely.

## Tomorrow

Continue website bug pass. User said "we will continue more website bugs tomorrow." Pending in queue:

- **Brand dashboard remake** (intended for showcase)
- **Shopper lobby v0.2** (Fortnite-lobby sketch at `/dashboard/lobby`, open since 2026-05-02)
- Any other website surface bugs the user flags
