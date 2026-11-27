"""PROTOTYPE: the sculpt about each eyeball's fitted centre (eyefit.py): with the sculpt placed so those centres sit on
the Mech's eyes (SPACING 73.33, the frame's origin midway between them), each eye opening's top and bottom edge by
column of the lid, the skin's radius past the edge, the largest radius that stays 2.1 mm under the skin there, and the
opening's edge by direction about the gaze. Saved as geom2.npz for the checks."""
import sys; sys.path.insert(0, "/tmp/967-lids"); sys.path.insert(0, "/tmp/967-proto")
import numpy as np, trimesh, common
from matplotlib.path import Path
from model import skin
FIT = np.load("/tmp/967-proto/eyefit.npy")
SHIFT = (FIT[0, :3] + FIT[1, :3]) / 2
C = float(np.linalg.norm(FIT[0, :3] - FIT[1, :3]) / 2)
R_EYE = float(FIT[:, 3].mean())
print(f"shift {SHIFT.round(2)}, half spacing {C:.3f}, eye radius {R_EYE:.2f}; the fitted centres in the new frame: {(FIT[:, :3] - SHIFT).round(2).tolist()}")
raw = common.meshes(raw=True)[0][1]; raw.apply_translation(-SHIFT)
outside = common.outer_depth(raw)
cuts = {k: v[1] - SHIFT[[0, 2]] for k, v in skin.cuts().items() if "eye white" in k}
R = np.arange(30.0, 50.01, 0.1)
MARGIN = 2.1
np.set_printoptions(linewidth=220, precision=1, suppress=True)
def first_out(centre, u):
    d = outside((centre + u[:, None, :] * R[None, :, None]).reshape(-1, 3)).reshape(len(u), len(R))
    first = np.where((d > 0).any(1), (d > 0).argmax(1), len(R) - 1)
    ok = d <= -MARGIN
    limit = R[np.where(ok.all(1), len(R) - 1, ((~ok).argmax(1) - 1).clip(0))]
    return R[first], limit
out = {}
A = np.arange(-70, 88.1, 2.0); PAST = (0.5, 1, 2, 3, 5, 7.5, 10, 15)
for side, s in (("L", 1), ("R", -1)):
    centre = np.array([s * C, 0, 0]); poly = Path(cuts[f"{side} eye white"])
    for name, phis in (("top", np.arange(0, 120.01, 0.5)), ("bottom", np.arange(0, -120.01, -0.5))):
        aa, pp = np.meshgrid(A, phis, indexing="ij")
        u = common.unit(aa.ravel(), pp.ravel(), s)
        skin_r, limit = first_out(centre, u)
        surf = centre + u * skin_r[:, None]
        eye = poly.contains_points(surf[:, [0, 2]]).reshape(aa.shape) & (surf[:, 1] < 15).reshape(aa.shape)
        skin_r, limit = skin_r.reshape(aa.shape), limit.reshape(aa.shape)
        rows = []
        for i in range(len(A)):
            if not eye[i].any(): continue
            k = len(phis) - 1 - int(np.argmax(eye[i][::-1]))          # the last eye sample going out
            rows.append((A[i], phis[k], skin_r[i, : k + 1].min(), skin_r[i, : k + 1].max(),
                         *[skin_r[i, min(k + int(p / 0.5), len(phis) - 1)] for p in PAST], *[limit[i, min(k + int(p / 0.5), len(phis) - 1)] for p in PAST]))
        rows = np.array(rows); out[f"{side}_{name}"] = rows; n = len(PAST)
        print(f"\n{side} {name}: columns a {rows[:,0].min()}..{rows[:,0].max()}; edge by a (every 10): { {int(r[0]): float(r[1]) for r in rows if r[0] % 10 == 0} }")
        print(f"   the dome's radius within the opening: {rows[:,2].min():.1f}..{rows[:,3].max():.1f}")
        print("   deg past the edge        " + "".join(f"{p:7}" for p in PAST))
        print("   skin's radius, least     " + "".join(f"{v:7.1f}" for v in rows[:, 4:4 + n].min(0)))
        print("   skin's radius, 10th pct  " + "".join(f"{v:7.1f}" for v in np.percentile(rows[:, 4:4 + n], 10, axis=0)))
        print("   2.1 mm under it, least   " + "".join(f"{v:7.1f}" for v in rows[:, 4 + n:].min(0)))
        print("   2.1 mm under it, 10th pct" + "".join(f"{v:7.1f}" for v in np.percentile(rows[:, 4 + n:], 10, axis=0)))
    # the opening's edge by direction about the gaze: theta off it, psi from outward toward up
    PSI, TH = np.arange(0, 360, 5.0), np.arange(0, 121, 1.0)
    pp, tt = np.meshgrid(np.radians(PSI), np.radians(TH), indexing="ij")
    u = np.stack([s * np.sin(tt) * np.cos(pp), -np.cos(tt), np.sin(tt) * np.sin(pp)], -1).reshape(-1, 3)
    skin_r, _ = first_out(centre, u); surf = centre + u * skin_r[:, None]
    eye = (poly.contains_points(surf[:, [0, 2]]) & (surf[:, 1] < 15)).reshape(pp.shape)
    out[f"{side}_rim"] = np.array([TH[len(TH) - 1 - int(np.argmax(r[::-1]))] if r.any() else 0 for r in eye])
    print(f"   {side} opening's edge, deg off the gaze: outward {out[f'{side}_rim'][0]:.0f}, up {out[f'{side}_rim'][18]:.0f}, inward {out[f'{side}_rim'][36]:.0f}, down {out[f'{side}_rim'][54]:.0f}; every 30 deg {out[f'{side}_rim'][::6]}")
np.savez("/tmp/967-proto/geom2.npz", shift=SHIFT, c=C, r_eye=R_EYE, psi=PSI, **out)
