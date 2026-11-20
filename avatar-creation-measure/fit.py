"""Fit an SMPL-X body to a stated height and weight.

The photo gives a shape estimate (betas). Instead of stretching that body to the stated
height (which inflates every girth), find the body CLOSEST to the estimate, in the model's
own shape space, whose height and mass equal what the person told us.

Shape coefficients are unit-variance principal components, so Euclidean distance between
beta vectors is the natural "how different are these two bodies" measure. Height and mass
are close to linear in the betas, so a few constrained Gauss-Newton steps land exactly.
"""
import numpy as np
import torch

BODY_DENSITY_KG_M3 = 985.0   # whole-body average with lungs at rest; calibrated in the population check


def tpose_vertices(layer, betas):
    return layer(betas=betas, body_pose=torch.zeros(1, 21, 3, dtype=betas.dtype)).vertices[0]


def height_cm(v):
    return (v[:, 1].max() - v[:, 1].min()) * 100.0


def mass_kg(v, faces, density=BODY_DENSITY_KG_M3):
    t = v[faces]
    volume = (t[:, 0] * torch.cross(t[:, 1], t[:, 2], dim=1)).sum() / 6.0
    return volume.abs() * density


def fit_to_height_weight(layer, betas0, target_height_cm, target_weight_kg=None,
                         density=BODY_DENSITY_KG_M3, iters=12, max_beta=4.0):
    """Returns (betas [n], info). betas0: array [n]. Weight is optional: without it only
    height is enforced."""
    faces = torch.as_tensor(layer.faces.astype(np.int64))
    b0 = torch.as_tensor(np.asarray(betas0, dtype=np.float32)).reshape(1, -1)
    b = b0.clone()
    for _ in range(iters):
        b = b.detach().requires_grad_(True)
        v = tpose_vertices(layer, b)
        h = height_cm(v)
        rows = [torch.autograd.grad(h, b, retain_graph=True)[0][0]]
        resid = [float(target_height_cm) - float(h)]
        if target_weight_kg is not None:
            m = mass_kg(v, faces, density)
            rows.append(torch.autograd.grad(m, b)[0][0])
            resid.append(float(target_weight_kg) - float(m))
        J = torch.stack(rows).detach().double().numpy()          # constraints x n
        r = np.asarray(resid, dtype=np.float64)
        d0 = (b0 - b.detach()).double().numpy()[0]               # pull back towards the estimate
        # minimise |delta - d0|^2 subject to J delta = r
        lam = np.linalg.solve(J @ J.T + 1e-9 * np.eye(len(r)), r - J @ d0)
        delta = d0 + J.T @ lam
        step = np.clip(delta, -1.5, 1.5)                         # trust region: the maps are only locally linear
        b = (b.detach() + torch.as_tensor(step, dtype=torch.float32)[None]).clamp(-max_beta, max_beta)
        if np.abs(r).max() < 0.02 and np.abs(step).max() < 1e-3:
            break
    with torch.no_grad():
        v = tpose_vertices(layer, b)
        info = {"height_cm": float(height_cm(v)),
                "mass_kg": float(mass_kg(v, faces, density)),
                "beta_shift": float((b - b0).norm()),
                "max_abs_beta": float(b.abs().max())}
    return b[0].numpy(), info
