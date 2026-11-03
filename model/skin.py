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


# Morty's head (#665, #850: one smooth sculpted shell, round from every angle), in the head's frame (model/neck.py): the
# face comes off forward, the hair up. Each section across z is a superellipse of power HEAD_N (by z) round HEAD_C (y),
# out to the front outline's half-width (HEAD_W: an egg, its half-width at its widest, that height, and its powers over
# and under) and to the side outline's front and back (a smooth closed curve through PROFILE's (y, z)). Fitted round the
# mechanism at every pose, the jaw's arms setting its lower half and the eyes' openings the face over them (#850's
# prototype, branch prototype/850-egg-head); every size is inferred.
HEAD_Z = (-80.0, 69.0)
HEAD_W = (64.0, -35.0, 2.2, 2.7)
HEAD_C = 21.0
PROFILE = (
    *((-26.0, -80.0), (-37.0, -74.0), (-39.0, -60.0), (-36.0, -40.0), (-32.0, -20.0), (-30.5, 0.0), (-30.0, 20.0)),
    *((-25.0, 40.0), (-8.0, 60.0), (21.0, 69.0), (52.0, 63.0), (80.0, 40.0), (92.0, 5.0), (92.0, -30.0), (89.0, -50.0)),
    *((80.0, -70.0), (58.0, -80.0)),
)
HEAD_N = ((-80.0, 2.7), (-45.0, 2.7), (0.0, 2.3), (69.0, 2.1))


@functools.cache
def _profile():
    """PROFILE's closed curve, sampled: (y, z) of its front run and of its back run, each by rising z."""
    from scipy.interpolate import splev, splprep

    y, z = np.array(PROFILE).T
    tck, _ = splprep([np.r_[y, y[0]], np.r_[z, z[0]]], s=0, per=True)
    cy, cz = splev(np.linspace(0, 1, 4000, endpoint=False), tck)
    top, bottom = sorted((int(np.argmax(cz)), int(np.argmin(cz))))
    runs = [np.r_[top : bottom + 1], np.r_[bottom : len(cz), 0 : top + 1]]
    runs = [(cy[r][np.argsort(cz[r])], np.sort(cz[r])) for r in runs]
    return tuple(sorted(runs, key=lambda r: r[0].mean()))


def _egg(z, w, widest, over, under):
    h, p = (HEAD_Z[1] - widest, over) if z > widest else (widest - HEAD_Z[0], under)
    return w * (1 - min(abs(z - widest) / h, 1.0) ** p) ** (1 / p)


def head_section(z, t=0.0):
    """(half-width, front y, back y, power) of the head's section at height z, `t` in from its outside."""
    (fy, fz), (by, bz) = _profile()
    n = float(np.interp(z, *zip(*HEAD_N)))
    return _egg(z, *HEAD_W) - t, float(np.interp(z, fz, fy)) + t, float(np.interp(z, bz, by)) - t, n


def head_x(y, z):
    """The head's outside half-width at (y, z): where its section's superellipse crosses y."""
    a, front, back, n = head_section(z)
    d = (y - HEAD_C) / (HEAD_C - front if y < HEAD_C else back - HEAD_C)
    return a * max(1 - abs(d) ** n, 0.0) ** (1 / n)


# outside: half-width, front to back, z
HEAD_X = HEAD_W[0]
HEAD_Y = (float(min(_profile()[0][0])), float(max(_profile()[1][0])))
MUZZLE_Y = HEAD_Y[0]  # the face's front at its most forward, over the jaw's chin
WALL = 1.6  # every Shell's wall: four 0.4 mm perimeters
# The hairline (his model sheet's): the hair is the head inside a circle along x, (y, z, r), from over the forehead down
# behind the ears, and all behind NAPE, so the hair comes off upward and the face forward; it stands HAIR proud of the face
HAIRLINE = (99.4, 67.4, 111.5)
NAPE = 78.0
HAIR = 1.5
NECK = (42.0, 4.0)  # the head's floor open round the neck and the jaw within this half-width, up to this over its foot
BACK_OPEN = (nk.AXIS[0] - 20.0, nk.AXIS[1] + 7.0)  # (y, z): the head open behind y and under z within NECK's width
# (#838), where the neck's yoke tilts in under the skull's base and out past the head's back; closed either side (#850)
TORSO = nb.TORSO[1]  # the Torso's front and back walls
_PLATE = (gm.PLATE_Y[0], sum(gm.BEAM_Z) / 2)  # the front of the gimbal frame's beam (its bar to the lids'), mid height
_BACK = (32.5, 64.0)  # (|x|, y) on the gimbal frame plate's back, behind the pitch servo, clear of its collar (#838)
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
    # the face forward off the front of the gimbal frame's beam, its bar to the lids' uprights (#838, #852); its top
    # held by the hair
    *[
        Seat(
            "next morty face",
            "next gimbal frame",
            (x, _PLATE[0], _PLATE[1]),
            (0.0, -1.0, 0.0),
            0.0,
            _PLATE[0] - GAP - (head_section(_PLATE[1])[1] + WALL) + 1.0,
            1,
        )
        for x in (-45.0, 45.0)
    ],
    # the hair down onto the gimbal frame plate's back (a web from its back wall, model/printed/skin.py, #838) and onto
    # the face's temples under the hairline, back from the forehead (each boss up to the hair's wall, cut at its outside)
    *[
        Seat("next morty hair", "next gimbal frame", (x, _BACK[1], gm.PLATE_Z[1]), (0.0, 0.0, 1.0), 0.0, 6.0, 1)
        for x in (-_BACK[0], _BACK[0])
    ],
    *[
        Seat("next morty hair", "next morty face", (x, -2.0, 47.0), (0.0, 0.0, 1.0), 6.0, HEAD_Z[1] - 47.0, 1)
        for x in (-40.0, 40.0)
    ],
    # the mouth cover up off the top of the jaw's chin (model/neck.py CHIN_Y, JAW_ARM_Z), the chin thickened behind it
    # (inside the jaw's U), flush with its front: under the chin it would make the head taller (#708's gate)
    Seat(
        "next morty mouth cover",
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
        Seat("next morty shirt front", "next torso", (x, TORSO[0], -137.5), (0.0, -1.0, 0.0), 3.0, 4.0, 1)
        for x in (-24.0, 24.0)
    ],
    *[
        Seat("next morty shirt back", "next torso", (x, TORSO[1], -137.5), (0.0, 1.0, 0.0), 3.0, 4.0, 1)
        for x in (-24.0, 24.0)
    ],
]
GLUED = {"next morty L pupil": (0.0, -1.0, 0.0), "next morty R pupil": (0.0, -1.0, 0.0)}  # keyed in the caps' seats
SHELLS = list(dict.fromkeys([s.shell for s in SEATS] + list(GLUED)))
DIRECTIONS = {s.shell: s.normal for s in SEATS} | GLUED  # each Shell's Assembly direction, in its carrier's frame
# The Shells physics draws whole (#665): uncut and colliding with nothing, their mass on their drawn mesh (#830), so the
# servos carry the Skin and the sim collides the Skeleton (and the eyeball caps, the gimbal's own gates read) alone;
# their hold is checked against the peak acceleration of where they sit (model/mujoco_report.py), their clearance on
# their own shapes (model/printed/test_skin.py). The head less these is its bare one, which the balance spring holds too
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
