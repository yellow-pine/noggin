"""The next Mech's head variants in MuJoCo (#686; their numbers and ranking: model/base.py): each one's parameters
optimised on its MJCF (optimise(), `python -m model.candidates`, whose numbers model/base.py draws) and its figures for
the sim report (report(), model/report.py), which rank() orders."""

import mujoco
import numpy as np
from scipy.optimize import minimize_scalar

from model import base, gimbal, mjcf, mujoco_report, skin, stages
from model import geometry as g

# each variant's carrier and the boards on it, which optimise() moves (Back alone since #712)
CARRIER = {"next-mech-back": ("next board rack", base.back_boards)}


def _rest(model):
    data = mujoco.MjData(model)
    mujoco.mj_kinematics(model, data)
    return data


def _drawn(model, data, names):
    return np.vstack([mujoco_report.vertices(model, data, model.body(n).id) for n in names])


def head(doc, model):
    """What rides the head (the tilt's parts) at rest: its box, mm, as gimbal.HEAD_MM (width, depth, height), and how
    far up the box the eye centres sit (0 its bottom, 1 its top)."""
    rides = stages.STAGES[doc].horns["tilt horn"].loops[0].rockers
    v = _drawn(model, _rest(model), [n for n in rides if n.removesuffix(":1") not in skin.DRAWN])  # the Skeleton's
    lo, hi = v.min(axis=0), v.max(axis=0)
    eyes = stages.DOCS[doc]["next-eyes"][0][2]
    return [round(float(s), 1) for s in hi - lo], round(float((eyes - lo[2]) / (hi[2] - lo[2])), 2)


def report(doc, model):
    """The variant's figures for rank() from its document and its MJCF (model/report.py): the parts beside the neck and
    the gimbal (the Torso, the pack, the carriers and the boards) and how many are printed, the leads crossing pan and
    tilt, the head's box and the eyes' height in it and its parameters."""
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
        "back_z_mm": base.BACK_Z,
    }


def optimise(doc):
    """The variant's parameters at their optimum on its MJCF without collision pieces (derivative-free, scipy): Back
    {"back_z_mm"}: the row's height, its top from higher over the eyes than the head's bottom is under them (the eyes in
    the head's lower half, #708) up to the head's height (gimbal.HEAD_MM), 0.25 mm inside each, where the tilt servo's
    worst hold against gravity over its range is least (MuJoCo's inverse dynamics, mujoco_report.torques, at each pose
    its sweep settles to). It also gives the hold there and at the drawn place."""
    model = mjcf.model(doc, collide=False)
    stage, still = stages.STAGES[doc], _rest(model)
    _, boards = CARRIER[doc]
    group = [model.body(f"{b}:1").id for b in boards()]  # the boards alone: the carrier is redrawn round them
    rides = stage.horns["tilt horn"].loops[0].rockers
    rest = [n for n in rides if model.body(n).id not in group and n.removesuffix(":1") not in skin.DRAWN]  # Skeleton
    lo, hi = stage.horns["tilt horn"].limits
    tilts = [mjcf.pose(model, {"tilt horn": d}) for d in np.linspace(lo, hi, 9)]
    pos0, turn = model.body_pos[group].copy(), still.xmat[model.body("next head mount:1").id].reshape(3, 3)
    origin = np.array(stages.DOCS[doc]["next-eyes"][0])

    def hold(dy, dz):
        model.body_pos[group] = pos0 + turn.T @ [0, dy, dz] / 1000
        for d in tilts:
            mujoco.mj_kinematics(model, d)
        k = model.actuator("tilt horn").id
        return max(abs(mujoco_report.torques(model, d, moving=False)[k]) for d in tilts) / mujoco_report.KGF_CM

    try:
        low = _drawn(model, still, rest)[:, 2].min() - origin[2]  # the head's bottom, under the eyes
        span = (-low - base.BOARD_H / 2 + 0.25, low + gimbal.HEAD_MM[2] - base.BOARD_H / 2 - 0.25)  # inside each gate
        found = minimize_scalar(lambda z: hold(0, z - base.BACK_Z), bounds=span, method="bounded")
        return {"back_z_mm": round(float(found.x), 1), "hold_kgf_cm": float(found.fun), "drawn_kgf_cm": hold(0, 0)}
    finally:
        model.body_pos[group] = pos0


if __name__ == "__main__":
    for doc in CARRIER:
        print(doc, optimise(doc))
