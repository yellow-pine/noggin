"""The Mech's eye gimbal (#630, GLOSSARY Eye gimbal): our own design, clean-room (#618). Its numbers (one source:
model/printed/gimbal.py draws the parts from them, model/stages.py places them), its kinematics and its report.

Frame (the eyes Sub-assembly's): x along the eye line (the L eye at +x), -y forward, z up, the origin midway
between the eye centres. Each eyeball core pitches inside a yoke that yaws on a vertical axis through the eye centre
(yaw on the outer ring). One servo yaws both yokes through a three-crank parallelogram: its horn and both yokes'
cranks, equal, pinned to one tie-bar. One servo pitches both cores: its horn drives the bail (a rocker on an x axis
up behind the eyes, over the lid servos, #967) through a bar, and each bail arm, hanging forward of that axis, pushes a
rod that leans up to its ball end on the core's lever, up the yaw axis, so a yaw moves it only at second order: the
Hooke form, sin(pitch) cos(yaw) (docs/research/2026-11-02-literature-mechanical.md 2). Each lid is a shell wedge about
the up/down axis through its eye centre, on its own servo through a parallelogram. Angles are degrees: yaw positive toward +x, pitch and lid positive up. Every size is ours and inferred
(no build settles one yet), each chosen against the gates in report()."""

import math

import numpy as np
from scipy.optimize import brentq
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from model import fits, linkage
from model import geometry as g

# Morty at life size (#872 step 3 round 2, his sculpt x7.126, #901): his eye a sphere this radius (37.1 fitted, #967:
# the cap and the lids follow with the lids' re-layout); its outline's radius about its centre every 30 deg from +x
# (outward on the L eye) toward up, seen from the front; his eyeballs' centres this far apart
MORTY_EYE_R = 40.4
MORTY_OUTLINE = (39.5, 39.0, 39.0, 37.5, 35.5, 33.0, 31.0, 29.5, 30.0, 32.0, 35.0, 37.5)
SPACING = 73.3  # eye centres apart: his Sculpt's eyeballs', each fitted to its dome (#967, model/review MORTY_EYES)
K = round(MORTY_EYE_R / 27.0, 1)  # the eye's growth, x1.5, from the 27 mm cap the gimbal was first drawn round (#630)
EYE = {"L": (SPACING / 2, 0.0, 0.0), "R": (-SPACING / 2, 0.0, 0.0)}
SERVO_DEG = 90.0  # a servo's travel either side of its centre
YAW, PITCH = 25.0, 15.0  # each eye's range, +-: the neck joins larger gaze shifts (#51)
CRANK = g.HORN_STEP["pin"]  # the horn's pin hole from its hub: every crank the horns drive or match
PIN_R = 1.6  # the busy pivots' M3 steel shank (model/printed/coupon.py) in a bore 0.1 over it
CORE_R, SEAT_R = 13.0 * K, 8.0 * K  # the core ball; the boss its cap sits on
LEVER, BALL_R = 17.0 * K, 3.0  # the lever up the yaw axis to its ball's centre
# a push-rod's reach about the line between its balls: its cups' 1.5 mm walls, and the skirt its bail cup stands on
# its bed with (#967, model/printed/gimbal.py push_rod)
ROD_R = BALL_R + 1.7
# yoke U from below; stem bottom: the U grows with the core, the stem keeps its foot on the frame's plate (#901)
YOKE = {"inner": 14.0 * K, "wall": 3.0, "half_y": 4.0, "stem_r": 4.0, "stem_z": -27.0}
YAW_CRANK_Z = (-27.0, -24.0)  # the yokes' cranks; the tie-bar under them, the yaw horn's outer face under that
TIE_Z = (-30.0, -27.0)
# the yaw horn's axis behind the eyes' centres, so its servo's case and tabs lie behind them (#684) and behind the lower
# lids' sweep (#901); near enough that the tie-bar from its pin to each yoke's leans 23.8 deg off x, so each crank meets
# it at 41.2 deg or more over the yaw's range (the MuJoCo report's floor is 40; 22 read 33.8, #1003)
YAW_Y = 16.0
# The pitch drive (#967, the re-layout round the lids' shell): the belt behind each eye, between its two stowed lids, is
# the only way out of the eye's sphere, so each push-rod leans down to the back through it, from the lever's ball to a
# ball on the bail's arm; the bail's axis stands up behind the eyes, over the lid servos' cases and under the cranium
# tray, each arm hanging forward and down from it, square to its rod at rest (over the pitch and the yaw the rod meets
# the arm at 70 deg or more and the lever at 50, the pitch bar its horn and the input arm at 51); the input arm leans
# down to the back over the lid servos, to the pitch bar from the pitch horn, which stays where it was. (y, z) each,
# inferred, from the rough CAD of the layout (#967, comment 7209502441)
BAIL = (50.9, 23.7)  # the bail's axis
# each arm's ball at rest, 24.5 mm from the axis: 1.5 mm forward of the layout's, so the rod's cup stays 2.3 mm from
# its lid servo's case at the pitch's upper end (0.9 there)
BAIL_BALL = (38.2, 2.7)
BAIL_IN, BAIL_IN_DEG = 30.0, -15.0  # the input arm: mm, deg from +y toward +z
BAIL_TIP = (
    BAIL[0] + BAIL_IN * math.cos(math.radians(BAIL_IN_DEG)),
    BAIL[1] + BAIL_IN * math.sin(math.radians(BAIL_IN_DEG)),
)  # its pin, the pitch bar's
# the bail's rod's ends past each eye's centre, on the frame's uprights outside the pitch servo (#838)
BAIL_END = 12.0 * K
PITCH_HORN = (72.25, -20.0)  # its arm along +y at rest: where the bail's old axis put it (60 behind the eyes, #838)
CAP_R, CAP_HALF = MORTY_EYE_R, 45.0  # each Character's largest eyeball cap, Morty's eye: a sphere segment this wide
PUPIL_DEG = 15.0  # the pupil's half-span on the cap (inferred)
PUPIL_FIT = 0.15  # the pupil's key in its seat, per side: 0.3 mm of seat play (#650; the coupon's 0.1-0.4 per side)
LID_R = (CAP_R + 1.0, CAP_R + 3.1)  # the upper lid's shell, inner and outer radius: 1 mm off Morty's eye (#872)
# the lower lid's, outside the upper's: tracking a pitch down, shut, they pass
LOWER_R = (LID_R[1] + 1.5, LID_R[1] + 4.0)
LID_COVER = 3.0  # how far past the cap's rim a shut lid reaches


def _outline(deg):
    """The angle off the gaze where Morty's eye outline meets his eye's sphere, `deg` from +x toward up."""
    return math.degrees(math.asin(min(1.0, MORTY_OUTLINE[round(deg / 30) % 12] / MORTY_EYE_R)))


# at the lid servo's centre, each lid's edge on Morty's outline (#872) but within the cap, whose rim is the most eye
# white there is to show (#901: his outline, 68 deg up and 52 down, lies past the cap's 45)
LID_REST = min(_outline(90), CAP_HALF)
LOWER_EDGE = -min(_outline(270), CAP_HALF)  # the lower lid's, which its drive sets (LOWER_REST)
LID_SHUT, LID_GAP = -4.0, 1.5  # shut, the upper lid's edge slightly below the eye's middle, the lower's this far under
LID_SPAN = CAP_HALF + LID_COVER - LID_SHUT  # the upper wedge's width about x: shut, it covers the cap's top
LOWER_SPAN = CAP_HALF + LID_COVER + LID_SHUT - LID_GAP  # the lower wedge's: shut, it covers the cap's bottom
# the upper lid's edge over the servo's range: shut tracking a pitch down, open tracking a pitch up (#51, #698)
LID_EDGES = (LID_SHUT - PITCH, LID_REST + PITCH)
LID_FOLLOW = 1.0  # lid = rest + k*pitch (#51 Gestures): k 1 keeps the lid's edge where it sits on the eye
# (y, z) of each lid servo's horn: behind the eye and under its centre, its case upright behind the yawing yoke and under
# the push-rods, so nothing of the eyes' drives hangs where the mandible's ramus is (#838; under the eye before)
# #967: its case stood across the belt behind the eye, where the push-rod, the tie-bar and the yaw bearing's rail have
# to leave the eye's sphere once the lids stow under Morty's skin; now behind that belt, under the bail's axis (the
# layout's 56.5, -8.5, comment 7209502441, a tenth up: its horn's hub 2.0 mm over the pan's moving cap, 1.9 before)
LID_HORN = (56.5, -8.4)


# the upper lid's crank at rest, deg from forward toward up: square to the bar (from the lid's pivot to the horn's)
# mid-range, so the bar meets it at 64 deg at either end of the lid's range (#684; the MuJoCo report's floor is 40)
def _crank(horn):
    return math.degrees(math.atan2(horn[1], -horn[0])) % 360 - 90.0 - (sum(LID_EDGES) / 2 - LID_REST)


LID_CRANK = _crank(LID_HORN)
LID_PIN = (-CRANK * math.cos(math.radians(LID_CRANK)), CRANK * math.sin(math.radians(LID_CRANK)))  # (y, z) at rest


# The lower lid (#698): the bar turns none (a parallelogram), so a link from a pin on it to the lower lid's crank is a
# four-bar whose crank pivots at LINK_PIN - LID_PIN and turns as the servo; crossed, it turns the lower lid against the
# upper about 0.8x. Inferred, searched (#901, again for the horn's axis behind the belt, #967) for the lower lid's edge
# from its rest on the cap's rim to shut, its link meeting the crank at 52 deg or more (54 before: the bar now keeps
# 8 mm off where the tie-bar's cross-bar is to pass behind the eyes, y 36.5 to 46.5, z -16.9 to -13.9), every pin behind
# the cap's flat back however the eye turns and above the frame's plate
LINK_PIN = (41.0, -3.0)  # (y, z) of the link's pin on the bar at rest
LOWER_PIN = (8.24, -11.32)
_LOWER = linkage.four_bar(
    (0, *np.subtract(LINK_PIN, LID_PIN)), (0, *LINK_PIN), (0, 0, 0), (0, *LOWER_PIN), (-1, 0, 0)
)  # about -x: up positive, as the lids


def lower(lid):
    """The lower lid's turn, deg up from rest, with the lid servo at `lid` deg (its upper lid's turn)."""
    return _LOWER(lid)[0]


LOWER_REST = LID_SHUT - LID_GAP - lower(LID_SHUT - LID_REST)  # the lower lid's edge at the servo's centre
CONVERGE_MM = 1000.0  # the fixed toe-in converges the gazes here (#51), set in the caps' pupil seats
TOE_IN = math.degrees(math.atan(SPACING / 2 / CONVERGE_MM))
PRINT_SCALE = 0.0075  # in-plane print error (docs/research/2026-11-02-literature-cams-am.md [ZF]), on one eye's cranks
GAZE_DEG, CAP_GAP_MM, LID_CLEAR_MM = 2.0, 1.0, 0.5  # the gates (#51, #630): model/test_report.py reads them
PITCH_BAR_X = (24.0, 27.0)  # #978: translate the planar drive along its X axis, clear of the C0 bearing/cable
BAIL_INPUT_X = (PITCH_BAR_X[0] - 4.0, PITCH_BAR_X[0])  # face-to-face with the bar; YZ linkage unchanged
# |x| from each eye's centre (#698): outboard each lid's boss, clear of the yawing yoke (24.3), which turns on a shank
# from the frame's upright beside the caps; inboard the lid bar on the horn's face (behind the yoke, so nearer the eye:
# its servo under the eye then clears the pitch servo's collar), then the link and the lids' ears face to face, within
# SPACING / 2 so the two eyes' drives turn apart about their shared axis (#838). Every pin the cap could reach lies
# behind its flat back (gimbal.report, the sweep); the slabs moved out with the eye (#901), 3 mm each as before
LID_X = {
    **{"upper boss": (27.0, 30.0), "lower boss": (30.0, 33.0), "upright": (33.3, 36.3)},
    **{"bar": (24.75, 27.75), "link": (27.75, 30.75), "ear": (30.75, 33.75)},
}
# each lid's main shell ends this far inside its boss's slab, so a cover on it stays 0.6 mm off the frame's upright;
# the boss itself still turns 0.3 mm off the upright
LID_SHELL_IN = 0.3
# Each main shell's ends; the upper's inboard end clears the lower lid's rising hoop.
LID_SHELL_X = {
    "upper": (-LID_X["ear"][0] + LID_CLEAR_MM, LID_X["upper boss"][1] - LID_SHELL_IN),
    "lower": (-LID_X["ear"][0], LID_X["lower boss"][1] - LID_SHELL_IN),
}
# The gimbal frame's plate (#838): up under the tie-bar, above the mandible, the yaw servo hanging under it through its
# hole: its body PLATE_X either side from PLATE_Y[0] to the bail's uprights, wider behind them (BACK_X), its front out
# to the lids' uprights, and a bar under the eyes (CHEEK_Y, BEAM_Z) hung from those uprights' feet
PLATE_Z = (-38.0, -35.0)
# under the eyes' centres, behind the lower lids' sweep (#901: in front of the coronoids before), to past the head
# mount's rear screws (model/neck.py)
PLATE_Y = (16.0, 87.0)
PLATE_X, BACK_Y = 33.5, 40.0  # the body's half-width, out under the jaw's lugs (model/neck.py JAW_LUG_X)
BACK_X = SPACING / 2 + BAIL_END + 4.0  # behind BACK_Y (the condyles') the back's, out to the bail's uprights
CHEEK_Y = (-10.0, -6.0)
# the bar a beam down its whole width, under the lower lids' sweep (#901), hung from the lid uprights' feet
BEAM_Z = (-(LOWER_R[1] + 16.0), -(LOWER_R[1] + 4.0))  # a cover's room under the lower lids
# #967: Morty's life-size cheeks narrow under his eyes and widen behind them (the private reference, read locally by
# model/review/test_hidden.py), so the beam ends inside them, and an arm at its level runs
# back from each end to its lid upright's foot, behind the lower lids' sweep; the upright leans back down to the plate's
# level, where its rail reaches forward to meet it; his cheeks curve in under the beam, so its lower outer corners are
# cut back BEAM_CUT and the arms start that far up
BEAM_X, BEAM_CUT = 53.0, 4.0
FOOT_Y = (14.0, 20.0)
# each lid upright's head is flat in front, this far from the lids' axis, inside the temple's Skin, its outer front
# edge cut back UPRIGHT_EDGE; the mechanical yoke's lower corners are cut back YOKE_CUT, which yawed near the cheek's
UPRIGHT_FLAT, UPRIGHT_EDGE, YOKE_CUT = 3.5, 2.0, 2.0
# #967: a window through the plate either side of the yaw servo's collar, out to WINDOW_X and back to WINDOW_Y: the
# realistic skull's maxillae rise through them from the palate to the cranium's base, behind the orbits' openings
# (model/skeleton REACH), so the palate stays on the skull; a bar in front of each window, WINDOW_BAR deep, joins the
# plate to its yoke's rail
WINDOW_X, WINDOW_Y, WINDOW_BAR = 30.0, 21.0, 4.0
# #967, #978: nodded, with the pan half a degree past either end (where its loaded servo sags to), the plate's back edge
# passed 0.5 mm from the tilt servo's tab and 0.9 mm from the nod plate, less than their collision pieces stray: Linux's
# sim read the frame 0.35 mm into each. A pocket in the edge at each, (x span, depth, how far its inboard end flares
# out to the edge), keeps BACK_ROOM_MM on the exact solids: the first ends at the cranium tray's leg, the second 1.6 mm
# short of the head mount's rear screw, flared round it
BACK_ROOM_MM = 1.9
BACK_POCKETS = (((37.5, 44.0), 1.7, 0.0), ((-27.5, -23.6), 1.4, 1.4))
# the head the gimbal fits (#684, #838): width, depth, height; Morty's life-size cranium (#893: 160 x 176 x 175)
HEAD_MM = (160.0, 176.0, 175.0)


def drives():
    """{label: (horn's outer face centre, shaft direction, tab direction, arm direction at rest)}: the four servos of the
    eyes Core, each horn at its drive's crank (model/stages.py mounts them, model/printed/gimbal.py seats them), each
    case behind the eyes' centres and within their width (#684): the yaw servo under the tie-bar, the pitch servo
    beside the pitch bar, each lid servo upright behind its eye (#838), its horn between the eyes on the lid bar (#698)."""
    out = {
        "yaw": ((0.0, YAW_Y, TIE_Z[0]), g.Z, (-1, 0, 0), g.Y),  # its case across, in front of the mouth servo (#838)
        "pitch": ((PITCH_BAR_X[1], *PITCH_HORN), (-1, 0, 0), (0, 0, -1), g.Y),
    }
    for s, sign in (("L", 1), ("R", -1)):
        x = EYE[s][0] - sign * LID_X["bar"][0]
        out[f"{s} lid"] = ((x, *LID_HORN), (-sign, 0, 0), (0, 0, -1), (0, *np.divide(LID_PIN, CRANK)))
    return out


def servo_origin(face, shaft):
    """The servo's tab mid-plane under its shaft (geometry.servo_frame's origin) for its horn's outer face at `face`."""
    return tuple(np.subtract(face, np.multiply(g.SERVO_STEP["horn_seat"] + g.HORN_STEP["height"], shaft)))


def servo_matrix(face, shaft, tab):
    """4x4 placing the servo Envelope (its STEP frame) as model/stages.py mounts it."""
    return np.array(g.align_rows(servo_origin(face, shaft), tab, [-c for c in shaft], g.SERVO_STEP["shaft"]))


def _rot(axis, deg):
    return linkage.rotation(axis, deg)[:3, :3]


def core(yaw, pitch):
    """The core's rotation: pitch about x (up positive), then yaw about z."""
    return _rot(g.Z, yaw) @ _rot(g.X, -pitch)


def gaze(yaw, pitch):
    return core(yaw, pitch) @ (0.0, -1.0, 0.0)


# The pitch drive: horn -> pitch bar -> the bail's input arm (a planar four-bar about x).
_PITCH = linkage.four_bar((0, *PITCH_HORN), (0, PITCH_HORN[0] + CRANK, PITCH_HORN[1]), (0, *BAIL), (0, *BAIL_TIP), g.X)
_BAIL_ARM = np.array([0.0, *np.subtract(BAIL_BALL, BAIL)])  # from the bail's axis to each arm's ball, at rest


def _pitch(yaw, bail, side, scale=0.0):
    """The core's pitch where the push-rod from the bail arm (at `bail` deg about +x, `scale` longer) reaches the
    lever's ball with the eye at `yaw`: the rod is as long as at rest."""
    c = np.array(EYE[side])
    pivot, arm = np.array([c[0], *BAIL]), _BAIL_ARM * (1 + scale)
    rod = math.dist(pivot + arm, c + (0, 0, LEVER))
    pin = pivot + _rot(g.X, bail) @ arm
    reach = lambda p: math.dist(pin, c + core(yaw, p) @ (0, 0, LEVER)) - rod  # noqa: E731
    return brentq(reach, -45, 45)  # the rod runs back from the ball: its reach grows with the pitch all the way


def eyes(yaw_servo, pitch_servo, scale=0.0):
    """{side: (yaw, pitch)} each eye takes at the two servos' angles (deg from their centres). `scale` lengthens the R
    yoke's crank and the R bail arm by that fraction (a print error), so the R eye strays from the L."""
    bail = _PITCH(pitch_servo)[0]
    l, r = EYE["L"], EYE["R"]
    tie = linkage.four_bar(l, (l[0], CRANK, 0), r, (r[0], CRANK * (1 + scale), 0), g.Z)
    yaws = {"L": yaw_servo, "R": tie(yaw_servo)[0]}
    return {s: (yaws[s], _pitch(yaws[s], bail, s, scale * (s == "R"))) for s in "LR"}


def servos(yaw, pitch):
    """(yaw servo, pitch servo) degrees that point the L eye at (yaw, pitch): the command map the noggin service applies
    for the Mech, undoing the Hooke coupling."""
    s = brentq(lambda s: eyes(yaw, s)["L"][1] - pitch, -60, 60)
    return yaw, s


def _carry(a0, b0, a, b):
    """4x4 taking a part pinned at a0 and b0 to its pins at a and b: the least turn about a0, then a shift (in a plane
    across x, a turn about x)."""
    m = np.eye(4)  # scipy's single-pair alignment is the least turn; trimesh's align_vectors is not (#670)
    m[:3, :3] = Rotation.align_vectors([np.subtract(b, a)], [np.subtract(b0, a0)])[0].as_matrix()
    m[:3, 3] = np.subtract(a, m[:3, :3] @ a0)
    return m


def moved(lid, pitch, yaw=0.0):
    """{eyes part: 4x4 from its rest placement} for both lid servos at `lid` deg (or {side: deg}, each its own) and
    the L eye at (yaw, pitch) through the command map (#650, #656): each eye's lids, its bar, link and horn; yawed, the
    yaw horn, the tie-bar and each yoke; the pitch horn, the pitch bar, the bail, each push-rod, core and cap."""
    out, lids = {}, lid if isinstance(lid, dict) else dict.fromkeys(EYE, lid)
    for s, (x, _, _) in EYE.items():
        lid_m, horn_m = linkage.rotation(g.X, -lids[s], (x, 0, 0)), linkage.rotation(g.X, -lids[s], (x, *LID_HORN))
        low_m = linkage.rotation(g.X, -lower(lids[s]), (x, 0, 0))
        crank, pin, link, low = ((x, *p) for p in (LID_PIN, np.add(LID_HORN, LID_PIN), LINK_PIN, LOWER_PIN))
        out[f"{s} upper lid:1"], out[f"{s} lower lid:1"], out[f"{s} lid horn:1"] = lid_m, low_m, horn_m
        bar = out[f"{s} lid bar:1"] = _carry(crank, pin, (lid_m @ [*crank, 1])[:3], (horn_m @ [*pin, 1])[:3])
        out[f"{s} lid link:1"] = _carry(link, low, (bar @ [*link, 1])[:3], (low_m @ [*low, 1])[:3])
    yaw_servo, servo = servos(yaw, pitch)
    if yaw:  # else they stay at rest, left out: the lid drives' sweep (model/printed/gimbal.py) poses what is here
        out["yaw horn:1"] = horn = linkage.rotation(g.Z, yaw_servo, (0, YAW_Y, 0))
        out["tie-bar:1"] = tie = np.eye(4)
        pin = (0, YAW_Y + CRANK, 0)
        tie[:3, 3] = (horn @ (*pin, 1))[:3] - pin  # a parallelogram: the bar shifts, never turns
    bail, a, b = _PITCH(servo)
    out["pitch horn:1"] = linkage.rotation(g.X, servo, (0, *PITCH_HORN))
    out["bail:1"] = linkage.rotation(g.X, bail, (0, *BAIL))
    out["pitch bar:1"] = _carry((0, PITCH_HORN[0] + CRANK, PITCH_HORN[1]), (0, *BAIL_TIP), a, b)
    for s, (y, p) in eyes(yaw_servo, servo).items():
        x = EYE[s][0]
        yoke = linkage.rotation(g.Z, y, (x, 0, 0))
        if yaw:
            out[f"{s} yaw yoke:1"] = yoke
        core_m = yoke @ linkage.rotation(g.X, -p, (x, 0, 0))  # as core()
        out[f"{s} eyeball core:1"] = out[f"{s} eyeball cap:1"] = core_m
        lever, arm = (x, 0, LEVER), (x, *BAIL_BALL)
        rod = (core_m @ [*lever, 1])[:3], (out["bail:1"] @ [*arm, 1])[:3]
        out[f"{s} push-rod:1"] = _carry(lever, arm, *rod)
    return out


def _angle(a, b):
    return math.degrees(math.acos(min(1.0, float(np.dot(a, b)))))


def _sin(u, v):
    """The sine of the angle two links meet at: the share of a pin's play along one that turns the other."""
    return float(np.linalg.norm(np.cross(u, v)) / np.linalg.norm(u) / np.linalg.norm(v))


def _pitch_play(yaw, pitch, c):
    """Degrees the L eye's pitch can stray at (yaw, pitch) with each of the pitch drive's pins `c` mm loose: the pitch
    bar's two stray the bail's input arm, which the bail's arm and the push-rod carry to the eye as they gear it there;
    the push-rod's two balls stray the lever. Each through the angle its link meets its arm at (#967: the leaned rod
    is square to neither)."""
    servo = servos(yaw, pitch)[1]
    bail, a, b = _PITCH(servo)
    x = EYE["L"][0]
    ball = np.array([x, 0, 0]) + core(yaw, pitch) @ (0, 0, LEVER)
    pin = np.array([x, *BAIL]) + _rot(g.X, bail) @ _BAIL_ARM
    gear = abs(_pitch(yaw, bail + 0.5, "L") - _pitch(yaw, bail - 0.5, "L"))  # the eye's degrees per degree of bail
    bar = 2 * c / BAIL_IN / _sin(np.subtract(b, a), np.subtract(b, (0, *BAIL)))
    rod = 2 * c / LEVER / _sin(pin - ball, ball - (x, 0, 0))
    return math.degrees(gear * bar + rod)


def _grid(n_yaw=11, n_pitch=7):
    return [(y, p) for y in np.linspace(-YAW, YAW, n_yaw) for p in np.linspace(-PITCH, PITCH, n_pitch)]


def _moving(yaw, pitch):
    """The capsules (a, b, r) inside the L lid at the eye's pose, about its centre: the lever and its ball, the
    push-rod with its sockets, the yoke's arms and stem."""
    rot = core(yaw, pitch)
    ball = rot @ (0, 0, LEVER)
    bail = _PITCH(servos(yaw, pitch)[1])[0]
    pin = np.array([0, *BAIL]) + _rot(g.X, bail) @ _BAIL_ARM  # the bail arm's ball, behind this eye
    x, bottom = YOKE["inner"] + YOKE["wall"] / 2, -(YOKE["inner"] + YOKE["wall"])
    arm_r = math.hypot(YOKE["wall"] / 2, YOKE["half_y"])
    yaw_rot = _rot(g.Z, yaw)
    out = [(rot @ (0, 0, CORE_R), ball, BALL_R), (ball, pin, ROD_R)]
    out += [(yaw_rot @ (s * x, 0, YOKE["half_y"]), yaw_rot @ (s * x, 0, bottom), arm_r) for s in (-1, 1)]
    return out + [((0, 0, bottom), (0, 0, YOKE["stem_z"]), YOKE["stem_r"])]


def lid_points(edge, n=48, radii=LID_R, span=LID_SPAN):
    """Points on an L lid's two faces (about its eye centre), its wedge about x from `edge` deg up `span`: the upper
    lid's from its edge, the lower lid's (LOWER_R, LOWER_SPAN) from its edge less its span."""
    u, phi = np.meshgrid(np.linspace(0.02, math.pi - 0.02, n), np.radians(np.linspace(edge, edge + span, n)))
    unit = np.stack([np.cos(u), -np.sin(u) * np.cos(phi), np.sin(u) * np.sin(phi)], -1).reshape(-1, 3)
    return np.concatenate([r * unit for r in radii])


def _to_segment(p, a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    t = np.clip((p - a) @ (b - a) / max(float((b - a) @ (b - a)), 1e-12), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * (b - a)), axis=1)


def cap_points(n=40):
    """Points on the L cap's dome and rim (about its eye centre, at rest): the sphere within CAP_HALF of the gaze."""
    u, phi = np.meshgrid(np.radians(np.linspace(0, CAP_HALF, n)), np.linspace(0, 2 * math.pi, n))
    return CAP_R * np.stack([np.sin(u) * np.cos(phi), -np.cos(u), np.sin(u) * np.sin(phi)], -1).reshape(-1, 3)


def _link_deg(lid):
    """The angle the lower lid's link meets its crank at, folded to 0..90, with the lid servo at `lid` deg."""
    m, q = (np.asarray(p) for p in _LOWER(lid)[1:])
    link, crank = (m - q)[1:] / np.linalg.norm(m - q), q[1:] / np.linalg.norm(q)
    return math.degrees(math.asin(min(1.0, abs(float(link[0] * crank[1] - link[1] * crank[0])))))


def report():
    """The gimbal's numbers against #630's gates (model/test_report.py), over the (yaw, pitch) grid: the worst gaze
    error through the command map with every pin's play, the yaw-pitch crosstalk (the pitch a yaw adds when the pitch
    servo ignores it) beside the Hooke form's, the vergence error a print error makes, the lids' clearance to the
    parts moving inside them over the pitch x lid grid and their servo range, and the caps' closest approach. The gaze
    error adds the pupil's seating (#650): the pupil strays up to PUPIL_FIT from its seat's centre, which on the cap
    turns the gaze the way the play may, so the two add."""
    grid = _grid()
    c = fits.CLEARANCE[0]  # every pin at the tightest agreed fit, its play counted at the arm it turns
    gaze_err, cross, verge, play = 0.0, 0.0, 0.0, (math.degrees(2 * c / CRANK), 0.0)
    for yaw, pitch in grid:
        cmd = servos(yaw, pitch)
        y, p = eyes(*cmd)["L"]
        here = _pitch_play(yaw, pitch, c)
        play = (play[0], max(play[1], here))  # the report's: the pitch's worst
        for sy in (-1, 1):
            for sp in (-1, 1):
                gaze_err = max(gaze_err, _angle(gaze(yaw, pitch), gaze(y + sy * play[0], p + sp * here)))
        cross = max(cross, abs(eyes(yaw, servos(0, pitch)[1])["L"][1] - pitch))
        e = eyes(*cmd, scale=PRINT_SCALE)
        verge = max(verge, _angle(gaze(*e["L"]), gaze(*e["R"])))
    pupil = math.degrees(math.atan(PUPIL_FIT / CAP_R))  # shortcut: the largest cap's; a smaller cap's seat strays more
    hooke = max(
        abs(math.degrees(math.asin(math.sin(math.radians(p)) / math.cos(math.radians(y)))) - p) for y, p in grid
    )
    edges = LID_EDGES
    shells = [
        p
        for edge in np.linspace(*edges, 9)
        for p in (
            lid_points(edge),
            lid_points(LOWER_REST + lower(edge - LID_REST) - LOWER_SPAN, 48, LOWER_R, LOWER_SPAN),
        )
    ]
    clear = min(
        min(float(_to_segment(shell, a, b).min()) - r for a, b, r in _moving(yaw, pitch))
        for yaw in (-YAW, 0, YAW)
        for pitch in np.linspace(-PITCH, PITCH, 7)
        for shell in shells
    )
    link = min(_link_deg(lid) for lid in np.linspace(*np.subtract(edges, LID_REST), 41))
    cap, offset = cap_points(), np.subtract(EYE["L"], EYE["R"])
    gap = min(float(cKDTree(cap @ core(*pose).T + offset).query(cap @ core(*pose).T)[0].min()) for pose in grid)
    return {
        "gaze_deg": round(gaze_err + pupil, 2),
        "play_deg": round(math.hypot(*play), 2),
        "pupil_deg": round(pupil, 2),
        "crosstalk_deg": round(cross, 2),
        "hooke_deg": round(hooke, 2),
        "vergence_deg": round(verge, 3),
        "toe_in_deg": round(TOE_IN, 2),
        "cap_gap_mm": round(gap, 2),
        "lid": {
            "edge_deg": list(edges),
            "servo_deg": [e - LID_REST for e in edges],
            "shut_deg": [LID_SHUT, round(LOWER_REST + lower(LID_SHUT - LID_REST), 2)],  # upper, lower
            "link_deg": round(link, 1),
            "clearance_mm": round(min(clear, LID_R[0] - CAP_R), 2),
            "apart_mm": SPACING - 2 * LID_X["ear"][1],  # the two eyes' lid drives, between the eyes
        },
    }
