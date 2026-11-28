"""The eyeball caps and the eye liners inside them as CadQuery parts, and the Seats cut into what carries a Shell, every
Seat and size from model/skin.py. No Shell is drawn by hand (docs/adr/0027, #850): Morty's are cut from his Sculpt.
seated() cuts each Seat into what carries it. Each cap and liner is drawn in its eye's frame (the L one's, the R its
mirror)."""

import math

import cadquery as cq

from model import fits
from model import geometry as g
from model import gimbal as gm
from model import skin as sk
from model.envelopes import box
from model.printed.gimbal import RAIL_ROOM, ball, cone, cyl, fan, opening


def _at(seat):
    """The Seat's frame in its carrier's (skin.frame)."""
    return cq.Matrix([list(map(float, row)) for row in sk.frame(seat)[:3]])


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
        mine = [s for s in sk.SEATS if s.carrier == stem.removesuffix(g.MECHANICAL)]
        for seat in {(s.at, s.normal, s.pad): s for s in mine}.values():  # Seats that share a place: cut once
            pad, cut = carrier(seat)
            out = (out.union(pad) if pad else out).cut(cut)
        return out

    return draw


def _finish(stem, out):
    """The Shell `stem` with its Seats' bosses and balls on, their pockets cut, then the Seats it carries (seated)."""
    for seat in (s for s in sk.SEATS if s.shell == stem):
        add, cut = shell(seat)
        out = out.union(add).cut(cut)
    return seated(stem, lambda: out)()


def _star(r_out, r_in, n=7):
    """Morty's jagged pupil: an n-pointed star, a point up, symmetric across x."""
    pts = [
        ((r_in, r_out)[i % 2] * math.sin(math.pi * i / n), (r_in, r_out)[i % 2] * math.cos(math.pi * i / n))
        for i in range(2 * n)
    ]
    return [(x, y) for x, y in pts[1:] + pts[:1]]


PUPIL_DEPTH = 3.0  # the pupil's seat in the cap, at its middle


def _pupil_prism(side):
    """The pupil's seat through the cap's front, turned TOE_IN toward the other eye (#630), down to PUPIL_DEPTH under
    the cap's front."""
    r = gm.CAP_R * math.sin(math.radians(gm.PUPIL_DEG))
    inward = -1 if side == "L" else 1
    sketch = cq.Workplane(
        "XZ", origin=(inward * gm.CAP_R * math.sin(math.radians(gm.TOE_IN)), -gm.CAP_R + PUPIL_DEPTH, 0)
    )
    return (
        sketch.polyline(_star(r, 0.6 * r)).close().extrude(PUPIL_DEPTH + 1.0)
    )  # XZ's normal is -y: out through the front


def _about(axis, deg):
    """Every way out from the eye's centre within `deg` (under 90) of `axis`: a cone, its apex the centre. Cut one at a
    time from a shell about the centre: two that share their apex inside one solid come out of OCCT invalid (#967)."""
    reach = 2 * gm.CAP_R
    cut = cq.Solid.makeCone(0.0, reach * math.tan(math.radians(deg)), reach, cq.Vector(0, 0, 0), cq.Vector(*axis))
    return cq.Workplane().add(cut)


def _ring(points, middle=None):
    """The fan through the ring of (az, el) `points` on the L eye's sphere (gm.ray), about `middle`."""
    return fan([gm.ray(*q) for q in points], middle and gm.ray(*middle))


def cap(side):
    """The `side` eyeball cap (#967), Morty's eye white: a shell gm.CAP_WALL thick of his eye's sphere gm.CAP_R on a
    stem, gm.CAP_STEM about the gaze, whose back stands GAP off the core's seat face and whose front holds the pupil's
    jagged seat. One shell, cut: where it would pass gm.CAP_OUT from the gaze, behind its equator; under gm.CAP_SIDE
    below the eye line, but on its eye opening's own way out from the eye's centre (gm.CAP_LOW: short of the yaw
    bearing, and where the lower lid's edge lies) and in gm.CAP_LOW_OUT; and where the lids' hubs turn (gm.CAP_HUBS)."""
    r, back = gm.CAP_R, gm.CAP_R * math.cos(math.radians(gm.CAP_HALF)) + sk.GAP
    rim = opening(side) * ((1, 1) if side == "L" else (-1, 1))  # in this eye's own frame
    sided = (lambda shape: shape) if side == "L" else (lambda shape: shape.mirror("YZ"))
    low = ball(r + 1).cut(ball(r - gm.CAP_WALL - 1)).intersect(_about((0, 0, -1), 90.0 - gm.CAP_SIDE))
    low = low.cut(cone(rim)).cut(sided(_ring(gm.CAP_LOW_OUT)))
    shell = ball(r).cut(ball(r - gm.CAP_WALL)).cut(_about((0, 1, 0), 180.0 - gm.CAP_OUT)).cut(low)
    for ring, middle in zip(gm.CAP_HUBS, gm.HUB_MIDDLES, strict=True):
        shell = shell.cut(sided(_ring(ring, middle)))
    stem = ball(r).intersect(box((-r, r), (-r - 1, -back), (-r, r))).intersect(_about((0, -1, 0), gm.CAP_STEM))
    return _finish(f"{side} eyeball cap", stem.union(shell).cut(_pupil_prism(side)))


def _window(deg, n=4):
    """Where a cap's stem sweeps on a sphere about its eye's centre: the ring of directions `deg` from the gaze as it
    goes round the edge of its range (gm.YAW, gm.PITCH), its chords on that edge or outside it. Round each corner of
    the range an arc drawn round its chords, `n` of them; along each side its ends and its middle."""

    def at(yaw, pitch, turn, off):
        turn, off = math.radians(turn), math.radians(off)
        return gm.core(yaw, pitch) @ (math.sin(off) * math.cos(turn), -math.cos(off), math.sin(off) * math.sin(turn))

    corners = [(gm.YAW, gm.PITCH), (-gm.YAW, gm.PITCH), (-gm.YAW, -gm.PITCH), (gm.YAW, -gm.PITCH)]
    ring = []
    for i, (yaw, pitch) in enumerate(corners):
        ring += [at(yaw, pitch, 90.0 * (i + k / n), deg / math.cos(math.radians(45.0 / n))) for k in range(n + 1)]
        to_yaw, to_pitch = corners[(i + 1) % 4]
        ring.append(at((yaw + to_yaw) / 2, (pitch + to_pitch) / 2, 90.0 * (i + 1), deg))
    return ring


def liner(side):
    """The `side` eye liner (#967, GLOSSARY Eye liner), drawn about its eye's centre (the L one's, the R its mirror):
    a shell gm.LINER_R in front of the plane gm.LINER_RIM ahead of the centre, open where the cap's stem sweeps
    (_window, the lids' clearance and gm.LID_OVER round it) and where the lids' drive turns (gm.LINER_HUBS), and at
    its bottom round the yaw bearing: its foot is a collar round the bearing's post (gm.CLIP), between the pad's top
    and the yoke's bar, whose jaws reach past the post's middle either side, so it snaps on along the bearing's own
    way, from the front and the outside, with the yoke and the core in place and before the cap; under the pad's top
    the collar is cut back to the pad's front face, which its two ends meet, so it cannot turn on the post."""
    (lo, hi), room = gm.LINER_R, gm.LID_CLEAR_MM + gm.LID_OVER
    under, top = gm.FINGER_Z[0] - RAIL_ROOM, gm.YAW_CRANK_Z[0] - gm.CLIP["under"]  # the pad's top; under the yoke's bar
    r0, r1 = gm.POST_R + fits.CLEARANCE[0], gm.POST_R + gm.CLIP["wall"]
    behind = lambda y0, z: box((-hi, hi), (y0, hi), z).rotate((0, 0, 0), (0, 0, 1), gm.RAIL_TURN)  # noqa: E731
    out = ball(hi).cut(ball(lo)).intersect(box((-hi, hi), (-hi, -gm.LINER_RIM), (-hi, hi)))
    out = out.cut(fan(_window(gm.CAP_STEM + math.degrees(math.asin(room / lo))))).cut(
        _ring(gm.LINER_HUBS, gm.LINER_MIDDLE)
    )
    # clear of the pad, and a hole its collar fills
    out = out.cut(behind(-gm.LID_CLEAR_MM, (-hi, under + gm.LID_CLEAR_MM))).cut(
        cyl("z", (0, 0, 0), r1 - 0.3, (-hi - 1, 0))
    )
    collar = cyl("z", (0, 0, 0), r1, (-hi, top)).cut(cyl("z", (0, 0, 0), r0, (-hi - 1, top + 1))).intersect(ball(hi))
    gap = math.radians(180.0 - gm.CLIP["wrap"])  # the jaws' mouth, half of it, about the bearing's way
    mouth = [
        (0.0, 0.0),
        (-20 * math.sin(gap), 20 * math.cos(gap)),
        (0.0, 30.0),
        (20 * math.sin(gap), 20 * math.cos(gap)),
    ]
    mouth = cq.Workplane("XY", origin=(0, 0, under)).polyline(mouth).close().extrude(top - under + 1)
    collar = collar.cut(mouth.rotate((0, 0, 0), (0, 0, 1), gm.RAIL_TURN)).cut(behind(0.0, (-hi - 1, under)))
    out = out.union(collar)
    return out if side == "L" else out.mirror("YZ")
