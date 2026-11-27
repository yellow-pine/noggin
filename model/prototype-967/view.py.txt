"""PROTOTYPE: section plots of the document about the eyes, gimbal frame. usage: view.py out.png axis v1 v2 ..."""
import sys; sys.path.insert(0, "/tmp/967-proto")
from lib import *
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
DOC = "mech-back-mechanical"
def doc_meshes(skip=("morty", "lid cover", "pupil")):
    st = stages.STAGES[DOC]; inv = np.linalg.inv(stages.align(*stages.DOCS[DOC]["eyes"]))
    out = {}
    for n, p in st.parts.items():
        if any(k in n for k in skip) or not os.path.isfile(p.file): continue
        m = trimesh.load(p.file, force="mesh"); m.apply_transform(inv @ p.matrix); out[n] = m
    return out
if __name__ == "__main__":
    out, axis, vals = sys.argv[1], "xyz".index(sys.argv[2]), [float(v) for v in sys.argv[3:]]
    ms = doc_meshes()
    cmap = plt.get_cmap("tab20")
    fig, axes = plt.subplots(1, len(vals), figsize=(11 * len(vals), 11))
    for ax, v in zip(np.atleast_1d(axes), vals):
        o, nrm = [0, 0, 0], [0, 0, 0]; o[axis] = v; nrm[axis] = 1
        i, j = [k for k in range(3) if k != axis]
        for k, (n, m) in enumerate(ms.items()):
            sec = m.section(plane_origin=o, plane_normal=nrm)
            if sec is None: continue
            first = True
            for e in sec.entities:
                p = sec.vertices[e.points]
                ax.plot(p[:, i], p[:, j], color=cmap(k % 20), lw=1.0, label=n if first else None); first = False
        for s in (1, -1):
            for r, ls in ((R_IN, "--"), (R_OUT, "--"), (19.5, ":")):
                d = v - s * C if axis == 0 else v
                rr2 = r * r - d * d
                if rr2 <= 0: continue
                t = np.linspace(0, 2 * np.pi, 300); rr = np.sqrt(rr2)
                cx = 0 if axis == 0 else s * C
                ax.plot(cx + rr * np.cos(t), rr * np.sin(t), color="k", lw=0.5, ls=ls)
            if axis == 0: break
        ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.set_title(f"{'xyz'[axis]} = {v}   ({'xyz'[i]} right, {'xyz'[j]} up)")
        lim = {0: (-20, 100), 1: (-20, 100), 2: (-90, 60)}
        ax.set_xlim(*( (-80, 80) if i == 0 else lim[i])); ax.set_ylim(*lim[j]); ax.legend(fontsize=6, loc="upper right", ncol=2)
    fig.tight_layout(); fig.savefig(out, dpi=55)
