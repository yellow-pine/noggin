"""The next Mech's eye gimbal (#630, GLOSSARY Eye gimbal): our own design, clean-room (#618). Its numbers (one source:
model/printed/gimbal.py draws the parts from them, model/stages.py places them), its kinematics and its report.

Frame (the next-eyes Sub-assembly's): x along the eye line (the L eye at +x), -y forward, z up, the origin midway
between the eye centres. Each eyeball core pitches inside a yoke that yaws on a vertical axis through the eye centre
(yaw on the outer ring). One servo yaws both yokes through a three-crank parallelogram: its horn and both yokes'
cranks, equal, pinned to one tie-bar. One servo pitches both cores: its horn drives the bail (a rocker on an x axis
behind the eyes) through a bar, and each bail arm pushes a rod whose ball end sits on the core's lever, up the yaw
axis, so a yaw moves it only at second order: the Hooke form, sin(pitch) cos(yaw) (docs/research/2026-11-02-literature-
mechanical.md 2). Each lid is a shell wedge about the up/down axis through its eye centre, on its own servo through a
parallelogram. Angles are degrees: yaw positive toward +x, pitch and lid positive up. Every size is ours and inferred
(no build settles one yet), each chosen against the gates in report()."""

import math

import numpy as np
from scipy.optimize import brentq
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from model import fits, linkage
from model import geometry as g

# Morty at life size (#872 step 3 round 2, his sculpt x7.123, #901): his eye a sphere this radius; its outline's radius
# about its centre every 30 deg from +x (outward on the L eye) toward up, seen from the front; his pupils this far apart
MORTY_EYE_R = 40.4
MORTY_OUTLINE = (39.5, 39.0, 39.0, 37.5, 35.5, 33.0, 31.0, 29.5, 30.0, 32.0, 35.0, 37.5)
SPACING = 72.7  # eye centres apart: on Morty's pupils
K = round(MORTY_EYE_R / 27.0, 1)  # the eye's growth, x1.5, from the 27 mm cap the gimbal was first drawn round (#630)
EYE = {"L": (SPACING / 2, 0.0, 0.0), "R": (-SPACING / 2, 0.0, 0.0)}
SERVO_DEG = 90.0  # a servo's travel either side of its centre
YAW, PITCH = 25.0, 15.0  # each eye's range, +-: the neck joins larger gaze shifts (#51)
CRANK = g.HORN_STEP["pin"]  # the horn's pin hole from its hub: every crank the horns drive or match
PIN_R = 1.6  # the busy pivots' M3 steel shank (model/printed/coupon.py) in a bore 0.1 over it
CORE_R, SEAT_R = 13.0 * K, 8.0 * K  # the core ball; the boss its cap sits on
LEVER, BALL_R = 17.0 * K, 3.0  # the lever up the yaw axis to its ball's centre
# yoke U from below; stem bottom: the U grows with the core, the stem keeps its foot on the frame's plate (#901)
YOKE = {"inner": 14.0 * K, "wall": 3.0, "half_y": 4.0, "stem_r": 4.0, "stem_z": -27.0}
YAW_CRANK_Z = (-27.0, -24.0)  # the yokes' cranks; the tie-bar under them, the yaw horn's outer face under that
TIE_Z = (-30.0, -27.0)
# the yaw horn's axis behind the eyes' centres, so its servo's case and tabs lie behind them (#684) and behind the lower
# lids' sweep (#901)
YAW_Y = 22.0
BAIL = (40.0 * K, 0.0)  # (y, z) of the bail's axis
BAIL_IN = 25.0  # the bail's input arm, along +y
BAIL_END = (
    12.0 * K
)  # the bail's rod's ends past each eye's centre, on the frame's uprights outside the pitch servo (#838)
PITCH_HORN = (BAIL[0] + BAIL_IN - CRANK, -20.0)  # (y, z): its arm along +y, the pitch bar straight up to the input arm
CAP_R, CAP_HALF = MORTY_EYE_R, 45.0  # each Character's largest eyeball cap, Morty's eye: a sphere segment this wide
PUPIL_DEG = 15.0  # the pupil's half-span on the cap (inferred; the Shells ticket draws it)
PUPIL_FIT = 0.15  # the pupil's key in its seat, per side: 0.3 mm of seat play (#650; the coupon's 0.1-0.4 per side)
LID_R = (CAP_R + 1.0, CAP_R + 3.1)  # the upper lid's shell, inner and outer radius: 1 mm off Morty's eye (#872)
LOWER_R = (
    LID_R[1] + 1.5,
    LID_R[1] + 4.0,
)  # the lower lid's, outside the upper's: tracking a pitch down, shut, they pass
LID_COVER = 3.0  # how far past the cap's rim a shut lid reaches


def _outline(deg):
    """The angle off the gaze where Morty's eye outline meets his eye's sphere, `deg` from +x toward up."""
    return math.degrees(math.asin(min(1.0, MORTY_OUTLINE[round(deg / 30) % 12] / MORTY_EYE_R)))


LID_REST = _outline(90)  # the upper lid's edge on Morty's outline (#872), at the lid servo's centre
LOWER_EDGE = -_outline(270)  # the lower lid's, at the servo's centre (LOWER_REST, which the lower lid's drive sets)
# shut, the upper lid's edge at the eye's middle (#901; slightly below it before, #698), the lower's LID_GAP under it:
# high enough that the upper lid, open, stays clear of the push-rod, low enough that the lower's sweep stays clear of
# the frame's plate and the yaw servo
LID_SHUT, LID_GAP = 0.0, 1.5
LID_SPAN = CAP_HALF + LID_COVER - LID_SHUT  # the upper wedge's width about x: shut, it covers the cap's top
LOWER_SPAN = CAP_HALF + LID_COVER + LID_SHUT - LID_GAP  # the lower wedge's: shut, it covers the cap's bottom
# the upper lid's edge over the servo's range: shut tracking a pitch down (#51, #698), open LID_OPEN past rest, as far
# as the crank's transmission floor allows (#901: Morty's lids rest wide open, clear of the cap pitched up; open
# tracking a pitch up before)
LID_OPEN = 14.5
LID_EDGES = (LID_SHUT - PITCH, LID_REST + LID_OPEN)
LID_FOLLOW = 1.0  # lid = rest + k*pitch (#51 Gestures): k 1 keeps the lid's edge where it sits over the pupil
# (y, z) of each lid servo's horn: behind the eye and under its centre, its case upright behind the yawing yoke and under
# the push-rods, so nothing of the eyes' drives hangs where the mandible's ramus is (#838; under the eye before)
LID_HORN = (37.0, -12.0)  # its case 1 mm behind the jaw's hinge (#901)


# the upper lid's crank at rest, deg from forward toward up: square to the bar (from the lid's pivot to the horn's)
# mid-range, so the bar meets it at 64 deg at either end of the lid's range (#684; the MuJoCo report's floor is 40)
def _crank(horn):
    return math.degrees(math.atan2(horn[1], -horn[0])) % 360 - 90.0 - (sum(LID_EDGES) / 2 - LID_REST)


LID_CRANK = _crank(LID_HORN)
LID_PIN = (-CRANK * math.cos(math.radians(LID_CRANK)), CRANK * math.sin(math.radians(LID_CRANK)))  # (y, z) at rest


# The lower lid (#698): the bar turns none (a parallelogram), so a link from a pin on it to the lower lid's crank is a
# four-bar whose crank pivots at LINK_PIN - LID_PIN and turns as the servo; crossed, it turns the lower lid against the
# upper. Inferred, searched (#901) for the lower lid turning as far as the upper from rest to shut, its link meeting the
# crank at 50 deg or more, every pin behind the cap's flat back however the eye turns, above the frame's plate
LINK_PIN = (28.6, -17.4)  # (y, z) of the link's pin on the bar at rest
LOWER_PIN = (4.6, -15.4)  # (y, z) of the lower lid's crank pin at rest
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
PITCH_BAR_X = (2.0, 5.0)  # the pitch bar's slab; the bail's input arm is x +-2, the pitch horn outboard of the bar
# |x| from each eye's centre (#698): outboard each lid's boss, clear of the yawing yoke (24.3), which turns on a shank
# from the frame's upright beside the caps; inboard the lid bar on the horn's face (behind the yoke, so nearer the eye:
# its servo under the eye then clears the pitch servo's collar), then the link and the lids' ears face to face, within
# SPACING / 2 so the two eyes' drives turn apart about their shared axis (#838). Every pin the cap could reach lies
# behind its flat back (gimbal.report, the sweep); the slabs moved out with the eye (#901), 3 mm each as before
LID_X = {
    **{"upper boss": (27.0, 30.0), "lower boss": (30.0, 33.0), "upright": (33.3, 36.3)},
    **{"bar": (24.75, 27.75), "link": (27.75, 30.75), "ear": (30.75, 33.75)},
}
# The gimbal frame's plate (#838): up under the tie-bar, between the realistic skull's coronoids (|x| 32..40, y -5..12)
# and its condyles, above the mandible, the yaw servo hanging under it through its hole: its body PLATE_X either side
# from PLATE_Y[0] to the bail's uprights, wider behind them (BACK_X), and a bar in front of the coronoids (CHEEK_Y) out
# to the lids' uprights
PLATE_Z = (-38.0, -35.0)
# under the eyes' centres, behind the lower lids' sweep (#901: in front of the coronoids before), to past the head
# mount's rear screws (model/neck.py)
PLATE_Y = (16.0, 87.0)
PLATE_X, BACK_Y = 33.5, 40.0  # the body's half-width, out under the jaw's lugs (model/neck.py JAW_LUG_X)
BACK_X = SPACING / 2 + BAIL_END + 4.0  # behind BACK_Y (the condyles') the back's, out to the bail's uprights
CHEEK_Y = (-10.0, -6.0)
# the bar a beam down its whole width, the face's Seats flush in its front (#852), under the lower lids' sweep (#901),
# hung from the lid uprights' feet
BEAM_Z = (-(LOWER_R[1] + 13.0), -(LOWER_R[1] + 1.0))
# the head the gimbal fits (#684, #838): width, depth, height; Morty's life-size cranium (#893: 160 x 176 x 175)
HEAD_MM = (160.0, 176.0, 175.0)


def drives():
    """{label: (horn's outer face centre, shaft direction, tab direction, arm direction at rest)}: the four servos of the
    eyes Core, each horn at its drive's crank (model/stages.py mounts them, model/printed/gimbal.py seats them), each
    case behind the eyes' centres and within their width (#684): the yaw servo under the tie-bar, the pitch servo
    beside the pitch bar, each lid servo upright behind its eye (#838), its horn between the eyes on the lid bar (#698)."""
    out = {
        "yaw": ((0.0, YAW_Y, TIE_Z[0]), g.Z, (-1, 0, 0), g.Y),  # its case across, in front of the mouth servo (#838)
        "pitch": ((PITCH_BAR_X[1], *PITCH_HORN), (-1, 0, 0), g.Y, g.Y),
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
_PITCH = linkage.four_bar(
    (0, *PITCH_HORN), (0, PITCH_HORN[0] + CRANK, PITCH_HORN[1]), (0, *BAIL), (0, BAIL[0] + BAIL_IN, BAIL[1]), g.X
)


def _pitch(yaw, bail, side, arm=LEVER):
    """The core's pitch where the push-rod from the bail arm (`arm` long, at `bail` deg about +x) reaches the lever's
    ball with the eye at `yaw`: the rod is as long as at rest."""
    c = np.array(EYE[side])
    pivot = np.array([c[0], *BAIL])
    rod = math.dist(pivot + (0, 0, arm), c + (0, 0, LEVER))
    pin = pivot + _rot(g.X, bail) @ (0, 0, arm)
    reach = lambda p: math.dist(pin, c + core(yaw, p) @ (0, 0, LEVER)) - rod  # noqa: E731
    return brentq(reach, -bail - 30, -bail + 30)


def eyes(yaw_servo, pitch_servo, scale=0.0):
    """{side: (yaw, pitch)} each eye takes at the two servos' angles (deg from their centres). `scale` lengthens the R
    yoke's crank and the R bail arm by that fraction (a print error), so the R eye strays from the L."""
    bail = _PITCH(pitch_servo)[0]
    l, r = EYE["L"], EYE["R"]
    tie = linkage.four_bar(l, (l[0], CRANK, 0), r, (r[0], CRANK * (1 + scale), 0), g.Z)
    yaws = {"L": yaw_servo, "R": tie(yaw_servo)[0]}
    arms = {"L": LEVER, "R": LEVER * (1 + scale)}
    return {s: (yaws[s], _pitch(yaws[s], bail, s, arms[s])) for s in "LR"}


def servos(yaw, pitch):
    """(yaw servo, pitch servo) degrees that point the L eye at (yaw, pitch): the command map the noggin service applies
    for the next Mech, undoing the Hooke coupling."""
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
    """{next-eyes part: 4x4 from its rest placement} for both lid servos at `lid` deg (or {side: deg}, each its own) and
    the L eye at (yaw, pitch) through the command map (#650, #656): each eye's lids, its bar, link and horn; yawed, the
    yaw horn, the tie-bar and each yoke; the pitch horn, the pitch bar, the bail, each push-rod, core and cap."""
    out, lids = {}, lid if isinstance(lid, dict) else dict.fromkeys(EYE, lid)
    for s, (x, _, _) in EYE.items():
        lid_m, horn_m = linkage.rotation(g.X, -lids[s], (x, 0, 0)), linkage.rotation(g.X, -lids[s], (x, *LID_HORN))
        low_m = linkage.rotation(g.X, -lower(lids[s]), (x, 0, 0))
        crank, pin, link, low = ((x, *p) for p in (LID_PIN, np.add(LID_HORN, LID_PIN), LINK_PIN, LOWER_PIN))
        out[f"next {s} upper lid:1"], out[f"next {s} lower lid:1"], out[f"next {s} lid horn:1"] = lid_m, low_m, horn_m
        bar = out[f"next {s} lid bar:1"] = _carry(crank, pin, (lid_m @ [*crank, 1])[:3], (horn_m @ [*pin, 1])[:3])
        out[f"next {s} lid link:1"] = _carry(link, low, (bar @ [*link, 1])[:3], (low_m @ [*low, 1])[:3])
    yaw_servo, servo = servos(yaw, pitch)
    if yaw:  # else they stay at rest, left out: the lid drives' sweep (model/printed/gimbal.py) poses what is here
        out["next yaw horn:1"] = horn = linkage.rotation(g.Z, yaw_servo, (0, YAW_Y, 0))
        out["next tie-bar:1"] = tie = np.eye(4)
        pin = (0, YAW_Y + CRANK, 0)
        tie[:3, 3] = (horn @ (*pin, 1))[:3] - pin  # a parallelogram: the bar shifts, never turns
    bail, a, b = _PITCH(servo)
    out["next pitch horn:1"] = linkage.rotation(g.X, servo, (0, *PITCH_HORN))
    out["next bail:1"] = linkage.rotation(g.X, bail, (0, *BAIL))
    out["next pitch bar:1"] = _carry((0, PITCH_HORN[0] + CRANK, PITCH_HORN[1]), (0, BAIL[0] + BAIL_IN, BAIL[1]), a, b)
    for s, (y, p) in eyes(yaw_servo, servo).items():
        x = EYE[s][0]
        yoke = linkage.rotation(g.Z, y, (x, 0, 0))
        if yaw:
            out[f"next {s} yaw yoke:1"] = yoke
        core_m = yoke @ linkage.rotation(g.X, -p, (x, 0, 0))  # as core()
        out[f"next {s} eyeball core:1"] = out[f"next {s} eyeball cap:1"] = core_m
        lever, arm = (x, 0, LEVER), (x, BAIL[0], BAIL[1] + LEVER)
        rod = (core_m @ [*lever, 1])[:3], (out["next bail:1"] @ [*arm, 1])[:3]
        out[f"next {s} push-rod:1"] = _carry(lever, arm, *rod)
    return out


def _angle(a, b):
    return math.degrees(math.acos(min(1.0, float(np.dot(a, b)))))


def _grid(n_yaw=11, n_pitch=7):
    return [(y, p) for y in np.linspace(-YAW, YAW, n_yaw) for p in np.linspace(-PITCH, PITCH, n_pitch)]


def _moving(yaw, pitch):
    """The capsules (a, b, r) inside the L lid at the eye's pose, about its centre: the lever and its ball, the
    push-rod with its sockets, the yoke's arms and stem."""
    rot = core(yaw, pitch)
    ball = rot @ (0, 0, LEVER)
    bail = _PITCH(servos(yaw, pitch)[1])[0]
    pin = np.array([0, *BAIL]) + _rot(g.X, bail) @ (0, 0, LEVER)  # the bail arm's ball, behind this eye
    x, bottom = YOKE["inner"] + YOKE["wall"] / 2, -(YOKE["inner"] + YOKE["wall"])
    arm_r = math.hypot(YOKE["wall"] / 2, YOKE["half_y"])
    yaw_rot = _rot(g.Z, yaw)
    out = [(rot @ (0, 0, CORE_R), ball, BALL_R), (ball, pin, BALL_R + 1.5)]
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
    play = (math.degrees(2 * c / CRANK), math.degrees(c * (2 / BAIL_IN + 2 / LEVER)))
    gaze_err, cross, verge = 0.0, 0.0, 0.0
    for yaw, pitch in grid:
        cmd = servos(yaw, pitch)
        y, p = eyes(*cmd)["L"]
        for sy in (-1, 1):
            for sp in (-1, 1):
                gaze_err = max(gaze_err, _angle(gaze(yaw, pitch), gaze(y + sy * play[0], p + sp * play[1])))
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
