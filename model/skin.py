"""The Mech's Skin (GLOSSARY Skin, Seat, Sculpt): how a Shell sits on what carries it and how hard its magnets hold it
there, Morty's contours and the cuts they make on his Sculpt, and the Motion regions. No Shell is drawn by hand
(docs/adr/0027, #850): the eyeball caps are the mechanism's own, and Morty's are cut from his Sculpt along these cuts
(model/morty/shells.py), with no Seat yet and worn by no document yet (g.SKINS).
One source: model/printed/skin.py draws the caps and cuts the Seats from these numbers, model/stages.py places the caps
on their cores, model/mujoco_report.py reads each Shell's peak acceleration and model/test_report.py holds it to
hold_n().

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

from model import geometry as g
from model import gimbal as gm

MAGNET = (4.0, 2.0)  # one size everywhere (#51): a 4x2 mm N52 disc, flush in its pocket, glued
MAGNET_T = 1.43  # N52's least remanence, T: the pull it gives is the least the grade promises
FIT = 0.1  # the pocket's play round the magnet, per side
BALL_R, GROOVE_D = 1.0, 1.2  # each ball, and its 90 deg V-groove's depth
GAP = math.sqrt(2) * BALL_R - GROOVE_D  # between the Seat's faces (and so its magnets), the balls in their grooves
RING, GROOVE = 4.5, 1.5  # the balls' circle round the magnet; each groove's half-length along its radius
PAD_R = RING + GROOVE + 1.0  # a Seat's thickening's or boss's radius
SF = 2.0  # the magnets hold at least this many times a Shell's weight at its peak acceleration (model/test_report.py)

Seat = namedtuple("Seat", "shell carrier at normal pad boss polarity")  # at: the carrier's face, normal: out of it

WALL = 1.6  # every Shell's wall: four 0.4 mm perimeters
# Morty's contours (#991, #992): our control points (contours.json, its research note), in his eyes' spacing from their
# midpoint, each in the view it was measured in, front (x, z) or side (y, z), and swept through the head along that
# view's axis. Cut once, on his Sculpt's skin (docs/adr/0027, cuts()), each where the Sculpt itself has the form: its
# hair's boundary ("sculpt hairline"), each eye dome's foot, each pupil's ring, the middle of its lips' ridge, and the
# collar where its head meets its shirt
with open(os.path.join(os.path.dirname(__file__), "contours.json")) as _f:
    _SHEET = json.load(_f)
CONTOURS = _SHEET["contours"]
FAR = 400.0  # mm out, past the whole head and body, where an open contour's region closes


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


def outline(name, step=2.0):
    """The region contour `name` bounds, a closed polygon in its view's plane: an eye white's or a pupil's its own; the
    hair above and behind a hairline (forehead first), the shirt under the collar, the jaw under the mouth line between
    its corners, each closed FAR out."""
    p = contour(name, step)
    (a0, b0), (a1, b1) = p[0], p[-1]  # (y, z) on a side view, (x, z) on a front one
    if name.endswith("hairline"):  # on past the forehead along its end, out of the head
        t = (p[0] - p[1]) / np.linalg.norm(p[0] - p[1])
        a0, b0 = p[0] + FAR * t
        # it ends at his collar behind an ear, all behind it hair
        return np.vstack([(a0, b0), p, (a1, -FAR), (FAR, -FAR), (FAR, FAR), (a0, FAR)])
    if name == "collar":
        return np.vstack([(-FAR, b0), p, (FAR, b1), (FAR, -FAR), (-FAR, -FAR)])
    if name == "mouth":
        return np.vstack([p, (a1, -FAR), (a0, -FAR)])
    return p


def inside(points, poly):
    """Even-odd: which (n, 2) points lie inside the closed polygon (a cut's region, in its view's plane)."""
    a, b = poly, np.roll(poly, -1, axis=0)
    x, y = points[:, :1], points[:, 1:]
    span = (a[:, 1] > y) != (b[:, 1] > y)
    t = (y - a[:, 1]) / np.where(span, b[:, 1] - a[:, 1], 1.0)
    return (span & (x < a[:, 0] + t * (b[:, 0] - a[:, 0]))).sum(axis=1) % 2 == 1


def cuts():
    """Morty's cuts on his Sculpt, {cut: (its view, the closed region it bounds, mm in the head's frame)}: the one source
    that colours the review's Morty (model/review) and splits the printed Shells (#850), each cut where the Sculpt
    itself has the form. The hair is above and behind the hairline, its hair's boundary; an eye white is its eye's whole
    dome, inside its foot, and its pupil the ring on it (no lid has a cut: the lids are the mechanism's covers); the jaw
    is under the mouth line, the middle of the lips' ridge, between its corners and in front of the eyes; the shirt is
    under the collar, where the head meets it, on the fixed body, where it takes what the hair's region covers too."""
    names = {"hairline": "sculpt hairline"} | {n: n for n in CONTOURS if "hairline" not in n}
    return {cut: (CONTOURS[n]["view"], outline(n)) for cut, n in names.items()}


# The eyeball caps on the cores' seat faces, along the gaze: every Character's (#665)
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

SHELLS = list(dict.fromkeys(s.shell for s in SEATS))
DIRECTIONS = {s.shell: s.normal for s in SEATS}  # each Shell's Assembly direction, in its carrier's frame
# A Skin's Shells physics draws whole (#665): uncut and colliding with nothing, their mass on their drawn mesh (#830), so
# the servos carry the Skin and the sim collides the Skeleton (and the eyeball caps, the gimbal's own gates read) alone;
# their hold is checked against the peak acceleration of where they sit (model/mujoco_report.py). None until a
# document wears a Skin's Shells (g.SKINS)
DRAWN = [s for s in SHELLS if s.split()[0] in g.SKINS]
# The Motion regions (#969, GLOSSARY): {region: the part that carries it, None for the body, fixed through every horn}.
# One source for the Morty reference's semantic meshes (model/review) and the Shells cut from his Sculpt (#850), so a
# seam cut on either side lands on the same region.
MOTION = {
    "head": "gimbal frame",
    "jaw": "jaw",
    **{f"{s} eye": f"{s} eyeball cap" for s in "LR"},
    **{f"{s} {lid} lid": f"{s} {lid} lid" for s in "LR" for lid in ("upper", "lower")},
    **dict.fromkeys(("neck", "shoulders", "torso")),
}
# {a word of a Shell's name: its region}, an eye's or a lid's after the Shell's side
_WORDS = {"face": "head", "hair": "head", "chin": "jaw", "shirt": "torso"}
_WORDS |= {"pupil": "eye", "eyeball": "eye", "upper": "upper lid", "lower": "lower lid"}


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
