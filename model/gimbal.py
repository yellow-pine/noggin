"""The Mech's eye gimbal (#630, GLOSSARY Eye gimbal): our own design, clean-room (#618). Its numbers (one source:
model/printed/gimbal.py draws the parts from them, model/stages.py places them), its kinematics and its report.

Frame (the eyes Sub-assembly's): x along the eye line (the L eye at +x), -y forward, z up, the origin midway
between the eye centres. Each eyeball core pitches inside a yoke that yaws on a vertical axis through the eye centre
(yaw on the outer ring). One servo yaws both yokes through a three-crank parallelogram: its horn and both yokes'
cranks, equal, pinned to one tie-bar, which reaches each yoke's by a finger through the belt behind its eye (#967).
One servo pitches both cores: its horn drives the bail (a rocker on an x axis up behind the eyes, over the lid servos,
#967) through a bar, and each bail arm, hanging forward of that axis, pushes a rod that leans up to its ball end on the
core's lever, up the yaw axis, so a yaw moves it only at second order: the Hooke form, sin(pitch) cos(yaw)
(docs/research/2026-11-02-literature-mechanical.md 2). Each lid is a band of a sphere about its eye's centre, under
Morty's skin, turning about the eye line on a hub between the eyes: the upper on its servo through a parallelogram,
the lower off the same horn's inner hole, the other way (#967). Angles are degrees: yaw positive toward +x, pitch
and lid positive up. Every size is ours and inferred (no build settles one yet), each chosen against the gates in report()."""

import math

import numpy as np
from scipy.optimize import brentq
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from model import fits, linkage
from model import geometry as g

# Morty at life size (his Sculpt x7.126, #901): his eyeball, a sphere fitted to each dome of his Sculpt (#967,
# model/review MORTY_EYES); his eyeballs' centres this far apart
MORTY_BALL_R = 37.1
SPACING = 73.3  # eye centres apart: his Sculpt's eyeballs', each fitted to its dome (#967, model/review MORTY_EYES)
# the eye's growth, x1.4, from the 27 mm cap the gimbal was first drawn round (#630): the core, its lever and the yoke
# are sized to his eyeball's own radius (x1.5, to the 40.4 mm cap's, before #967), so they turn inside the lids' shell
K = round(MORTY_BALL_R / 27.0, 1)
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
YOKE = {"inner": 14.0 * K, "wall": 3.0, "half_y": 4.0}  # the yoke's U from below, round the core
# The yaw drive round the lids' shell (#967, the re-layout). The hidden lids and their cap sweep a shell
# LIDS_SHELL from each eye's centre (the cap's 35.8, the lids' band 36.3 to 37.1, 0.5 clear: CAP_R, LID_R), through
# LIDS_SWEEP deg about the eye line where the yaw drive stands (from forward, up positive), and nothing else may
# cross it: only the belt behind the eye, between the two stowed lids' back edges, is a way out of the eye's sphere,
# and the lids' own hubs between the eyes. The face's wall comes no nearer an eye's centre than LIDS_SHELL[1] where
# a lid ever is (#850: the band is 0.8 mm, not 1.2, so a brow laid on the face has 1.4 mm under it). So each
# yoke has no stem: its crank lies at its bottom bar's level and it turns on a post (POST_R) on its yaw bearing, which
# lies inside the shell (out to RAIL_R[1], the lids' band less its clearance: the cap never comes behind the yaw axis
# inboard), runs back and inboard from under the yoke and leaves the shell RAIL_EXIT (deg inboard along the eye line,
# deg about it) to a pylon on the plate (model/printed/gimbal.py rail). The tie-bar has a finger from each yoke's
# crank pin, under the crank (FINGER_Z), back and up inside the shell and level out through the belt (FINGER: its
# (y, z) line, FINGER_X outboard of the pin) to a cross-bar behind the eyes (CROSS_Y, CROSS_Z), and a tail down the
# midline to the yaw horn's pin, which stays in TIE_Z with the horn and its servo. Inferred, from the rough CAD of the
# layout (#967, comment 7209502441) and the exact solids since
LIDS_SHELL = (35.8, 37.6)
LIDS_SWEEP = (-144.0, 166.0)
YAW_CRANK_Z = (-(YOKE["inner"] + YOKE["wall"]), -YOKE["inner"])  # the yokes' cranks, at their bottom bars' level
FINGER_Z = (YAW_CRANK_Z[0] - 3.0, YAW_CRANK_Z[0])  # the tie-bar's fingers' pins, under the cranks
TIE_Z = (-30.0, -27.0)  # the tie-bar's tail at the yaw horn's pin, the horn's outer face under it
POST_R = 4.5
RAIL_R = (LIDS_SHELL[0] - 2.0, LIDS_SHELL[0])
# 25 deg inboard: past the tie-bar's fingers, which stand outboard of their pins, and 3 mm outboard of the lid bars
RAIL_EXIT = (25.0, -150.0)
FINGER_X = (0.0, 8.0)
# the cross-bar: 2.8 mm behind the shut lower lids' hoops over the yaw, 4 mm in front of the lid servos' cases
CROSS_Y, CROSS_Z = (38.5, 46.5), (-16.0, -12.0)
# from its pin, at CRANK back of the eye's centre: level under the crank's head, up at 44 deg, level out through the
# belt (so the stalled yaw servo twists it about a line 10 mm over its pin, not 18)
FINGER = ((19.5, sum(FINGER_Z) / 2), (30.0, sum(CROSS_Z) / 2), (CROSS_Y[0] + 1.0, sum(CROSS_Z) / 2))
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
BAIL_END = 18.0
PITCH_HORN = (72.25, -20.0)  # its arm along +y at rest: where the bail's old axis put it (60 behind the eyes, #838)
GAZE_DEG, CAP_GAP_MM, LID_CLEAR_MM = 2.0, 1.0, 0.5  # the gates (#51, #630): model/test_report.py reads them
# Each eyeball cap (#967): his eye white, a sphere 1.3 mm under his Sculpt's eye (Cansin: 35.8), solid within CAP_HALF
# of the gaze (its flat back on the core's seat, where the old cap's was) and a shell CAP_WALL thick from there out
# to its eye opening's own outline as the front sees it (model/printed/skin.py cap): the opening is the Sculpt's, and
# the eye has no Shell. Below the eye line it ends on the rim's own way out from the eye's centre instead, CAP_LOW of
# the outline as the front sees it: pitched down, a cap that filled the outline there met the yaw bearing under it
CAP_R, CAP_HALF, CAP_WALL = LIDS_SHELL[0], 37.0, 1.6
CAP_LOW = CAP_R / MORTY_BALL_R
# how far toward the other eye a cap reaches, deg off its gaze: where the front sees its opening's inner corner on
# it (30.9 mm from the eye's middle, the R eye's), through the shell's depth, so yawed in it stays 3.5 mm from the
# eye line
CAP_IN = 59.7
PUPIL_DEG = 15.0  # the pupil's half-span on the cap (inferred)
PUPIL_FIT = 0.15  # the pupil's key in its seat, per side: 0.3 mm of seat play (#650; the coupon's 0.1-0.4 per side)
# The lids (#967, Cansin, 2026-11-28: "the shut line works, build it"): both in one band LID_R, two perimeters, its
# outer face on his eye's own surface, so no lid stands proud of his skin at an opening's rim. Open, the lower lid's
# edge lies along its opening's bottom rim, where the cap's bottom edge shows (CAP_LOW: cut to the rim's curve, seen
# from the front, so the sliver of lid Cansin accepted, 1.2 mm, fills the opening under the cap), and the upper
# lid's, the same curve, is parked wholly behind the top rim; shut, the two edges meet LID_SLIT apart on that curve
# lifted LOWER_TRAVEL, LID_SHUT deg over the eye's middle. The upper lid turns UPPER_TRAVEL from there to the servo's
# centre, the lids' rest: the opening's greatest height about the eye line over that curve, less the lower's, so its
# edge's outer corner is on the top rim; its edge is cut along the lower lid's view and lies further round on the
# band's inside, so 9 mm2 of it show past the top rim's outer part at rest. LID_WIDE more, the servo's open end, and
# 3 mm2 do (7 deg would hide all of it and reach the bail's arm): the room the eye program's lid map needs over its
# rest (eyes/eyes.py: rest inside both ends), the lower lid 3.5 deg under the cap's edge there. The same for both
# eyes (the R eye's opening is 1.2 deg lower: its upper lid parks that far behind its rim). Each lid covers LID_COVER deg past the rim it hides behind (and LID_TIPS mm past its opening's inner corner,
# seen from the front, within that far of the eye line's height), but the upper lid along the top rim's middle,
# COVER_FREE mm either side of the eye's (its back edge is the rim itself there, so wide open it stops 154 deg
# round, short of the bail's arm at 157: comment 7226349814's cure 1). The travels are read off his Sculpt's eye whites' cuts
# (model/printed/test_gimbal.py holds them to it); every other size here is inferred
LID_R = (LIDS_SHELL[0] + LID_CLEAR_MM, LIDS_SHELL[1] - LID_CLEAR_MM)
LID_SHUT, LOWER_TRAVEL, UPPER_TRAVEL, LID_WIDE = 6.5, 65.9, 76.8, 4.5
LID_SLIT = 0.6  # between the shut lids' edges: the lids' clearance, and a tenth for what a sampled sweep misreads
LID_COVER, LID_TIPS, COVER_FREE = 4.0, (2.6, 12.0), 5.2
LID_ENDS = (-62.0, 82.0)  # the lids' ends along the eye line, deg from the eye's middle (outward positive)
# the upper lid's edge at the eye's middle with the lid servo at its centre: open, the lids' rest (no lid shows but
# the sliver of lower lid along the bottom rim, and the upper lid's corner)
LID_REST = LID_SHUT + UPPER_TRAVEL
LOWER_REST = LID_SHUT - LOWER_TRAVEL  # the lower lid's: the cap's bottom edge there, 3.7 deg over the bottom rim
# the upper lid's edge over the servo's range: shut, wide open. No lid follows the eyes' pitch any more (#51
# Gestures, #698): a hidden lid has no edge on the eye to keep there
LID_EDGES = (LID_SHUT, LID_REST + LID_WIDE)
# (y, z) of each lid servo's horn: behind the eye and under its centre, its case upright behind the yawing yoke and under
# the push-rods, so nothing of the eyes' drives hangs where the mandible's ramus is (#838; under the eye before)
# #967: its case stood across the belt behind the eye, where the push-rod, the tie-bar and the yaw bearing's rail have
# to leave the eye's sphere once the lids stow under Morty's skin; now behind that belt, under the bail's axis (the
# layout's 56.5, -8.5, comment 7209502441, a tenth up: its horn's hub 2.0 mm over the pan's moving cap, 1.9 before)
LID_HORN = (56.5, -8.4)


# the upper lid's crank at rest, deg from forward toward up: square to the bar (from the lid's pivot to the horn's)
# mid-range, so the bar meets it at 49 deg at either end of the lid's range (#684; the MuJoCo report's floor is 40)
def _crank(horn):
    return math.degrees(math.atan2(horn[1], -horn[0])) % 360 - 90.0 - (sum(LID_EDGES) / 2 - LID_REST)


LID_CRANK = _crank(LID_HORN)
LID_PIN = (-CRANK * math.cos(math.radians(LID_CRANK)), CRANK * math.sin(math.radians(LID_CRANK)))  # (y, z) at rest


# The lower lid (#698, #967): its link runs from the lid horn's inner hole (LINK_CRANK from its hub, on the arm the
# bar's pin is on: model/envelopes.py HORN) forward under the eye line to the lower lid's crank, which points down:
# a crossed four-bar, so the lower lid turns against the upper, LOWER_TRAVEL for its UPPER_TRAVEL. A link from the bar
# (#698) needs a crank about 14 mm long, and between the eyes the cap's shell, which reaches its opening's inner
# corner and yaws 25 deg further in, sweeps everything past 10 mm from the eye line. Searched for the two travels,
# the link meeting the crank at 54 deg or more
LINK_CRANK = 6.75
LINK_PIN = tuple(np.add(LID_HORN, np.multiply(LID_PIN, LINK_CRANK / CRANK)))  # (y, z) of the link's pin on the horn
LOWER_CRANK = (7.61, -124.0)  # the lower lid's crank at rest: mm, deg from forward toward up
LOWER_PIN = (
    -LOWER_CRANK[0] * math.cos(math.radians(LOWER_CRANK[1])),
    LOWER_CRANK[0] * math.sin(math.radians(LOWER_CRANK[1])),
)
_LOWER = linkage.four_bar(
    (0, *LID_HORN), (0, *LINK_PIN), (0, 0, 0), (0, *LOWER_PIN), (-1, 0, 0)
)  # about -x: up positive, as the lids


def lower(lid):
    """The lower lid's turn, deg up from rest, with the lid servo at `lid` deg (its upper lid's turn)."""
    return _LOWER(lid)[0]


CONVERGE_MM = 1000.0  # the fixed toe-in converges the gazes here (#51), set in the caps' pupil seats
TOE_IN = math.degrees(math.atan(SPACING / 2 / CONVERGE_MM))
PRINT_SCALE = 0.0075  # in-plane print error (docs/research/2026-11-02-literature-cams-am.md [ZF]), on one eye's cranks
PITCH_BAR_X = (24.0, 27.0)  # #978: translate the planar drive along its X axis, clear of the C0 bearing/cable
BAIL_INPUT_X = (PITCH_BAR_X[0] - 4.0, PITCH_BAR_X[0])  # face-to-face with the bar; YZ linkage unchanged
# The lids' hubs (#967), |x| from each eye's centre, inboard: both lids turn on one M3 shank along the eye line, held
# in the frame's wall on the midline (WALL_X either side of it), each on a sleeve HUB_R in radius (the cap's shell
# passes 3.6 mm from the eye line in front of them), the lower lid's nearer the midline, face to face. In slabs along
# it: the lower lid's spoke, back and down to its band; its crank, far enough from the midline that the cap's shell is
# 12 mm from the eye line there, its pin's boss out to the link; the bar and the link, side by side on the horn's
# face (the bar above, the link under it), 3 mm for the link's buckling; and the upper lid's crank and spoke, short of
# the yawing yoke (22.95), the 1.45 mm the lid servo leaves them (0.15 mm further in than it stood: further, and the
# bail's input arm comes under 1.9 mm from its tab). No lid has a guide at its outer end (comment 7209505450); a
# sleeve is 5.4 to 5.8 mm long where that layout had lands 11 mm apart, which two lids a side do not fit: about
# 0.5 mm of tilt at the band's middle (inferred), all of the band's room, until a build shows it
LID_X = {
    **{"upper": (23.45, 24.9), "bar": (24.9, 27.9), "link": (24.9, 27.9), "crank": (29.05, 31.0)},
    **{"lower": (32.45, 34.85), "upper sleeve": (23.45, 28.85), "lower sleeve": (29.05, 34.85)},
}
HUB_R, WALL_X = 2.5, 1.3
# each lid's spoke from its hub to its band, deg from forward toward up, shut: the edge of it nearer the front, which
# lies on a line through the eye line, so all of the spoke is behind what the cap's shell sweeps between the eyes
# (lid angles -93 to 105, read on its mesh over the yaw and the pitch); SPOKE_W wide behind that edge, for the
# lid servo's stall through a jammed lid at SF 2 across the layers (a hand sum: 9 and 12 MPa)
SPOKES, SPOKE_W = {"upper": 108.0, "lower": -98.0}, {"upper": 8.0, "lower": 6.0}
# The gimbal frame's plate (#838): up under the tie-bar, above the mandible, the yaw servo hanging under it through its
# hole: its body PLATE_X either side from PLATE_Y[0] to the bail's uprights, wider behind them (BACK_X), its front out
# to a foot behind each cheek (FOOT_X: where the lids' uprights stood before the lids' hubs moved between the eyes,
# #967), and a bar under the eyes (CHEEK_Y, BEAM_Z) hung from those feet: Morty's face sits on it (model/skin.py)
PLATE_Z = (-38.0, -35.0)
# under the eyes' centres, behind the lower lids' sweep (#901: in front of the coronoids before), to past the head
# mount's rear screws (model/neck.py)
PLATE_Y = (16.0, 87.0)
PLATE_X, BACK_Y = 33.5, 40.0  # the body's half-width, out under the jaw's lugs (model/neck.py JAW_LUG_X)
BACK_X = SPACING / 2 + BAIL_END + 4.0  # behind BACK_Y (the condyles') the back's, out to the bail's uprights
CHEEK_Y = (-10.0, -6.0)
# the bar a beam down its whole width, under the lids (#901: where the old lower lids' sweep, 47.5 mm, left it)
BEAM_Z = (-63.5, -51.5)
# #967: Morty's life-size cheeks narrow under his eyes and widen behind them (the private reference, read locally by
# model/review/test_hidden.py), so the beam ends inside them, and an arm at its level runs
# back from each end to its foot, FOOT_X from the eye's centre; his cheeks curve in under the beam, so its lower outer
# corners are cut back BEAM_CUT and the arms start that far up
BEAM_X, BEAM_CUT = 53.0, 4.0
FOOT_X, FOOT_Y = (33.3, 36.3), (14.0, 20.0)
YOKE_CUT = 2.0  # the mechanical yoke's lower corners are cut back, which yawed near the cheek's Skin
# The lids' carrier (#967): a wall on the midline, WALL_X either side, from a boss HUB_R round the lids' shank back
# over the tie-bar's cross-bar (WALL_Z, 4 mm over it) to a post down to the plate behind it (WALL_POST: its y span,
# and its half-width), in the plane the lid drives' loads lie in
# #967: a window through the plate either side of the yaw servo's collar, out to WINDOW_X and back to WINDOW_Y: the
# realistic skull's maxillae rise through them from the palate to the cranium's base, behind the orbits' openings
# (model/skeleton REACH), so the palate stays on the skull; open in front since the yaw bearings left the plate's front
WINDOW_X, WINDOW_Y = 30.0, 21.0
WALL_Z, WALL_POST = (-8.0, 4.0), ((48.5, 56.0), 4.0)
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
        x = EYE[s][0] - sign * LID_X["bar"][0]  # the bar's and the link's slab's face on the horn
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
        out[f"{s} lid bar:1"] = _carry(crank, pin, (lid_m @ [*crank, 1])[:3], (horn_m @ [*pin, 1])[:3])
        out[f"{s} lid link:1"] = _carry(link, low, (horn_m @ [*link, 1])[:3], (low_m @ [*low, 1])[:3])
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


def cap_points(side, n=40):
    """Points on the `side` cap's sphere about its eye's centre, at rest: from CAP_IN toward the other eye round to its
    outer pole, the front half (more than the cap, which ends on its opening's outline)."""
    u, phi = np.meshgrid(np.radians(np.linspace(-CAP_IN, 90.0, n)), np.radians(np.linspace(-90.0, 90.0, n)))
    out = CAP_R * np.stack([np.sin(u), -np.cos(u) * np.cos(phi), np.cos(u) * np.sin(phi)], -1).reshape(-1, 3)
    return out * ((1, 1, 1) if side == "L" else (-1, 1, 1))


def _link_deg(lid):
    """The angle the lower lid's link meets its crank at, folded to 0..90, with the lid servo at `lid` deg."""
    m, q = (np.asarray(p) for p in _LOWER(lid)[1:])
    link, crank = (m - q)[1:] / np.linalg.norm(m - q), q[1:] / np.linalg.norm(q)
    return math.degrees(math.asin(min(1.0, abs(float(link[0] * crank[1] - link[1] * crank[0])))))


def report():
    """The gimbal's numbers against #630's gates (model/test_report.py), over the (yaw, pitch) grid: the worst gaze
    error through the command map with every pin's play, the yaw-pitch crosstalk (the pitch a yaw adds when the pitch
    servo ignores it) beside the Hooke form's, the vergence error a print error makes, the lids' band's room over the
    cap and their servo range, and the caps' closest approach (the lids against every other part: the sweep,
    model/printed/gimbal.py). The gaze
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
    link = min(_link_deg(lid) for lid in np.linspace(*np.subtract(edges, LID_REST), 41))
    caps = {side: cap_points(side) for side in EYE}
    gap = min(
        float(cKDTree(caps["R"] @ core(*e["R"]).T + EYE["R"]).query(caps["L"] @ core(*e["L"]).T + EYE["L"])[0].min())
        for e in (eyes(*servos(*pose)) for pose in grid)
    )
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
            "clearance_mm": round(LID_R[0] - CAP_R, 2),
            "apart_mm": round(SPACING - 2 * LID_X["lower"][1], 2),  # the two eyes' lids' hubs, between the eyes
        },
    }
