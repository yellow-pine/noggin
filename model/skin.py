"""The next Mech's Skins (#665, GLOSSARY Skin, Seat): where each Shell sits on what carries it, and how hard its
magnets hold it there. One source: model/printed/skin.py draws the Shells and cuts the Seats from these numbers,
model/stages.py places the Shells on their carriers, model/mujoco_report.py reads each Shell's peak acceleration and
model/test_report.py holds it to hold_n().

A Seat is the same for every Skin (#51 Skeleton and shells): on the carrier, a magnet in a flush pocket and three V-grooves
round it; on the Shell, its magnet and three balls that rest in the grooves, which take the shear and hold the magnets
GAP apart, so the magnets only preload it (a Maxwell coupling). Where the carrier is too thin for the pocket and the
grooves, the Seat stands on a pad (`pad` mm long, back into the carrier); where the Shell is too far from it, on a boss
(`boss` mm long, out into the Shell). Each Seat is drawn in its carrier's frame, which is its Shell's too. One polarity
rule: the carrier's magnet shows N to its Shell, reversed (polarity -1) on the R Seat of an L/R pair, so a Shell on the
other side's Seat is pushed off. Every size is ours and inferred (no build settles one yet)."""

import functools
import math
from collections import namedtuple

import numpy as np

from model import gimbal as gm
from model import neck as nk

MAGNET = (4.0, 2.0)  # one size everywhere (#51): a 4x2 mm N52 disc, flush in its pocket, glued
MAGNET_T = 1.43  # N52's least remanence, T: the pull it gives is the least the grade promises
FIT = 0.1  # the pocket's play round the magnet, per side
BALL_R, GROOVE_D = 1.0, 1.2  # each ball, and its 90 deg V-groove's depth
GAP = math.sqrt(2) * BALL_R - GROOVE_D  # between the Seat's faces (and so its magnets), the balls in their grooves
RING, GROOVE = 4.5, 1.5  # the balls' circle round the magnet; each groove's half-length along its radius
PAD_R = RING + GROOVE + 1.0  # a pad's or a boss's radius
SF = 2.0  # the magnets hold at least this many times a Shell's weight at its peak acceleration (model/test_report.py)
COVER = 2.6  # a lid cover's or a cap's thickness behind its magnet: the pocket and 0.6 mm of skin

Seat = namedtuple("Seat", "shell carrier at normal pad boss polarity")  # at: the carrier's face, normal: out of it

# The upper lid's cover (#698): the lower lid passes outside the upper one when a shut eye looks down, up to this far
# over its edge, so the cover only takes the band above it (and a degree's clearance)
_OVER = max(
    gm.LOWER_REST + gm.lower(s) - gm.LID_REST - s for s in np.linspace(*np.subtract(gm.LID_EDGES, gm.LID_REST), 91)
)
UPPER_COVER = (gm.LID_REST + _OVER + 1.0, gm.LID_REST + gm.LID_SPAN)  # deg from forward toward up, as the lid at rest
LOWER_COVER = (gm.LOWER_REST - gm.LOWER_SPAN, gm.LOWER_REST)
COVER_X = (-gm.LID_X["ear"][0], gm.LID_X["upper boss"][1])  # the L lids' main shell (printed/gimbal.py _lid)


def _on_lid(r, deg, side):
    """(at, normal): the L (or R, mirrored) lid's outer face at radius r, deg up from forward, mid across its shell."""
    x = sum(COVER_X) / 2 * (1 if side == "L" else -1)
    rho = math.sqrt(r * r - x * x)
    at = (x, -rho * math.cos(math.radians(deg)), rho * math.sin(math.radians(deg)))
    return tuple(round(c, 4) for c in at), tuple(round(c / r, 6) for c in at)


def _lid_seats(side, polarity):
    out = []
    for lid, r, span in (("upper", gm.LID_R[1], UPPER_COVER), ("lower", gm.LOWER_R[1], LOWER_COVER)):
        at, n = _on_lid(r, sum(span) / 2, side)
        out.append(Seat(f"next morty {side} {lid} lid cover", f"next {side} {lid} lid", at, n, 0.0, 0.0, polarity))
    return out


# Morty's head (#665), in the head's frame (model/neck.py): the face comes off forward, the hair up
HEAD_X, HEAD_Y, HEAD_Z = 64.0, (-24.0, 81.0), (-80.0, 81.0)  # outside: half-width, front (over the eyes) to back, z
ROUND = (16.0, 10.0)  # the head's edges rounded, over the eyes and the muzzle: clear of the frame plate's back corners
MUZZLE_Y, MUZZLE_Z = -49.0, -36.0  # the face's front under the eyes, over the jaw and the head mount, up to here
WALL = 1.6  # every Shell's wall: four 0.4 mm perimeters
HAIRLINE = (50.0, 20.0)  # (z, y): the hair over z at the front, back to y, then down to the back's foot
TORSO = (-35.0, 58.5)  # the Torso's front and back walls (model/base.py TORSO)
_PLATE = (gm.PLATE_Y[0], sum(gm.PLATE_Z) / 2)  # the gimbal frame plate's front edge, its middle height
_BACK = (53.0, 62.0)  # (|x|, y) on the plate's top at its back corners: outboard of the rack and the lid servos
SEATS = [
    # the eyeball caps on the cores' seat faces, along the gaze
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
    *_lid_seats("L", 1),
    *_lid_seats("R", -1),
    # the face forward off the gimbal frame plate's front corners, under the mouth servo; its top held by the hair
    *[
        Seat(
            "next morty face",
            "next gimbal frame",
            (x, _PLATE[0] - 4.0, _PLATE[1]),
            (0.0, -1.0, 0.0),
            5.0,
            _PLATE[0] - 4.0 - GAP - (MUZZLE_Y + WALL) + 1.0,
            1,
        )
        for x in (-53.0, 53.0)
    ],
    # the hair down onto the plate's back corners (a web from its back wall, model/printed/skin.py) and onto the face's
    # top corners under the hairline
    *[
        Seat("next morty hair", "next gimbal frame", (x, _BACK[1], gm.PLATE_Z[1] + 4.0), (0.0, 0.0, 1.0), 5.0, 6.0, 1)
        for x in (-_BACK[0], _BACK[0])
    ],
    *[
        Seat(
            "next morty hair",
            "next morty face",
            (x, -15.0, 44.0),
            (0.0, 0.0, 1.0),
            6.0,
            HEAD_Z[1] - WALL - 44.0 - GAP + 1.0,
            1,
        )
        for x in (-45.0, 45.0)
    ],
    # the mouth cover down off the jaw's chin (model/neck.py CHIN_Y, JAW_ARM_Z)
    Seat(
        "next morty mouth cover",
        "next jaw",
        (0.0, nk.CHIN_Y + 2.0, nk.JAW_ARM_Z[0] - 3.0),
        (0.0, 0.0, -1.0),
        4.0,
        0.0,
        1,
    ),
    # the shirt's halves off the Torso's front and back walls
    *[
        Seat("next morty shirt front", "next torso", (x, TORSO[0] - 4.0, -137.5), (0.0, -1.0, 0.0), 5.0, 0.0, 1)
        for x in (-24.0, 24.0)
    ],
    *[
        Seat("next morty shirt back", "next torso", (x, TORSO[1] + 4.0, -137.5), (0.0, 1.0, 0.0), 5.0, 0.0, 1)
        for x in (-24.0, 24.0)
    ],
]
GLUED = {"next morty L pupil": (0.0, -1.0, 0.0), "next morty R pupil": (0.0, -1.0, 0.0)}  # keyed in the caps' seats
SHELLS = list(dict.fromkeys([s.shell for s in SEATS] + list(GLUED)))
DIRECTIONS = {s.shell: s.normal for s in SEATS} | GLUED  # each Shell's Assembly direction, in its carrier's frame
# The Shells physics leaves out (#665): drawn, weightless and colliding with nothing, so the sim weighs and collides the
# Skeleton (and the eyeball caps, the gimbal's own gates read) alone; their hold is checked against the peak acceleration
# of where they sit (model/mujoco_report.py), their clearance on their own shapes (model/printed/test_skin.py).
# shortcut: the servos carry the Skeleton's load alone; weighed, Morty's head takes the tilt hold to 0.43 kgf.cm, over
# the rated 0.4: weigh the Shells once the tilt servo holds a head in its Skin (#830)
DRAWN = [s for s in SHELLS if s.startswith("next morty ")]


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
