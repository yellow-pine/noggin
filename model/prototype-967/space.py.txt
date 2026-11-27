"""PROTOTYPE: the occupied space about the eyes in the gimbal frame, mm voxels: every part of the document but the
eyes' own, the ones that move against the head swept over pan x tilt and the jaw's opening. Saved for the checks."""
import sys; sys.path.insert(0, "/tmp/967-proto")
from lib import *
from scipy import ndimage
DOC = "mech-back-mechanical"
LO, HI, P = np.array([-85.0, -45.0, -70.0]), np.array([85.0, 100.0, 60.0]), 1.0
st = stages.STAGES[DOC]
FR = "gimbal frame:1"
rest = {n: p.matrix for n, p in st.parts.items()}
inv0 = np.linalg.inv(rest[FR])
print("horns:", {h: st.horns[h].limits for h in st.horns})
def cl(n):
    m = trimesh.load(st.parts[n].file, force="mesh")
    return np.vstack([m.vertices, trimesh.sample.sample_surface_even(m, int(m.area * 2), seed=0)[0]])
skip = ("morty", "lid cover", "pupil")
own = set(SUB.parts)
names = [n for n in st.parts if n not in own and not any(k in n for k in skip) and os.path.isfile(st.parts[n].file)]
grid = {}
shape = tuple(((HI - LO) / P).astype(int) + 1)
def put(g, pts):
    q = np.floor((pts - LO) / P).astype(int)
    ok = ((q >= 0) & (q < shape)).all(1)
    g[tuple(q[ok].T)] = True
neck = [h for h in st.horns if h not in SUB.horns]
poses = [("rest", rest)]
lim = {h: st.horns[h].limits for h in neck}
print(neck)
for h in neck:
    for d in np.linspace(*lim[h], 13):
        poses.append((f"{h} {d:.0f}", stages.pose(st, h, d).parts))
moving = {}
for n in names:
    c = cl(n); g = np.zeros(shape, bool); mv = False
    for label, mats in poses:
        rel = np.linalg.inv(mats[FR]) @ mats[n]
        if label != "rest" and np.allclose(rel, inv0 @ rest[n], atol=1e-9): continue
        mv = mv or label != "rest"
        put(g, trimesh.transform_points(c, rel))
    if g.any():
        grid[n] = g; moving[n] = mv
print("in the box:", {n: ("moves" if moving[n] else "fixed") for n in grid})
np.savez_compressed("/tmp/967-proto/space.npz", names=np.array(list(grid)), occ=np.array([grid[n] for n in grid]), lo=LO, pitch=P)
