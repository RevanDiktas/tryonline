# Garment stress / heatmap simulation — research notes

Purpose: choose an open pipeline that can run on **RunPod** (Linux, GPU optional), ingest **body + garment meshes + measurements**, and output **per-triangle or per-vertex scalar fields** mappable to blue→red in the widget. **CLO3D** is the product reference for *what* designers expect, not necessarily *what we clone*.

---

## 1. What CLO shows (public information)

CLO Virtual Fashion is **closed source**. They do **not** publish solver internals (no public paper describing their cloth PDE, material model, or contact method).

They **do** document *modes* that match your product language:

| CLO term (public/community) | Meaning (high level) |
|------------------------------|----------------------|
| **Strain map** | How the fabric / texture is **distorted** (e.g. garment effectively “too small” for the avatar → high stretch). |
| **Stress map** | How the **avatar influences the pattern** — community descriptions align with **contact / fit pressure** on the garment (often shown with a color scale; some references mention **kPa**-style readouts in the UI). |

**Takeaway:** For your heatmap, decide explicitly which **physical proxy** you implement first:

- **Strain-based heatmap:** stretch of rest → deformed configuration (warp/weft or isotropic stretch ratio). Good for “tight vs loose” in a **pattern / material** sense.
- **Contact / pressure proxy:** normal impulse, gap function, or penetration depth resolved by collision response — closer to “pressure from body on cloth.”
- **Hybrid:** strain where no contact, pressure-weighted where in contact (common in design tools conceptually; implementation is yours).

CLO also offers a **CLO API** ([developer.clo3d.com](https://developer.clo3d.com/)) for **desktop automation** (Python plugins, `Simulate()`, exports). That path assumes **Windows/Mac + CLO license + their runtime**, not a lightweight Linux RunPod container. Useful for **ground-truth comparison** if you have licenses; not the default “clone and deploy” stack.

---

## 2. Open-source and research stacks (similar problems)

Grouped by how close they are to **garment + body + contact + scalars for visualization**.

### 2.1 Full cloth simulators (physics-forward)

| Project | Language / runtime | Notes |
|---------|-------------------|--------|
| **ARCSim** ([Berkeley resource](https://graphics.berkeley.edu/resources/ARCSim/), forks e.g. [jiongchen/arcsim](https://github.com/jiongchen/arcsim)) | C++, JSON scenes | Classic research simulator; adaptive mesh; cited in VTO datasets. **License: non-commercial** — check before production use. |
| **IPC / Codim-IPC** ([ipc-sim/IPC](https://github.com/ipc-sim/IPC), [Codim-IPC](https://github.com/ipc-sim/Codim-IPC)) | C++ | Strong **contact** guarantees; cloth extension (C-IPC). Good reference for **robust collision**. Integration effort: bind or port scenes to your assets. |
| **NVIDIA Warp** `warp.sim` ([NVIDIA/warp](https://github.com/NVIDIA/warp)) | Python → CUDA/CPU | Practical for **custom GPU jobs** on RunPod. Includes cloth examples; you implement **garment + body collision** and **per-element output** (stress proxy). |
| **NvidiaWarp-GarmentCode** ([maria-korosteleva/NvidiaWarp-GarmentCode](https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode)) | Python + Warp | Extends Warp with **self-collision, body collision, attachments** for garment-style XPBD. Closer to a **sewing-pattern / panel** workflow than “random OBJ pair,” but patterns are reusable. |

### 2.2 Differentiable / ML-oriented (often PyTorch)

| Project | Role |
|---------|------|
| **DiffCloth** ([omegaiota/DiffCloth](https://github.com/omegaiota/DiffCloth)) | Differentiable cloth + frictional contact — optimization / research. |
| **DifferentiableCloth** ([williamljb/DifferentiableCloth](https://github.com/williamljb/DifferentiableCloth)) | PyTorch cloth demos — good for **inverse** problems, less “drop-in VTO server.” |
| **Projective dynamics** ([pratyai/projective-dynamics-2022](https://github.com/pratyai/projective-dynamics-2022)) | Python + Numba — **triangle meshes**, springs; useful for **prototyping** strain visualization on cloth-like meshes. |

### 2.3 Virtual try-on / SMPL + garment (collision, not necessarily CLO-style maps)

| Project | Role |
|---------|------|
| **vto-garment-collisions** ([isantesteban/vto-garment-collisions](https://github.com/isantesteban/vto-garment-collisions)) | Garment + **SMPL**; collision-aware deformation (TensorFlow-era). |
| **GAPS**, **ISP**, **SMPLicit** | Generative / draping — strong for **mesh quality**, weaker as a direct “export kPa field” server without extra work. |

These are useful if your **canonical body** is SMPL/SMPL-X and you need **alignment** literature; heatmap still needs an explicit **scalar field** definition on the garment.

---

## 3. What you must define before picking a repo

1. **Input contract:** garment = single closed mesh (OBJ/GLB) vs **panelized / sewed** pattern. CLO works on patterns; many OSS demos work on **single sheets** or **simple tops**.
2. **Scalar for color:** stretch ratio | Cauchy stress proxy | contact gap | combined metric; **units** (kPa) require **material thickness + stiffness calibration** — otherwise use **normalized 0–1** per session for v1.
3. **Body representation:** collision mesh only vs SMPL-X surface; your **cm measurements** enter as **scale checks** or **collision body sizing**, not automatically as CLO’s internal avatars.
4. **License:** ARCSim **non-commercial** vs Apache-style (Warp ecosystem, IPC tooling) for long-term product use.

---

## 4. Suggested tech stack overview (RunPod + your backend)

```
Widget (PDP)
    → Your API (auth, shop, try-on session)
        → Issue signed URLs / bundle: garment mesh, body mesh/OBJ, NPZ/pose, measurements JSON
        → Enqueue RunPod job (job id)
RunPod worker
    → Pull assets (HTTP)
    → Load into sim framework (Warp / IPC-backed / custom)
    → Simulate to steady state (or N steps)
    → Compute per-triangle or per-vertex stress/strain proxy
    → Output: heatmap texture OR vertex colors + optional aggregate JSON
    → Upload result to short-lived storage OR return in callback
Your API
    → Poll / webhook complete → return to iframe
Merchant analytics (later)
    → Aggregate per garment (not per shopper); store rolled-up fields + optional representative image
```

**GPU:** Warp on CUDA fits RunPod **A4000/L40** class machines. Pure CPU IPC/ARCSim is possible but slower for interactive iteration.

**Not “one PNG only”:** The authoritative artifact can be **per-vertex or per-face scalars** + mesh; PNG is a **derived** view for dashboard or quick preview.

---

## 5. Practical research sequence (before clone + deploy)

1. **Spike A (fast):** Garment + rigid/smooth body mesh in **Warp** or **projective-dynamics** — output **stretch** heatmap only (validate pipeline: URL → sim → scalar field → Three.js).
2. **Spike B (contact):** Same with **body collision** using **Warp GarmentCode** patterns or **IPC** literature-aligned constraints — output **penetration depth** or **contact pressure proxy**.
3. **Optional ground truth:** If you have CLO licenses, reproduce **one** garment in CLO and compare **qualitative** hotspot locations (not exact kPa) against Spike B.

---

## 6. References (starting points)

- CLO API docs: [developer.clo3d.com](https://developer.clo3d.com/)
- CLO community — stress vs strain discussion: [support.clo3d.com community post](https://support.clo3d.com/hc/en-us/community/posts/900003118523-Difference-between-stress-map-and-strain-map)
- ARCSim (Berkeley): [graphics.berkeley.edu/resources/ARCSim](https://graphics.berkeley.edu/resources/ARCSim/)
- IPC: [ipc-sim.github.io](https://ipc-sim.github.io/)
- NVIDIA Warp: [github.com/NVIDIA/warp](https://github.com/NVIDIA/warp)
- NvidiaWarp-GarmentCode: [github.com/maria-korosteleva/NvidiaWarp-GarmentCode](https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode)

---

*Last updated: 2026-03-29 — literature survey for internal planning; not legal or licensing advice.*
