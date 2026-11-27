"""PROTOTYPE (#967 option A), throwaway: shared helpers. Run from the repo worktree with its venv."""
import os, sys, functools
import numpy as np, trimesh
sys.path.insert(0, os.getcwd()); sys.path.insert(0, "/tmp/967-lids")
from model import stages, gimbal as gm, envelopes, geometry as g
OURS = os.path.join(os.getcwd(), "model/build/ours")
G = np.load("/tmp/967-proto/geom2.npz")           # measure.py: the sculpt about the eyeballs' fitted centres (eyefit.py)
C = float(G["c"])                               # half the fitted spacing: the frame's origin stays midway between the eyes
R_EYE = float(G["r_eye"])                       # the sculpt's eye, a ball
R_CAP = round(R_EYE - 1.2, 1)                   # the cap 1.2 mm under it (Cansin, 7207851129)
R_IN, R_OUT = R_CAP, R_CAP + 2.2                # the lids' 1.2 mm band 0.5 mm over the cap, and its 0.5 mm either side
OPEN_UP, OPEN_LOW, SHUT, OV = 81.0, -74.0, -4.0, 4.0   # the lids' edges open and shut; the cover past the opening's edge
A_LID = (-58.0, 86.0)                           # the lids' reach along their axis, deg (+ outward): the opening and OV
PHI_KEEP = (OPEN_LOW - 70.0, OPEN_UP + 85.0)    # both lids' sweep as plain bands; the belt behind the eye is the rest
SUB = stages.eyes_sub()

@functools.cache
def cloud(stem, k=2.0):
    m = trimesh.load(f"{OURS}/{stem}.stl", force="mesh")
    return np.vstack([m.vertices, trimesh.sample.sample_surface_even(m, int(m.area * k), seed=0)[0]])

def part(name, mech=True):
    """Point cloud of an eyes part where the stage places it (gimbal frame)."""
    p = SUB.parts[name]; stem = stages.stem(p.file)
    f = stem + " mechanical" if mech and os.path.isfile(f"{OURS}/{stem} mechanical.stl") else stem
    dx = (C - gm.EYE["L"][0]) * (1 if name.startswith("L ") else -1 if name.startswith("R ") else 0)
    return trimesh.transform_points(cloud(f), p.matrix) + (dx, 0, 0)

def polar(pts, s=1):
    """(r, a, phi) about the s eye's centre: a along the lids' axis (+ outward), phi about it (0 forward, 90 up)."""
    q = np.asarray(pts, float) - (s * C, 0, 0)
    r = np.linalg.norm(q, axis=1)
    return r, np.degrees(np.arcsin(np.clip(s * q[:, 0] / np.maximum(r, 1e-9), -1, 1))), np.degrees(np.arctan2(q[:, 2], -q[:, 1]))

def keepout(pts, s=1, r=(R_IN, R_OUT)):
    """Mask: the points inside the lids' swept shell about the s eye."""
    rr, a, phi = polar(pts, s)
    return (rr > r[0]) & (rr < r[1]) & (a > A_LID[0]) & (a < A_LID[1]) & (phi > PHI_KEEP[0]) & (phi < PHI_KEEP[1])

def report(name, pts, both=True):
    """Print how a cloud sits against the lids' shell of each eye."""
    for side, s in (("L", 1), ("R", -1)) if both else (("L", 1),):
        m = keepout(pts, s)
        r, a, phi = polar(pts, s)
        if m.any():
            print(f"  {name:28s} {side}: CROSSES {int(m.sum()):6d} pts  a {a[m].min():6.1f}..{a[m].max():6.1f}  phi {phi[m].min():7.1f}..{phi[m].max():7.1f}")
        else:
            near = (r > R_IN - 3) & (r < R_OUT + 3) & (a > A_LID[0]) & (a < A_LID[1]) & (phi > PHI_KEEP[0]) & (phi < PHI_KEEP[1])
            # least room to the shell among the points beside it
            room = np.minimum(np.abs(r[near] - R_IN), np.abs(r[near] - R_OUT)).min() if near.any() else np.inf
            print(f"  {name:28s} {side}: clear (least room to the shell where beside it {room:.2f} mm)")

def solid_cloud(shape, tol=0.05, k=3.0):
    """Points on a CadQuery solid's surface."""
    v, f = shape.val().tessellate(tol) if hasattr(shape, "val") else shape.tessellate(tol)
    m = trimesh.Trimesh([p.toTuple() for p in v], f)
    return np.vstack([m.vertices, trimesh.sample.sample_surface_even(m, int(m.area * k), seed=0)[0]])

@functools.cache
def depth():
    import common
    raw = common.meshes(raw=True)[0][1]; raw.apply_translation(-G["shift"])   # his fitted eye centres on the Mech's eyes
    return common.outer_depth(raw)

# ---- the lids as decided (#967, 7207851129), their back edges cut to the opening (the prototype's own step) ----
_AA = np.arange(-58, 87)
_TOP = np.maximum.reduce([np.interp(_AA, G[k][:, 0], G[k][:, 1]) for k in ("L_top", "R_top")])
_BOT = np.minimum.reduce([np.interp(_AA, G[k][:, 0], G[k][:, 1]) for k in ("L_bottom", "R_bottom")])
def lid_back(a):
    """(lower lid's back edge, upper lid's back edge) stowed, deg, by a: what the lids sweep lies between them."""
    top, bot = np.interp(a, _AA, _TOP), np.interp(a, _AA, _BOT)
    return OPEN_LOW - (SHUT - (bot - OV)), OPEN_UP + (top + OV - SHUT)

def keepout2(pts, s=1, r=(R_IN, R_OUT), margin=1.0):
    """As keepout, the lids' back edges cut to the opening's own (each lid covers the opening and OV past it)."""
    rr, a, phi = polar(pts, s)
    lo, hi = lid_back(a)
    return (rr > r[0]) & (rr < r[1]) & (a > A_LID[0]) & (a < A_LID[1]) & (phi > lo - margin) & (phi < hi + margin)

def report2(name, pts, shaped=True):
    out = []
    for side, s in (("L", 1), ("R", -1)):
        m = keepout2(pts, s) if shaped else keepout(pts, s)
        if m.any():
            r, a, phi = polar(pts[m], s)
            out.append(f"{side} CROSSES {int(m.sum())} pts a {a.min():.0f}..{a.max():.0f} phi {phi.min():.0f}..{phi.max():.0f}")
    print(f"  {name:26s} lids' shell ({'cut' if shaped else 'band'}): " + ("; ".join(out) or "clear"))
    return not out

# ---- the 37.4 mm cap out to the opening's edge, carried by the eye ----
_RIM = {"L": G["L_rim"], "R": G["R_rim"], "PSI": G["psi"]}
CAP_T = 2.0
def in_cap(pts, yaw, pitch, s=1, grow=0.5):
    """Mask: points inside the s cap's shell (R_CAP - CAP_T .. R_CAP, within the opening's cone), the eye at yaw, pitch."""
    q = (np.asarray(pts, float) - (s * C, 0, 0)) @ gm.core(yaw, pitch)
    r = np.linalg.norm(q, axis=1)
    theta = np.degrees(np.arccos(np.clip(-q[:, 1] / np.maximum(r, 1e-9), -1, 1)))
    psi = np.degrees(np.arctan2(q[:, 2], s * q[:, 0])) % 360
    rim = _RIM["L" if s == 1 else "R"][(np.round(psi / 5).astype(int)) % len(_RIM["PSI"])]
    return (r > R_CAP - CAP_T - grow) & (r < R_CAP + grow) & (theta < rim + np.degrees(grow / R_CAP))

def cap_sweep(name, pts):
    """Print whether a fixed cloud meets either cap anywhere over yaw x pitch."""
    hit = {}
    for side, s in (("L", 1), ("R", -1)):
        for yaw in np.linspace(-25, 25, 11):
            for pitch in np.linspace(-15, 15, 7):
                y, p = gm.eyes(*gm.servos(yaw, pitch))[side]
                n = int(in_cap(pts, y, p, s).sum())
                if n > hit.get(side, (0,))[0]: hit[side] = (n, round(float(yaw)), round(float(pitch)))
    print(f"  {name:26s} caps: " + ("; ".join(f"{k} MEETS {v[0]} pts at yaw {v[1]} pitch {v[2]}" for k, v in hit.items()) or "clear"))
    return not hit

_OCC = None
def occupied(name, pts, floor=1.0):
    """Print the document's other parts (swept over pan, tilt, jaw) within `floor`+1 mm (voxels) of the cloud."""
    global _OCC
    from scipy import ndimage
    if _OCC is None:
        z = np.load("/tmp/967-proto/space.npz")
        _OCC = (list(z["names"]), [ndimage.distance_transform_edt(~o) for o in z["occ"]], z["lo"])
    names, edts, lo = _OCC
    q = np.floor((pts - lo)).astype(int); ok = ((q >= 0) & (q < edts[0].shape)).all(1); q = q[ok]
    near = {n: float(e[tuple(q.T)].min()) for n, e in zip(names, edts)}
    near = {n: round(v, 1) for n, v in near.items() if v < floor + 1.5}
    for n, e in zip(names, edts):
        if n in near and near[n] < 1.0:
            hit = pts[ok][e[tuple(q.T)] < 1.0]
            near[n] = (near[n], "at", hit.min(0).round(0).tolist(), hit.max(0).round(0).tolist())
    print(f"  {name:26s} others (voxels, mm): " + (str(near) if near else "clear"))
    return near

def skin(name, pts):
    d = depth()(pts)
    print(f"  {name:26s} under Morty's skin: least {-d.max():.2f} mm" + ("" if d.max() <= -2.1 else "   <-- LESS THAN 2.1"))
    return -d.max()

def gap(a, b):
    """Least distance between two clouds, mm (to their spacing)."""
    from scipy.spatial import cKDTree
    return float(cKDTree(a).query(b)[0].min())
