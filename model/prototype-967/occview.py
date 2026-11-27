"""PROTOTYPE: slices of space.npz with the eyes' own parts at rest drawn over. usage: occview.py out.png axis v1 v2 ..."""
import sys; sys.path.insert(0, "/tmp/967-proto")
from lib import *
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
z = np.load("/tmp/967-proto/space.npz"); names, occ, LO, P = list(z["names"]), z["occ"], z["lo"], float(z["pitch"])
out, axis, vals = sys.argv[1], "xyz".index(sys.argv[2]), [float(v) for v in sys.argv[3:]]
half = 1.5
cmap = plt.get_cmap("tab20")
own = {n: part(n) for n in SUB.parts if not any(k in n for k in ("lid:1", "cap"))}
fig, axes = plt.subplots(1, len(vals), figsize=(12 * len(vals), 12))
i, j = [k for k in range(3) if k != axis]
for ax, v in zip(np.atleast_1d(axes), vals):
    k0 = int((v - LO[axis]) / P)
    for k, n in enumerate(names):
        sl = np.take(occ[k], range(max(k0 - 1, 0), k0 + 2), axis=axis).any(axis=axis)
        if not sl.any(): continue
        ii, jj = np.nonzero(sl)
        ax.scatter(LO[i] + ii * P, LO[j] + jj * P, s=3, color=cmap(k % 20), label=n, marker="s")
    for k, (n, p) in enumerate(own.items()):
        m = np.abs(p[:, axis] - v) < half
        if m.any(): ax.scatter(p[m, i], p[m, j], s=1.5, color=plt.get_cmap("Dark2")(k % 8), label="* " + n, marker=".")
    for s in (1, -1):
        for r, ls in ((R_IN, "--"), (R_OUT, "--")):
            d = v - s * C if axis == 0 else v
            if r * r - d * d <= 0: continue
            t = np.linspace(0, 2 * np.pi, 300); rr = np.sqrt(r * r - d * d)
            ax.plot((0 if axis == 0 else s * C) + rr * np.cos(t), rr * np.sin(t), color="k", lw=0.6, ls=ls)
        if axis == 0: break
    ax.set_aspect("equal"); ax.grid(alpha=0.4); ax.set_title(f"{'xyz'[axis]} = {v} ({'xyz'[i]} right, {'xyz'[j]} up)", fontsize=16)
    ax.set_xlim(LO[i], HI_[i] if (HI_ := LO + np.array(occ.shape[1:]) * P) is not None else 0); ax.set_ylim(LO[j], HI_[j])
    ax.set_xticks(np.arange(-80, 101, 10)); ax.set_yticks(np.arange(-70, 101, 10)); ax.set_xlim(LO[i], HI_[i]); ax.set_ylim(LO[j], HI_[j])
    ax.legend(fontsize=9, loc="upper right", ncol=2, markerscale=4)
fig.tight_layout(); fig.savefig(out, dpi=50)
