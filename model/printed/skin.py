"""The Skins (g.SKINS) as CadQuery parts, every Seat and size from model/skin.py. Morty's (#665): the head's face (with
the nose and ears) and hair, the eyeball caps with their jagged pupils keyed in, a cover on each lid, the mouth cover on
the jaw and the shirt's two halves on the Torso. Cansin's (#813), in Rick and Morty style on the same head and Seats:
his short hair tufted on top over higher temples, straight brows, dot pupils in plugs that fill the caps' jagged seats, a
toothy smile on the mouth cover, an open jacket's lapels over the tee and aviators hooked on its neckline. Bart's
(#807), on the same Seats: Morty's head with a flat crown, nine spikes on it, and Cansin's dot pupils. seated()
cuts each Seat into what carries it. Each Shell is drawn in its carrier's frame: the head's, an eye's (the L one's, the R
its mirror) or the Torso's."""

import functools
import math

import cadquery as cq
import numpy as np
from OCP.Approx import Approx_ParametrizationType
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.GeomAPI import GeomAPI_PointsToBSplineSurface
from OCP.gp import gp_Pnt
from OCP.TColgp import TColgp_Array2OfPnt
from scipy.spatial import ConvexHull

from model import base
from model import geometry as g
from model import gimbal as gm
from model import neck as nk
from model import skin as sk
from model.envelopes import box
from model.printed.gimbal import _at as gimbal_at
from model.printed.gimbal import ball, cyl


def _at(seat):
    """The Seat's frame in its carrier's: z out of the carrier's face along the normal, origin on that face."""
    n = seat.normal
    ref = (1, 0, 0) if abs(n[0]) < 0.9 else (0, 1, 0)
    return g.align_rows(seat.at, ref, n)


def _placed(shape, seat):
    # moved rigidly: transformGeometry's B-spline copies of the balls never finished a union with the head's surface
    return cq.Workplane().add(shape.val().moved(gimbal_at(_at(seat))))


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
        for seat in {(s.at, s.normal, s.pad): s for s in mine}.values():  # each Skin's on the same Seats: cut once
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


def lid_cover(skin, side, lid):
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
    return _finish(f"{skin} {side} {lid} lid cover", out)


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


def _head(t, skin="morty"):
    """The Skin's head (model/skin.py HEADS, else Morty's) `t` in from its outside (out of it, negative): one smooth
    surface through Morty's rings (model/skin.py head_grid) closed by a flat floor under the head's own (#850), and on
    Bart's a prism round his crown (_crown). Each call its own copy of the one built: a Shell built again on Linux's OCCT,
    over shapes an earlier build's booleans had used, came out broken (four solids, a 200 mm clip box left in; #838)."""
    return cq.Workplane().add(_built_head(t, skin if skin in sk.HEADS else "morty").copy())


def _wall(t, skin="morty"):
    """The head's wall, from `t` in from its outside to WALL in: built between its two surfaces, since OCCT cut one
    head out of the other broken (two solids, a sliver left)."""
    return cq.Workplane().add(_built_wall(t, skin if skin in sk.HEADS else "morty").copy())


def _wire(ring):
    return cq.Wire.assembleEdges([cq.Edge.makeSpline([cq.Vector(*p) for p in ring], periodic=True)])


@functools.cache
def _side(t):
    """The head's surface `t` in: one periodic cubic through every ring's points (head_grid), bottom up to the apex,
    its lowest ring flat at the outside's, so a plane closes it (a loft through the rings cut by a plane came out
    broken)."""
    rings = sk.head_grid(t)[::-1]
    rings[0, :, 2] = sk.RINGS[-1, 0]
    pts = TColgp_Array2OfPnt(1, rings.shape[1], 1, len(rings) + 1)
    for j, ring in enumerate(rings):
        for i, p in enumerate(ring):
            pts.SetValue(i + 1, j + 1, gp_Pnt(*map(float, p)))
    for i in range(rings.shape[1]):
        pts.SetValue(i + 1, len(rings) + 1, gp_Pnt(0.0, sk.APEX[0], sk.APEX[1] - t))
    fit = GeomAPI_PointsToBSplineSurface()
    fit.Interpolate(pts, Approx_ParametrizationType.Approx_Centripetal, True)
    return cq.Face(BRepBuilderAPI_MakeFace(fit.Surface(), 1e-6).Face())


def _rim(face):
    return cq.Wire.assembleEdges([min(face.Edges(), key=lambda e: e.Center().z)])


BART_UP = 0.1  # Bart's flat crown over Morty's apex: touching it, OCCT's fuse failed


def _crown(t):
    """Bart's crown, `t` in: a prism round every ring from 5 mm over the widest (WIDEST) up to BART_UP over the apex,
    0.5 mm out, so it holds Morty's crown."""
    rings = sk.head_grid(t)[: sk.WIDEST + 1, :, :2].reshape(-1, 2)
    hull = rings[ConvexHull(rings).vertices]
    out = hull - hull.mean(axis=0)
    hull = hull + 0.5 * out / np.linalg.norm(out, axis=1)[:, None]
    z = sk.RINGS[sk.WIDEST, 0] + 5.0
    face = cq.Face.makeFromWires(_wire(np.c_[hull, np.full(len(hull), z)]))
    return cq.Workplane().add(cq.Solid.extrudeLinear(face, cq.Vector(0, 0, sk.HEAD_Z[1] + BART_UP - t - z)))


@functools.cache  # every Shell cuts and clips by the same few
def _built_head(t, skin):
    side = _side(t)
    head = cq.Workplane().add(cq.Solid.makeSolid(cq.Shell.makeShell([side, cq.Face.makeFromWires(_rim(side))])).fix())
    return (head.union(_crown(t)) if skin == "bart" else head).val()


@functools.cache
def _built_wall(t, skin):
    outer, inner = _side(t), _side(sk.WALL)
    floor = cq.Face.makeFromWires(_rim(outer), [_rim(inner)])
    wall = cq.Workplane().add(cq.Solid.makeSolid(cq.Shell.makeShell([outer, inner, floor])).fix())
    if skin == "bart":  # Morty's wall less the crown's inside, and the crown's wall outside Morty's inside
        wall = wall.cut(_crown(sk.WALL)).union(_crown(t).cut(_crown(sk.WALL)).cut(_head(sk.WALL)))
    return wall.val()


# the eyes' openings: a ball's radius round each eye, and how far from the midline they reach
EYES = (gm.LOWER_R[1] + sk.GAP + sk.COVER + 2.0, gm.SPACING / 2 + gm.LID_X["lower boss"][1] + 4.0)


def _eyes():
    """What the eyes' openings leave out: round each eye, everything its lids and their covers reach with 2 mm to
    spare, ahead of the eye centres and inside the lids' reach across."""
    out = None
    r, across = EYES
    for x, _, _ in gm.EYE.values():
        o = ball(r, (x, 0, 0)).intersect(box((-across, across), (-r - 5, 5), (-r, r)))
        out = o if out is None else out.union(o)
    return out


# Cansin's likeness (#813), every size ours and inferred: his higher temples, each a ball ((|x|, y, z), r) the face takes
# from the hair; each brow's (|x|, z) span over its eye, sunk into the face and standing proud of it; his dot pupils'
# radius and depth in their plugs; his teeth's x and z span on the chin's top front, how deep they reach back and each
# tooth's width; his lapels' proud; and the L aviator lens' outline (x, z) round the bridge's Seat
TEMPLES = ((sk.head_x(3.0, 57.0) + 14.0, 3.0, 57.0), 20.0 * sk.GROW)  # 16 mm into the head's side, as first drawn
BROW, BROW_SUNK, BROW_PROUD = (sk.grown(12.0, 40.0), sk.grown(41.0, 45.0)), 1.0, 1.5
DOT = (3.0, 2.0)
# the teeth across the jaw's chin, grown with it (model/neck.py JAW_K)
TEETH, TOOTH = ((-18.0 * nk.JAW_K, 18.0 * nk.JAW_K), (-77.5, -75.0), 3.0), 6.0
LAPEL_PROUD = 1.2
LENS = ((3.0, 4.0), (26.0, 5.0), (28.0, -2.0), (22.0, -10.0), (12.0, -11.0), (5.0, -4.0))


def _hair(grow, skin="morty"):
    """The hair's region (model/skin.py outline("hairline"), NAPE), `grow` mm out of it; Cansin's less his temples."""
    # sampled every 5 mm: within 0.1 mm of the curve, with few enough planes for OCCT's booleans (#992)
    side = (
        cq.Workplane("YZ", origin=(-200, 0, 0))
        .polyline([tuple(p) for p in sk.outline("hairline", sk.FACE_Y, 5.0)])
        .close()
    )
    out = side.offset2D(grow, "intersection").extrude(400).union(box((-200, 200), (sk.NAPE - grow, 300), (-300, 300)))
    if skin == "cansin":
        (x, ty, tz), tr = TEMPLES
        for s in (-1, 1):
            out = out.cut(ball(tr - grow, (s * x, ty, tz)))
    return out


def _skull(t, skin="morty"):
    """The head's shell, from `t` in from its outside (out of it, negative) to WALL in, its eyes' openings cut, its
    floor open round the neck and the jaw (NECK), its back closed down to the floor (#850)."""
    x, up = sk.NECK
    neck = box((-x, x), (-200, 300), (sk.HEAD_Z[0] - 5, sk.HEAD_Z[0] + up))
    out = _wall(t, skin).cut(_eyes()).cut(neck)
    return out.intersect(box((-200, 200), (-200, 200), (sk.HEAD_Z[0], 200)))


def _ear(s):
    """The `s` (1 L, -1 R) ear (model/skin.py EAR): a dome out of the head's side, its hollow (the concha) open forward,
    so it reads as his C."""
    y, z, r, out = sk.EAR
    cheek = sk.head_x(y, z)
    x = cheek + out - r

    def on_x(
        radius, at
    ):  # a ball its poles on x, its seam off the cheek's cut: OCCT cuts a ball across its seam to nothing
        return cq.Workplane().add(cq.Solid.makeSphere(radius, cq.Vector(*at), cq.Vector(1, 0, 0), -90, 90))

    ear = on_x(r, (x, y, z)).cut(box((0, cheek - 6.0), (-200, 200), (-200, 200)))
    ear = ear.cut(on_x(r - 4.0, (x + 6.0, y - 4.0, z)))
    return ear if s > 0 else ear.mirror("YZ")


def face(skin="morty"):
    """The face (face): the head's shell under the hairline, the nose between the eyes, an ear each side and the
    mouth's opening over the mouth cover; forward off the gimbal frame plate's Seats, the hair's Seats on its temples.
    Cansin's: his temples higher, a pocket over each eye for his brow."""
    out = _skull(0.0, skin).cut(_hair(0.1, skin))
    r, z, back = sk.NOSE
    front = sk.head_front(0.0, z)
    out = out.union(ball(r, (0, front + back, z)).cut(box((-r, r), (front + sk.WALL, 100), (z - r, z + r))))
    for s in (-1, 1):
        out = out.union(_ear(s).cut(_head(sk.WALL, skin)))
    y0 = sk.HEAD_Y[0]
    out = out.cut(_mouth())
    for seat in (s for s in sk.SEATS if s.carrier == f"{skin} face"):  # each a pad on a web from the forehead
        x, y, z = seat.at
        out = out.union(box((x - 3, x + 3), (y0, y), (z - seat.pad, z)).intersect(_head(sk.WALL / 2, skin)))
    if skin == "cansin":
        for s in "LR":
            out = out.cut(_brow(s, gm.PUPIL_FIT, BROW_SUNK + gm.PUPIL_FIT))
    # clipped mid-wall: a boss ending on the face's own outside, OCCT's union of the two never finished
    return _finish(f"{skin} face", out, _head(sk.WALL / 2, skin))


# Cansin's tufts on top (#813): balls (x, y, z, r) over the hairline's front, the head's top 1.5 mm proud at most
# (model/printed/test_skin.py), so they stand out of its forward slope as a short quiff
TUFTS = tuple(
    sk.grown(*t)
    for t in (
        (0.0, -4.0, 59.0, 10.0),
        (-17.0, -1.0, 58.0, 10.0),
        (17.0, -1.0, 58.0, 10.0),
        (-9.0, 8.0, 61.0, 8.5),
        (9.0, 8.0, 61.0, 8.5),
    )
)


# Bart's spikes (#807): nine cones round a ring (centre y, half-width, half-depth) inside his flat crown, each (base
# radius, height) over the crown's top (inferred)
SPIKES, SPIKE = sk.grown(36.5, 40.0, 22.0), sk.grown(8.0, 18.0)


def _spikes():
    y, a, b = SPIKES
    r, h = SPIKE
    top = sk.HEAD_Z[1] - sk.WALL  # each base in the crown's wall, so it fuses with it and stays out of the head
    at = [cq.Vector(a * math.sin(2 * math.pi * k / 9), y - b * math.cos(2 * math.pi * k / 9), top) for k in range(9)]
    cones = (cq.Workplane().add(cq.Solid.makeCone(r, 0.0, h + sk.WALL, p, cq.Vector(0, 0, 1))) for p in at)
    return functools.reduce(lambda u, c: u.union(c), cones)


def hair(skin="morty"):
    """The hair (hair): the head's shell over the hairline and behind the nape, HAIR proud of the face; down onto the
    cranium tray's back corners and onto the face over the eyes, each Seat's boss straight up into it.
    Cansin's: short, his temples higher, tufted on top (TUFTS). Bart's (#807): his crown, flush with his face, its
    spikes on."""
    out = _skull(0.0 if skin == "bart" else -sk.HAIR, skin).intersect(_hair(-0.1, skin))
    if skin == "bart":
        out = out.union(_spikes())
    if skin == "cansin":
        face = _head(0.0).cut(_hair(-0.1, skin))  # the face's, under the hairline
        top = box((-200, 200), (-200, 200), (-200, sk.HEAD_Z[1] + sk.HAIR))
        # the tufts as one first: unioned one by one, OCCT failed on the second over the hairline's many planes (#992)
        tufts = functools.reduce(lambda u, b: u.union(b), (ball(r, (x, y, z)) for x, y, z, r in TUFTS))
        out = out.union(tufts.cut(face).cut(_head(sk.WALL)).intersect(top))
    return _finish(f"{skin} hair", out, _head(0.0, skin))


# The mouth (#850): the face open over the chin within MOUTH's half-width and from its front back to MOUTH's y, from
# the floor up over the jaw's Seat, where the mouth cover is the head's shell; GAP_MM round it
MOUTH = (24.0 * sk.GROW, sk.HEAD_Y[0] + 25.0, nk.JAW_ARM_Z[1] + sk.GAP + sk.COVER + 1.0)
GAP_MM = 0.5


def _mouth(gap=0.0):
    x, y, z = MOUTH
    return box((-x + gap, x - gap), (sk.HEAD_Y[0] - 11.0, y - gap), (sk.HEAD_Z[0] - 1.0, z - gap))


def mouth_cover(skin="morty"):
    """The mouth cover (face), the lower lip and chin: the head's shell in the face's mouth opening, GAP_MM inside it,
    and a plate on from it over the jaw's Seat, which the jaw swings down; up off its Seat once the face is off.
    Cansin's: his teeth's pocket in the chin's top front."""
    (seat,) = (s for s in sk.SEATS if s.shell == f"{skin} mouth cover")
    _, y, z = seat.at
    plate = box((-sk.PAD_R - 2, sk.PAD_R + 2), (sk.HEAD_Y[0], y + sk.PAD_R), (z + sk.GAP, z + sk.GAP + sk.COVER))
    chin = _wall(0.0).intersect(_mouth(GAP_MM))
    out = plate.intersect(_head(0.0)).union(chin).intersect(box((-200, 200), (-200, 200), (sk.HEAD_Z[0], 200)))
    return _finish(f"{skin} mouth cover", out.cut(_teeth(gm.PUPIL_FIT)) if skin == "cansin" else out)


SHIRT_SPLIT = nk.AXIS[0]  # the halves part across the neck's pan axis
SHIRT_TOP = 6.0  # the collar's rise over the shirt's top, round the neck
SHIRT_ROUND = (10.0, 3.0, 25.0)  # his T-shirt's rounding: its sides, its shoulders, and the crew neck's corners


def shirt(skin, half):
    """The shirt's `half` (front, back) (shirt and collar), his T-shirt: a sleeve round the Torso GAP outside its Seats'
    pads, its sides and shoulders rounded, a rim over its walls' top and the round crew neck's collar rising round the
    neck; each half off its Torso wall's Seats, the front forward, the back backward."""
    (x0, x1), (y0, y1), (z0, z1) = base.TORSO
    sides, shoulders, neck = SHIRT_ROUND
    front = next(s for s in sk.SEATS if s.shell == f"{skin} shirt front")
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
    out = out.intersect(box((-80, 80), ys, (z0 - 5, z1 + 30)))
    if skin == "cansin" and half == "front":  # the open jacket's lapels over the tee, a V down from its shoulders
        y = sk.SHIRT_FRONT
        for s in (-1, 1):
            lapel = [(s * x, z) for x, z in LAPEL]
            out = out.union(cq.Workplane("XZ", origin=(0, y + 0.1, 0)).polyline(lapel).close().extrude(LAPEL_PROUD))
    return _finish(f"{skin} shirt {half}", out)


# Cansin's open jacket (#813): each lapel's outline on the shirt's front (x, z), its L one, standing LAPEL_PROUD proud
LAPEL = (
    (50.0, -145.0),
    (40.0, -145.0),
    (16.0, -175.0),
    (26.0, -175.0),
)  # 22 mm under #978's lower Torso, its slope kept


def pupil_plug(side):
    """Cansin's `side` pupil plug (eye whites): the cap's jagged seat filled, PUPIL_FIT smaller each side, flush with
    its dome, the dot's seat sunk in its middle; glued in."""
    return _pupil_prism(side, gm.PUPIL_FIT).intersect(ball(gm.CAP_R)).cut(_dot(side, gm.PUPIL_FIT))


def dot(side):
    """Cansin's `side` pupil (pupils): a small round dot in its plug, flush with the cap's dome; glued in."""
    return _dot(side).intersect(ball(gm.CAP_R))


def _dot(side, grow=0.0):
    """The dot, `grow` mm larger round and deeper: DOT[0] round its pupil's middle, DOT[1] deep from its
    front."""
    r, deep = DOT
    x = (-1 if side == "L" else 1) * gm.CAP_R * math.sin(math.radians(gm.TOE_IN))
    return cyl("y", (x, 0, 0), r + grow, (-gm.CAP_R - 1.0, -gm.CAP_R + deep + grow))


def _brow(side, grow=0.0, sunk=BROW_SUNK):
    """Cansin's `side` brow over its eye (BROW), `grow` mm larger round, from `sunk` mm into the face out to
    BROW_PROUD proud of it, in the head's frame."""
    (x0, x1), (z0, z1) = BROW
    s = 1 if side == "L" else -1
    xs = sorted((s * (x0 - grow), s * (x1 + grow)))
    region = box(xs, (-200, 0), (z0 - grow, z1 + grow)).intersect(_head(-BROW_PROUD))
    return region.cut(_head(sunk))


def brow(side):
    """Cansin's `side` brow (hair): straight and dark, over its eye, sunk in its pocket in the face; glued in. Drawn in
    its eye's frame, which places it."""
    x, y, z = gm.EYE[side]
    return _brow(side).translate((-x, -y, -z))


def _teeth(grow=0.0):
    """Cansin's teeth, `grow` mm larger round: the chin's top front band (TEETH), flush with the head's outline."""
    (x0, x1), (z0, z1), deep = TEETH
    y0 = sk.head_front(0.0, (z0 + z1) / 2)
    return box((x0 - grow, x1 + grow), (y0 - 1.0, y0 + deep + grow), (z0 - grow, z1 + grow)).intersect(_head(0.0))


def teeth():
    """Cansin's teeth (eye whites), his toothy smile: a white band in the chin's top front, a groove between each
    tooth; glued in its pocket in the mouth cover, which the jaw swings down."""
    out, (x0, x1) = _teeth(), TEETH[0]
    for x in np.arange(x0 + TOOTH, x1 - 1.0, TOOTH):
        y0 = sk.head_front(0.0, sum(TEETH[1]) / 2)
        out = out.cut(box((x - 0.4, x + 0.4), (y0 - 2.0, y0 + 0.6), (-200, 200)))
    return out


def sunglasses():
    """Cansin's aviators (accessories), hooked on the tee's neckline: two teardrop lenses and a bar over the bridge,
    sk.COVER thick, GAP off the shirt front, on its bridge's Seat."""
    (seat,) = (s for s in sk.SEATS if s.shell == "cansin sunglasses")
    x, y, z = seat.at
    back, front = y - sk.GAP, y - sk.GAP - sk.COVER
    out = cyl("y", (x, 0, z), sk.PAD_R, (front, back))
    for s in (-1, 1):
        lens = cq.Workplane("XZ", origin=(0, back, 0)).polyline([(s * u, v + z) for u, v in LENS]).close()
        out = out.union(lens.extrude(sk.COVER).edges("|Y").fillet(2.0))
    bar = box((-LENS[1][0], LENS[1][0]), (front, back), (z + 4.0, z + 6.0))
    return _finish("cansin sunglasses", out.union(bar))
