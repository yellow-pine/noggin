"""The next Mech's eye gimbal (#630) as CadQuery parts, every size from model/gimbal.py (its frame and its design).
Parts at one eye are drawn about the L eye's centre (the R one's mirror where it differs); the rest in the gimbal's
frame. Bores take the busy pivots' M3 steel shanks; each push-rod's cups close on a ball under its equator."""

import functools
import math

import cadquery as cq
import mujoco
import numpy as np
from OCP.gp import gp_Trsf
from scipy.spatial import ConvexHull

from model import envelopes, fits, gates, neck
from model import gimbal as gm
from model.envelopes import box
from model.printed import bone

LEVER_R, NECK_R, CUP_R, ARM = 2.5, 1.2, gm.BALL_R + 1.5, 6.0  # ARM: every printed arm's width
# the Bones' (head, waist) as (semi-width, height): the tie-bar's heads flattened to its 3 mm slab, each push-rod's
# inside its cups and within CUP_R of the line between the balls (the lids' clearance, gimbal.report, reads it so)
TIE_BONE, ROD_BONE = ((4.5, 4.2), (2.2, 2.6)), ((3.6, 5.5), (2.4, 4.0))
MM = 0.001  # MuJoCo's metres per mm
CAP_BACK = gm.CAP_R * math.cos(math.radians(gm.CAP_HALF))  # the cap's flat back, on the core's seat


def cyl(axis, centre, r, span):
    """A cylinder along x, y or z through `centre` (the other two coordinates), from span[0] to span[1]."""
    i = "xyz".index(axis)
    lo = list(centre)
    lo[i] = span[0]
    d = [0, 0, 0]
    d[i] = 1
    return cq.Workplane().add(cq.Solid.makeCylinder(r, span[1] - span[0], cq.Vector(*lo), cq.Vector(*d)))


def ball(r, at=(0, 0, 0)):
    return cq.Workplane().add(cq.Solid.makeSphere(r, cq.Vector(*at), angleDegrees1=-90, angleDegrees2=90))


def ball_on(base, at):
    """A ball on a neck up from z `base` to its centre `at`: the push-rod's cup closes round it from above."""
    x, y, z = at
    return ball(gm.BALL_R, at).union(cyl("z", (x, y, 0), NECK_R, (base, z)))


def core():
    """The eyeball core: a ball, the seat its cap sits on (forward), the lever up the yaw axis to its ball, and the
    pitch axle's bores along x."""
    top = gm.LEVER - gm.BALL_R - 1.2
    out = ball(gm.CORE_R).union(cyl("y", (0, 0, 0), gm.SEAT_R, (-CAP_BACK, -gm.CORE_R + 3)))
    out = out.union(cyl("z", (0, 0, 0), LEVER_R, (gm.CORE_R - 3, top))).union(ball_on(top, (0, 0, gm.LEVER)))
    for s in (-1, 1):
        out = out.cut(cyl("x", (0, 0, 0), gm.PIN_R, sorted((s * 8.0, s * (gm.CORE_R + 1)))))
    return out


def cap(side):
    """The largest eyeball cap (a Shell): the sphere segment within CAP_HALF of the gaze, flat on its seat, with the
    pupil's seat 1 mm deep, its centre turned TOE_IN toward the other eye."""
    r = gm.CAP_R
    out = ball(r).intersect(box((-r, r), (-r - 1, -CAP_BACK), (-r, r)))
    inward = -1 if side == "L" else 1
    seat_r = r * math.sin(math.radians(gm.PUPIL_DEG))
    seat = cyl("y", (inward * r * math.sin(math.radians(gm.TOE_IN)), 0, 0), seat_r, (-r - 1, -r + 1))
    return out.cut(seat)


def yoke():
    """The yaw yoke: a U from below round the core, the pitch axle's bores through its arms, the stem down the yaw axis
    with its crank (back) on the tie-bar."""
    y = gm.YOKE
    x0, x1, h = y["inner"], y["inner"] + y["wall"], y["half_y"]
    out = box((-x1, x1), (-h, h), (-x1, -x0))
    for s in (-1, 1):
        xs = sorted((s * x0, s * x1))
        out = out.union(box(xs, (-h, h), (-x1, 0))).union(cyl("x", (0, 0, 0), h, xs))
        out = out.cut(cyl("x", (0, 0, 0), gm.PIN_R, xs))
    out = out.union(cyl("z", (0, 0, 0), y["stem_r"], (y["stem_z"], -x1)))
    z = gm.YAW_CRANK_Z
    out = out.union(box((-ARM / 2, ARM / 2), (0, gm.CRANK), z)).union(cyl("z", (0, gm.CRANK, 0), ARM / 2, z))
    out = out.cut(cyl("z", (0, gm.CRANK, 0), gm.PIN_R, z))
    return out.cut(cyl("z", (0, 0, 0), gm.PIN_R, (y["stem_z"], y["stem_z"] + 8)))


def tie_bar():
    """The tie-bar under the yokes' cranks: a Bone (model/printed/bone.py) from each eye's pin back to the yaw horn's,
    one parallelogram, flat on top within its slab where the cranks ride on it."""
    c, horn = gm.EYE["L"][0], (0.0, gm.YAW_Y + gm.CRANK, gm.TIE_Z[0])
    slab = box((-c - ARM, c + ARM), (0, horn[1] + ARM), (gm.TIE_Z[0] - 1, gm.TIE_Z[1]))  # past the bed: no shared face
    arms = [bone.bone((x, gm.CRANK, gm.TIE_Z[0]), horn, *TIE_BONE).intersect(slab) for x in (-c, c)]
    out = arms[0].union(arms[1])  # clipped first: the two heads on the horn's pin, fused unclipped, clip invalid
    for x, y, _ in ((-c, gm.CRANK, 0), (c, gm.CRANK, 0), horn):
        out = out.cut(cyl("z", (x, y, 0), gm.PIN_R, (gm.TIE_Z[0] - 1, gm.TIE_Z[1] + 1)))
    return out


def bail():
    """The bail: its rod on an x axis behind the eyes, an arm up to a ball behind each eye, the input arm back to the
    pitch bar's pin, the shanks' bores in its ends."""
    by, bz = gm.BAIL
    end, top = gm.EYE["L"][0] + 8.0, gm.LEVER - gm.BALL_R - 1.2
    out = cyl("x", (0, by, bz), 3.0, (-end, end))
    for s in (-1, 1):
        x = s * gm.EYE["L"][0]
        out = out.union(box((x - 1.5, x + 1.5), (by - ARM / 2, by + ARM / 2), (bz, top)))
        out = out.union(ball_on(top, (x, by, gm.LEVER)))
        out = out.cut(cyl("x", (0, by, bz), gm.PIN_R, sorted((s * end, s * (end - 8)))))
    tip = by + gm.BAIL_IN
    out = out.union(box((-2, 2), (by, tip), (bz - 3, bz + 3))).union(cyl("x", (0, tip, bz), 3.0, (-2, 2)))
    return out.cut(cyl("x", (0, tip, bz), gm.PIN_R, (-2, 2)))


def push_rod():
    """One push-rod (drawn at x 0): a Bone back from the lever's ball to the bail arm's on its cups' rims, a cup round
    each ball."""
    z, back = gm.LEVER, gm.BAIL[0]
    out = bone.bone((0, 0, z - 2), (0, back, z - 2), *ROD_BONE)
    for y in (0.0, back):
        out = out.union(ball(CUP_R, (0, y, z)).cut(box((-CUP_R, CUP_R), (y - CUP_R, y + CUP_R), (z - CUP_R, z - 2))))
    for y in (0.0, back):
        out = out.cut(ball(gm.BALL_R + 0.1, (0, y, z)))
    return out


def link(a, b, x):
    """A flat bar in the slab `x` with pin holes along x at the (y, z) points a and b."""
    w = ARM / 2
    side = np.array([a[1] - b[1], b[0] - a[0]]) * w / math.dist(a, b)
    outline = [tuple(map(float, p)) for p in (a + side, b + side, b - side, a - side)]
    out = cq.Workplane("YZ", origin=(x[0], 0, 0)).polyline(outline).close().extrude(x[1] - x[0])
    for y, z in (a, b):
        out = out.union(cyl("x", (0, y, z), w, x)).cut(cyl("x", (0, y, z), gm.PIN_R, x))
    return out


def pitch_bar():
    hy, hz = gm.PITCH_HORN
    return link((hy + gm.CRANK, hz), (gm.BAIL[0] + gm.BAIL_IN, gm.BAIL[1]), gm.PITCH_BAR_X)


def lid_bar():
    """One lid's bar (drawn centred on x 0): the lid's crank back to its horn, behind the eye."""
    w = (gm.LID_X["bar"][1] - gm.LID_X["bar"][0]) / 2
    return link(gm.LID_PIN, tuple(np.add(gm.LID_HORN, gm.LID_PIN)), (-w, w))


def lid(side):
    """The `side` lid (drawn for L, the R its mirror): a shell wedge about x through the eye centre, its lower edge at LID_REST and LID_SPAN wide, the boss
    on its outboard pole turning on the frame's shank, and the crank back to its bar."""
    ri, ro = gm.LID_R
    arc = np.radians(np.linspace(gm.LID_REST, gm.LID_REST + gm.LID_SPAN, 24))
    fan = [(0.0, 0.0)] + [(-(ro + 5) * math.cos(a), (ro + 5) * math.sin(a)) for a in arc]
    wedge = cq.Workplane("YZ", origin=(-ro - 1, 0, 0)).polyline(fan).close().extrude(2 * ro + 2)
    out = ball(ro).cut(ball(ri)).intersect(wedge)
    bx, cx, pin = gm.LID_X["boss"], gm.LID_X["crank"], (0, *gm.LID_PIN)
    out = out.union(cyl("x", (0, 0, 0), 4.0, bx)).union(link((0.0, 0.0), gm.LID_PIN, cx))
    out = out.cut(cyl("x", pin, gm.PIN_R, cx)).cut(cyl("x", (0, 0, 0), gm.PIN_R, (bx[0] + 2, bx[1])))
    return out if side == "L" else out.mirror("YZ")


def frame():
    """The gimbal frame (Skeleton): a plate under everything, the yaw bearings under the yokes' stems, the bail's and
    the lids' uprights with the shanks' bores, a collar on posts round each servo at its tab plate, and the holes the
    head mount (model/printed/neck.py) is screwed up through."""
    c, top = gm.EYE["L"][0], gm.PLATE_Z[1]
    by, bz = gm.BAIL
    edge = c + gm.LID_X["upright"][1]
    out = box((-edge, edge), gm.PLATE_Y, gm.PLATE_Z)
    for s in (-1, 1):
        stem = gm.YOKE["stem_z"]
        out = out.union(cyl("z", (s * c, 0, 0), 5.0, (top, stem))).cut(
            cyl("z", (s * c, 0, 0), gm.PIN_R, (stem - 8, stem))
        )
        bx = sorted((s * (c + 8), s * (c + 12)))
        out = out.union(box(bx, (by - 4, by + 4), (top, bz + 4))).cut(cyl("x", (0, by, bz), gm.PIN_R, bx))
        ux = sorted(s * (c + u) for u in gm.LID_X["upright"])
        out = out.union(box(ux, (-4, 4), (top, 4)))
        out = out.cut(cyl("x", (0, 0, 0), gm.PIN_R, ux))
    for x, y in neck.HEAD_SCREWS:  # the head mount's screws (model/printed/neck.py)
        out = out.cut(cyl("z", (x, y, 0), 1.7, gm.PLATE_Z))
    for face, shaft, tab, _ in gm.drives().values():
        out = out.union(collar(gm.servo_matrix(face, shaft, tab), top))
    return out


def collar(m, floor):
    """A plate round the servo's case under its tab plate, with its two screw holes, on a post under each hole down
    (or up) to `floor`."""
    s = envelopes.SERVO
    (x0, x1), (y0, y1), _ = s["case"]
    (tx0, tx1), (ty0, ty1), _ = s["tabs"]
    local = box((tx0 - 2, tx1 + 2), (ty0 - 2, ty1 + 2), (0, 3)).cut(
        box((x0 - 0.3, x1 + 0.3), (y0 - 0.3, y1 + 0.3), (0, 3))
    )
    for hx, hy in s["tab_holes"]:
        local = local.cut(cq.Workplane("XY").circle(s["tab_r"]).extrude(3).translate((hx, hy, 0)))
    out = _moved(local, m)
    for hx, hy in s["tab_holes"]:
        corners = [(hx + a, hy + b, z) for a in (-2.4, 2.4) for b in (-2.4, 2.4) for z in (0, 3)]
        w = (m @ np.c_[corners, np.ones(8)].T)[:3].T
        lo, hi = w.min(axis=0), w.max(axis=0)
        out = out.union(box((lo[0], hi[0]), (lo[1], hi[1]), (floor, hi[2]) if floor < lo[2] else (lo[2], floor)))
    return out


def _moved(shape, m):
    t = cq.Matrix([list(map(float, row)) for row in m[:3]])
    return cq.Workplane().add(shape.val().transformGeometry(t))


def at_rest():
    """{next-eyes part: its solid where model/stages.py places it}, each lid's pivot shank beside them (the M3 steel
    shank from the frame's upright through the lid's boss)."""
    from model import stages
    from model.printed import PARTS  # here: model.printed imports this module

    out = {}
    for name, p in stages.next_eyes().parts.items():
        stem = stages.stem(p.file)
        out[name] = (PARTS.get(stem) or envelopes.ENVELOPES[stem])().val().moved(_at(p.matrix))
    for s, sign in (("L", 1), ("R", -1)):
        x = sorted(gm.EYE[s][0] + sign * u for u in (gm.LID_X["boss"][0] + 2, gm.LID_X["upright"][1]))
        out[f"next {s} lid shank"] = cyl("x", (0, 0, 0), gm.PIN_R - fits.CLEARANCE[0], x).val()
    return out


# the parts moved() carries by a pin on another moving part: each turns on that part's pin
COUPLED = {
    **{f"next {s} lid bar:1": f"next {s} lid horn:1" for s in "LR"},
    **{f"next {s} push-rod:1": "next bail:1" for s in "LR"},
    "next pitch bar:1": "next pitch horn:1",
}


def _turn(m):
    """Radians a 4x4 turns about x."""
    return math.atan2(m[2, 1], m[1, 1])


def skeleton(rest, tol=0.1):
    """The gimbal as hinges for gates.certify (#655), in metres: a body per part in `rest`, its pieces a ball of `tol`
    mm on each corner of its tessellation's hull (the surface strays from it by `tol` at most), each part moved() turns
    hinged about x through the point its turn fixes (a COUPLED part on the part that carries it), the parts that turn
    alike about one line on one hinge; and rows(poses), a qpos row per (lid, pitch). Every move at yaw 0 turns about x."""
    probe = gm.moved(-30.0, 10.0)  # a pose that turns every hinge
    s, bodies, hinged, carrier = mujoco.MjSpec(), {}, {}, {}  # hinged: (carrier, line, turn) -> the hinge's part

    def add(name):
        if name not in bodies:
            parent = COUPLED.get(name)
            host = add(parent) if parent else s.worldbody
            if name in probe:
                rel = np.linalg.inv(probe[parent]) @ probe[name] if parent else probe[name]
                y, z = np.linalg.solve(np.eye(2) - rel[1:3, 1:3], rel[1:3, 3])  # the point the turn fixes
                key = (carrier.get(parent), round(y, 6), round(z, 6), round(_turn(rel), 9), " lid" in name)
                carrier[name] = hinged.setdefault(key, name)
                if carrier[name] != name:  # the hinge of a part that turns alike carries it
                    host = bodies[carrier[name]]
            body = bodies[name] = host.add_body(name=name)
            if carrier.get(name) == name:
                body.add_joint(type=mujoco.mjtJoint.mjJNT_HINGE, axis=[1, 0, 0], pos=[0, y * MM, z * MM])
            v = np.array([p.toTuple() for p in rest[name].tessellate(tol)[0]])
            for corner in v[ConvexHull(v).vertices]:
                body.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[tol * MM, 0, 0], pos=corner * MM)
        return bodies[name]

    for name in rest:
        add(name)
    model = s.compile()
    # a lid part turns with the lid servo alone, every other with the pitch alone (moved())
    lid_m, pitch_m = functools.cache(lambda lid: gm.moved(lid, 0.0)), functools.cache(lambda p: gm.moved(0.0, p))

    def rows(poses):
        qpos = np.zeros((len(poses), model.nq))
        for i, (lid, pitch) in enumerate(poses):
            for name in hinged.values():
                m = lid_m(lid) if " lid" in name else pitch_m(pitch)
                turn = _turn(m[name]) - (_turn(m[COUPLED[name]]) if name in COUPLED else 0.0)
                qpos[i, model.jnt_qposadr[model.body(name).jntadr[0]]] = turn
        return qpos

    return model, rows


def _path(segments, step):
    """(lid, pitch) rows `step` deg apart along the segments in turn, each joined straight to the next."""
    ends = [e for s in segments for e in s]
    rows = [ends[0]]
    for a, b in zip(ends, ends[1:]):
        rows += list(np.linspace(a, b, max(1, math.ceil(np.abs(np.subtract(b, a)).max() / step)) + 1)[1:])
    return np.round(rows, 6)  # a value shared by two lines reads the same


def sweep(n_lid=9, n_pitch=7, within=5.0, step=0.1):
    """The lid drives' sweep (#650): each lid, its bar, its horn and its shank against every other part over the lid x
    pitch grid (both lid servos together, yaw 0; model/gimbal.py moved()). Every pair at least LID_CLEAR_MM apart at rest
    is certified to stay so along the grid's lines that turn it (#655, lines(): gates.certify on skeleton()'s hinges,
    reading the exact solids, the bounding boxes' gap past `within` mm), rows `step` deg apart; the closest it read is
    reported. Every pair closer at rest (a pin, a face sliding on a face, the boss on its shank) is checked for overlap
    at the grid's samples: every move here turns about x, so one of two lifts 0.01 mm along x parts a pair that only
    touches."""
    rest = at_rest()
    drives = [f"next {s} {n}" for s in "LR" for n in ("lid:1", "lid bar:1", "lid horn:1", "lid shank")]
    spline = {(f"next {s} lid horn:1", f"next {s} lid servo:1") for s in "LR"}  # the horn's hub on its spline
    pairs = [(a, b) for i, a in enumerate(drives) for b in rest if b not in drives[: i + 1] and (a, b) not in spline]
    near = {(a, b) for a, b in pairs if _gap(rest[a], rest[b]) < gm.LID_CLEAR_MM > rest[a].distance(rest[b])}
    lids, pitches = (
        np.linspace(*np.subtract(gm.LID_EDGES, gm.LID_REST), n_lid),
        np.linspace(-gm.PITCH, gm.PITCH, n_pitch),
    )
    lift = [cq.Location(cq.Vector(e, 0, 0)) for e in (-0.01, 0.01)]
    overlaps, seen = [], set()
    for lid in lids:  # the lid servo's range
        for pitch in pitches:
            m = gm.moved(lid, pitch)
            turned = {k for k in m if " lid" in k}
            for a, b in near:
                # each pair once per angle that moves it
                pose = (a, b, lid if {a, b} & turned else None, pitch if {a, b} & set(m) - turned else None)
                if pose in seen:
                    continue
                seen.add(pose)
                sa, sb = (rest[k].moved(_at(m[k])) if k in m else rest[k] for k in (a, b))
                if _gap(sa, sb) < 0 and max(sa.moved(t).distance(sb) for t in lift) < 0.005:
                    overlaps.append(
                        {"pair": [a, b], "at": {"lid_deg": round(float(lid), 1), "pitch_deg": round(float(pitch), 1)}}
                    )
    model, rows = skeleton(rest)
    moving, closest = set(gm.moved(0, 0)), [within, None, None]

    def certify(pairs, path):
        qpos, posed = rows(path), {}
        row_of = {q.tobytes(): i for i, q in enumerate(qpos)}

        def shape(k, data):
            if k not in posed:
                m = np.eye(4)
                m[:3, :3], m[:3, 3] = data.body(k).xmat.reshape(3, 3), data.body(k).xpos / MM
                posed[k] = rest[k].moved(_at(m)) if k in moving else rest[k]
            return posed[k]

        def separation(model, data, pair):
            row = row_of[data.qpos.tobytes()]
            if posed.get("row") != row:
                posed.clear()
                posed["row"] = row
            a, b = (shape(k, data) for k in pair)
            mm = _gap(a, b)  # a lower bound on the gap; the exact one within `within`
            if mm < within:
                mm = a.distance(b)
            if mm < closest[0]:
                lid, pitch = (round(float(d), 1) for d in path[row])
                closest[:] = mm, list(pair), {"lid_deg": lid, "pitch_deg": pitch}
            return mm

        # a reading under LID_CLEAR_MM is the closest one, so closest carries what the gate reads
        gates.certify(model, qpos, dict.fromkeys(pairs, gm.LID_CLEAR_MM), separation=separation)

    def lines(a, b):
        """The grid's lines a pair is certified along, as (the pitches of its lid lines, the lids of its pitch lines):
        those of the servos that turn it."""
        turns = {" lid" in k for k in (a, b) if k in moving}  # True: the lid servo turns it, False: the pitch servo
        if any(k.endswith(" lid:1") for k in (a, b)) and any(" eyeball " in k for k in (a, b)):
            # a lid and an eye turn about one line through the eyes' centres, so their gap follows the turn between
            # them alone: the lid lines at the pitch's two ends sweep all of it, the lid's range being the wider
            assert np.ptp(lids) >= np.ptp(pitches)
            return pitches[[0, -1]], []
        if False not in turns:
            return pitches[:1], []
        return (pitches, lids) if True in turns else ([], lids[:1])

    groups = {}
    for a, b in pairs:
        if (a, b) not in near:
            groups.setdefault(tuple(map(tuple, lines(a, b))), []).append((a, b))
    for (ps, ls), group in groups.items():
        segments = [((lids[0], p), (lids[-1], p)) for p in ps] + [((lid, pitches[0]), (lid, pitches[-1])) for lid in ls]
        certify(group, _path([s[:: (-1) ** i] for i, s in enumerate(segments)], step))
    return {"clearance_mm": round(closest[0], 2), "pair": closest[1], "at": closest[2], "overlaps": overlaps}


def bounds():
    """The gimbal's bounding box at rest, mm: its width (x), depth (y) and height (z), servos and horns included (#684)."""
    b = cq.Compound.makeCompound(list(at_rest().values())).BoundingBox()
    return [round(b.xlen, 1), round(b.ylen, 1), round(b.zlen, 1)]


def _gap(a, b):
    """mm between the two solids' bounding boxes along the axis they are furthest apart on (negative: they overlap)."""
    ba, bb = a.BoundingBox(), b.BoundingBox()
    return max(
        max(getattr(ba, f"{k}min") - getattr(bb, f"{k}max"), getattr(bb, f"{k}min") - getattr(ba, f"{k}max"))
        for k in "xyz"
    )


def _at(m):
    """A rigid 4x4 as a CadQuery Location: the solid moves, its geometry stays exact."""
    t = gp_Trsf()
    t.SetValues(*map(float, np.asarray(m)[:3].ravel()))
    return cq.Location(t)
