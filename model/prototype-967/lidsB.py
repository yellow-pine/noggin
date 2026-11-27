"""PROTOTYPE: where the lids' own carriers may stand, about the L eye (fitted centre): what the cap sweeps over yaw x
pitch between the eyes and behind the outer corner, and the skin's room there."""
import sys; sys.path.insert(0, "/tmp/967-proto")
from lib import *
np.set_printoptions(linewidth=220, precision=0, suppress=True)
POSES = [gm.eyes(*gm.servos(y, p))["L"] for y in np.linspace(-25, 25, 11) for p in np.linspace(-15, 15, 7)]
def capfree(pts):
    hit = np.zeros(len(pts), bool)
    for y, p in POSES: hit |= in_cap(pts, y, p, 1)
    return ~hit
E = np.array([C, 0, 0])
def dirs(a, phi, r):
    a, phi = np.radians(a), np.radians(phi)
    u = np.stack(np.broadcast_arrays(np.sin(a), -np.cos(a) * np.cos(phi), np.cos(a) * np.sin(phi)), -1)
    return (E + np.multiply.outer(np.atleast_1d(r), u)).reshape(-1, 3)
PHI = np.arange(-180, 180, 5.0)
print(f"cap: r {R_CAP - CAP_T}..{R_CAP}; lids' band {R_CAP + 0.5}..{R_CAP + 1.7}")
print("\n1. between the eyes: the largest radius about the eye line (rho, mm) free of the cap at every pose, by x (mm from the midline), in front (y<0) and behind")
for x in (1.4, 3, 5, 7, 9, 11, 12):
    rho = np.arange(0, 30.01, 0.5)
    rr, pp = np.meshgrid(rho, np.radians(PHI), indexing="ij")
    pts = np.stack([np.full(rr.shape, x), -rr * np.cos(pp), rr * np.sin(pp)], -1).reshape(-1, 3)
    free = capfree(pts).reshape(rr.shape)
    front = np.cos(pp[0]) > 0
    def reach(mask):
        ok = free[:, mask].all(1); return rho[np.argmin(ok) - 1] if not ok.all() else rho[-1]
    print(f"   x {x:4.1f}: front {reach(front):5.1f}  behind {reach(~front):5.1f}   (the lids' band here is at rho {np.sqrt(max((R_CAP+0.5)**2 - (C-x)**2, 0)):.1f}..{np.sqrt(max((R_CAP+1.7)**2 - (C-x)**2, 0)):.1f})")
print("\n2. where a lid's end wall may cross the cap's radii (r 33.3..36.3) at its inner end, a -62..-52: the lid angles phi free of the cap at every pose")
for a in (-62, -58, -54, -50):
    free = np.array([capfree(dirs(a, ph, np.linspace(R_CAP - CAP_T - 0.5, R_CAP + 0.5, 7))).all() for ph in PHI])
    print(f"   a {a}: free phi", PHI[free].astype(int).tolist() if free.sum() < 40 else f"{int(PHI[free].min())}..{int(PHI[free].max())} ({free.sum()} of {len(PHI)})")
print("\n3. behind the outer corner: by a, the lid angles phi where the cap never comes (r 33.3..36.3), and the skin's depth over the band (r 38.0)")
d = depth()
for a in (55, 60, 65, 70, 75, 80, 85):
    free = np.array([capfree(dirs(a, ph, np.linspace(R_CAP - CAP_T - 0.5, R_CAP + 0.5, 7))).all() for ph in PHI])
    under = -d(dirs(a, PHI, R_OUT))
    print(f"   a {a}: cap-free phi {PHI[free].astype(int).tolist()}")
    print(f"          2.1 mm under the skin at r {R_OUT} for phi {PHI[under >= 2.1].astype(int).tolist()}")
