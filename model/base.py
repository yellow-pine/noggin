"""The next Mech's two Base candidates (#642, #51; GLOSSARY), clean-room (#618): their numbers (one source:
model/printed/base.py draws the parts from them, model/stages.py places them and the boards), what the sim report
reads (sway(), leads()) and the ranking of the two (rank()); model/candidates.py optimises their parameters in MuJoCo.

Frame: the head's (model/neck.py), z up, -y forward. In both the pack lies flat on the base plate behind the neck mount,
as low as it goes, inside the shirt; the base plate is the shirt's floor and the footprint the Mech stands on.
- (a) next-mech-a: the boards (both Shields, each Core plugged in under it, and the switch board) on the board tray,
  screwed under the gimbal frame's plate behind the head mount: they ride pan and tilt, behind and below the tilt axis.
  Optimised: the tray's place (TRAY), for the tilt servo's least worst hold over its range (mujoco_report.torques),
  kept clear of the yoke and the pack as the head tilts.
- (b) next-mech-b: the boards on the board tower's shelf over the lids, the tower a PETG rod on the pan axis, the only
  line a static post can rise along inside a head that pans, standing on the neck mount's column (the base carries the
  mount) in the pan shank's place. Optimised: its radius (TOWER_R), the thinnest whose sway stays at MODE_HZ or more. The neck's pan shank and the gimbal's middle sit on
  that axis, so the tower meets them: (b) fails the clearance gate until the neck and the gimbal are hollowed for it.
Every size is ours and inferred (no build settles one yet)."""

import math
import os

from model import geometry as g
from model import neck

PLATE = ((-60.0, 60.0), (-45.0, 95.0), (neck.MOUNT_Z[0] - 3, neck.MOUNT_Z[0]))  # the base plate: x, y, z
PACK_Y = 30.0  # the pack's front end, behind the neck mount's foot; its lead out the back
TRAY = (64.6, -89.6)  # (a): (y of the tray's front face, z of the boards' middles), candidates.optimise()'s
TRAY_T = 3.0  # the tray's plate
SHELF_Z = 45.0  # (b): the shelf's underside, over the lids' highest reach as the head tilts
TOWER_R = 3.21  # (b): candidates.optimise()'s
MODE_HZ = 8.0  # #51's lowest mode, at least (docs/research/2026-11-02-literature-motion-control.md)
GAP = 2.0  # between two boards in a row
CLEAR = 3.0  # (a): what candidates.optimise() keeps the tray from the parts it swings past (inferred)
# each place in the row: (the parts on it, as (name, Envelope); the Envelope's x extent and its back, the -y face:
# model/envelopes.py, held to it by model/test_base.py)
_ROW = (
    ((("next Shield 1", "receiver"), ("next Core 1", "core")), (-14.5, 14.5), -10.68),
    ((("next Shield 2", "receiver"), ("next Core 2", "core")), (-14.5, 14.5), -10.68),
    ((("next switch board", "switch"),), (-7.25, 13.25), -4.6),
)
ROW_W = sum(x1 - x0 for _, (x0, x1), _ in _ROW) + GAP * (len(_ROW) - 1)
BOARD_H, BOARD_D = 32.0, 21.5  # the row's height (the switch board's) and depth (a Shield with its Core)


def boards(back, z):
    """{part name: (Envelope, translation)}: the boards upright in a row along x, centred on x 0, their backs on the
    plane y = back, their middles at height z."""
    x, out = -ROW_W / 2, {}
    for parts, (x0, x1), y0 in _ROW:
        for name, mesh in parts:
            out[name] = (mesh, (x - x0, back - y0, z))
        x += x1 - x0 + GAP
    return out


def tray_boards():
    return boards(TRAY[0] + TRAY_T, TRAY[1])


def tower_boards():
    return boards(neck.AXIS[0] - BOARD_D / 2, SHELF_Z + TRAY_T + BOARD_H / 2)


def sway(r, grams, length, material="PETG HF"):
    """Hz: the lowest mode of a printed rod of radius r (mm) standing `length` mm free under `grams` on its tip, a
    cantilever bending across its layers (Rayleigh's tip mass plus 0.236 of the rod's own; geometry.MATERIALS)."""
    m = g.MATERIALS[material]
    k = 3 * m["E_mpa"]["z"] * math.pi * r**4 / 4 / length**3 * 1000  # N/m
    rod = m["density_g_cm3"] * math.pi * r**2 * length / 1000
    return math.sqrt(k / ((grams + 0.236 * rod) / 1000)) / (2 * math.pi)


def leads(stage):
    """{pivot: leads crossing it} for the pan and tilt pivots: each servo's lead and the pack's run to the boards (the
    Shields and the switch board stand together), so one crosses each pivot that turns one end and not the other."""

    def rides(part):
        return {loop.joint for h in stage.horns.values() for loop in h.loops if part in loop.rockers}

    boards = rides("next Shield 1:1")
    ends = [n for n, p in stage.parts.items() if os.path.basename(p.file) in ("servo.stl", "battery.stl")]
    return {j: sum(j in rides(n) ^ boards for n in ends) for j in ("pan pivot", "tilt pivot")}


def rank(reports):
    """The Base candidates ranked from their sim reports ({doc: model/build/reports/<doc>-sim.json}): the gate first (a
    candidate whose base meets another part anywhere in the sweep or along a motion is out), then #51's marks in its
    order (each servo holds at most its rated torque and peaks at most half its stall, the lowest mode at least MODE_HZ,
    the moving centre of mass inside the footprint), then its figures in that order, the first that differs deciding:
    simplicity (the base's printed parts), servo torque (worst hold, then peak), gravity torque at rest (the tilt
    servo's), the lowest mode (the neck servos' loops and the tower's sway), the leads crossing pan and tilt, the
    tip-over margin. Pack access is no criterion here: the pack lies in the same base in both."""
    out = {}
    for doc, r in reports.items():
        m, b = r["mujoco"], r["base"]
        servos = m["motions"]["servos"].values()
        modes = [v["servo_loop_hz"] for v in m["vibration"].values() if isinstance(v, dict)]
        c = {
            "printed": b["printed"],
            "hold_kgf_cm": max(
                [s["hold_kgf_cm"] for s in servos] + [a["hold_kgf_cm"] for a in m["actuators"].values()]
            ),
            "peak_kgf_cm": max(s["peak_kgf_cm"] for s in servos),
            "rest_kgf_cm": m["motions"]["servos"]["tilt horn"]["rest_kgf_cm"],
            "mode_hz": min(modes + ([b["sway_hz"]] if b["sway_hz"] else [])),
            "leads": sum(b["leads"].values()),
            "tip_mm": min(m["tip_over"]["margin_mm"], m["tip_over"]["moving"]["margin_mm"]),
        }
        rated, stall = (max(s[k] for s in servos) for k in ("rated_kgf_cm", "stall_kgf_cm"))
        marks = (c["hold_kgf_cm"] > rated, c["peak_kgf_cm"] > stall / 2, c["mode_hz"] < MODE_HZ, c["tip_mm"] <= 0)
        band = -m["clearance_mm"]  # past the pieces' own reading of a designed contact
        clear = sorted(p["pair"] for p in m["pairs"] if p["min_mm"] < band and set(p["pair"]) & set(b["parts"]))
        costs = (c["printed"], c["hold_kgf_cm"], c["peak_kgf_cm"], c["rest_kgf_cm"], -c["mode_hz"], c["leads"])
        out[doc] = {
            "gates": {"clearance": clear},
            "marks_missed": sum(marks),
            "criteria": c,
            "_key": (bool(clear), marks, (*costs, -c["tip_mm"])),
        }
    order = sorted(out, key=lambda d: out[d]["_key"])
    return {"order": order, "candidates": {d: {k: v for k, v in out[d].items() if k != "_key"} for d in order}}
