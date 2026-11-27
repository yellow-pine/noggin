"""PROTOTYPE: each eyeball's centre fitted in 3D to the sculpt's own eye dome (#967, Cansin 2026-11-27). The dome is the
sculpt's surface seen from the front inside its eye white's cut (skin.cuts(), the dome's foot), INSET mm in from the
foot (its fillet into the face is not the ball); a sphere, centre and radius free, is fitted to it by least squares
(soft L1, 0.3 mm). Head frame as today: origin midway between the Mech's eyes, x to his left, -y forward, z up."""
import sys; sys.path.insert(0, "/tmp/967-lids"); sys.path.insert(0, "/tmp/967-proto")
import numpy as np, trimesh, common
from matplotlib.path import Path
from scipy.optimize import least_squares
from model import skin, gimbal as gm
np.set_printoptions(precision=2, suppress=True)
raw = common.meshes(raw=True)[0][1]            # the whole sculpt, life size, in the head's frame
cuts = skin.cuts()
from model.review import test_hidden as th
S = th._points(raw, 0.25)
res = {}
for side in "LR":
    view, poly = cuts[f"{side} eye white"]
    c2 = poly.mean(0); foot_r = np.linalg.norm(poly - c2, axis=1)
    print(f"{side} eye white's cut: front-view centre (x, z) {c2.round(2)}, radius {foot_r.min():.1f}..{foot_r.max():.1f}")
    for inset in (2.0, 4.0, 8.0):
        inner = c2 + (poly - c2) * (1 - inset / foot_r.mean())
        box = (S[:, 0] > poly[:, 0].min()) & (S[:, 0] < poly[:, 0].max()) & (S[:, 2] > poly[:, 1].min()) & (S[:, 2] < poly[:, 1].max()) & (S[:, 1] < 20)
        q = S[box]; q = q[Path(inner).contains_points(q[:, [0, 2]])]
        cell = np.round(q[:, [0, 2]] / 0.5).astype(int)          # the front-most point of each 0.5 mm column
        order = np.lexsort((q[:, 1], cell[:, 1], cell[:, 0])); q, cell = q[order], cell[order]
        p = q[np.r_[True, (np.diff(cell, axis=0) != 0).any(1)]]
        f = least_squares(lambda v: np.linalg.norm(p - v[:3], axis=1) - v[3], [c2[0], 0, c2[1], 38.0], loss="soft_l1", f_scale=0.3)
        r = np.linalg.norm(p - f.x[:3], axis=1) - f.x[3]
        apex = p[p[:, 1].argmin()]
        print(f"  inset {inset}: {len(p)} points, y {p[:,1].min():.1f}..{p[:,1].max():.1f}; centre {f.x[:3].round(2)} radius {f.x[3]:.2f}; residual rms {np.sqrt((r**2).mean()):.2f}, 5..95 pct {np.percentile(r,5):.2f}..{np.percentile(r,95):.2f}; front-most point {apex.round(1)}")
        if inset == 4.0: res[side] = f.x
    view, pp = cuts[f"{side} pupil"]; pc = pp.mean(0)
    c, R = res[side][:3], res[side][3]
    yy = c[1] - np.sqrt(R**2 - (pc[0]-c[0])**2 - (pc[1]-c[2])**2)
    d = np.array([pc[0], yy, pc[1]]) - c
    print(f"  pupil ring's centre (x, z) {pc.round(2)}, radius {np.linalg.norm(pp-pc,axis=1).mean():.1f}: on the fitted ball at y {yy:.1f}, {np.degrees(np.arctan2(d[0], -d[1])):.1f} deg outward(+x) and {np.degrees(np.arcsin(d[2]/R)):.1f} deg up of straight ahead")
L, R = res["L"], res["R"]
print("fitted centres apart", np.linalg.norm(L[:3] - R[:3]).round(2), "; midpoint", ((L[:3] + R[:3]) / 2).round(2), "; the Mech's eyes today", gm.EYE)
np.save("/tmp/967-proto/eyefit.npy", np.array([L, R]))
