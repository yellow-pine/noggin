"""The next Mech's neck and jaw (#641): our own design, clean-room (#618). Its numbers (one source: model/printed/neck.py
draws the parts from them, model/stages.py places them), its kinematics and its report.

Frame: the eye gimbal's (model/gimbal.py), which is the head's: x along the eye line (the L eye at +x), -y forward, z
up, the origin midway between the eye centres. The head is the gimbal with the head mount screwed under its plate; it
turns on its own pivots and every servo drives through a bar, so the splines carry torque only:
- pan: the pan yoke turns on the neck mount about a vertical axis, the pan servo (on the mount) driving the yoke's lever;
- tilt: the head turns on the yoke's cheeks about an x axis under its plate, straight under the head's centre of mass at
  rest (AXIS), the tilt servo (on the yoke) driving the head mount's lever;
- jaw: the jaw turns on the head mount's lugs about an x axis behind the mouth, the mouth servo (on the head) driving it.
Each drive is a four-bar whose horn and lever lie parallel at rest, the bar square to both (model/linkage.py). Each
busy pivot is a steel shank (an M3 screw from the kit's spares, greased) turning in a bore printed along Z and threaded
into the part it is fixed in: the yoke turns on the mount's shank, the head mount (printed on its side) on the cheeks',
the jaw (on its side) on the head mount's, each bar (flat) on its lever's.
The leads cross pan and tilt in two flexing spans (GLOSSARY): pan's runs up beside the pan axis, so the turn is a twist
and a gentle S over its free length; tilt's is an arc about the tilt axis whose radius breathes as the head turns. The
pack's Y lead crosses as one pair and splits after the joints (#51). Angles are degrees: pan positive toward +x's
left (right-handed about +z), tilt and jaw right-handed about +x (the face down, the jaw open). Every size is ours and
inferred (no build settles one yet), each chosen against the gates in report()."""

import math

import numpy as np
from scipy.optimize import brentq

from model import geometry as g
from model import linkage

CRANK = g.HORN_STEP["pin"]  # every horn's pin from its hub
SERVO_DEG, TRANSMISSION_DEG = 90.0, 40.0  # a servo's travel either side of its centre; the bars' floor (#641)
RANGES = {"pan": (-45.0, 45.0), "tilt": (-20.0, 20.0), "jaw": (0.0, 25.0)}  # the eyes take +-25 more (#51)
AXIS = (8.5, -77.0)  # (y, z) where the pan axis (vertical, x 0) meets the tilt axis (along x): under the head's com
FLANGE_Z = (-70.0, -67.0)  # the head mount's flange, under the gimbal frame's plate
HEAD_SCREWS = (
    (16.0, -20.0),
    (-16.0, -20.0),
    (16.0, 26.0),
    (-16.0, 26.0),
)  # (x, y): the flange to the plate, nuts on top
CHEEK_X, LUG_X, BOSS_R = (9.0, 13.0), (13.0, 17.0), 6.0  # the yoke's cheeks, the head's tilt lugs outside them
DISC_R, DISC_Z = 15.0, (-110.0, -106.0)  # the yoke's disc on the mount's thrust face, its floor at the same depth
MOUNT_Z = (-150.0, -147.0)  # the neck mount's foot: the base (#642) carries it
PAN_LEVER, PAN_BAR, PAN_Z = 15.0, 30.0, (-113.0, -110.0)  # the yoke's lever back along +y; the bar along x under it
TILT_LEVER, TILT_BAR, TILT_BAR_X = 28.0, 20.0, (1.5, 4.5)  # the head's lever back along +y; the bar down to the horn
JAW = (-8.0, -92.0)  # (y, z) of the jaw's hinge
JAW_LEVER, JAW_HORN_Z, JAW_BAR_X = 20.0, -78.0, (22.0, 25.0)  # the jaw's pin forward of the hinge; the horn above it
JAW_X, CHIN_Y = (18.0, 22.0), -40.0  # the jaw's arms and hinge bosses, outside its lugs (LUG_X + 1); its chin's front
LEAD_OD = 1.4  # the thickest lead that crosses, the pack's pair (inferred: 24 AWG)
BEND_X = 10  # the flexing spans' floor: 10 x the lead's diameter (docs/research/2026-11-02-literature-electrical.md 4)
PAN_SPAN = (18.0, (-138.0, -108.0))  # its clamps in front of the pan axis at this radius: the mount's, then the yoke's
TILT_SPAN = (22.0, 45.0)  # its arc about the tilt axis: radius, and the turn from the head's clamp (straight below) to
LOOP_X = (-21.0, -17.0)  # the yoke's (behind, 45 deg up), outside the R tilt lug
# the parts the tilt turns with the eye gimbal: model/report.py weighs the head from them
HEAD = ("next head mount:1", "next jaw:1", "next jaw bar:1", "next mouth servo:1", "next mouth horn:1")


def _four_bar(o4, lever, horn, axis):
    """The drive with its lever from the pivot o4 to `lever` (its pin) and the horn's pivot at `horn`, the bar between the
    two pins square to both at rest."""
    pin = np.add(horn, np.subtract(lever, o4) / np.linalg.norm(np.subtract(lever, o4)) * CRANK)
    return linkage.four_bar(horn, tuple(pin), o4, lever, axis)


def pins():
    """{drive: (rocker pivot, its lever's pin, the horn's pivot, axis)} at rest."""
    y, z = AXIS
    pan_z = sum(PAN_Z) / 2
    return {
        "pan": ((0, y, pan_z), (0, y + PAN_LEVER, pan_z), (PAN_BAR, y + PAN_LEVER - CRANK, pan_z), g.Z),
        "tilt": ((0, y, z), (0, y + TILT_LEVER, z), (0, y + TILT_LEVER - CRANK, z - TILT_BAR), g.X),
        "jaw": ((0, *JAW), (0, JAW[0] - JAW_LEVER, JAW[1]), (0, JAW[0] - JAW_LEVER + CRANK, JAW_HORN_Z), g.X),
    }


LINKAGES = {d: _four_bar(o4, b, o2, axis) for d, (o4, b, o2, axis) in pins().items()}


def drives():
    """{label: (horn's outer face centre, shaft direction, tab direction, arm direction at rest)}: the neck Core's three
    servos, each horn on its bar (model/stages.py mounts them, model/printed/neck.py seats them)."""
    p = pins()
    pan, tilt, jaw = (p[d][2] for d in ("pan", "tilt", "jaw"))
    return {
        "pan": ((pan[0], pan[1], PAN_Z[0]), g.Z, g.Y, g.Y),
        "tilt": ((TILT_BAR_X[1], *tilt[1:]), (-1, 0, 0), (0, -1, 0), g.Y),
        "mouth": ((JAW_BAR_X[1], *jaw[1:]), (-1, 0, 0), (0, -1, 0), (0, -1, 0)),
    }


def servo_for(drive, out):
    """The servo angle (deg from its centre) that turns the drive's output to `out` deg: walked out from rest a degree at
    a time, then found within the degree."""
    solve = LINKAGES[drive]
    step = 1.0 if (solve(1.0)[0] > 0) == (out > 0) else -1.0
    s = 0.0
    while (solve(s + step)[0] - out) * (solve(s)[0] - out) > 0:
        s += step
        assert abs(s) < 180, f"{drive} never reaches {out} deg"
    return brentq(lambda a: solve(a)[0] - out, *sorted((s, s + step)))


def transmission(drive, servo_deg):
    """The angle between the bar and its lever at the servo's angle, folded to 0..90 (0 at the toggle)."""
    solve = LINKAGES[drive]
    _, a, b = solve(servo_deg)
    u, v = linkage._PLANE[tuple(solve.axis)]
    bar, lever = np.subtract(b, a)[[u, v]], np.subtract(b, solve.o4)[[u, v]]
    return math.degrees(math.acos(abs(bar @ lever) / (np.linalg.norm(bar) * np.linalg.norm(lever))))


def _sweep(drive):
    lo, hi = (servo_for(drive, d) if d else 0.0 for d in RANGES[drive])
    return np.linspace(*sorted((lo, hi)), 41)


def _hold(head, deg, gain):
    """kgf.cm the tilt servo holds the head with at `deg`, through the linkage's speed ratio `gain` there: the head's
    weight times its com's horizontal distance from the tilt axis (g x mm / 10^4 = kgf.cm)."""
    grams, (_, cy, cz) = head
    dy, dz = cy - AXIS[0], cz - AXIS[1]
    a = math.radians(deg)
    return abs(grams * (dy * math.cos(a) - dz * math.sin(a)) * gain) / 1e4


def _spans():
    """The flexing spans' tightest bend, mm. Pan: its two clamps hold the lead along z, the yoke's swung by the pan's
    largest turn, so the lead runs an S of two equal arcs. Tilt: the lead's turn between its clamps is the arc's,
    shortened or lengthened by the tilt; its length spread over it (an arc about the axis whose radius breathes)."""
    r, (z0, z1) = PAN_SPAN
    off = 2 * r * math.sin(math.radians(max(map(abs, RANGES["pan"]))) / 2)
    pan = ((z1 - z0) ** 2 / 4 + off**2 / 4) / off
    rho, turn = TILT_SPAN
    tilt = rho * turn / (turn + max(map(abs, RANGES["tilt"])))
    return {"pan": {"bend_mm": round(pan, 2)}, "tilt": {"bend_mm": round(tilt, 2)}, "floor_mm": BEND_X * LEAD_OD}


def report(head):
    """The neck's numbers against #641's gates, for a head of (grams, centre of mass in this frame, mm): per drive its
    output range, the servo angles that reach it, the bar's worst transmission angle on the way and the gain at rest;
    for tilt the head's hold at rest and at worst; where the head's centre of mass sits from the tilt axis; and the
    flexing spans' tightest bends against their floor."""
    out = {}
    for drive, solve in LINKAGES.items():
        sweep = _sweep(drive)
        out[drive] = {
            "range_deg": list(RANGES[drive]),
            "servo_deg": [round(servo_for(drive, d), 1) for d in RANGES[drive]],
            "transmission_deg": round(min(transmission(drive, s) for s in sweep), 1),
            "gain": round((solve(0.5)[0] - solve(-0.5)[0]), 3),
        }
    sweep = _sweep("tilt")
    solve = LINKAGES["tilt"]
    holds = [_hold(head, solve(s)[0], (solve(s + 0.5)[0] - solve(s - 0.5)[0])) for s in sweep]
    out["tilt"] |= {"rest_kgf_cm": round(_hold(head, 0.0, out["tilt"]["gain"]), 3), "hold_kgf_cm": round(max(holds), 3)}
    grams, (_, cy, cz) = head
    out["head"] = {
        "grams": round(grams, 1),
        "above_tilt_mm": round(cz - AXIS[1], 1),
        "behind_tilt_mm": round(cy - AXIS[0], 1),
    }
    out["spans"] = _spans()
    return out
