"""Morty's Skin (#665) as CadQuery parts, every Seat and size from model/skin.py: the head's face (with the nose and
ears) and hair, the eyeball caps with their jagged pupils keyed in, a cover on each lid, the mouth cover on the jaw and
the shirt's two halves on the Torso. seated() cuts each Seat into what carries it. Each Shell is drawn in its carrier's
frame: the head's, an eye's (the L one's, the R its mirror) or the Torso's."""

import math

import cadquery as cq

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
    """The `side` (L, R its mirror) `lid` (upper, lower) lid's cover: a shell COVER thick GAP outside it over the lid's
    main shell, the upper one over its top band alone (model/skin.py UPPER_COVER)."""
    r, span = (gm.LID_R[1], sk.UPPER_COVER) if lid == "upper" else (gm.LOWER_R[1], sk.LOWER_COVER)
    ri = r + sk.GAP
    out = ball(ri + sk.COVER).cut(ball(ri)).intersect(_wedge(span, sk.COVER_X, ri + sk.COVER + 5))
    out = out if side == "L" else out.mirror("YZ")
    return _finish(f"next morty {side} {lid} lid cover", out)


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
    return _finish(f"next {side} eyeball cap", out)


def pupil(side):
    """The `side` pupil: its seat's star, PUPIL_FIT smaller each side, flush with the cap's dome; glued in (#51: keyed,
    not held by magnets alone)."""
    return _pupil_prism(side, gm.PUPIL_FIT).intersect(ball(gm.CAP_R))


def _rounded(x, y, z, r):
    """A box (spans) its top and upright edges rounded r."""
    return box(x, y, z).edges(">Z or |Z").fillet(r)


def _head(t):
    """The head's solid (Morty's, the face's eye band over the muzzle) `t` in from its outside."""
    x, (y0, y1), (z0, z1) = sk.HEAD_X - t, sk.HEAD_Y, sk.HEAD_Z
    upper = _rounded((-x, x), (y0 + t, y1 - t), (z0 - 30, z1 - t), sk.ROUND[0] - t)
    muzzle = _rounded((-x, x), (sk.MUZZLE_Y + t, y1 - t), (z0 - 30, sk.MUZZLE_Z - t), sk.ROUND[1] - t)
    return upper.union(muzzle)


def _eyes():
    """What the eyes' openings leave out: round each eye, everything its lids and their covers reach (r 36.3) with
    1.2 mm to spare, ahead of the eye centres and inside the lids' reach across."""
    out = None
    for x, _, _ in gm.EYE.values():
        o = ball(37.5, (x, 0, 0)).intersect(box((-58, 58), (-60, 0), (-40, 40)))
        out = o if out is None else out.union(o)
    return out


def _hair(lift):
    """The hair's region, `lift` mm up: over the hairline at the front back to its y, then down to the back's foot, with
    the bangs' points down to 8 mm under it at the front (between the face's Seats)."""
    z, y = sk.HAIRLINE
    foot = sk.HEAD_Z[0] - 2
    back = y + (z - foot) / (z - sk.HEAD_Z[0]) * (sk.HEAD_Y[1] - y)
    side = [(-100, z), (y, z), (back, foot), (200, foot), (200, 200), (-100, 200)]
    out = cq.Workplane("YZ", origin=(-100, 0, 0)).polyline(side).close().extrude(200)
    for c in (-15.0, 0.0, 15.0):
        bang = cq.Workplane("XZ", origin=(0, -10, 0)).polyline([(c - 7, z), (c + 7, z), (c, z - 8)]).close()
        out = out.union(bang.extrude(40))  # XZ's normal is -y: from y -10 forward through the front
    return out.translate((0, 0, lift))


def _skull():
    """The head's shell (WALL thick, open underneath and at the back under the head mount, for the neck: #838), its eyes'
    openings cut."""
    out = _head(0.0).cut(_head(sk.WALL)).cut(_eyes()).intersect(box((-100, 100), (-100, 100), (sk.HEAD_Z[0], 100)))
    return out.cut(box((-100, 100), (sk.NECK[0], 200), (sk.HEAD_Z[0] - 1, sk.NECK[1])))


def face():
    """Morty's face (face): the head's shell under the hairline, the nose between the eyes, an ear each side and the
    mouth's opening over the mouth cover; forward off the gimbal frame plate's Seats, the hair's Seats on its top."""
    out = _skull().cut(_hair(-0.1))
    # spheres and cylinders alone: a scaled sphere is a B-spline that Linux's OCCT writes into an invalid STEP (#833)
    # the nose under the lower lids, which the eyes 52 mm apart bring in over it (#838)
    out = out.union(ball(5.0, (0, sk.HEAD_Y[0], -27)).cut(box((-10, 10), (sk.HEAD_Y[0] + sk.WALL, 0), (-40, 0))))
    for s in (-1, 1):
        x = sorted(s * c for c in (sk.HEAD_X - sk.WALL, sk.HEAD_X + 6.0))
        ear = cyl("x", (0, 8, -2), 13.0, x).faces(">X" if s > 0 else "<X").edges().fillet(2.0)
        out = out.union(ear.cut(cyl("x", (0, 8, -2), 8.0, sorted(s * c for c in (sk.HEAD_X + 3.0, sk.HEAD_X + 7.0)))))
    out = out.cut(box((-24, 24), (-60, -40), (sk.HEAD_Z[0] - 1, sk.HEAD_Z[0] + 6)))
    for seat in (s for s in sk.SEATS if s.carrier == "next morty face"):  # each a pad on a web from the front wall
        x, y, z = seat.at
        out = out.union(box((x - 3, x + 3), (sk.HEAD_Y[0] + 1, y), (z - seat.pad, z)))
    return _finish("next morty face", out, _head(0.0))


def hair():
    """Morty's hair (hair): the head's shell over the hairline, its bangs jagged; down onto the gimbal frame plate's
    back (#838), each Seat's boss on a web from its back wall, and onto the face's top."""
    out = _skull().intersect(_hair(0.1))
    for seat in (s for s in sk.SEATS if s.shell == "next morty hair" and s.carrier == "next gimbal frame"):
        x, y, z = seat.at
        web = box((x - sk.PAD_R, x + sk.PAD_R), (y, sk.HEAD_Y[1] - 1.0), (z + sk.GAP + 1.0, z + sk.GAP + seat.boss))
        out = out.union(web.intersect(_head(0.0)))
    return _finish("next morty hair", out, _head(0.0))


def mouth_cover():
    """The mouth cover (face), his lower lip and chin: a plate on the jaw's Seat, a wall down in front of the chin
    inside the face, and the chin under the face's foot, flush with its front, which the jaw swings down; up off its
    Seat once the face is off."""
    (seat,) = (s for s in sk.SEATS if s.shell == "next morty mouth cover")
    _, y, z = seat.at
    bottom, foot, inner = sk.HEAD_Z[0] - 6.0, sk.HEAD_Z[0] - 0.5, sk.MUZZLE_Y + sk.WALL + 0.6
    plate = box((-sk.PAD_R - 2, sk.PAD_R + 2), (inner, y + sk.PAD_R), (z + sk.GAP, z + sk.GAP + sk.COVER))
    wall = box((-22, 22), (inner, inner + sk.COVER), (bottom, z + sk.GAP + sk.COVER))
    chin = box((-22, 22), (sk.MUZZLE_Y, -30), (bottom, foot)).edges("not >Z").fillet(2.0)
    return _finish("next morty mouth cover", plate.union(wall).union(chin))


SHIRT_SPLIT = nk.AXIS[0]  # the halves part across the neck's pan axis
SHIRT_TOP = 6.0  # the collar's rise over the shirt's top, round the neck


def shirt(half):
    """The shirt's `half` (front, back) (shirt and collar): a sleeve round the Torso GAP outside its Seats' pads, a
    rim over its walls' top and the collar rising round the neck; each half off its Torso wall's Seats, the front
    forward, the back backward."""
    (x0, x1), (y0, y1), (z0, z1) = base.TORSO
    front = next(s for s in sk.SEATS if s.shell == "next morty shirt front")
    off = y0 - front.at[1] + sk.GAP  # the pads' faces out of the walls, and the Seat's gap
    inner = box((x0 - off, x1 + off), (y0 - off, y1 + off), (z0 + 0.5, z1 + 0.5))
    outer = box(
        (x0 - off - sk.WALL, x1 + off + sk.WALL),
        (y0 - off - sk.WALL, y1 + off + sk.WALL),
        (z0 + 0.5, z1 + 0.5 + sk.WALL),
    )
    hole = box((x0 + 2.0, x1 - 2.0), (y0 + 2.0, y1 - 2.0), (z0, z1 + 20))
    collar = box(
        (x0 + 2.0 - sk.WALL, x1 - 2.0 + sk.WALL),
        (y0 + 2.0 - sk.WALL, y1 - 2.0 + sk.WALL),
        (z1 + 0.5, z1 + 0.5 + sk.WALL + SHIRT_TOP),  # clear of the Torso's lid (#838)
    )
    out = outer.cut(inner).union(collar).cut(hole).edges("|Z").fillet(1.0)
    ys = (y0 - 20, SHIRT_SPLIT - 0.1) if half == "front" else (SHIRT_SPLIT + 0.1, y1 + 20)
    return _finish(f"next morty shirt {half}", out.intersect(box((-80, 80), ys, (z0 - 5, z1 + 30))))
