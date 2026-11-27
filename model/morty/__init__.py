"""Morty's Sculpt (GLOSSARY, docs/adr/0027): ChelsCCT's "Morty Smith [Rick and Morty]" under CC BY 4.0 (LICENSE.md),
the one source his Skin is cut from (shells.py). SCULPT is the whole figure as adopted (adopt.py: decimated in Blender,
nothing else), in the Sculpt's own frame and millimetres: z up, -y forward, his feet on z 0. placed() scales it and puts
it on the Mech's eyes."""

import numpy as np

from model import geometry as g
from model import gimbal as gm
from model import stages

SCULPT = "model/morty/sculpt.ply"
# the Sculpt's eyeballs' centres, its own mm: each a sphere fitted to its dome, which model/test_skin.py refits (#967;
# #872's measure on a front depth map before). His pupils sit 9 deg outward of them
EYES = {"L": (84.467, 245.677, 107.54), "R": (74.186, 245.682, 107.54)}
DOC = next(iter(g.MECH))  # the document his Skin is on


def placed():
    """4x4 taking the Sculpt's own frame to the documents' world: his eyes on the Mech's, scaled to their spacing."""
    eyes = stages.align(*stages.DOCS[DOC]["eyes"])
    mech = {s: (eyes @ [*e, 1])[:3] for s, e in gm.EYE.items()}
    raw = {s: np.array(e) for s, e in EYES.items()}
    scale = np.linalg.norm(mech["L"] - mech["R"]) / np.linalg.norm(raw["L"] - raw["R"])
    out = np.diag([scale] * 3 + [1.0])
    out[:3, 3] = (mech["L"] + mech["R"]) / 2 - scale * (raw["L"] + raw["R"]) / 2
    return out
