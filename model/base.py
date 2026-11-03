"""The next Mech's head variants (#686, #51; GLOSSARY), clean-room (#618): their numbers (one source: model/printed/base.py
draws the parts from them, model/stages.py places them and the boards), what the sim report reads (sway(), leads(),
head()) and the ranking of their reports (rank()); model/candidates.py optimises their parameters in MuJoCo.

Frame: the head's (model/neck.py), z up, -y forward. In each the base is the Torso (#685, GLOSSARY): the shirt itself, a
compact open box whose floor carries the neck mount (with the pan servo in its collar) and, behind it, the pack lying
flat across x as low as it goes; its bottom is the foot the Mech stands on. Only the pack's pair and the pan servo's
lead leave it for the head's side of pan (leads(); #51's wiring rules). The boards (both Shields, each Core plugged in
under it, and the switch board) go in the compact head, everything riding it within gimbal.HEAD_MM (#51), in one
variant since Cansin picked it (#712; the ranking stays for the next):
- Back, next-mech-back: the board rack screwed under the gimbal frame's plate at its back edge rises behind the eye
  gimbal and reaches forward over it, the boards upright in a row on its shelf over the eyes, in the head's crown, so
  the eyes sit in the head's lower half (#708). Optimised: the row's height (BACK_Z) between the eyes' gate and the
  head's, for the tilt servo's least worst hold over its range (mujoco_report.torques).
Every size is ours and inferred (no build settles one yet)."""

import os

import numpy as np

from model import gimbal, neck

# the Torso's outside: x, y, and z from its foot to its walls' top (under the pack's, 16.3 mm up), round the neck mount's
# foot (x -14..42, y -13.5..24.5) and the pack in its cradle behind it; its front reaches on to y -35, where the next
# hero's tilt (~3.8 m/s2 on the old tower candidate's head) bears the moving centre of mass to y -25.5 (inferred, #685)
TORSO = ((-46.0, 46.0), (-35.0, 58.5), (neck.MOUNT_Z[0] - 3, neck.MOUNT_Z[0] + 16))
PACK_Y = 41.5  # the pack's middle, lying across x behind the neck mount's foot; its lead out to -x
PACK = (51.2, 28.36)  # the pack's footprint lying across x: model/envelopes.py battery's (model/test_base.py)
TRAY_T = 3.0  # the carriers' plates
MODE_HZ = 8.0  # #51's lowest mode, at least (docs/research/2026-11-02-literature-motion-control.md)
EYES_UP = 0.5  # the eye centres at most this far up what rides the head, 0 its bottom: cartoon proportions (#708)
GAP = 2.0  # between two boards in a row
RACK_Y = gimbal.PLATE_Y[1]  # the rack's posts' front face, on the gimbal frame plate's back edge
BACK_Z = 58.8  # Back: the row's middle, candidates.optimise()'s
BACK_Y = -2.0  # Back: the row's backs, its middle over the tilt axis (inferred)
# each place in the row: (the parts on it, as (name, Envelope); the Envelope's x extent, its back (the -y face) and its
# bottom: model/envelopes.py, held to it by model/test_base.py)
ROW = (
    ((("next Shield 1", "receiver"), ("next Core 1", "core")), (-14.5, 14.5), -10.68, -15.0),
    ((("next Shield 2", "receiver"), ("next Core 2", "core")), (-14.5, 14.5), -10.68, -15.0),
    ((("next switch board", "switch"),), (-7.25, 13.25), -4.6, -16.0),
)
BOARD_H, BOARD_D = 32.0, 21.5  # the row's height (the switch board's) and depth (a Shield with its Core)


def width(row=ROW):
    return sum(x1 - x0 for _, (x0, x1), _, _ in row) + GAP * (len(row) - 1)


def _row(row):
    """{part name: (Envelope, 4x4)}: the boards upright in a row along x, centred on x 0, their backs on y 0, their
    bottoms on z 0."""
    x, out = -width(row) / 2, {}
    for parts, (x0, x1), y0, z0 in row:
        for name, mesh in parts:
            m = np.eye(4)
            m[:3, 3] = (x - x0, -y0, -z0)
            out[name] = (mesh, m)
        x += x1 - x0 + GAP
    return out


def _moved(row, m):
    return {n: (mesh, m @ at) for n, (mesh, at) in row.items()}


def standing(back, z, row=ROW):
    """The row upright, its backs on the plane y = back, its bottoms level BOARD_H / 2 under z (the tallest's middle at
    z), so each stands on what holds them (#687)."""
    m = np.eye(4)
    m[:3, 3] = (0, back, z - BOARD_H / 2)
    return _moved(_row(row), m)


def back_boards():
    return standing(BACK_Y, BACK_Z)


# Stage 1's test stand (#720): a box under the gimbal frame's plate, screwed up through the head mount's holes, from the
# desk to the plate's underside, the eyes Core (Shield 1, Core 1) standing on the desk against its back face (inferred)
STAND_H = 40.0
STAND_Z = gimbal.PLATE_Z[0] - STAND_H  # its foot, in the head's frame


def stand_boards():
    return standing(RACK_Y, STAND_Z + BOARD_H / 2, ROW[:1])


def leads(stage):
    """{pivot: leads crossing it} for the pan and tilt pivots: each servo's lead to the Shields, the pack's to the switch
    board and the switch board's on to the Shields, so one crosses each pivot that turns one end and not the other."""

    def rides(part):
        return {loop.joint for h in stage.horns.values() for loop in h.loops if part in loop.rockers}

    shield, switch = rides("next Shield 1:1"), rides("next switch board:1")
    ends = [(rides(n), shield) for n, p in stage.parts.items() if os.path.basename(p.file) == "servo.stl"]
    ends += [(rides(n), switch) for n, p in stage.parts.items() if os.path.basename(p.file) == "battery.stl"]
    ends.append((switch, shield))
    return {j: sum(j in a ^ b for a, b in ends) for j in ("pan pivot", "tilt pivot")}


AXES = ("width", "depth", "height")  # gimbal.HEAD_MM's order


def rank(reports):
    """The head variants ranked from their sim reports ({doc: model/build/reports/<doc>-sim.json}): the gates first (a
    variant whose boards or their carriers meet another part anywhere in the sweep or along a motion, whose head is
    past gimbal.HEAD_MM, or whose eyes sit higher up it than EYES_UP, is out), then #51's marks in its order (each
    servo holds at most its rated torque and peaks at most half its stall, the lowest mode at least MODE_HZ, the moving
    centre of mass inside the footprint), then its figures in that order, the first that differs deciding: simplicity (the printed parts beside the neck and gimbal),
    servo torque (worst hold, then peak), gravity torque at rest (the tilt servo's), the lowest mode (the servos'
    loops), the head's fit (its least room left, mm), the leads crossing pan and tilt, the tip-over
    margin. Pack access is no criterion here: the pack lies in the same Torso in each. Each variant's `fails` names the
    gates and marks it misses, as the viewer marks its button; a four-bar its sweep opens past the report's gate is one
    ("tilt loop", #705), which model/test_report.py then excuses for any variant but the first."""
    out = {}
    for doc, r in reports.items():
        m, v = r["mujoco"], r["variant"]
        servos = m["motions"]["servos"].values()
        modes = [x["servo_loop_hz"] for x in m["vibration"].values() if isinstance(x, dict)]
        c = {
            "printed": v["printed"],
            "hold_kgf_cm": max(
                [s["hold_kgf_cm"] for s in servos] + [a["hold_kgf_cm"] for a in m["actuators"].values()]
            ),
            "peak_kgf_cm": max(s["peak_kgf_cm"] for s in servos),
            "rest_kgf_cm": m["motions"]["servos"]["tilt horn"]["rest_kgf_cm"],
            "mode_hz": min(modes),
            "head_room_mm": round(min(h - s for s, h in zip(v["head_mm"], gimbal.HEAD_MM)), 1),
            "leads": sum(v["leads"].values()),
            "tip_mm": min(m["tip_over"]["margin_mm"], m["tip_over"]["moving"]["margin_mm"]),
        }
        rated, stall = (max(s[k] for s in servos) for k in ("rated_kgf_cm", "stall_kgf_cm"))
        marks = {
            "torque": c["hold_kgf_cm"] > rated or c["peak_kgf_cm"] > stall / 2,
            "mode": c["mode_hz"] < MODE_HZ,
            "tip-over": c["tip_mm"] <= 0,
        }
        band = -m["clearance_mm"]  # past the pieces' own reading of a designed contact
        clear = sorted(sorted(p["pair"]) for p in m["pairs"] if p["min_mm"] < band and set(p["pair"]) & set(v["parts"]))
        gates = {
            "clearance": clear,
            "head": [a for a, s, h in zip(AXES, v["head_mm"], gimbal.HEAD_MM) if s > h],
            "eyes": v["eyes_up"] > EYES_UP,
            "loops": [n for n, x in m["residuals"].items() if x["max_mm"] > m["loop_mm"]],
        }
        costs = (c["printed"], c["hold_kgf_cm"], c["peak_kgf_cm"], c["rest_kgf_cm"], -c["mode_hz"], -c["head_room_mm"])
        out[doc] = {
            "gates": gates,
            "fails": [
                n for n, k in (("clearance", "clearance"), ("head size", "head"), ("eyes up", "eyes")) if gates[k]
            ]
            + [f"{n.removesuffix(' pivot')} loop" for n in gates["loops"]]
            + [n for n, missed in marks.items() if missed],
            "criteria": c,
            "_key": (sum(map(bool, gates.values())), tuple(marks.values()), (*costs, c["leads"], -c["tip_mm"])),
        }
    order = sorted(out, key=lambda d: out[d]["_key"])
    return {"order": order, "variants": {d: {k: v for k, v in out[d].items() if k != "_key"} for d in order}}
