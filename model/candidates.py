"""The next Mech's head variants in MuJoCo (#686; their numbers and ranking: model/base.py): each one's figures for the
sim report (report(), model/report.py), which rank() orders. Back's boards sit where the cheeks have room (#828): no
parameter is left to optimise."""

import mujoco
import numpy as np

from model import base, mujoco_report, skin, stages
from model import geometry as g


def _rest(model):
    data = mujoco.MjData(model)
    mujoco.mj_kinematics(model, data)
    return data


def _drawn(model, data, names):
    return np.vstack([mujoco_report.vertices(model, data, model.body(n).id) for n in names])


def head(doc, model):
    """The head at rest, what rides it (the tilt's Skeleton parts, not its Skin's: skin.DRAWN) under its shell
    (base.shelled): its box, mm, as gimbal.HEAD_MM (width, depth, height), and how far up the box the eye centres sit
    (0 its bottom, 1 its top)."""
    eyes = np.array(stages.DOCS[doc]["next-eyes"][0])
    rides = stages.STAGES[doc].horns["tilt horn"].loops[0].rockers
    v = _drawn(model, _rest(model), [n for n in rides if n.removesuffix(":1") not in skin.DRAWN]) - eyes
    lo, hi = base.shelled(v.min(axis=0), v.max(axis=0))
    return [round(float(s), 1) for s in hi - lo], round(float(-lo[2] / (hi[2] - lo[2])), 2)


def report(doc, model):
    """The variant's figures for rank() from its document and its MJCF (model/report.py): the parts beside the neck and
    the gimbal (the Torso, the pack, the carriers and the boards) and how many are printed, the leads crossing pan and
    tilt, the head's box and the eyes' height in it."""
    stage = stages.STAGES[doc]
    parts = [
        n
        for sub in g.NEXT[doc]
        if sub not in ("next-neck", "next-jaw", "next-eyes", "next-morty")
        for n in stages.SUBS[sub]().parts
    ]
    size, eyes = head(doc, model)
    return {
        "parts": parts,
        "printed": sum(stages.stem(stage.parts[n].file).startswith("next ") for n in parts),
        "leads": base.leads(stage),
        "head_mm": size,
        "eyes_up": eyes,
    }
