#!/usr/bin/env python3
"""
Procedural jewellery builder for the Vanrycke AR pilot.

Why a script and not a modelling session: Vanrycke has no CAD, all three pieces are
cable-chain based, and the AR page needs a known local frame per piece (origin, up,
forward). Generating the geometry means the frame, the real-world millimetre
dimensions and the mesh are produced together and can be regenerated in seconds when
a dimension changes.

Pieces (all 18k rose gold, Vanrycke "Calamity Jane" / "One"):
  ring      bague-calamity-jane          cable chain ring closed by a tube bar
  earring   chaine-doreille-calamity-jane threader: chain teardrop loop, chain drop, bar post
  necklace  collier-one                   cable chain + bezel-set brilliant, worn shape

Frames (metres in the GLB, Three.js axes: +Y up, +Z towards the camera):
  ring      origin on the finger axis, ring axis = +Y (finger direction), bar at +Z (back of hand)
  earring   origin at the piercing point, hangs along -Y, front of the ear = +Z
  necklace  origin at the neck centre at collar height, pendant hangs at +Z (front), lowest -Y

Usage:
  python3 build_jewelry.py --out ./out [--ring-size 52] [--chain-cm 42] [--piece all|ring|earring|necklace]
"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial

# --------------------------------------------------------------------------- materials
# 18k rose gold, linear sRGB-ish base colour. Metals in glTF keep their colour in
# baseColor with metallic = 1; roughness low but not mirror, polished jewellery ~0.2.
METALS = {
    # glTF baseColorFactor is LINEAR, and trimesh writes these bytes as value / 255 with no
    # conversion. The first rose value (236, 190, 172) was picked as an sRGB swatch, so it
    # was stored far paler than intended and displayed as (246, 224, 214): next to white gold
    # the two were hard to tell apart on a phone (Revan, 2026-11-15). The values below are
    # linear reflectance x 255. 18k rose gold: (0.93, 0.64, 0.54), between the old value and
    # copper (0.955, 0.637, 0.538 is already copper once the red is this strong; keep green
    # and blue above it or it reads as copper again).
    "rose": PBRMaterial(name="rose_gold", baseColorFactor=[237, 163, 138, 255], metallicFactor=1.0, roughnessFactor=0.15),
    # 18k white gold (rhodium-plated): near-neutral, a touch warm, slightly brighter than steel.
    "white": PBRMaterial(name="white_gold", baseColorFactor=[244, 243, 240, 255], metallicFactor=1.0, roughnessFactor=0.14),
}
ROSE_GOLD = METALS["rose"]
# Diamond: glTF core cannot express transmission/IOR; the AR page swaps any material
# named "diamond" for a MeshPhysicalMaterial at load time. Keep it white here.
DIAMOND = PBRMaterial(
    name="diamond",
    baseColorFactor=[255, 255, 255, 255],
    metallicFactor=0.0,
    roughnessFactor=0.02,
)


# --------------------------------------------------------------------------- helpers
def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def resample_by_arclength(points: np.ndarray, step: float) -> np.ndarray:
    """Even arc-length resampling of a polyline. Returns the points at 0, step, 2*step ...
    up to the curve length (last sample may fall short of the end by < step)."""
    seg = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = cum[-1]
    targets = np.arange(0.0, total + 1e-9, step)
    out = np.empty((len(targets), 3))
    for k in range(3):
        out[:, k] = np.interp(targets, cum, points[:, k])
    return out


def rotation_minimizing_frames(points: np.ndarray, up_hint: np.ndarray):
    """Tangent + two normals per point without twist (double-reflection method).
    Twist matters here: alternating link orientation is relative to this frame, a
    twisting frame would make the chain visibly corkscrew."""
    n = len(points)
    T = np.zeros((n, 3))
    T[:-1] = points[1:] - points[:-1]
    T[-1] = T[-2]
    T = np.array([_unit(t) for t in T])
    N = np.zeros((n, 3))
    r0 = up_hint - np.dot(up_hint, T[0]) * T[0]
    if np.linalg.norm(r0) < 1e-6:
        r0 = np.cross(T[0], [1.0, 0.0, 0.0])
    N[0] = _unit(r0)
    for i in range(n - 1):
        v1 = points[i + 1] - points[i]
        c1 = float(np.dot(v1, v1))
        if c1 < 1e-14:
            N[i + 1] = N[i]
            continue
        rL = N[i] - (2.0 / c1) * np.dot(v1, N[i]) * v1
        tL = T[i] - (2.0 / c1) * np.dot(v1, T[i]) * v1
        v2 = T[i + 1] - tL
        c2 = float(np.dot(v2, v2))
        N[i + 1] = _unit(rL - (2.0 / c2) * np.dot(v2, rL) * v2) if c2 > 1e-14 else rL
    B = np.cross(T, N)
    return T, N, B


def tube_along(centerline: np.ndarray, radius: float, closed: bool, sides: int = 8) -> trimesh.Trimesh:
    """Sweep a circle of `radius` along a polyline (closed = ring of points)."""
    pts = centerline
    if closed:
        pts = np.vstack([centerline, centerline[:1]])
    T, N, B = rotation_minimizing_frames(pts, np.array([0.0, 0.0, 1.0]))
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ring = np.stack([np.cos(ang), np.sin(ang)], axis=1) * radius
    verts = []
    for i in range(len(pts) - (1 if closed else 0)):
        for c, s in ring:
            verts.append(pts[i] + c * N[i] + s * B[i])
    verts = np.array(verts)
    m = len(pts) - (1 if closed else 0)
    faces = []
    rows = m if closed else m - 1
    for i in range(rows):
        i2 = (i + 1) % m
        for j in range(sides):
            j2 = (j + 1) % sides
            a, b = i * sides + j, i * sides + j2
            c, d = i2 * sides + j, i2 * sides + j2
            faces.append([a, c, b])
            faces.append([b, c, d])
    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    if not closed:
        # Cap the ends so open tubes (bar, post) don't show their inside.
        cap0 = [[0, j2, j] for j, j2 in zip(range(sides), list(range(1, sides)) + [0])]
        base = (m - 1) * sides
        cap1 = [[base, base + j, base + j2] for j, j2 in zip(range(sides), list(range(1, sides)) + [0])]
        mesh = trimesh.Trimesh(
            vertices=verts, faces=np.vstack([mesh.faces, np.array(cap0[1:-1]), np.array(cap1[1:-1])]), process=False
        )
    mesh.fix_normals()
    return mesh


# --------------------------------------------------------------------------- primitives
def cable_link(length: float, width: float, wire: float, sides: int = 8, arc_pts: int = 7) -> trimesh.Trimesh:
    """One oval cable-chain link lying in the XY plane, long axis = X, centred at origin.
    `length`/`width` are OUTER dimensions, `wire` the wire diameter."""
    r = (width - wire) / 2.0            # centreline radius of the rounded ends
    s = max(length - width, 0.0) / 2.0  # half straight length
    pts = []
    # right semicircle (from top-right going clockwise through +X to bottom-right)
    for a in np.linspace(np.pi / 2, -np.pi / 2, arc_pts):
        pts.append([s + r * np.cos(a), r * np.sin(a), 0.0])
    # left semicircle
    for a in np.linspace(-np.pi / 2, -3 * np.pi / 2, arc_pts):
        pts.append([-s + r * np.cos(a), r * np.sin(a), 0.0])
    return tube_along(np.array(pts), wire / 2.0, closed=True, sides=sides)


def cable_chain(curve: np.ndarray, link_len: float, link_w: float, wire: float,
                closed: bool = False, up_hint=(0.0, 0.0, 1.0)) -> tuple[trimesh.Trimesh, int]:
    """Lay interlocking links along `curve` (polyline, mm). Consecutive links alternate
    90° about the tangent. Pitch = outer length minus two wire diameters, so the end
    wire of one link sits inside the hole of the previous."""
    pitch = link_len - 2.0 * wire
    pts = np.vstack([curve, curve[:1]]) if closed else curve
    # Fill the curve exactly: round the link count and stretch the pitch a hair so a
    # link sits on both ends of an open chain (the ends are what connect to a bezel,
    # a bar or a jump ring) and no overlap appears where a closed chain meets itself.
    total = float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))
    n_links = max(1, int(round(total / pitch)))
    if closed:
        samples = resample_by_arclength(pts, total / n_links)[:n_links]
    else:
        samples = resample_by_arclength(pts, total / n_links)[: n_links + 1]
        if len(samples) < n_links + 1 or np.linalg.norm(samples[-1] - pts[-1]) > 1e-6:
            samples = np.vstack([samples[:n_links], pts[-1:]])
    T, N, B = rotation_minimizing_frames(np.vstack([samples, samples[:1]]) if closed else samples,
                                         np.array(up_hint, dtype=float))
    link = cable_link(link_len, link_w, wire)
    meshes = []
    for i, p in enumerate(samples):
        t, n, b = T[i], N[i], B[i]
        plane_y = n if i % 2 == 0 else b
        M = np.eye(4)
        M[:3, 0] = t
        M[:3, 1] = plane_y
        M[:3, 2] = np.cross(t, plane_y)
        M[:3, 3] = p
        li = link.copy()
        li.apply_transform(M)
        meshes.append(li)
    return trimesh.util.concatenate(meshes), len(samples)


def bar(length: float, diameter: float, sides: int = 24) -> trimesh.Trimesh:
    """Short tube bar / earring post along X, centred at origin, with rounded ends."""
    cap = trimesh.creation.capsule(height=max(length - diameter, 0.01), radius=diameter / 2.0, count=[sides, 6])
    cap.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))  # capsule axis Z -> X
    return cap


def brilliant(diameter: float) -> trimesh.Trimesh:
    """Round brilliant with the real 57-facet layout: octagonal table, 8 star facets
    (triangles on the table edges), 8 kite facets (table vertex down to a girdle main),
    16 upper-girdle facets, a 16-sided girdle band, 8 pavilion mains and 16 lower-girdle
    facets meeting at the culet. Proportions: table 57 %, crown 15 %, pavilion 43 % of
    diameter, girdle 2.5 %. Girdle plane at y = 0, table faces +Y."""
    R = diameter / 2.0
    crown_h, g_h, pav_d = 0.15 * diameter, 0.025 * diameter, 0.43 * diameter
    main = np.deg2rad(np.arange(8) * 45.0)                 # table vertices / girdle mains
    half = main + np.deg2rad(22.5)                         # star tips / girdle halves
    g16 = np.deg2rad(np.arange(16) * 22.5)                 # even = mains, odd = halves

    def ring(radius, y, angs):
        return [[radius * np.cos(a), y, radius * np.sin(a)] for a in angs]

    V: list = []
    T = len(V); V += ring(0.57 * R, crown_h, main)
    S = len(V); V += ring(0.79 * R, crown_h * 0.45, half)
    GT = len(V); V += ring(R, 0.0, g16)
    GB = len(V); V += ring(R, -g_h, g16)
    L = len(V); V += ring(0.26 * R, -g_h - pav_d * 0.76, half)
    C = len(V); V += [[0.0, -g_h - pav_d, 0.0]]
    F: list = []
    for i in range(1, 7):
        F.append([T, T + i, T + i + 1])                                   # table
    for k in range(8):
        k1 = (k + 1) % 8
        F.append([T + k, T + k1, S + k])                                  # star k (over edge k..k+1)
        F.append([T + k, S + (k - 1) % 8, GT + 2 * k])                    # kite k, left half
        F.append([T + k, GT + 2 * k, S + k])                              # kite k, right half
        F.append([S + k, GT + 2 * k, GT + 2 * k + 1])                     # upper girdle pair
        F.append([S + k, GT + 2 * k + 1, GT + (2 * k + 2) % 16])
    for k in range(16):
        a, b = GT + k, GT + (k + 1) % 16
        c, d = GB + k, GB + (k + 1) % 16
        F.append([a, c, b]); F.append([b, c, d])                          # girdle band
    for k in range(8):
        gm, gh, gn = GB + 2 * k, GB + 2 * k + 1, GB + (2 * k + 2) % 16
        F.append([gm, L + k, gh]); F.append([gh, L + k, gn])              # lower girdle pair
        F.append([gm, C, L + (k - 1) % 8]); F.append([gm, L + k, C])      # pavilion main
    m = trimesh.Trimesh(vertices=np.array(V), faces=np.array(F), process=True)
    m.fix_normals()
    # Facets must stay flat: unmerge so every face owns its vertices and the exported
    # normals are per-facet, otherwise the viewer smooths the stone into a disc.
    m.unmerge_vertices()
    return m


def bezel(stone_d: float, wall: float, height: float, sides: int = 48) -> trimesh.Trimesh:
    """Bezel cup as on the Vanrycke One: a slightly tapered outer wall, a thin rim that laps
    over the stone's girdle, a seat below the girdle and an open back for light.
    Stone girdle plane is y = 0 (same as brilliant()); the cup extends down to -height."""
    R = stone_d / 2.0
    rim_top = 0.10                       # rim just above the girdle plane; the crown stands proud of it
    lip_in = R * 0.95                    # thin lip over the girdle, as on the One bezel
    lip_h = 0.25
    seat_t = 0.30
    hole = R * 0.55
    ro_top, ro_bot = R + wall, R + wall * 0.75
    # closed profile in (radius, y), counter-clockwise
    prof = np.array([
        [hole, -height], [ro_bot, -height], [ro_top, rim_top], [lip_in, rim_top],
        [lip_in, rim_top - lip_h], [R * 1.03, rim_top - lip_h], [R * 1.03, -height + seat_t],
        [hole, -height + seat_t], [hole, -height],
    ])
    m = trimesh.creation.revolve(prof, sections=sides)
    # revolve builds around +Z; we want +Y up
    m.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
    m.fix_normals()
    return m


# --------------------------------------------------------------------------- pieces
def build_ring(size_fr: float, spec: dict, metal: PBRMaterial = ROSE_GOLD) -> tuple[trimesh.Scene, dict]:
    """Chain ring. FR size == inner circumference in mm. The chain centreline sits
    half a link width outside the finger so the links don't intersect skin."""
    finger_r = size_fr / (2 * math.pi)
    centre_r = finger_r + spec["link_w"] / 2.0
    bar_len, bar_d = spec["bar_len"], spec["bar_d"]
    # The bar occupies an arc at the top (+Z); the chain fills the rest.
    bar_arc = bar_len / centre_r
    a0 = math.pi / 2 + bar_arc / 2
    a1 = math.pi / 2 - bar_arc / 2 + 2 * math.pi
    ang = np.linspace(a0, a1, 180)
    curve = np.stack([centre_r * np.cos(ang), np.zeros_like(ang), centre_r * np.sin(ang)], 1)
    chain, n_links = cable_chain(curve, spec["link_len"], spec["link_w"], spec["wire"], closed=False,
                                 up_hint=(0, 1, 0))
    b = bar(bar_len, bar_d)
    b.apply_translation([0, 0, centre_r])
    jr = spec["link_w"] * 0.9
    jumps = []
    for sx in (-1.0, 1.0):
        cx = sx * (bar_len / 2 + jr / 2 - spec["wire"] / 2)
        ring_pts = np.array([[cx + jr / 2 * np.cos(a), jr / 2 * np.sin(a), centre_r]
                             for a in np.linspace(0, 2 * np.pi, 20, endpoint=False)])
        jumps.append(tube_along(ring_pts, spec["wire"] / 2.0, closed=True))
    jump = trimesh.util.concatenate(jumps)
    scene = trimesh.Scene()
    for name, m in (("chain", chain), ("bar", b), ("jump", jump)):
        m.visual = trimesh.visual.TextureVisuals(material=metal)
        scene.add_geometry(m, node_name=name, geom_name=name)
    meta = {"anchor": "ring", "size_fr": size_fr, "inner_diameter_mm": round(2 * finger_r, 2),
            "links": n_links, "bar_mm": [bar_len, bar_d]}
    return scene, meta


def build_earring(spec: dict, metal: PBRMaterial = ROSE_GOLD) -> tuple[trimesh.Scene, dict]:
    """Threader. Origin = piercing point. A teardrop chain loop hangs below it in front
    (+Z), the chain continues straight down, the straight post ends the piece."""
    loop_h, loop_w = spec["loop_h"], spec["loop_w"]
    # Teardrop as worn: a semicircle of radius loop_w/2 at the top (this is the part
    # that rests over the lobe), two tangent straights converging to a point at -loop_h
    # where a jump ring joins the drop chain.
    r = loop_w / 2.0
    cy = -r                                  # circle centre
    d = abs(-loop_h - cy)                    # centre -> bottom point
    phi = math.acos(r / d)                   # tangent angle measured from the centre->bottom line
    # tangent points on the circle (angles from +x axis, bottom point is at -90deg)
    a_right = -math.pi / 2 + phi
    a_left = -math.pi / 2 - phi
    arc = np.linspace(a_right, a_left + 2 * math.pi, 60)  # go over the top from right to left
    circ = [[r * math.cos(a), cy + r * math.sin(a), 0.0] for a in arc]
    bottom = [0.0, -loop_h, 0.0]
    right_line = [list(np.array(bottom) * (1 - u) + np.array(circ[0]) * u) for u in np.linspace(0, 1, 30)]
    left_line = [list(np.array(circ[-1]) * (1 - u) + np.array(bottom) * u) for u in np.linspace(0, 1, 30)]
    loop_curve = np.array(right_line[:-1] + circ + left_line[1:])
    drop = spec["drop"]
    jr = spec["link_w"] * 0.9
    chain_curve = np.array([[0.0, -loop_h - jr, -0.6], [0.0, -loop_h - drop, -0.6]])
    loop_m, n1 = cable_chain(loop_curve, spec["link_len"], spec["link_w"], spec["wire"], closed=False,
                             up_hint=(0, 0, 1))
    drop_m, n2 = cable_chain(chain_curve, spec["link_len"], spec["link_w"], spec["wire"], closed=False,
                             up_hint=(0, 0, 1))
    jump = tube_along(np.array([[jr / 2 * math.cos(a), -loop_h - jr / 2 + jr / 2 * math.sin(a), 0.0]
                                for a in np.linspace(0, 2 * np.pi, 24, endpoint=False)]),
                      spec["wire"] / 2.0, closed=True)
    post = bar(spec["post_len"], spec["post_d"])
    post.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))  # X -> Y
    post.apply_translation([0.0, -loop_h - drop - spec["post_len"] / 2.0, -0.6])
    scene = trimesh.Scene()
    for name, m in (("loop", loop_m), ("jump", jump), ("drop", drop_m), ("post", post)):
        m.visual = trimesh.visual.TextureVisuals(material=metal)
        scene.add_geometry(m, node_name=name, geom_name=name)
    meta = {"anchor": "earring", "total_length_mm": round(loop_h + drop + spec["post_len"], 1),
            "links": n1 + n2}
    return scene, meta


def build_necklace(chain_cm: float, spec: dict, metal: PBRMaterial = ROSE_GOLD) -> tuple[trimesh.Scene, dict]:
    """'One' necklace in its worn shape, as it lies on a person.

    The chain does not sit in a level ring round the neck. It rests on the nape, runs
    forward and DOWN over the base of the neck where the shoulders begin, and meets at the
    hollow between the collarbones, so the loop is tilted (nape high, front low) and widens
    a little as the body does. Whatever length is left over after that loop is what the
    pendant pulls into a shallow V at the front. The first version put the whole back half
    level at nape height and dropped two straight arcs from the sides of the neck; on a
    person that read as a rigid triangle standing off the throat (Revan, phone test
    2026-11-15).

    Path, by angle phi round the neck axis (0 = front, pi = nape):
      x = a * r * sin(phi),  z = b * r * cos(phi),  r = 1 + widen * f,  f = (1 + cos phi) / 2
      y = -tilt * f  -  V * max(0, 1 - |phi| / v_span) ** v_pow
    V is solved so the path length equals the chain length.
    """
    total = chain_cm * 10.0
    a, b = spec["neck_a"], spec["neck_b"]            # neck ellipse semi-axes at nape height (x left-right, z front-back)
    tilt, widen = spec["tilt"], spec["widen"]
    v_span, v_pow = np.radians(spec["v_span_deg"]), spec["v_pow"]
    phi = np.linspace(-np.pi, np.pi, 1441)           # nape -> one side -> front -> other side -> nape

    def path(V: float) -> np.ndarray:
        f = (1 + np.cos(phi)) / 2
        r = 1 + widen * f
        y = -tilt * f - V * np.clip(1 - np.abs(phi) / v_span, 0, None) ** v_pow
        return np.stack([a * r * np.sin(phi), y, b * r * np.cos(phi)], 1)

    def length(pts: np.ndarray) -> float:
        return float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))

    if length(path(0.0)) > total:
        raise ValueError(f"neck loop {length(path(0.0)):.0f} mm is longer than the {total:.0f} mm chain; "
                         "reduce neck_a/neck_b/tilt or use a longer chain")
    lo, hi = 0.0, 300.0
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if length(path(mid)) < total else (lo, mid)
    V = (lo + hi) / 2
    loop = path(V)
    front = int(np.argmin(np.abs(phi)))               # index of the pendant point
    pend = loop[front].copy()
    drop = float(-pend[1])
    # Open the loop at the pendant: pendant -> one side -> nape -> other side -> pendant, and
    # trim each end by arc length so the last link overlaps the bezel wall by ~half a wire.
    opened = np.vstack([loop[front:], loop[1:front + 1]])
    bez_r = spec["stone_d"] / 2 + spec["bezel_wall"]
    cut = max(bez_r - spec["wire"] * 0.5, 0.0)
    fine = resample_by_arclength(opened, 0.1)
    seg = np.linalg.norm(np.diff(fine, axis=0), axis=1)
    from_start = np.concatenate([[0.0], np.cumsum(seg)])
    curve = fine[(from_start >= cut) & (from_start <= from_start[-1] - cut)]
    chain, n = cable_chain(curve, spec["link_len"], spec["link_w"], spec["wire"], closed=False,
                           up_hint=(0, 1, 0))
    stone = brilliant(spec["stone_d"])
    cup = bezel(spec["stone_d"], spec["bezel_wall"], spec["bezel_h"])
    # Pendant faces forward: rotate so the table (+Y) points to +Z, then hang it.
    face_fwd = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    for m in (stone, cup):
        m.apply_transform(face_fwd)
        m.apply_translation(pend)
    scene = trimesh.Scene()
    chain.visual = trimesh.visual.TextureVisuals(material=metal)
    cup.visual = trimesh.visual.TextureVisuals(material=metal)
    stone.visual = trimesh.visual.TextureVisuals(material=DIAMOND)
    scene.add_geometry(chain, node_name="chain", geom_name="chain")
    scene.add_geometry(cup, node_name="bezel", geom_name="bezel")
    scene.add_geometry(stone, node_name="diamond", geom_name="diamond")
    side = loop[int(np.argmin(np.abs(phi - np.pi / 2)))]
    meta = {"anchor": "necklace", "chain_cm": chain_cm, "pendant_drop_mm": round(drop, 1),
            "pendant_v_mm": round(V, 1), "pendant_z_mm": round(float(pend[2]), 1),
            "side_x_mm": round(float(abs(side[0])), 1), "side_y_mm": round(float(side[1]), 1),
            "links": n, "stone_mm": spec["stone_d"]}
    return scene, meta


# --------------------------------------------------------------------------- export
def export(scene: trimesh.Scene, path: str) -> dict:
    """Write metres GLB (Three.js / Shopify / Quick Look all expect metres)."""
    scene = scene.copy()
    scene.apply_transform(trimesh.transformations.scale_matrix(0.001))
    scene.export(path)
    tri = int(sum(len(g.faces) for g in scene.geometry.values()))
    ext = scene.bounds
    return {"triangles": tri, "bytes": os.path.getsize(path),
            "bbox_mm": [[round(v * 1000, 2) for v in ext[0]], [round(v * 1000, 2) for v in ext[1]]]}


# Dimensions in mm. Starting values are read off the product photos against the
# known ring circumference / chain length; refine once Vanrycke confirms.
SPECS = {
    # Measured off Vanrycke's product photos on 2026-11-14 (ring photographed flat,
    # ~29 px/mm at a 52 inner circumference): links ~1.3 x 0.75 mm, wire ~0.28 mm,
    # bar ~4 x 1 mm with a jump ring at each end. The chains are "diamantée" (faceted).
    "ring": {"link_len": 1.4, "link_w": 0.8, "wire": 0.28, "bar_len": 4.0, "bar_d": 1.0},
    "earring": {"link_len": 1.3, "link_w": 0.75, "wire": 0.26, "loop_h": 22.0, "loop_w": 11.0,
                "drop": 52.0, "post_len": 22.0, "post_d": 0.7},
    # Worn shape (see build_necklace): neck 60 x 56 mm half-axes at the nape = 365 mm round,
    # an average woman's neck base; the loop tilts 55 mm from nape to collarbone hollow and
    # widens 8 % on the way down. The pendant V is whatever chain is left.
    "necklace": {"link_len": 1.3, "link_w": 0.75, "wire": 0.26, "neck_a": 60.0, "neck_b": 56.0,
                 "tilt": 55.0, "widen": 0.08, "v_span_deg": 75.0, "v_pow": 1.25,
                 "stone_d": 2.2, "bezel_wall": 0.35, "bezel_h": 1.6},
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--piece", default="all", choices=["all", "ring", "earring", "necklace"])
    ap.add_argument("--ring-size", type=float, default=52.0, help="FR size = inner circumference mm")
    ap.add_argument("--chain-cm", type=float, default=42.0)
    ap.add_argument("--metal", default="all", choices=["all", "rose", "white"])
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    report = {}
    want = ["ring", "earring", "necklace"] if args.piece == "all" else [args.piece]
    metals = ["rose", "white"] if args.metal == "all" else [args.metal]
    for piece in want:
        for metal in metals:
            mat = METALS[metal]
            suffix = "" if metal == "rose" else "_white"
            if piece == "ring":
                scene, meta = build_ring(args.ring_size, SPECS["ring"], mat)
                name = f"bague-calamity-jane_{int(args.ring_size)}{suffix}"
            elif piece == "earring":
                scene, meta = build_earring(SPECS["earring"], mat)
                name = f"chaine-doreille-calamity-jane{suffix}"
            else:
                scene, meta = build_necklace(args.chain_cm, SPECS["necklace"], mat)
                name = f"collier-one_{int(args.chain_cm)}cm{suffix}"
            path = os.path.join(args.out, name + ".glb")
            meta.update(export(scene, path))
            meta["file"] = path; meta["metal"] = metal
            report[f"{piece}_{metal}"] = meta
            print(f"{piece:9s} {metal:5s} {meta['triangles']:7d} tris {meta['bytes']/1024:7.1f} KB  links {meta.get('links')}")
    with open(os.path.join(args.out, "report.json"), "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
