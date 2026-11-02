"""The next Mech's Base candidates in MuJoCo (#642; their numbers and ranking: model/base.py): each one's parameters
optimised on its MJCF (optimise(), `python -m model.candidates`, whose numbers model/base.py draws) and its figures for
the sim report (report(), model/report.py), which rank() orders."""

import mujoco
import numpy as np
from scipy.optimize import brentq, minimize

from model import base, mjcf, mujoco_report, neck, stages
from model import geometry as g


def _tip(model):
    """(grams on the tower's tip, the boards and the shelf, as the MJCF weighs the boards; its free length, mm: from the
    neck mount's column, which holds it, to the boards' middles)."""
    boards = sum(model.body(f"{n}:1").mass[0] for n in base.tower_boards()) * 1000
    shelf = g.MATERIALS["PETG HF"]["density_g_cm3"] * (base.ROW_W + 6) * base.BOARD_D * base.TRAY_T / 1000
    return boards + shelf, base.SHELF_Z + base.TRAY_T + base.BOARD_H / 2 - neck.DISC_Z[0]


def report(doc, model):
    """The candidate's figures for rank() from its document and its MJCF (model/report.py): the base's parts (the base
    plate, the pack, the carrier and the boards) and how many are printed, the leads crossing pan and tilt, its
    parameters and, for (b), the tower's sway."""
    stage = stages.STAGES[doc]
    parts = [n for sub in g.NEXT[doc] if sub not in ("next-neck", "next-eyes") for n in stages.SUBS[sub]().parts]
    out = {
        "parts": parts,
        "printed": sum(stages.stem(stage.parts[n].file).startswith("next ") for n in parts),
        "leads": base.leads(stage),
        "sway_hz": None,
    }
    if "next board tower:1" in stage.parts:
        return out | {"sway_hz": round(base.sway(base.TOWER_R, *_tip(model)), 1), "tower_r_mm": base.TOWER_R}
    return out | {"tray_mm": list(base.TRAY)}


def optimise(doc):
    """The candidate's parameters at their optimum, derivative-free (scipy), on its MJCF without collision pieces:
    (b) {"tower_r_mm"}: the thinnest tower whose sway is MODE_HZ (brentq); (a) {"tray_mm"}: the tray's place where the
    tilt servo's worst hold against gravity over its range is least (MuJoCo's inverse dynamics, mujoco_report.torques,
    at each pose its sweep settles to; COBYLA), every point of the tray and its boards below the tilt axis staying
    CLEAR behind what the pan turns and the tilt does not (the yoke, the tilt servo and its bar), and every one CLEAR
    above the static parts behind those (the pack in its cradle), at every pose, the boards under the tray's flange
    (model/base.py's numbers)."""
    model = mjcf.model(doc, collide=False)
    if doc == "next-mech-b":
        return {"tower_r_mm": round(brentq(lambda r: base.sway(r, *_tip(model)) - base.MODE_HZ, 0.5, 20.0), 2)}
    stage, still = stages.STAGES[doc], mujoco.MjData(model)
    mujoco.mj_kinematics(model, still)
    tilted = set(stage.horns["tilt horn"].loops[0].rockers)
    panned = set(stage.horns["pan horn"].loops[0].rockers) - tilted
    tray = [model.body(n).id for n in ("next board tray:1", *(f"{b}:1" for b in base.tray_boards()))]
    lo, hi = stage.horns["tilt horn"].limits
    poses = [mjcf.pose(model, {"tilt horn": d}) for d in np.linspace(lo, hi, 9)]
    axis_z = (stage.horns["tilt horn"].frame @ [0, *neck.AXIS, 1])[2]

    def drawn(names, data):
        return np.vstack([mujoco_report.vertices(model, data, model.body(n).id) for n in names])

    back = drawn(panned, still)[:, 1].max()
    static = drawn(stages.next_base().parts, still)
    floor = static[static[:, 1] > back][:, 2].max()
    pos0, head = model.body_pos[tray].copy(), model.body("next head mount:1").id
    turn = still.xmat[head].reshape(3, 3)

    def place(s):
        model.body_pos[tray] = pos0 + turn.T @ [0, s[0], s[1]] / 1000
        for d in poses:
            mujoco.mj_kinematics(model, d)
        return [np.vstack([mujoco_report.vertices(model, d, b) for b in tray]) for d in poses]

    def hold(s):
        place(s)
        k = model.actuator("tilt horn").id
        return max(abs(mujoco_report.torques(model, d, moving=False)[k]) for d in poses) / mujoco_report.KGF_CM

    def clear(s):
        vs = place(s)
        behind = min(v[v[:, 2] < axis_z][:, 1].min(initial=np.inf) - back for v in vs) - base.CLEAR
        above = min(v[:, 2].min() - floor for v in vs) - base.CLEAR
        under = neck.FLANGE_Z[0] - base.BOARD_H / 2 - (base.TRAY[1] + s[1])  # the boards under the tray's flange
        return min(behind, above, under)

    try:
        s = minimize(
            hold,
            [0.0, 0.0],
            method="COBYLA",
            constraints={"type": "ineq", "fun": clear},
            options={"rhobeg": 5.0, "tol": 0.05},
        ).x
    finally:
        model.body_pos[tray] = pos0
    return {"tray_mm": [round(float(base.TRAY[0] + s[0]), 1), round(float(base.TRAY[1] + s[1]), 1)]}


if __name__ == "__main__":
    for doc in g.NEXT:
        print(doc, optimise(doc))
