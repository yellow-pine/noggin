"""The next Mech's head variants in MuJoCo (#686; their numbers and ranking: model/base.py): each one's parameters
optimised on its MJCF (optimise(), `python -m model.candidates`, whose numbers model/base.py draws) and its figures for
the sim report (report(), model/report.py), which rank() orders."""

import itertools

import mujoco
import numpy as np
from scipy.optimize import minimize_scalar

from model import base, gimbal, mjcf, mujoco_report, stages
from model import geometry as g

GIMBAL = ("next yaw horn", "next pitch horn", "next L lid horn", "next R lid horn")
# each variant's carrier and the boards on it, which optimise() moves
CARRIER = {
    "next-mech-back": ("next board rack", base.back_boards),
    "next-mech-crown": ("next crown shelf", base.crown_boards),
    "next-mech-split": ("next split shelf", base.split_boards),
}


def _rest(model):
    data = mujoco.MjData(model)
    mujoco.mj_kinematics(model, data)
    return data


def _drawn(model, data, names):
    return np.vstack([mujoco_report.vertices(model, data, model.body(n).id) for n in names])


def head(doc, model):
    """What rides the head (the tilt's parts) at rest: its box, mm, as gimbal.HEAD_MM (width, depth, height), and how
    far up the box the eye centres sit (0 its bottom, 1 its top)."""
    v = _drawn(model, _rest(model), stages.STAGES[doc].horns["tilt horn"].loops[0].rockers)
    lo, hi = v.min(axis=0), v.max(axis=0)
    eyes = stages.DOCS[doc][0]["next-eyes"][0][2]
    return [round(float(s), 1) for s in hi - lo], round(float((eyes - lo[2]) / (hi[2] - lo[2])), 2)


def report(doc, model):
    """The variant's figures for rank() from its document and its MJCF (model/report.py): the parts beside the neck and
    the gimbal (the Torso, the pack, the carriers and the boards) and how many are printed, the leads crossing pan and
    tilt, the head's box and the eyes' height in it, its parameters and, for a crown shelf, its wall's sway."""
    stage = stages.STAGES[doc]
    parts = [n for sub in g.NEXT[doc] if sub not in ("next-neck", "next-eyes") for n in stages.SUBS[sub]().parts]
    size, eyes = head(doc, model)
    out = {
        "parts": parts,
        "printed": sum(stages.stem(stage.parts[n].file).startswith("next ") for n in parts),
        "leads": base.leads(stage),
        "head_mm": size,
        "eyes_up": eyes,
        "sway_hz": None,
    }
    stem, boards = CARRIER[doc]
    if stem == "next board rack":
        return out | {"back_z_mm": base.BACK_Z}
    # on the wall's tip: the boards and the whole carrier, as the MJCF weighs them (its wall and flange too: an
    # underestimate of the mode)
    tip = sum(model.body(f"{n}:1").mass[0] for n in (stem, *boards())) * 1000
    wide = base.width(base.PAIR if "split" in stem else base._ROW) + 6
    length = base.CROWN_Z + base.TRAY_T - gimbal.PLATE_Z[0]  # the wall, free from the plate's underside
    y = base.SPLIT_Y if "split" in stem else base.CROWN_Y
    return out | {
        "sway_hz": round(base.sway(wide, base.TRAY_T, tip, length), 1),
        "crown_mm": [y, base.CROWN_Z],
    }


def optimise(doc):
    """The variant's parameters at their optimum on its MJCF without collision pieces (derivative-free, scipy): Back
    {"back_z_mm"}: the row's height, within the gimbal's (from the plate's underside to its top), where the tilt
    servo's worst hold against gravity over its range is least (MuJoCo's inverse dynamics, mujoco_report.torques, at
    each pose its sweep settles to); Crown and Split {"crown_mm": [y, z]}: the shelf's underside z the lowest CLEAR over
    the gimbal's top over its whole range (each of its horns at either end or at rest, every combination), then the
    row's place front to back y, within the head's depth, where that hold is least. Each also gives the hold there and
    at the drawn place."""
    model = mjcf.model(doc, collide=False)
    stage, still = stages.STAGES[doc], _rest(model)
    stem, boards = CARRIER[doc]
    group = [model.body(f"{b}:1").id for b in boards()]  # the boards alone: the carrier is redrawn round them
    lo, hi = stage.horns["tilt horn"].limits
    tilts = [mjcf.pose(model, {"tilt horn": d}) for d in np.linspace(lo, hi, 9)]
    pos0, turn = model.body_pos[group].copy(), still.xmat[model.body("next head mount:1").id].reshape(3, 3)
    origin = np.array(stages.DOCS[doc][0]["next-eyes"][0])

    def hold(dy, dz):
        model.body_pos[group] = pos0 + turn.T @ [0, dy, dz] / 1000
        for d in tilts:
            mujoco.mj_kinematics(model, d)
        k = model.actuator("tilt horn").id
        return max(abs(mujoco_report.torques(model, d, moving=False)[k]) for d in tilts) / mujoco_report.KGF_CM

    eyes = list(stages.next_eyes().parts)
    try:
        if stem == "next board rack":
            top = _drawn(model, still, eyes)[:, 2].max() - origin[2]
            span = (gimbal.PLATE_Z[0] + base.BOARD_H / 2, top - base.BOARD_H / 2)
            found = minimize_scalar(lambda z: hold(0, z - base.BACK_Z), bounds=span, method="bounded")
            return {"back_z_mm": round(float(found.x), 1), "hold_kgf_cm": float(found.fun), "drawn_kgf_cm": hold(0, 0)}
        ends = [(0.0, *stage.horns[h].limits) for h in GIMBAL]
        poses = [mjcf.pose(model, dict(zip(GIMBAL, c))) for c in itertools.product(*ends)]
        moving = [n for n in eyes if n != "next gimbal frame:1"]
        top = max(_drawn(model, d, moving)[:, 2].max() for d in poses) - origin[2]
        z = round(float(top + base.CLEAR), 1)
        y0 = base.SPLIT_Y if "split" in stem else base.CROWN_Y
        front = _drawn(model, still, stage.horns["tilt horn"].loops[0].rockers)[:, 1].min() - origin[1]
        span = (front + base.BOARD_H / 2, base.RACK_Y - base.BOARD_H / 2)  # the row on the shelf, inside the head
        found = minimize_scalar(lambda y: hold(y - y0, z - base.CROWN_Z), bounds=span, method="bounded")
        out = {"crown_mm": [round(float(found.x), 1), z], "hold_kgf_cm": float(found.fun)}
        return out | {"drawn_kgf_cm": hold(0, 0)}
    finally:
        model.body_pos[group] = pos0


if __name__ == "__main__":
    for doc in CARRIER:
        print(doc, optimise(doc))
