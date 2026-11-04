"""The Mech's neck and jaw (#641): our own design, clean-room (#618). Its numbers (one source: model/printed/neck.py
draws the parts from them, model/stages.py places them), its kinematics and its report.

Frame: the eye gimbal's (model/gimbal.py), which is the head's: x along the eye line (the L eye at +x), -y forward, z
up, the origin midway between the eye centres. The head is the gimbal with the head mount screwed under its plate; it
turns on its own pivots and every servo drives through a bar, so the splines carry torque only:
- pan: the pan yoke turns on the top of the neck mount's post about a vertical axis, under the head (#858), the pan
  servo (on the post, over the Torso's lid) driving the yoke's lever;
- tilt: the head turns on the yoke's cheeks about an x axis under its plate, where the realistic skull's foramen magnum
  is (AXIS, #838): behind the head's centre of mass, whose weight a balance spring on the tilt shank holds (balance()),
  the tilt servo (on the yoke) driving the head mount's lever;
- jaw: the jaw turns on the gimbal frame's lugs about an x axis through the realistic mandible's condyles (#838), the
  mouth servo (on the frame, behind the jaw) driving it.
Each drive is a four-bar whose horn and lever lie parallel at rest, the bar square to both (model/linkage.py). Each
busy pivot is a steel shank (an M3 screw from the kit's spares, greased) turning in a bore printed along Z and threaded
into the part it is fixed in: the yoke turns on the mount's shank, the head mount (printed on its side) on the cheeks',
the jaw (on its side) on the frame's, each bar (flat) on its lever's.
The leads cross pan and tilt in two flexing spans (GLOSSARY): pan's runs up beside the pan axis, so the turn is a twist
and a gentle S over its free length; tilt's is an arc about the tilt axis whose radius breathes as the head turns. The neck
cable (#858: up the hollow post from the Torso, out of it over the lid) crosses as pairs and the pan servo's lead with
it (#51). Angles are degrees: pan positive toward +x's
left (right-handed about +z), tilt and jaw right-handed about +x (the face down, the jaw open). Every size is ours and
inferred (no build settles one yet), each chosen against the gates in report()."""

import math

import numpy as np
from scipy.optimize import brentq

from model import geometry as g
from model import linkage

# #902's actual mechanical interface in the head's frame. #874 verifies anatomical registration and finished loads;
# prototype canal estimates are not anatomical anchors.
HEAD_FRAME = g._HEAD
HEAD_AXES = {
    "tilt": ((0.0, 76.6, -48.7), g.X),
    "pan": ((0.0, 46.2, -35.2), g.Z),
    "jaw": ((0.0, 60.05856, -41.60731), g.X),  # measured #874 v7 condylar patch line, within 0.03 mm of +X
}
HEAD_PARENTS = {"tilt": None, "pan": "tilt", "jaw": "pan"}
HEAD_CARRIERS = {"fixed": "cervical carrier:1", "tilt": "nod plate:1", "pan": "head mount:1", "jaw": "jaw:1"}
BONE_CARRIERS = {"head": HEAD_CARRIERS["pan"], "jaw": HEAD_CARRIERS["jaw"], "fixed": HEAD_CARRIERS["fixed"]}
HEAD_SERVOS = {"tilt": "tilt", "pan": "tilt", "mouth": "pan"}  # cases: both head servos on the nod plate
NOD_X, NOD_Y, NOD_Z = (-28.0, 28.0), (34.2, 88.6), (-52.0, -47.0)
BEARING_Z = (-47.0, -42.0)  # lower axial stack clears the actual condylar lugs throughout pan
TILT_SHAFT = (-24.4, 60.0, 78.0)  # actual case above the electronics: public CAD + private 6.8 mm stack preflight #978
TILT_ARM = (46.0, -18.0)  # lower fixed pin clears the nod plate at full tilt; equal moving/fixed arms preserve 1:1
TILT_PIN = (0.0, TILT_SHAFT[1] + TILT_ARM[0], TILT_SHAFT[2] + TILT_ARM[1])
TILT_ANCHOR = (0.0, HEAD_AXES["tilt"][0][1] + TILT_ARM[0], HEAD_AXES["tilt"][0][2] + TILT_ARM[1])
TILT_BAR_PATH = (TILT_ANCHOR, (0.0, 120.0, 30.0), (0.0, 120.0, 65.0), TILT_PIN)  # behind the full swept PCB/tray volume
REACTION_BAR_X = (-4.5, 1.5)  # actual standard-servo stall bending load, not a micro-servo bar
REACTION_TAP_X = (REACTION_BAR_X[0] - 4.3, REACTION_BAR_X[0] - 0.3)
PAN_HORN_Z = BEARING_Z[0] - 7.0  # keyed torque foot below the plate; quill passes freely through the 8 mm bearing
WIRE_R = 4.0  # four power conductors through the actual cervical canal, never a full-width tilt axle
CERVICAL_PATH = (
    (64.0, -171.0),
    (76.0, -154.0),
    (91.6, -146.0),
    (78.5, -60.7),
    (76.6, -48.7),
)  # (y,z), over the pack into the true canal
CERVICAL_X = (16.0, 8.0, 8.0, 8.0, 8.0)  # medial rails keep the C0 trunnions inside the condyles' pan sweep
CARRIER_FEET = ((-16.0, 64.0), (16.0, 64.0))
FRAME_OPEN_R = 8.5  # the bearing's clearance opening in the gimbal plate, not the whole nod plate's swept disc

CRANK = g.HORN_STEP["pin"]  # every horn's pin from its hub
SERVO_DEG, TRANSMISSION_DEG = 90.0, 40.0  # a servo's travel either side of its centre; the bars' floor (#641)
RANGES = {"pan": (-45.0, 45.0), "tilt": (-20.0, 20.0), "jaw": (0.0, 25.0)}  # the eyes take +-25 more (#51)
AXIS = (61.0, -42.0)  # legacy base/Skin layout datum; actual physical joint axes are HEAD_AXES
FLANGE_Z = (-41.0, -38.0)  # the head mount's flange, under the gimbal frame's plate's back (model/gimbal.py PLATE_Z)
HEAD_SCREWS = (
    (16.0, 48.0),
    (-16.0, 48.0),
    (16.0, 83.0),
    (-16.0, 83.0),
)  # (x, y): the flange to the plate, nuts on top, behind the mouth servo, the rear pair by the tilt span's clamp
CHEEK_X, LUG_X, BOSS_R = (9.0, 13.0), (13.0, 17.0), 4.0
JAW_FIXED_R = 3.3  # M3 tapping bore r1.25 leaves 2.05 mm; clears the upper C0 knuckle through pan
# The neck as a spine (#838): the neck mount's post rising from its foot on the Torso's floor through the lid, hollow for
# the neck cable, and the pan at its top under the head (#858): the yoke's disc on it under its top floor, on which the
# tilt servo stands, the cheeks up from it to the tilt axis; the pan servo hangs on the post over the lid
DISC_R, DISC_Z = 15.0, (-84.0, -80.0)  # the yoke's disc on the post's thrust face, under its top floor
POST_R, TOP_Z = 10.0, (-80.0, -76.0)  # the neck mount's post, and the yoke's top floor under the tilt servo
MOUNT_Z = (-174.0, -171.0)  # the neck mount's foot: the base (#642) carries it
SHELF_Z = (-123.5, -120.5)  # the post's shelf under the pan servo, 1.5 mm over the Torso's lid (model/base.py)
PAN_LEVER, PAN_BAR, PAN_Z = 15.0, 30.0, (-87.0, -84.0)  # the yoke's lever back along +y; the bar along x under it
# the head's lever back along +y; the bar down to the horn, its servo on the yoke's top floor, clear of the Skin's back
# as the head tilts (#838)
TILT_LEVER, TILT_BAR, TILT_BAR_X = 28.0, 26.0, (1.5, 4.5)
JAW = HEAD_AXES["jaw"][0][1:]
# the jaw x1.08 about its hinge across and fore-aft (#901, #872: its arms inside Morty's life-size mandible), its floor
# where it was, over the Torso as the head tilts; its drive keeps its size
JAW_K = 1.08


def jaw_y(y):
    """y of the jaw at y as first drawn, grown JAW_K about its hinge."""
    return JAW[0] + (y - JAW[0]) * JAW_K


# the jaw's lever down its L arm (the mandible's ramus) to its pin, the bar back from it to the mouth horn's pin, the
# horn under that, its servo hanging under the frame's plate behind the jaw, inside the mandible's U and in front of the
# neck's cheeks however the head tilts (#838)
# the frame's lugs (model/printed/gimbal.py), the jaw's arms 2 mm outside
JAW_LUG_X, JAW_X = (32.0, 36.0), (36.5, 40.5)
JAW_PIN = (55.95, -66.99)  # measured ramus witness, head-local, not an L-shaped lever hung from the old hinge
JAW_LEVER, MOUTH_HORN, JAW_BAR_X = JAW[1] - JAW_PIN[1], (10.0, -70.0), (JAW_X[1] + 0.3, JAW_X[1] + 3.3)
# #874's actual public v7 posterior borders and low-body sections, shifted 2.5 mm medially for the hidden carrier.
# Finish/carving and Skin-motion acceptance remain #874/#968; these are measured anatomy, not prototype empties.
MANDIBLE_BORDER = {
    "L": (
        (42.17778, *JAW),
        (39.66932, 62.19767, -52.96658),
        (36.54052, 55.94899, -66.98728),
        (29.96298, 52.41924, -79.70661),
        (29.74866, 40.96716, -94.45120),
        (22.17178, 24.88939, -99.41578),
        (15.00794, 10.05259, -100.09533),
    ),
    "R": (
        (-42.43407, *JAW),
        (-40.85832, 63.96941, -49.35478),
        (-36.71729, 55.38586, -66.82533),
        (-30.42063, 51.63572, -79.25589),
        (-26.50951, 36.86854, -94.26046),
        (-20.49186, 24.76519, -99.17967),
        (-10.29882, 10.31181, -99.83649),
    ),
}
MENTON = (0.0, -1.4201, -97.7819)
CHIN_Y = -33.4  # existing Skin rest contour; moving the anatomical carrier must not reshape a resting Skin
JAW_BODY = ((27.0 * JAW_K, jaw_y(0.0)), (14.0 * JAW_K, jaw_y(-20.0)))  # (x, y) its body forward round to the chin
JAW_ARM_Z = (-74.5, -70.5)  # the jaw's body forward from its arms to the chin, as the mandible's, within the head gate
# the thickest lead that crosses, a 22 AWG conductor (inferred insulation OD): the neck cable's four conductors
# VBUS and GND down from the head's USB-C to the power-path board, its switched output and GND up to the Shields,
# docs/research/2026-11-03-usb-c-power.md 7)
LEAD_OD = 1.6
BEND_X = 10  # the flexing spans' floor: 10 x the lead's diameter (docs/research/2026-11-02-literature-electrical.md 4)
# its clamps in front of the pan axis at this radius: the post's, over where the neck cable leaves it, then the yoke's disc's
PAN_SPAN = (18.0, (-112.0, -82.0))
# its arc about the tilt axis: radius, and the turn from the head's clamp (straight behind, under the flange, #708) to
TILT_SPAN = (24.0, 45.0)
LOOP_X = (-21.0, -17.0)  # the yoke's (behind, 45 deg down), outside the R tilt lug
# the parts the tilt turns with the eye gimbal: model/report.py weighs the head from them
HEAD = ("head mount:1", "jaw:1", "jaw bar:1", "mouth servo:1", "mouth horn:1")


def _four_bar(o4, lever, horn, axis, turn=1):
    """The drive with its lever from the pivot o4 to `lever` (its pin) and the horn's pivot at `horn`, the horn's arm
    along the lever (`turn` -1: against it), the bar between the two pins square to both at rest."""
    pin = np.add(horn, turn * np.subtract(lever, o4) / np.linalg.norm(np.subtract(lever, o4)) * CRANK)
    return linkage.four_bar(horn, tuple(pin), o4, lever, axis)


def pins():
    """{drive: (rocker pivot, its lever's pin, the horn's pivot, axis)} at rest."""
    y, z = AXIS
    pan_z = sum(PAN_Z) / 2
    return {
        "pan": ((0, y, pan_z), (0, y + PAN_LEVER, pan_z), (PAN_BAR, y + PAN_LEVER - CRANK, pan_z), g.Z),
        "tilt": ((0, y, z), (0, y + TILT_LEVER, z), (0, y + TILT_LEVER - CRANK, z - TILT_BAR), g.X),
        "jaw": ((0, *JAW), (0, *JAW_PIN), (0, *MOUTH_HORN), g.X),
    }


TURN = {"jaw": -1}  # the mouth horn's arm up, its jaw's lever down
LINKAGES = {d: _four_bar(o4, b, o2, axis, TURN.get(d, 1)) for d, (o4, b, o2, axis) in pins().items() if d == "jaw"}


def output(drive, servo_deg):
    """Physical output angle from a servo command; the moving tilt case reacts against a fixed horn."""
    return LINKAGES[drive](servo_deg)[0] if drive in LINKAGES else servo_deg * (-1 if drive == "tilt" else 1)


def drives():
    """{label: (horn's outer face centre, shaft direction, tab direction, arm direction at rest)}: the neck Core's three
    servos, each horn on its bar (model/stages.py mounts them, model/printed/neck.py seats them)."""
    p = pins()
    pan, tilt, jaw = (p[d][2] for d in ("pan", "tilt", "jaw"))
    return {
        "pan": ((pan[0], pan[1], PAN_Z[0]), g.Z, g.Y, g.Y),
        "tilt": ((TILT_BAR_X[1], *tilt[1:]), (-1, 0, 0), (0, -1, 0), g.Y),
        "mouth": (
            (JAW_BAR_X[0], *jaw[1:]),
            g.X,
            (0, 0, -1),
            tuple(-np.subtract(p["jaw"][1], p["jaw"][0]) / math.dist(p["jaw"][1], p["jaw"][0])),
        ),
    }


def servo_for(drive, out):
    """The servo angle (deg from its centre) that turns the drive's output to `out` deg: walked out from rest a degree at
    a time, then found within the degree."""
    if out == 0:
        return 0.0
    if drive not in LINKAGES:
        return -out if drive == "tilt" else out
    solve = LINKAGES[drive]
    step = 1.0 if (solve(1.0)[0] > 0) == (out > 0) else -1.0
    s = 0.0
    while (solve(s + step)[0] - out) * (solve(s)[0] - out) > 0:
        s += step
        assert abs(s) < 180, f"{drive} never reaches {out} deg"
    return brentq(lambda a: solve(a)[0] - out, *sorted((s, s + step)))


def transmission(drive, servo_deg):
    """The angle between the bar and its lever at the servo's angle, folded to 0..90 (0 at the toggle)."""
    if drive == "tilt":
        theta = math.radians(-servo_deg)
        dy, dz = np.subtract(TILT_SHAFT, HEAD_AXES["tilt"][0])[1:]
        bar = np.array((dy * math.cos(theta) - dz * math.sin(theta), dy * math.sin(theta) + dz * math.cos(theta)))
        lever = np.array(TILT_ARM)  # the closed parallelogram keeps the reaction arms fixed in world orientation
        return math.degrees(math.acos(np.clip(abs(bar @ lever) / (np.linalg.norm(bar) * np.linalg.norm(lever)), 0, 1)))
    solve = LINKAGES[drive]
    _, a, b = solve(servo_deg)
    u, v = linkage._PLANE[tuple(solve.axis)]
    bar, lever = np.subtract(b, a)[[u, v]], np.subtract(b, solve.o4)[[u, v]]
    return math.degrees(math.acos(abs(bar @ lever) / (np.linalg.norm(bar) * np.linalg.norm(lever))))


def _sweep(drive):
    lo, hi = (servo_for(drive, d) if d else 0.0 for d in RANGES[drive])
    return np.linspace(*sorted((lo, hi)), 41)


def _weight(head, deg):
    """kgf.cm the head's weight turns it with about the tilt axis at `deg`, right-handed about +x: its grams times its
    com's horizontal distance from the axis (g x mm / 10^4 = kgf.cm)."""
    grams, (_, cy, cz) = head
    _, y, z = HEAD_AXES["tilt"][0]
    dy, dz = cy - y, cz - z
    a = math.radians(deg)
    return -grams * (dy * math.cos(a) - dz * math.sin(a)) / 1e4


def balance(head, bare=None):
    """The balance spring on the tilt shank (#838), for a head of (grams, centre of mass in this frame, mm): (kgf.cm it
    turns the head with at rest, its rate in kgf.cm a radian), a torsion spring wound against the weight's turn, so that
    turn and its change as the head tilts cancel at rest. Its torque at `deg` is rest - rate x rad, right-handed about +x;
    model/mjcf.py sets it on the tilt pivot (stiffness and springref). With the head's `bare` one too (its Skin off,
    #830): one spring for both, wound halfway between theirs, so each misses by half the Skin's turn."""
    springs = [
        (-_weight(h, 0.0), (_weight(h, 0.5) - _weight(h, -0.5)) / math.radians(1.0)) for h in (head, bare or head)
    ]
    assert all(r > 0 for _, r in springs), (
        "the head's centre of mass is under the tilt axis: a spring's rate would push it over"
    )
    rest, rate = np.mean(springs, axis=0).tolist()
    return rest, rate


def _hold(head, spring, deg, gain):
    """kgf.cm the tilt servo holds the head with at `deg`, through the linkage's speed ratio `gain` there: the head's
    weight's turn less the balance spring's."""
    rest, rate = spring
    return abs((_weight(head, deg) + rest - rate * math.radians(deg)) * gain)


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


def report(head, bare=None):
    """The neck's numbers against #641's gates, for a head of (grams, centre of mass in this frame, mm), and its `bare`
    one (its Skin off, #830) on the same balance spring: per drive its output range, the servo angles that reach it, the
    bar's worst transmission angle on the way and the gain at rest; for tilt each head's hold at rest and at worst; where
    the head's centre of mass sits from the tilt axis; and the flexing spans' tightest bends against their floor."""
    out = {}
    for drive, solve in LINKAGES.items():
        sweep = _sweep(drive)
        out[drive] = {
            "range_deg": list(RANGES[drive]),
            "servo_deg": [round(servo_for(drive, d), 1) for d in RANGES[drive]],
            "transmission_deg": round(min(transmission(drive, s) for s in sweep), 1),
            "gain": round((solve(0.5)[0] - solve(-0.5)[0]), 3),
        }
    for drive in ("pan", "tilt"):
        out[drive] = {
            "drive": "direct",
            "range_deg": list(RANGES[drive]),
            "servo_deg": [servo_for(drive, d) for d in RANGES[drive]],
            "gain": 1.0,
        }
    out["tilt"] |= {
        "drive": "parallelogram",
        "transmission_deg": round(min(transmission("tilt", s) for s in _sweep("tilt")), 1),
    }
    sweep = _sweep("tilt")
    spring = balance(head, bare)

    def holds(h):
        at = [_hold(h, spring, output("tilt", s), 1.0) for s in sweep]
        return {"rest_kgf_cm": round(_hold(h, spring, 0.0, out["tilt"]["gain"]), 3), "hold_kgf_cm": round(max(at), 3)}

    out["tilt"] |= {
        **holds(head),
        "bare": holds(bare or head),
        "spring": {"rest_kgf_cm": round(spring[0], 3), "rate_kgf_cm_rad": round(spring[1], 3)},
    }
    grams, (_, cy, cz) = head
    out["head"] = {
        "grams": round(grams, 1),
        "above_tilt_mm": round(cz - HEAD_AXES["tilt"][0][2], 1),
        "behind_tilt_mm": round(cy - HEAD_AXES["tilt"][0][1], 1),
    }
    out["spans"] = _spans()
    return out
