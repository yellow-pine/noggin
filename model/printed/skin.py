"""Morty's Skin (#665) as CadQuery parts, every Seat and size from model/skin.py: the head's face (with the nose and
ears) and hair, the eyeball caps with their jagged pupils keyed in, a cover on each lid, the mouth cover on the jaw and
the shirt's two halves on the Torso. seated() cuts each Seat into what carries it. Each Shell is drawn in its carrier's
frame: the head's, an eye's (the L one's, the R its mirror) or the Torso's."""

import functools
import math

import cadquery as cq
import numpy as np
from scipy.spatial import ConvexHull

from model import base
from model import geometry as g
from model import gimbal as gm
from model import neck as nk
from model import skin as sk
from model.envelopes import box
from model.printed.gimbal import ball, cyl


def _at(seat):
    """The Seat's frame in its carrier's: z out of the carrier's face along the normal, origin on that face."""
    n = seat.normal
    ref = (1, 0, 0) if abs(n[0]) < 0.9 else (0, 1, 0)
    return cq.Matrix([list(map(float, row)) for row in g.align_rows(seat.at, ref, n)[:3]])


def _placed(shape, seat):
    return cq.Workplane().add(shape.val().transformGeometry(_at(seat)))


def _groove(deg):
    """A 90 deg V-groove, its edge GROOVE_D down, along a radius at `deg` round the Seat's middle."""
    w, h = sk.GROOVE_D + 1.0, 1.0
    v = cq.Workplane("YZ", origin=(sk.RING - sk.GROOVE, 0, 0)).polyline([(-w, h), (w, h), (0, -sk.GROOVE_D)]).close()
    return v.extrude(2 * sk.GROOVE).rotate((0, 0, 0), (0, 0, 1), deg)


def _pocket(z0):
    return cyl("z", (0, 0, 0), sk.MAGNET[0] / 2 + sk.FIT, (z0, z0 + sk.MAGNET[1]))


def carrier(seat):
    """(what the Seat adds to its carrier, what it cuts): its pad, and the magnet's flush pocket and the grooves."""
    pad = cyl("z", (0, 0, 0), sk.PAD_R, (-seat.pad, 0.0)) if seat.pad else None
    cut = _pocket(-sk.MAGNET[1]).union(cyl("z", (0, 0, 0), sk.MAGNET[0] / 2 + sk.FIT, (0.0, 1.0)))
    for deg in (0, 120, 240):
        cut = cut.union(_groove(deg))
    return pad and _placed(pad, seat), _placed(cut, seat)


def shell(seat):
    """(what the Seat adds to its Shell, what it cuts): its boss and the three balls, and the magnet's flush pocket."""
    add = cyl("z", (0, 0, 0), sk.PAD_R, (sk.GAP, sk.GAP + seat.boss)) if seat.boss else None
    for deg in (0, 120, 240):
        a = math.radians(deg)
        b = ball(sk.BALL_R, (sk.RING * math.cos(a), sk.RING * math.sin(a), sk.GAP))
        add = b if add is None else add.union(b)
    cut = _pocket(sk.GAP).union(cyl("z", (0, 0, 0), sk.MAGNET[0] / 2 + sk.FIT, (sk.GAP - 1.0, sk.GAP)))
    return _placed(add, seat), _placed(cut, seat)


def seated(stem, build):
    """`build` (a part's builder, with its own arguments) with every Seat it carries cut into it, its pads on."""

    def draw(*args, **kw):
        out = build(*args, **kw)
        for seat in (s for s in sk.SEATS if s.carrier == stem.removesuffix(g.MECHANICAL)):
            pad, cut = carrier(seat)
            out = (out.union(pad) if pad else out).cut(cut)
        return out

    return draw


def _finish(stem, out, clip=None):
    """The Shell `stem` with its Seats' bosses and balls on (clipped to `clip`), their pockets cut, then the Seats it
    carries (seated)."""
    for seat in (s for s in sk.SEATS if s.shell == stem):
        add, cut = shell(seat)
        out = out.union(add.intersect(clip) if clip else add).cut(cut)
    return seated(stem, lambda: out)()


def _wedge(span, x, r):
    """The region within r of the eye's x axis from span[0] to span[1] deg (from forward toward up), over x."""
    arc = [math.radians(span[0] + (span[1] - span[0]) * i / 24) for i in range(25)]
    fan = [(0.0, 0.0)] + [(-r * math.cos(t), r * math.sin(t)) for t in arc]
    return cq.Workplane("YZ", origin=(x[0], 0, 0)).polyline(fan).close().extrude(x[1] - x[0])


def lid_cover(side, lid):
    """The `side` (L, R its mirror) `lid` (upper, lower) lid's cover: a shell GAP outside it over the lid's main shell
    and LIP past its free edge, COVER thick; the upper one that thick over its top band alone (model/skin.py
    UPPER_COVER), a skin BAND thick over the rest (UPPER_SKIN)."""
    ri = (gm.LID_R[1] if lid == "upper" else gm.LOWER_R[1]) + sk.GAP

    def band(t, span, x):
        return ball(ri + t).cut(ball(ri)).intersect(_wedge(span, x, ri + t + 5))

    if lid == "upper":  # the skin under the whole of it, so the two overlap and fuse
        out = band(sk.COVER, sk.UPPER_COVER, sk.COVER_X).union(band(sk.BAND, sk.UPPER_SKIN, sk.COVER_X))
    else:
        out = band(sk.COVER, sk.LOWER_COVER, sk.LOWER_X)
    out = out if side == "L" else out.mirror("YZ")
    return _finish(f"morty {side} {lid} lid cover", out)


def _star(r_out, r_in, n=7):
    """Morty's jagged pupil: an n-pointed star, a point up, symmetric across x."""
    pts = [
        ((r_in, r_out)[i % 2] * math.sin(math.pi * i / n), (r_in, r_out)[i % 2] * math.cos(math.pi * i / n))
        for i in range(2 * n)
    ]
    return [(x, y) for x, y in pts[1:] + pts[:1]]


PUPIL_DEPTH = 3.0  # the pupil's seat in the cap, at its middle


def _pupil_prism(side, shrink=0.0):
    """The pupil's seat (or, shrunk by its fit, the pupil) through the cap's front, turned TOE_IN toward the other
    eye (#630), down to PUPIL_DEPTH under the cap's front."""
    r = gm.CAP_R * math.sin(math.radians(gm.PUPIL_DEG))
    inward = -1 if side == "L" else 1
    sketch = cq.Workplane(
        "XZ", origin=(inward * gm.CAP_R * math.sin(math.radians(gm.TOE_IN)), -gm.CAP_R + PUPIL_DEPTH, 0)
    )
    face = sketch.polyline(_star(r, 0.6 * r)).close()
    face = face.offset2D(-shrink) if shrink else face
    return face.extrude(PUPIL_DEPTH + 1.0)  # XZ's normal is -y: out through the front


def cap(side):
    """The `side` eyeball cap (eye whites): the largest cap's sphere segment within CAP_HALF of the gaze (each
    Character's largest, #630), its back GAP off the core's seat face, its pupil's jagged seat cut in."""
    r, back = gm.CAP_R, gm.CAP_R * math.cos(math.radians(gm.CAP_HALF)) + sk.GAP
    out = ball(r).intersect(box((-r, r), (-r - 1, -back), (-r, r))).cut(_pupil_prism(side))
    return _finish(f"{side} eyeball cap", out)


def pupil(side):
    """The `side` pupil: its seat's star, PUPIL_FIT smaller each side, flush with the cap's dome; glued in (#51: keyed,
    not held by magnets alone)."""
    return _pupil_prism(side, gm.PUPIL_FIT).intersect(ball(gm.CAP_R))


def _hull(circles):
    """The outline of the convex hull of (u, v, r) circles, counter-clockwise, as lines and arcs: [(circle, in, out)],
    each circle on it with the angles its tangents meet it at."""
    t = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    pts = np.concatenate([np.c_[u + r * np.cos(t), v + r * np.sin(t)] for u, v, r in circles])
    seq = [int(i) // len(t) for i in ConvexHull(pts).vertices]
    order = [c for k, c in enumerate(seq) if c != seq[k - 1]]
    normals = []  # each tangent's outward normal, from one circle to the next
    for a, b in zip(order, order[1:] + order[:1]):
        (au, av, ar), (bu, bv, br) = circles[a], circles[b]
        normals.append(math.atan2(bv - av, bu - au) - math.acos((ar - br) / math.dist((au, av), (bu, bv))))
    return [(circles[c], normals[k - 1], normals[k]) for k, c in enumerate(order)]


def _outline(plane, circles):
    """The hull of the circles (_hull) on `plane` as a face."""
    at = lambda c, a: (c[0] + c[2] * math.cos(a), c[1] + c[2] * math.sin(a))  # noqa: E731
    pieces = _hull(circles)
    w = cq.Workplane(plane).moveTo(*at(*pieces[0][:2]))
    for k, (c, a_in, a_out) in enumerate(pieces):
        a_out += 2 * math.pi * (a_out <= a_in)
        w = w.threePointArc(at(c, (a_in + a_out) / 2), at(c, a_out))
        if k + 1 < len(pieces):
            w = w.lineTo(*at(*pieces[k + 1][:2]))
    return cq.Face.makeFromWires(w.close().wires().val())


def _profile(plane, hulls, t, rounded=0.0):
    """The hulls' outlines on `plane` as one, its inside corners rounded `rounded`, `t` in from its outside, through
    everything along the plane's normal."""
    face = _outline(plane, hulls[0])
    for h in hulls[1:]:
        face = face.fuse(_outline(plane, h)).clean().Faces()[0]
    wire = face.outerWire()
    if rounded:
        wire = wire.offset2D(rounded, "arc")[0].offset2D(-rounded, "arc")[0]
    wire = wire.offset2D(-t, "arc")[0] if t else wire
    n = cq.Plane.named(plane).zDir
    return cq.Workplane().add(cq.Solid.extrudeLinear(cq.Face.makeFromWires(wire), n * 400).translate(n * -200))


def _head(t):
    """Morty's head (model/skin.py FRONT, SIDE, TOP) `t` in from its outside (out of it, negative): arcs and lines
    swept straight, planes and cylinders alone, since a B-spline surface reads back invalid from Linux's STEP (#833).
    Each call its own copy of the one built: a Shell built again on Linux's OCCT, over shapes an earlier build's
    booleans had used, came out broken (four solids, a 200 mm clip box left in; #838)."""
    return cq.Workplane().add(_built_head(t).copy())


@functools.cache  # every Shell cuts and clips by the same few
def _built_head(t):
    side = _profile("YZ", sk.SIDE, t, sk.SIDE_ROUND)
    return _profile("XZ", [sk.FRONT], t).intersect(side).intersect(_profile("XY", [sk.TOP], t)).val()


def _eyes():
    """What the eyes' openings leave out: round each eye, everything its lids and their covers reach (r 36.3) with
    1.2 mm to spare, ahead of the eye centres and inside the lids' reach across."""
    out = None
    for x, _, _ in gm.EYE.values():
        o = ball(37.5, (x, 0, 0)).intersect(box((-58, 58), (-60, 0), (-40, 40)))
        out = o if out is None else out.union(o)
    return out


def _hair(grow):
    """The hair's region (model/skin.py HAIRLINE, NAPE), `grow` mm out of it."""
    y, z, r = sk.HAIRLINE
    return cyl("x", (0, y, z), r + grow, (-100, 100)).union(box((-100, 100), (sk.NAPE - grow, 200), (-200, 200)))


def _skull(t):
    """The head's shell, from `t` in from its outside (out of it, negative) to WALL in, its eyes' openings cut, its
    floor open round the neck and the jaw (NECK) and its back under the head mount (BACK_OPEN, #838)."""
    x, up = sk.NECK
    neck = box((-x, x), (-100, 200), (sk.HEAD_Z[0] - 5, sk.HEAD_Z[0] + up))
    back = box((-100, 100), (sk.BACK_OPEN[0], 200), (sk.HEAD_Z[0] - 5, sk.BACK_OPEN[1]))
    out = _head(t).cut(_head(sk.WALL)).cut(_eyes()).cut(neck).cut(back)
    return out.intersect(box((-100, 100), (-100, 100), (sk.HEAD_Z[0], 100)))


FACE_Y = min(u - r for u, _, r in sk.SIDE[0])  # the face's front over the eyes
NOSE = (7.0, -20.0)  # his nose: a ball's radius and its centre's height, the centre 4 mm out of the face
EAR = (18.0, -25.0, 13.0, 5.0)  # each ear: (y, z) and radius of its dome, standing this far out of the cheek


def _ear(s):
    """The `s` (1 L, -1 R) ear: a dome out of the cheek, its hollow (the concha) open forward, so it reads as his C."""
    y, z, r, out = EAR
    x = sk.HEAD_X + out - r

    def on_x(
        radius, at
    ):  # a ball its poles on x, its seam off the cheek's cut: OCCT cuts a ball across its seam to nothing
        return cq.Workplane().add(cq.Solid.makeSphere(radius, cq.Vector(*at), cq.Vector(1, 0, 0), -90, 90))

    ear = on_x(r, (x, y, z)).cut(box((0, sk.HEAD_X - 6.0), (-100, 100), (-100, 100)))
    ear = ear.cut(on_x(r - 4.0, (x + 6.0, y - 4.0, z)))
    return ear if s > 0 else ear.mirror("YZ")


def face():
    """Morty's face (face): the head's shell under the hairline, the nose between the eyes, an ear each side and the
    mouth's opening over the mouth cover; forward off the gimbal frame plate's Seats, the hair's Seats on its temples."""
    out = _skull(0.0).cut(_hair(0.1))
    r, z = NOSE
    out = out.union(ball(r, (0, FACE_Y - 4.0, z)).cut(box((-10, 10), (FACE_Y + sk.WALL, 0), (-40, 0))))
    for s in (-1, 1):
        out = out.union(_ear(s).cut(_head(sk.WALL)))
    y0 = sk.HEAD_Y[0]
    out = out.cut(box((-24, 24), (y0 - 11, y0 + 9), (sk.HEAD_Z[0] - 1, sk.HEAD_Z[0] + 6)))
    for seat in (s for s in sk.SEATS if s.carrier == "morty face"):  # each a pad on a web from the forehead
        x, y, z = seat.at
        out = out.union(box((x - 3, x + 3), (y0, y), (z - seat.pad, z)).intersect(_head(0.0)))
    return _finish("morty face", out, _head(0.0))


def hair():
    """Morty's hair (hair): the head's shell over the hairline and behind the nape, HAIR proud of the face; down onto
    the gimbal frame plate's back (#838), each Seat's boss on a web from its back wall, and onto the face's temples."""
    out = _skull(-sk.HAIR).intersect(_hair(-0.1))
    for seat in (s for s in sk.SEATS if s.shell == "morty hair" and s.carrier == "gimbal frame"):
        x, y, z = seat.at
        web = box((x - sk.PAD_R, x + sk.PAD_R), (y, sk.HEAD_Y[1] - 1.0), (z + sk.GAP + 1.0, z + sk.GAP + seat.boss))
        out = out.union(web.intersect(_head(0.0)))
    return _finish("morty hair", out, _head(0.0))


def mouth_cover():
    """The mouth cover (face), his lower lip and chin: a plate on the jaw's Seat, a wall down in front of the chin
    inside the face, and the chin under the jaw in the face's mouth opening, rounded as the head is, which the jaw
    swings down; up off its Seat once the face is off."""
    (seat,) = (s for s in sk.SEATS if s.shell == "morty mouth cover")
    _, y, z = seat.at
    bottom, inner = sk.HEAD_Z[0], sk.MUZZLE_Y + sk.WALL + 0.6
    plate = box((-sk.PAD_R - 2, sk.PAD_R + 2), (inner, y + sk.PAD_R), (z + sk.GAP, z + sk.GAP + sk.COVER))
    wall = box((-22, 22), (inner, inner + sk.COVER), (bottom, z + sk.GAP + sk.COVER))
    chin = box((-22, 22), (sk.MUZZLE_Y, -30), (bottom, nk.JAW_ARM_Z[0] - 0.5)).intersect(_head(0.0))
    return _finish("morty mouth cover", plate.union(wall).union(chin))


SHIRT_SPLIT = nk.AXIS[0]  # the halves part across the neck's pan axis
SHIRT_TOP = 6.0  # the collar's rise over the shirt's top, round the neck
SHIRT_ROUND = (10.0, 3.0, 25.0)  # his T-shirt's rounding: its sides, its shoulders, and the crew neck's corners


def shirt(half):
    """The shirt's `half` (front, back) (shirt and collar), his T-shirt: a sleeve round the Torso GAP outside its Seats'
    pads, its sides and shoulders rounded, a rim over its walls' top and the round crew neck's collar rising round the
    neck; each half off its Torso wall's Seats, the front forward, the back backward."""
    (x0, x1), (y0, y1), (z0, z1) = base.TORSO
    sides, shoulders, neck = SHIRT_ROUND
    front = next(s for s in sk.SEATS if s.shell == "morty shirt front")
    off = y0 - front.at[1] + sk.GAP + front.boss  # the Seats' faces out of the walls, their gap and the bosses
    inner = box((x0 - off, x1 + off), (y0 - off, y1 + off), (z0 + 0.5, z1 + 0.5)).edges("|Z").fillet(sides - sk.WALL)
    outer = box(
        (x0 - off - sk.WALL, x1 + off + sk.WALL),
        (y0 - off - sk.WALL, y1 + off + sk.WALL),
        (z0 + 0.5, z1 + 0.5 + sk.WALL),
    )
    outer = outer.edges("|Z").fillet(sides).edges(">Z").fillet(shoulders)
    hole = box((x0 + 2.0, x1 - 2.0), (y0 + 2.0, y1 - 2.0), (z0, z1 + 20)).edges("|Z").fillet(neck)
    collar = box(
        (x0 + 2.0 - sk.WALL, x1 - 2.0 + sk.WALL),
        (y0 + 2.0 - sk.WALL, y1 - 2.0 + sk.WALL),
        (z1 + 0.5, z1 + 0.5 + sk.WALL + SHIRT_TOP),  # clear of the Torso's lid (#838)
    )
    collar = collar.edges("|Z").fillet(neck + sk.WALL).edges(">Z").fillet(sk.WALL / 2)
    out = outer.cut(inner).union(collar).cut(hole)
    ys = (y0 - 20, SHIRT_SPLIT - 0.1) if half == "front" else (SHIRT_SPLIT + 0.1, y1 + 20)
    return _finish(f"morty shirt {half}", out.intersect(box((-80, 80), ys, (z0 - 5, z1 + 30))))
