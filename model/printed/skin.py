"""The eyeball caps as CadQuery parts and the Seats cut into what carries a Shell, every Seat and size from
model/skin.py. No Shell is drawn by hand (docs/adr/0027, #850): Morty's are cut from his Sculpt. seated() cuts each Seat
into what carries it. Each cap is drawn in its eye's frame (the L one's, the R its mirror)."""

import math

import cadquery as cq

from model import geometry as g
from model import gimbal as gm
from model import skin as sk
from model.envelopes import box
from model.printed.gimbal import ball, cone, cyl, opening, prism


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


def cap(side):
    """The `side` eyeball cap (#967), Morty's eye white: his eye's sphere gm.CAP_R, solid within CAP_HALF of the gaze
    (its back GAP off the core's seat face, its pupil's jagged seat cut in), and from there a shell gm.CAP_WALL thick
    out to its eye opening's own outline as the front sees it, so at rest it fills the opening and no more; below the
    eye line out to the rim's own way from the eye's centre (gm.CAP_LOW), short of the yaw bearing."""
    r, back = gm.CAP_R, gm.CAP_R * math.cos(math.radians(gm.CAP_HALF)) + sk.GAP
    rim = opening(side) * ((1, 1) if side == "L" else (-1, 1))  # in this eye's own frame
    shell = ball(r).cut(ball(r - gm.CAP_WALL)).intersect(prism(rim))
    shell = shell.intersect(cone(rim).union(box((-r - 1, r + 1), (-r - 1, 1), (0, r + 1))))
    # its end toward the other eye cut square to its face (the view's cut leaves its inside 5 deg longer)
    reach, inward = 45.0 / math.tan(math.radians(gm.CAP_IN)), -1 if side == "L" else 1
    shell = shell.cut(
        cq.Workplane().add(cq.Solid.makeCone(0.0, reach, 45.0, cq.Vector(0, 0, 0), cq.Vector(inward, 0, 0)))
    )
    out = ball(r).intersect(box((-r, r), (-r - 1, -back), (-r, r))).union(shell)
    out = out.cut(_pupil_prism(side))
    return _finish(f"{side} eyeball cap", out)
