"""The next Mech's Skins (#665, GLOSSARY Skin, Seat): where each Shell sits on what carries it, and how hard its
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
import math
from collections import namedtuple

import numpy as np

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
LIP = 5.0  # deg each cover reaches past its lid's free edge, which seen from the front peeks out under an edge flush
# with it (its face and the shell's curve), up to 4.6 deg at the lid's x ends wide open (model/test_skin.py)
UPPER_COVER = (gm.LID_REST + _OVER + 1.0, gm.LID_REST + gm.LID_SPAN)  # deg from forward toward up, as the lid at rest
UPPER_SKIN = (gm.LID_REST - LIP, UPPER_COVER[1])
LOWER_COVER = (gm.LOWER_REST - gm.LOWER_SPAN, gm.LOWER_REST + LIP)
COVER_X = (-gm.LID_X["ear"][0], gm.LID_X["upper boss"][1])  # the L upper lid's main shell (printed/gimbal.py _lid)
LOWER_X = (COVER_X[0], gm.LID_X["lower boss"][1])  # the lower lid's, out over its boss's slab


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
        out.append(Seat(f"next {skin} {side} {lid} lid cover", f"next {side} {lid} lid", at, n, 0.0, 0.0, polarity))
    return out


# Morty's head (#665, #844: his model sheet's round head), in the head's frame (model/neck.py): the face comes off
# forward, the hair up. The head is what lies inside three outlines, each the hull of (u, v, r) circles: from the front
# (x, z) a round cranium over the cheeks; from the side (y, z) the face
# flat over the eyes, the cranium round behind it, and the muzzle over the jaw and the head mount (two hulls, the corner
# between them rounded SIDE_ROUND); from above (x, y), square to the mouth servo's corners. Every size is inferred.
FRONT = ((0.0, 0.0, 68.0), (-48.5, -30.0, 20.0), (48.5, -30.0, 20.0), (-48.5, -58.0, 20.0), (48.5, -58.0, 20.0))
SIDE = (
    ((1.0, 25.7, 25.0), (-4.0, -12.0, 20.0), (30.0, 10.0, 58.0), (68.0, -60.0, 20.0)),
    ((-29.0, -50.0, 20.0), (-42.0, -73.0, 7.0), (40.0, -60.0, 20.0)),
)
SIDE_ROUND = 25.0
TOP = ((-43.5, -24.0, 25.0), (43.5, -24.0, 25.0), (-46.5, 66.0, 22.0), (46.5, 66.0, 22.0))
# outside: half-width, front (the muzzle's) to back, z
HEAD_X = max(u + r for u, _, r in FRONT)
HEAD_Y = (min(u - r for u, _, r in SIDE[1]), max(u + r for u, _, r in SIDE[0]))
HEAD_Z = (min(v - r for _, v, r in FRONT + SIDE[1]), max(v + r for _, v, r in FRONT))
MUZZLE_Y = HEAD_Y[0]  # the face's front under the eyes, over the jaw and the head mount
WALL = 1.6  # every Shell's wall: four 0.4 mm perimeters
# The hairline (his model sheet's): the hair is the head inside a circle along x, (y, z, r), from over the forehead down
# behind the ears, and all behind NAPE, so the hair comes off upward and the face forward; it stands HAIR proud of the face
HAIRLINE = (99.4, 67.4, 111.5)
NAPE = 78.0
HAIR = 1.5
NECK = (42.0, 4.0)  # the head's floor open round the neck and the jaw within this half-width, up to this over its foot
BACK_OPEN = (nk.AXIS[0] - 20.0, nk.AXIS[1] + 7.0)  # (y, z): the head open behind y and under z, where the neck tilts
# in under the skull's base and the head mount's flange and tilt lever reach back past the head (#838)
TORSO = nb.TORSO[1]  # the Torso's front and back walls
_PLATE = (gm.PLATE_Y[0], sum(gm.BEAM_Z) / 2)  # the front of the gimbal frame's beam (its bar to the lids'), mid height
_BACK = (32.5, 64.0)  # (|x|, y) on the gimbal frame plate's back, behind the pitch servo, clear of its collar (#838)
SHIRT_BOSS = 4.0  # each shirt half's bosses out to its sleeve
SHIRT_FRONT = TORSO[0] - GAP - SHIRT_BOSS - WALL  # the shirt front's outside, flat across its middle
# The eyeball caps on the cores' seat faces, along the gaze: every Skin's (#665)
SEATS = [
    *[
        Seat(
            f"next {s} eyeball cap",
            "next eyeball core",
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
                f"next {skin} face",
                "next gimbal frame",
                (x, _PLATE[0], _PLATE[1]),
                (0.0, -1.0, 0.0),
                0.0,
                _PLATE[0] - GAP - (MUZZLE_Y + WALL) + 1.0,
                1,
            )
            for x in (-45.0, 45.0)
        ],
        # the hair down onto the gimbal frame plate's back (a web from its back wall, model/printed/skin.py, #838) and onto
        # the face's temples under the hairline, back from the forehead (each boss up to the hair's wall, cut at its outside)
        *[
            Seat(f"next {skin} hair", "next gimbal frame", (x, _BACK[1], gm.PLATE_Z[1]), (0.0, 0.0, 1.0), 0.0, 6.0, 1)
            for x in (-_BACK[0], _BACK[0])
        ],
        *[
            Seat(f"next {skin} hair", f"next {skin} face", (x, -2.0, 47.0), (0.0, 0.0, 1.0), 6.0, HEAD_Z[1] - 47.0, 1)
            for x in (-40.0, 40.0)
        ],
        # the mouth cover up off the top of the jaw's chin (model/neck.py CHIN_Y, JAW_ARM_Z), the chin thickened behind it
        # (inside the jaw's U), flush with its front: under the chin it would make the head taller (#708's gate)
        Seat(
            f"next {skin} mouth cover",
            "next jaw",
            (0.0, nk.CHIN_Y + PAD_R, nk.JAW_ARM_Z[1]),
            (0.0, 0.0, 1.0),
            nk.JAW_ARM_Z[1] - nk.JAW_ARM_Z[0],
            0.0,
            1,
        ),
        # the shirt's halves off the Torso's front and back walls, each wall thickened 1 mm inside behind its Seats, each
        # half on bosses out to its sleeve, which rounds its corners clear of the Torso's
        *[
            Seat(f"next {skin} shirt front", "next torso", (x, TORSO[0], -137.5), (0.0, -1.0, 0.0), 3.0, SHIRT_BOSS, 1)
            for x in (-24.0, 24.0)
        ],
        *[
            Seat(f"next {skin} shirt back", "next torso", (x, TORSO[1], -137.5), (0.0, 1.0, 0.0), 3.0, SHIRT_BOSS, 1)
            for x in (-24.0, 24.0)
        ],
    ]


SUNGLASSES = (0.0, -131.0)  # (x, z) on the shirt front: Cansin's aviators hooked on the tee's neckline (#813)
SEATS += [
    *_seats("morty"),
    *_seats("cansin"),
    # the sunglasses' bridge on the shirt front's neckline, the shirt thickened behind it
    Seat(
        "next cansin sunglasses",
        "next cansin shirt front",
        (SUNGLASSES[0], SHIRT_FRONT, SUNGLASSES[1]),
        (0.0, -1.0, 0.0),
        1.0,
        0.0,
        1,
    ),
]
# {Shell: (what it is glued in, its Assembly direction)}: keyed in its seat (#51: not held by magnets alone)
_OUT = (0.0, -1.0, 0.0)
GLUED = {f"next morty {s} pupil": (f"next {s} eyeball cap", _OUT) for s in "LR"} | {
    **{f"next cansin {s} pupil plug": (f"next {s} eyeball cap", _OUT) for s in "LR"},  # fills the jagged seat
    **{f"next cansin {s} pupil": (f"next cansin {s} pupil plug", _OUT) for s in "LR"},  # a dot in its plug
    **{f"next cansin {s} brow": ("next cansin face", _OUT) for s in "LR"},
    "next cansin teeth": ("next cansin mouth cover", _OUT),
}
SHELLS = list(dict.fromkeys([s.shell for s in SEATS] + list(GLUED)))
DIRECTIONS = {s.shell: s.normal for s in SEATS} | {s: d for s, (_, d) in GLUED.items()}  # each Shell's Assembly
# direction, in its carrier's frame
# The Shells physics draws whole (#665): uncut and colliding with nothing, their mass on their drawn mesh (#830), so the
# servos carry the Skin and the sim collides the Skeleton (and the eyeball caps, the gimbal's own gates read) alone;
# their hold is checked against the peak acceleration of where they sit (model/mujoco_report.py), their clearance on
# their own shapes (model/printed/test_skin.py). The head less these is its bare one, which the balance spring holds too
DRAWN = [s for s in SHELLS if s.split()[1] in g.SKINS]


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
