"""The Mech's Skins (#665, GLOSSARY Skin, Seat): where each Shell sits on what carries it, and how hard its
magnets hold it there. One source: model/printed/skin.py draws the Shells and cuts the Seats from these numbers,
model/stages.py places the Shells on their carriers, model/mujoco_report.py reads each Shell's peak acceleration and
model/test_report.py holds it to hold_n().

A Seat is the same for every Skin (#51 Skeleton and shells): on the carrier, a magnet in a flush pocket and three V-grooves
round it; on the Shell, its magnet and three balls that rest in the grooves, which take the shear and hold the magnets
GAP apart, so the magnets only preload it (a Maxwell coupling). Every Seat is flush in its carrier's surface, so a bare
Skeleton shows at most its pocket's and grooves' small circle (#852): where the carrier is too thin for the pocket and
the grooves, it is thickened behind the Seat from inside (`pad` mm deep, a disc back into it); where the Shell is too
far from it, the Seat stands on a boss (`boss` mm long, out into the Shell). Each Seat is drawn in its carrier's frame,
which is its Shell's too. One polarity rule: the carrier's magnet shows N to its Shell, reversed (polarity -1) on the R
Seat of an L/R pair, so a Shell on the other side's Seat is pushed off. Every size is ours and inferred (no build settles one yet)."""

import functools
import json
import math
import os
from collections import namedtuple

import numpy as np
from scipy import interpolate

from model import base as nb
from model import geometry as g
from model import gimbal as gm
from model import neck as nk

MAGNET = (4.0, 2.0)  # one size everywhere (#51): a 4x2 mm N52 disc, flush in its pocket, glued
MAGNET_T = 1.43  # N52's least remanence, T: the pull it gives is the least the grade promises
FIT = 0.1  # the pocket's play round the magnet, per side
BALL_R, GROOVE_D = 1.0, 1.2  # each ball, and its 90 deg V-groove's depth
GAP = math.sqrt(2) * BALL_R - GROOVE_D  # between the Seat's faces (and so its magnets), the balls in their grooves
RING, GROOVE = 4.5, 1.5  # the balls' circle round the magnet; each groove's half-length along its radius
PAD_R = RING + GROOVE + 1.0  # a Seat's thickening's or boss's radius
SF = 2.0  # the magnets hold at least this many times a Shell's weight at its peak acceleration (model/test_report.py)
COVER = 2.6  # a lid cover's or a cap's thickness behind its magnet: the pocket and 0.6 mm of skin

Seat = namedtuple("Seat", "shell carrier at normal pad boss polarity")  # at: the carrier's face, normal: out of it

# The upper lid's cover (#698): the lower lid passes outside the upper one when a shut eye looks down, up to this far
# over its edge, so the cover is COVER thick (its magnet's) only in the band above it (and a degree's clearance), and
# forward of that a skin BAND thick (two 0.375 mm lines), inside the lower lid's path (#881)
_OVER = max(
    gm.LOWER_REST + gm.lower(s) - gm.LID_REST - s for s in np.linspace(*np.subtract(gm.LID_EDGES, gm.LID_REST), 91)
)
BAND = 0.75
LIP = 10.0  # deg each cover reaches past its lid's free edge, which seen from the front peeks out under an edge flush
# with it (its face and the shell's curve), up to 9.5 deg at the lid's x ends wide open on Morty's wide eyes (#901, 4.6
# before; model/test_skin.py)
UPPER_COVER = (gm.LID_REST + _OVER + 1.0, gm.LID_REST + gm.LID_SPAN)  # deg from forward toward up, as the lid at rest
UPPER_SKIN = (gm.LID_REST - LIP, UPPER_COVER[1])
LOWER_COVER = (gm.LOWER_REST - gm.LOWER_SPAN, gm.LOWER_REST + LIP)
COVER_X, LOWER_X = (gm.LID_SHELL_X[lid] for lid in ("upper", "lower"))  # their matching main shells (_lid)


def _on_lid(r, deg, side):
    """(at, normal): the L (or R, mirrored) lid's outer face at radius r, deg up from forward, mid across its shell."""
    x = sum(COVER_X) / 2 * (1 if side == "L" else -1)
    rho = math.sqrt(r * r - x * x)
    at = (x, -rho * math.cos(math.radians(deg)), rho * math.sin(math.radians(deg)))
    return tuple(round(c, 4) for c in at), tuple(round(c / r, 6) for c in at)


def _lid_seats(skin, side, polarity):
    out = []
    # each Seat mid its magnet section: the upper's top band, the whole lower lid
    for lid, r, deg in (
        ("upper", gm.LID_R[1], sum(UPPER_COVER) / 2),
        ("lower", gm.LOWER_R[1], gm.LOWER_REST - gm.LOWER_SPAN / 2),
    ):
        at, n = _on_lid(r, deg, side)
        out.append(Seat(f"{skin} {side} {lid} lid cover", f"{side} {lid} lid", at, n, 0.0, 0.0, polarity))
    return out


# Morty's head (#665, #844: his model sheet's round head), in the head's frame (model/neck.py): the face comes off
# forward, the hair up. The head is what lies inside three outlines, each the hull of (u, v, r) circles: from the front
# (x, z) a round cranium over the cheeks; from the side (y, z) the face
# flat over the eyes, the cranium round behind it, and the muzzle over the jaw and the head mount (two hulls, the corner
# between them rounded SIDE_ROUND); from above (x, y), square to the mouth servo's corners. Every size is inferred.
# The head grows with the eyes (#901: x1.5 about their midpoint, as the eye gimbal does round Morty's own eyes).
GROW = gm.K


def grown(*v):
    """The head's sizes `v`, mm as first drawn round the eyes (#665), grown GROW about the eyes' midpoint."""
    return tuple(c * GROW for c in v)


FRONT = tuple(
    grown(*c)
    for c in ((0.0, 0.0, 68.0), (-48.5, -30.0, 20.0), (48.5, -30.0, 20.0), (-48.5, -58.0, 20.0), (48.5, -58.0, 20.0))
)
SIDE = (
    tuple(grown(*c) for c in ((1.0, 25.7, 25.0), (-4.0, -12.0, 20.0), (30.0, 10.0, 58.0), (68.0, -60.0, 20.0))),
    tuple(grown(*c) for c in ((-29.0, -50.0, 20.0), (-42.0, -73.0, 7.0), (40.0, -60.0, 20.0))),
)
SIDE_ROUND = 25.0 * GROW
TOP = tuple(grown(*c) for c in ((-43.5, -24.0, 25.0), (43.5, -24.0, 25.0), (-46.5, 66.0, 22.0), (46.5, 66.0, 22.0)))
# Bart's head (#807): Morty's with a flat crown, from the front square at its top corners and from the side level over
# the cranium, so it holds all of Morty's in the same box (whatever clears his Shells clears Bart's); his spikes stand
# on the crown (model/printed/skin.py SPIKE). Every other Skin's head is Morty's
HEADS = {
    "morty": (FRONT, SIDE, TOP),
    "bart": (
        (grown(-48.5, 48.0, 20.0), grown(48.5, 48.0, 20.0), *FRONT[1:]),
        ((grown(5.0, 48.0, 20.0), grown(68.0, 48.0, 20.0), *SIDE[0]), SIDE[1]),
        TOP,
    ),
}
# outside: half-width, front (the muzzle's) to back, z
HEAD_X = max(u + r for u, _, r in FRONT)
HEAD_Y = (min(u - r for u, _, r in SIDE[1]), max(u + r for u, _, r in SIDE[0]))
# its floor where it was first drawn (#665), over the neck and the Torso however the head tilts (#901: grown, it met them)
HEAD_Z = (-80.0, max(v + r for _, v, r in FRONT))
MUZZLE_Y = HEAD_Y[0]  # the face's front under the eyes, over the jaw and the head mount
WALL = 1.6  # every Shell's wall: four 0.4 mm perimeters
# Morty's contours (#991, #992): our control points (contours.json, its research note), in his eyes' spacing from their
# midpoint, each in the view it was measured in, front (x, z) or side (y, z), and swept through the head along that
# view's axis. Cut once, on his sculpt's skin (#893's directive of 2026-11-27, cuts()): the sculpt's hairline and eye
# whites where the sculpt itself has them ("of": "sculpt": its hair's boundary, each eye dome's foot), the pupils, the
# mouth line and the collar off his model sheet. The hand-coded Shells' hair seam
# (model/printed/skin.py) still reads the sheet's "hairline" until #850 deletes them, and it with them: their hair also
# takes all behind NAPE, where the head starts to narrow (TOP), so the hair comes off upward and the face forward; it
# stands HAIR proud of the face
with open(os.path.join(os.path.dirname(__file__), "contours.json")) as _f:
    _SHEET = json.load(_f)
CONTOURS = _SHEET["contours"]
# (y, z): the sheet's face front, on the side view's midline over the eyes. His drawn eyes stand out of his face where
# ours sit behind it, so the eyes alone set no depth: a side view's contour moves along y to meet a head's own front
# there, the sculpt's SCULPT_FRONT (measured on it)
FACE_FRONT, SCULPT_FRONT = _SHEET["face front"], _SHEET["sculpt face front"]
FACE_Y = min(u - r for u, _, r in SIDE[0])  # the Shells' face's front over the eyes
FAR = 400.0  # mm out, past the whole head and body, where an open contour's region closes
NAPE = TOP[2][1]
HAIR = 1.5


def contour(name, step=2.0):
    """The contour `name` (CONTOURS) in the head's frame, mm, in its view's plane: a smooth spline through its points,
    scaled by the eyes' spacing, sampled about every `step` mm (at least 48 points)."""
    c = CONTOURS[name]
    pts = np.array(c["points"]) * gm.SPACING
    closed = c.get("closed", False)
    pts = np.vstack([pts, pts[:1]]) if closed else pts
    tck, _ = interpolate.splprep(pts.T, s=0, per=closed)
    n = max(48, int(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum() / step))
    return np.array(interpolate.splev(np.linspace(0, 1, n, endpoint=not closed), tck)).T


def outline(name, front=None, step=2.0):
    """The region contour `name` bounds, a closed polygon in its view's plane: an eye white's or a pupil's its own; the
    hair above and behind a hairline (forehead first), the shirt under the collar, the jaw under the mouth line between
    its corners, each closed FAR out. A side view's moves along y so the sheet's face front meets `front` (mm)."""
    p = contour(name, step)
    if front is not None and CONTOURS[name]["view"] == "side":
        p = p + (front - FACE_FRONT[0] * gm.SPACING, 0.0)
    (a0, b0), (a1, b1) = p[0], p[-1]  # (y, z) on a side view, (x, z) on a front one
    if name.endswith("hairline"):  # on past the forehead along its end, out of the head
        t = (p[0] - p[1]) / np.linalg.norm(p[0] - p[1])
        a0, b0 = p[0] + FAR * t
        return np.vstack([(a0, b0), p, (FAR, b1), (FAR, FAR), (a0, FAR)])
    if name == "collar":
        return np.vstack([(-FAR, b0), p, (FAR, b1), (FAR, -FAR), (-FAR, -FAR)])
    if name == "mouth":
        return np.vstack([p, (a1, -FAR), (a0, -FAR)])
    return p


def cuts():
    """Morty's cuts on his sculpt, {cut: (its view, the closed region it bounds, mm in the head's frame)}: the one source
    that colours the review's reference (model/review) and splits the printed Shells (#850). The hair is above and behind
    the hairline, the sculpt's own hair boundary; an eye white is its eye's whole dome, inside its foot, and its pupil
    the sheet's dot on it (no lid has a cut: the lids are the mechanism's covers); the jaw is under the mouth line
    between its corners, in front of the eyes; the shirt is under the collar, on the fixed body. What was measured off
    the sheet from the side (the collar) is moved along y, its face front onto the sculpt's."""
    front = SCULPT_FRONT[0] * gm.SPACING
    names = {"hairline": "sculpt hairline"} | {n: n for n in CONTOURS if "hairline" not in n}
    return {
        cut: (CONTOURS[n]["view"], outline(n, None if CONTOURS[n].get("of") == "sculpt" else front))
        for cut, n in names.items()
    }


NECK = (42.0, 4.0)  # the head's floor open round the neck and the jaw within this half-width, up to this over its foot
BACK_OPEN = (nk.AXIS[0] - 20.0, nk.AXIS[1] + 7.0)  # (y, z): the head open behind y and under z, where the neck tilts
# in under the skull's base and the head mount's flange and tilt lever reach back past the head (#838)
TORSO = nb.TORSO[1]  # the Torso's front and back walls
_PLATE = (gm.CHEEK_Y[0], sum(gm.BEAM_Z) / 2)  # the front of the gimbal frame's beam (its bar to the lids'), mid height
_BACK = (32.5, 64.0)  # (|x|, y) on the gimbal frame plate's back, behind the pitch servo, clear of its collar (#838)
SHIRT_BOSS = 4.0  # each shirt half's bosses out to its sleeve
SHIRT_FRONT = TORSO[0] - GAP - SHIRT_BOSS - WALL  # the shirt front's outside, flat across its middle
# The eyeball caps on the cores' seat faces, along the gaze: every Skin's (#665)
SEATS = [
    *[
        Seat(
            f"{s} eyeball cap",
            "eyeball core",
            (0.0, -gm.CAP_R * math.cos(math.radians(gm.CAP_HALF)), 0.0),
            (0.0, -1.0, 0.0),
            0.0,
            0.0,
            p,
        )
        for s, p in (("L", 1), ("R", -1))
    ],
]


def _seats(skin):
    """The Skin's Seats, the same for every Skin (#51, #813): its Shells on the Skeleton's, the hair on the face."""
    return [
        *_lid_seats(skin, "L", 1),
        *_lid_seats(skin, "R", -1),
        # the face forward off the front of the gimbal frame's beam, its bar to the lids' uprights (#838, #852); its top
        # held by the hair
        *[
            Seat(
                f"{skin} face",
                "gimbal frame",
                (x, _PLATE[0], _PLATE[1]),
                (0.0, -1.0, 0.0),
                0.0,
                _PLATE[0] - GAP - (MUZZLE_Y + WALL) + 1.0,
                1,
            )
            for x in (-45.0, 45.0)
        ],
        # the hair down onto the gimbal frame plate's back (a web from its back wall, model/printed/skin.py, #838) and onto
        # the face's temples under the hairline, back from the forehead (each boss up to the hair's wall, cut at its outside),
        # far enough back that the boss rises into the hair over the sheet's hairline, not the face (#992)
        *[
            Seat(f"{skin} hair", "gimbal frame", (x, _BACK[1], gm.PLATE_Z[1]), (0.0, 0.0, 1.0), 0.0, 6.0, 1)
            for x in (-_BACK[0], _BACK[0])
        ],
        *[
            Seat(f"{skin} hair", f"{skin} face", grown(x, 10.0, 42.0), (0.0, 0.0, 1.0), 6.0, HEAD_Z[1] - 42.0 * GROW, 1)
            for x in (-40.0, 40.0)
        ],
        # the mouth cover up off the top of the jaw's chin (model/neck.py CHIN_Y, JAW_ARM_Z), the chin thickened behind it
        # (inside the jaw's U), flush with its front: under the chin it would make the head taller (#708's gate)
        Seat(
            f"{skin} mouth cover",
            "jaw",
            (0.0, nk.CHIN_Y + PAD_R, nk.JAW_ARM_Z[1]),
            (0.0, 0.0, 1.0),
            nk.JAW_ARM_Z[1] - nk.JAW_ARM_Z[0],
            0.0,
            1,
        ),
        # the shirt's halves off the Torso's front and back walls, each wall thickened 1 mm inside behind its Seats, each
        # half on bosses out to its sleeve, which rounds its corners clear of the Torso's
        *[
            Seat(f"{skin} shirt front", "torso", (x, TORSO[0], -157.5), (0.0, -1.0, 0.0), 3.0, SHIRT_BOSS, 1)
            for x in (-24.0, 24.0)
        ],
        *[
            Seat(f"{skin} shirt back", "torso", (x, TORSO[1], -157.5), (0.0, 1.0, 0.0), 3.0, SHIRT_BOSS, 1)
            for x in (-24.0, 24.0)
        ],
    ]


SUNGLASSES = (
    0.0,
    -153.0,
)  # (x, z) on the shirt front: Cansin's aviators hooked on the tee's neckline (#813), 6 under it
SEATS += [
    *_seats("morty"),
    *_seats("cansin"),
    *_seats("bart"),
    # the sunglasses' bridge on the shirt front's neckline, the shirt thickened behind it
    Seat(
        "cansin sunglasses",
        "cansin shirt front",
        (SUNGLASSES[0], SHIRT_FRONT, SUNGLASSES[1]),
        (0.0, -1.0, 0.0),
        1.0,
        0.0,
        1,
    ),
]
# {Shell: (what it is glued in, its Assembly direction)}: keyed in its seat (#51: not held by magnets alone)
_OUT = (0.0, -1.0, 0.0)
GLUED = {f"morty {s} pupil": (f"{s} eyeball cap", _OUT) for s in "LR"} | {
    **{f"cansin {s} pupil plug": (f"{s} eyeball cap", _OUT) for s in "LR"},  # fills the jagged seat
    **{f"cansin {s} pupil": (f"cansin {s} pupil plug", _OUT) for s in "LR"},  # a dot in its plug
    **{f"cansin {s} brow": ("cansin face", _OUT) for s in "LR"},
    "cansin teeth": ("cansin mouth cover", _OUT),
    **{f"bart {s} pupil plug": (f"{s} eyeball cap", _OUT) for s in "LR"},  # Cansin's plug and dot (#807)
    **{f"bart {s} pupil": (f"bart {s} pupil plug", _OUT) for s in "LR"},
}
DOTTED = ("cansin", "bart")  # the Skins whose pupils are dots in plugs
SHELLS = list(dict.fromkeys([s.shell for s in SEATS] + list(GLUED)))
DIRECTIONS = {s.shell: s.normal for s in SEATS} | {s: d for s, (_, d) in GLUED.items()}  # each Shell's Assembly
# direction, in its carrier's frame
# The Shells physics draws whole (#665): uncut and colliding with nothing, their mass on their drawn mesh (#830), so the
# servos carry the Skin and the sim collides the Skeleton (and the eyeball caps, the gimbal's own gates read) alone;
# their hold is checked against the peak acceleration of where they sit (model/mujoco_report.py), their clearance on
# their own shapes (model/printed/test_skin.py). The head less these is its bare one, which the tilt servo holds too
DRAWN = [s for s in SHELLS if s.split()[0] in g.SKINS]
# The Motion regions (#969, GLOSSARY): {region: the part that carries it, None for the body, fixed through every horn}.
# One source for the Shells (model/stages.py RIDES, held to it by model/printed/test_skin.py) and the private Morty
# reference's semantic meshes (model/review), so a seam cut on either side lands on the same region.
MOTION = {
    "head": "gimbal frame",
    "jaw": "jaw",
    **{f"{s} eye": f"{s} eyeball cap" for s in "LR"},
    **{f"{s} {lid} lid": f"{s} {lid} lid" for s in "LR" for lid in ("upper", "lower")},
    **dict.fromkeys(("neck", "shoulders", "torso")),
}
# {a word of a Shell's name: its region}, an eye's or a lid's after the Shell's side
_WORDS = {"face": "head", "hair": "head", "brow": "head", "mouth": "jaw", "teeth": "jaw", "shirt": "torso"}
_WORDS |= {"sunglasses": "torso", "pupil": "eye", "eyeball": "eye", "upper": "upper lid", "lower": "lower lid"}


def region(shell):
    """The Motion region `shell` shows (MOTION); KeyError for a Shell no word of _WORDS names."""
    words = shell.split()
    own = [_WORDS[w] for w in words if w in _WORDS]
    if not own:
        raise KeyError(shell)
    side = next((w for w in words if w in ("L", "R")), None)
    return own[0] if own[0] in MOTION else f"{side} {own[0]}"


@functools.cache
def hold_n(gap=GAP, polarity=1):
    """N one magnet pair pulls its Shell on with, faces `gap` mm apart (Magpylib, meshed); negative: pushes it off."""
    import magpylib  # here: only the hold check needs it

    d, h = (c / 1000 for c in MAGNET)
    carrier = magpylib.magnet.Cylinder(polarization=(0, 0, MAGNET_T), dimension=(d, h), position=(0, 0, -h / 2))
    shell = magpylib.magnet.Cylinder(
        polarization=(0, 0, polarity * MAGNET_T), dimension=(d, h), position=(0, 0, h / 2 + gap / 1000)
    )
    force, _ = magpylib.getFT(carrier, shell, meshing=(12, 4, 4))
    return round(-float(force[2]), 3)
