# Garment Automation Research (CLO + TailorNet Hybrid)

## Why this document exists

You currently construct garments manually in CLO, which produces quality but does not scale.
This document defines a research-based path to automate garment construction while preserving fit quality.

Main question:
- What is accessible now with your current stack?
- What requires internal investment?
- What should be sequenced first after pilot validation and funding?

---

## Executive conclusion

The best near-term strategy is a shopper-first hybrid:

1. Improve avatar realism and fit confidence first (shopper satisfaction and trust).
2. Ship fit friction heatmaps so merchant actions improve quickly from real usage data.
3. Scale garment construction automation on top of that validated demand/data loop.

Implementation still uses CLO as the quality anchor and TailorNet/newer methods as acceleration modules.

---

## Research summary (practical takeaways)

## 1) TailorNet (CVPR 2020)

Reference:
- TailorNet paper: https://openaccess.thecvf.com/content_CVPR_2020/html/Patel_TailorNet_Predicting_Clothing_in_3D_as_a_Function_of_Human_CVPR_2020_paper.html
- Repo: https://github.com/chaitanya100100/TailorNet

What it is good at:
- Predicting garment deformation as a function of body shape, pose, and style.
- Useful for category-constrained garments and realistic draping behavior.

Limitations for your production use:
- Narrow garment categories and dataset assumptions.
- Not a complete "brand asset to production-ready garment" system.
- Still requires a full pipeline around it (ingestion, UV/material handling, QA, multi-size publishing, fallbacks).

Decision:
- Use TailorNet concepts and/or components for deformation and fit behavior, but do not rely on it as the only automation backbone.

## 2) CLO automation potential

Reference:
- CLO API docs: https://developer.clo3d.com/
- Python API page: https://developer.clo3d.com/python.html

What this means for Tryon:
- CLO can be scripted for repeatable operations (loading assets, simulation steps, exports, etc.).
- You can convert current artisanal workflows into semi-automated pipelines while keeping CLO output quality.

Decision:
- CLO scripting is your highest-leverage immediate path because it builds directly on your existing skill and assets.

## 3) Newer garment reconstruction and draping research

References:
- SPnet (single image to sewing-pattern based reconstruction): https://arxiv.org/abs/2312.16264
- DrapeNet (self-supervised multi-garment draping): https://arxiv.org/abs/2211.11277

What this means for Tryon:
- The field is moving toward pattern-aware and self-supervised methods that generalize better than rigid template-only pipelines.
- These are strong R&D directions, but they are not drop-in replacements for merchant-grade operations yet.

Decision:
- Treat these as medium-term modules for automation uplift after you stabilize your ingestion + QA + publishing backbone.

---

## What is accessible now vs what needs investment

## Accessible now (build immediately)

1. **CLO-assisted automation layer**
- Standard garment templates by category (tee, shirt, pants, skirt, etc.).
- Parameterized edits from size charts (chest/waist/hips/length deltas).
- Scripted export pipeline (OBJ/GLB, UV checks, naming standards).

2. **Asset ingestion service**
- Accept brand uploads: product images, size tables, optional pattern files, optional tech packs.
- Normalize metadata into one internal schema.

3. **Human-in-the-loop QA**
- Confidence scoring and checkpoints before publish.
- Manual correction only for low-confidence cases.

4. **Garment CI/CD**
- Ingest -> Build -> Simulate -> Validate -> Publish -> Version.
- Store every garment build with status and provenance.

## Needs internal investment (post-pilot, high priority)

1. **Automatic garment reconstruction modules**
- Image/pattern-to-panel estimation.
- Pattern topology inference for more categories.

2. **Material behavior estimation**
- Infer stretch, thickness, drape class from metadata/images.
- Improve simulation realism across fabrics.

3. **Automatic grading + fit sanity checks**
- Multi-size generation from base garment + size table.
- Rule-based and learned plausibility checks.

4. **Model training and evaluation loop**
- Build data flywheel from try-on outcomes + returns + fit feedback.
- Train category-specific and eventually cross-category garment intelligence models.

---

## Recommended target architecture

## Layer A: Ingestion
- Inputs: photos, size chart, optional patterns/tech pack.
- Output: normalized garment spec.

## Layer B: Construction
- Route 1 (default): CLO template + scripted parameterization.
- Route 2 (R&D assist): ML module proposes panels/shape, CLO validates/refines.

## Layer C: Simulation and fit checks
- Simulate on canonical body set and key fit-passport archetypes.
- Compute fit and geometry quality metrics.

## Layer D: QA and publish
- Auto-approve high confidence.
- Human review for low confidence.
- Publish model URLs + size chart package to production tables.

## Layer E: Feedback learning
- Attach post-purchase outcomes (keep/return, size exchanges, fit complaints).
- Feed model/heuristic improvements.

---

## Build plan after 1-3 pilot brands (your stated priority)

## Phase 1 (0-8 weeks): Realistic avatar and shopper confidence
- Improve avatar realism ladder (visual quality, body fidelity, texture consistency).
- Tighten fit passport output quality checks and rendering consistency.
- Add shopper-facing confidence UX (clear fit confidence messaging and reliability indicators).

Success metric:
- Higher shopper completion and repeat try-on usage, lower drop-off during onboarding/try-on.

## Phase 2 (8-16 weeks): Fit friction heatmaps and merchant actions
- Ship fit friction heatmaps by SKU/size/region/cohort.
- Add drill-down explanations: where friction happens and why.
- Convert insights into action recommendations (size chart adjustments, stock/size mix, PDP fixes).

Success metric:
- Merchants get actionable recommendations tied to measurable conversion/return deltas.

## Phase 3 (16-32 weeks): Garment construction automation
- Build ingestion schema/uploader for brand assets (images, size tables, patterns/tech packs).
- Build CLO scripting wrappers + automated export/validation.
- Add human-in-the-loop QA routing and internal garment build status dashboard.
- Pilot ML-assisted construction modules (pattern-aware reconstruction, material estimation).

Success metric:
- Manual CLO workload per SKU drops materially while preserving garment quality.

---

## Investment map

## Low investment / high immediate return
- CLO scripting pipeline
- Standardized templates
- Ingestion normalization
- QA gates and publish automation

## Medium investment / high leverage
- Auto grading engine
- Fit plausibility scoring
- Internal tooling for correction workflows

## High investment / strategic moat
- Pattern-aware generative models
- Material behavior inference
- End-to-end learned garment construction

---

## Risks and mitigations

1. **Risk: automation lowers quality**
- Mitigation: confidence thresholds + mandatory QA for low confidence outputs.

2. **Risk: category expansion complexity**
- Mitigation: launch by category waves (tees -> shirts -> pants -> outerwear).

3. **Risk: over-investing in frontier ML too early**
- Mitigation: first build deterministic pipeline and collect clean training data.

4. **Risk: bottleneck shifts from construction to QA**
- Mitigation: build QA scoring and triage early, not after scale pain appears.

---

## Decision statement

After pilot confirmation and early funding, prioritize in this order:

1. **Realistic avatar quality** (shopper trust, satisfaction, repeat usage).
2. **Fit friction heatmaps** (merchant action engine: SKU/size/region insights).
3. **Garment automation backbone** (ingestion, CLO scripting, grading, QA, publish).

This order is correct because:
- shoppers are the data source and growth engine,
- better shopper trust improves data quality and product loop strength,
- heatmaps monetize that data through merchant outcomes,
- automation then scales supply once demand and insight loops are validated.

---

## Realistic avatar track: PERSONA-first evaluation

Reference:
- PERSONA project page: https://mks0601.github.io/PERSONA/

Decision:
- Add **PERSONA** as the primary R&D candidate for realistic, pose-driven, single-image avatars.
- Keep current SMPL pipeline as production fallback until PERSONA proves stable on latency, identity consistency, and animation robustness.

Why this fits Tryon:
- Single-image input aligns with your onboarding UX.
- Pose-driven cloth deformation aligns with perceived realism goals.
- SMPL-X compatibility keeps the stack interoperable with existing body/animation tooling.

Validation checklist before production rollout:
1. Identity preservation under different poses.
2. Garment deformation realism under movement.
3. Runtime/cost profile on your GPU budget.
4. Failure cases (occlusion, low light, oversized garments).
5. Consistency with measurement and fit outputs used downstream.

---

## Pressure and fit heatmap research (CLO + alternatives)

## What CLO/MD-style tools expose

References:
- CLO support (stress vs strain): https://support.clo3d.com/hc/en-us/community/posts/900003118523-Difference-between-stress-map-and-strain-map
- CLO pressure tool: https://support.clo3d.com/hc/en-us/articles/115012381348-Pressure
- Marvelous Designer API docs: https://developer.marvelousdesigner.com/

Observed model:
- **Stress/pressure map**: pressure or force concentration across garment regions (commonly visualized as color scale).
- **Strain map**: local fabric deformation/stretch behavior under body/pose constraints.
- **Pressure parameter** in CLO/MD context is also used for inflation effects, but fit analysis is mostly stress/strain driven.

Implication for Tryon:
- You do not need to replicate CLO internals exactly to get merchant value.
- You need a stable, explainable approximation that ranks where garments are too tight/loose by body region and SKU/size.

## Build-vs-buy options for pressure/strain heatmaps

### Option A (recommended near term): Mimic with simulation-derived fit metrics
- Use your existing avatar + garment meshes.
- Compute per-vertex/per-region proxies:
  - distance penetration / collision pressure proxy,
  - stretch ratio (simulated vs rest edge length),
  - area distortion (triangle area ratio).
- Aggregate to body regions (chest, waist, hips, thighs, shoulders, sleeves).
- Render heatmap overlays and merchant summaries.

Pros:
- Fastest path, fully controllable, explainable, no vendor lock-in.
- Enough for "fit friction heatmap" value.

Cons:
- Not physically perfect Cauchy stress unless you add FEM-grade physics.

### Option B (mid term): FEM-grade engine for stress fields
- Framework candidates:
  - SOFA FEM/stress visualization: https://sofa-framework.github.io/doc/components/solidmechanics/fem/elastic/tetrahedronfemforcefield/
  - NVIDIA Warp simulation module: https://nvidia.github.io/warp/modules/sim.html
- Build true stress/strain field computation and then map to merchant-readable regions.

Pros:
- Higher physical fidelity and stronger defensibility.

Cons:
- Higher complexity and engineering cost.

### Option C (tool-assisted prototyping): Blender simulation + scripted extraction
- Blender cloth settings + Python API:
  - https://docs.blender.org/manual/en/latest/physics/cloth/settings/physical_properties.html
  - https://www.blender.org/api/current/bpy.types.ClothSettings.html
- Use for rapid prototyping, not final production core.

Pros:
- Quick iteration and visualization.

Cons:
- Harder to scale/operate as production compute backend.

## Open-source repos worth cloning for exploration

1. DrapeNet (self-supervised draping): https://github.com/liren2515/DrapeNet
2. DIG (implicit garment draping): https://github.com/liren2515/DIG
3. DiffCloth (differentiable cloth simulation): https://github.com/omegaiota/DiffCloth

These are best treated as R&D references, not immediate production drop-ins.

---

## Recommended implementation order (aligned with your priorities)

1. **Realistic avatar**
   - Add PERSONA benchmark track and compare against current pipeline.
2. **Fit friction heatmaps**
   - Ship Option A proxy heatmaps first (merchant-action focused).
3. **Garment automation**
   - Build CLO-assisted ingestion/templating/grading/QA/publish.
4. **Physics uplift**
   - Evaluate Option B (SOFA/Warp) for higher-fidelity stress fields once heatmaps are monetizing.

