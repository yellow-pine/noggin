"""The next Mech's head variants (#686, #51; GLOSSARY), clean-room (#618): their numbers (one source: model/printed/base.py
draws the parts from them, model/stages.py places them and the boards), what the sim report reads (sway(), leads(),
head()) and the ranking of their reports (rank()); model/candidates.py optimises their parameters in MuJoCo.

Frame: the head's (model/neck.py), z up, -y forward. In each the base is the Torso (#685, GLOSSARY): the shirt itself, a
compact open box whose floor carries the neck mount (with the pan servo in its collar) and, behind it, the pack lying
flat across x as low as it goes; its bottom is the foot the Mech stands on. Only the pack's pair and the pan servo's
lead leave it for the head's side of pan (leads(); #51's wiring rules). The boards (both Shields, each Core plugged in
under it, and the switch board) go in the compact head, everything riding it within gimbal.HEAD_MM (#51):
- Back, next-mech-back: the boards upright in a row on the back face of the board rack, screwed under the gimbal
  frame's plate at its back edge, behind the eye gimbal. Optimised: the row's height (BACK_Z) within the gimbal's, for
  the tilt servo's least worst hold over its range (mujoco_report.torques).
- Crown, next-mech-crown: the boards lying flat in a row on the crown shelf over the eye gimbal, carried on a wall
  screwed under the plate's back edge. Optimised: the shelf's height (CROWN_Z), the lowest that clears the gimbal over
  its whole range, and the row's place front to back (CROWN_Y) for the tilt servo's least worst hold.
- Split, next-mech-split: the Cores and Shields lying flat on the split shelf (the crown shelf for two), the switch
  board lying under the switch bracket at the back of the pan yoke, low, so it rides the pan alone. Optimised as Crown
  (SPLIT_Y); the switch board's place (SWITCH) is the nearest behind the Torso's pack it clears as the neck pans.
Every size is ours and inferred (no build settles one yet)."""

import math
import os

import numpy as np

from model import geometry as g
from model import gimbal, neck

# the Torso's outside: x, y, and z from its foot to its walls' top (under the pack's, 16.3 mm up), round the neck mount's
# foot (x -14..42, y -13.5..24.5) and the pack in its cradle behind it; its front reaches on to y -35, where the next
# hero's tilt (~3.8 m/s2 on the old tower candidate's head) bears the moving centre of mass to y -25.5 (inferred, #685)
TORSO = ((-46.0, 46.0), (-35.0, 58.5), (neck.MOUNT_Z[0] - 3, neck.MOUNT_Z[0] + 16))
PACK_Y = 41.5  # the pack's middle, lying across x behind the neck mount's foot; its lead out to -x
PACK = (51.2, 28.36)  # the pack's footprint lying across x: model/envelopes.py battery's (model/test_base.py)
TRAY_T = 3.0  # the carriers' plates
MODE_HZ = 8.0  # #51's lowest mode, at least (docs/research/2026-11-02-literature-motion-control.md)
GAP = 2.0  # between two boards in a row
CLEAR = 3.0  # what candidates.optimise() keeps the boards from the parts they ride past (inferred)
RACK_Y = gimbal.PLATE_Y[1]  # the rack's and the crown wall's front face, on the gimbal frame plate's back edge
BACK_Z = -51.0  # Back: the row's middle, candidates.optimise()'s
CROWN_Z = 33.5  # Crown and Split: the shelf's underside, candidates.optimise()'s
CROWN_Y = -24.0  # Crown: the row's middle front to back, candidates.optimise()'s
SPLIT_Y = -24.0  # Split: the pair's middle front to back, candidates.optimise()'s
SWITCH = (82.0, neck.DISC_Z[0])  # Split: (y of the switch board's middle, z of the bracket's underside) (inferred)
# each place in the row: (the parts on it, as (name, Envelope); the Envelope's x extent, its back (the -y face) and its
# bottom: model/envelopes.py, held to it by model/test_base.py)
ROW = (
    ((("next Shield 1", "receiver"), ("next Core 1", "core")), (-14.5, 14.5), -10.68, -15.0),
    ((("next Shield 2", "receiver"), ("next Core 2", "core")), (-14.5, 14.5), -10.68, -15.0),
    ((("next switch board", "switch"),), (-7.25, 13.25), -4.6, -16.0),
)
PAIR = ROW[:2]  # the Cores and Shields alone (Split's crown)
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


def lying(y, z, row=ROW):
    """The row turned onto its backs (90 deg about x, its tops forward), the backs on the plane z = z, the row's middle
    front to back on y (each board's bottom edge level, BOARD_H / 2 behind y)."""
    m = np.array([[1, 0, 0, 0], [0, 0, -1, y + BOARD_H / 2], [0, 1, 0, z], [0, 0, 0, 1]], dtype=float)
    return _moved(_row(row), m)


def back_boards():
    return standing(RACK_Y + TRAY_T, BACK_Z)


def crown_boards():
    return lying(CROWN_Y, CROWN_Z + TRAY_T)


def split_boards():
    return lying(SPLIT_Y, CROWN_Z + TRAY_T, PAIR)


def switch_boards():
    """The switch board lying face down under its bracket, its back on the bracket's underside, centred on x 0."""
    down = np.array([[1, 0, 0, 0], [0, 0, 1, SWITCH[0] - BOARD_H / 2], [0, -1, 0, SWITCH[1]], [0, 0, 0, 1]], float)
    return _moved(_row(ROW[2:]), down)


def sway(wide, thick, grams, length, material="PETG HF"):
    """Hz: the lowest mode of a printed plate `wide` x `thick` mm standing `length` mm free under `grams` on its tip,
    a cantilever bending across its thickness and its layers (Rayleigh's tip mass plus 0.236 of the plate's own;
    geometry.MATERIALS)."""
    m = g.MATERIALS[material]
    k = 3 * m["E_mpa"]["z"] * wide * thick**3 / 12 / length**3 * 1000  # N/m
    plate = m["density_g_cm3"] * wide * thick * length / 1000
    return math.sqrt(k / ((grams + 0.236 * plate) / 1000)) / (2 * math.pi)


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
    variant whose boards or their carriers meet another part anywhere in the sweep or along a motion, or whose head
    is past gimbal.HEAD_MM, is out), then #51's marks in its order (each servo holds at most its rated torque and peaks
    at most half its stall, the lowest mode at least MODE_HZ, the moving centre of mass inside the footprint), then its
    figures in that order, the first that differs deciding: simplicity (the printed parts beside the neck and gimbal),
    servo torque (worst hold, then peak), gravity torque at rest (the tilt servo's), the lowest mode (the neck servos'
    loops and the crown's sway), the head's fit (its least room left, mm), the leads crossing pan and tilt, the tip-over
    margin. Pack access is no criterion here: the pack lies in the same Torso in each. Each variant's `fails` names the
    gates and marks it misses, as the viewer marks its button."""
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
            "mode_hz": min(modes + ([v["sway_hz"]] if v["sway_hz"] else [])),
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
        gates = {"clearance": clear, "head": [a for a, s, h in zip(AXES, v["head_mm"], gimbal.HEAD_MM) if s > h]}
        costs = (c["printed"], c["hold_kgf_cm"], c["peak_kgf_cm"], c["rest_kgf_cm"], -c["mode_hz"], -c["head_room_mm"])
        out[doc] = {
            "gates": gates,
            "fails": [n for n, k in (("clearance", "clearance"), ("head size", "head")) if gates[k]]
            + [n for n, missed in marks.items() if missed],
            "criteria": c,
            "_key": (sum(map(bool, gates.values())), tuple(marks.values()), (*costs, c["leads"], -c["tip_mm"])),
        }
    order = sorted(out, key=lambda d: out[d]["_key"])
    return {"order": order, "variants": {d: {k: v for k, v in out[d].items() if k != "_key"} for d in order}}
