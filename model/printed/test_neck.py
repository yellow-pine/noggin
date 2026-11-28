"""Seam: the Mech's neck and jaw parts (model/printed/neck.py) as model/stages.py places them at rest, under the eye
gimbal in the head's frame: no two overlap, and the shanks' bores and tapping holes line up across each pivot."""

import functools
import itertools
import math

import cadquery as cq
import numpy as np
import pytest

from model import beams, envelopes, linkage, sim, stages
from model import geometry as g
from model import neck as nk
from model import skin as sk
from model.gimbal import LID_CLEAR_MM
from model.printed import PARTS, gimbal, neck
from model.printed.test_gimbal import ON_SPLINE, _overlaps

ON_SPLINE = ON_SPLINE | {frozenset((f"{d} servo:1", f"{d} horn:1")) for d in nk.drives()}


@functools.cache
def _built(stem):
    """The part's or envelope's solid, built once a worker (its placements share it)."""
    return (PARTS.get(stem) or envelopes.ENVELOPES[stem])().val()


def _shape(p):
    """The placed part's solid, moved exactly (a rigid placement: no transformGeometry's B-spline copy to intersect)."""
    return _built(stages.stem(p.file)).moved(gimbal._at(p.matrix))


@pytest.fixture(scope="module")
def shapes():
    """{part: its solid at rest}, the neck's and the eye gimbal's, built once a module: CI's 15 s times the test alone."""
    return {n: _shape(p) for sub in (stages.neck_sub(), stages.eyes_sub()) for n, p in sub.parts.items()}


@pytest.mark.model
def test_no_two_parts_overlap_at_rest(shapes):
    pairs = [(a, b) for a, b in itertools.combinations(shapes, 2) if frozenset((a, b)) not in ON_SPLINE]
    overlaps = _overlaps(shapes, pairs)
    assert overlaps == [], "\n".join(overlaps)


@pytest.mark.model
@pytest.mark.parametrize("stem", ("cervical carrier", "neck socket", "nod plate", "head mount"))
def test_each_head_carrier_is_one_valid_solid(stem):
    shape = _built(stem)
    assert shape.isValid() and len(shape.Solids()) == 1


@pytest.mark.model
def test_the_neck_stands_in_the_torso_clear_of_the_pack_and_lid_and_bolts_to_the_floor():
    """#1075, #1062: the neck socket, its tube and the carrier overlap nothing of the base and pass the lid's slot;
    the tube fits each printed bore without overlap; each of the socket's four M3 has its hole through the flange and
    the Torso's floor, its head's countersink under the floor and a flat on the flange for its nut."""
    from model.printed import base

    neck_parts, parts = stages.neck_sub().parts, stages.base_sub().parts
    fixed = {n: _shape(neck_parts[n]) for n in ("neck socket:1", "neck tube:1", "cervical carrier:1")}
    shapes = fixed | {n: _shape(p) for n, p in parts.items()}
    overlaps = _overlaps(shapes, [*itertools.product(fixed, parts), *itertools.combinations(fixed, 2)])
    assert overlaps == [], "\n".join(overlaps)
    socket, tube = fixed["neck socket:1"], fixed["neck tube:1"]
    lid, torso = base.lid(mechanical=True).val(), base.torso(mechanical=True).val()
    assert max(part.intersect(lid).Volume() for part in fixed.values()) < 0.01
    assert tube.distance(socket) == pytest.approx(neck.FIT, abs=0.01)
    assert tube.distance(fixed["cervical carrier:1"]) == pytest.approx(neck.FIT, abs=0.01)
    floor, under, t = nk.MOUNT_Z[0], base.nb.TORSO[2][0], nk.SOCKET_FLANGE[2]
    for x, y in nk.SOCKET_SCREWS:
        assert not socket.isInside(cq.Vector(x, y, floor + t / 2)) and not torso.isInside(cq.Vector(x, y, floor - 1))
        for dx, dy in ((2.6, 0), (-2.6, 0), (0, 2.6), (0, -2.6)):
            assert not torso.isInside(cq.Vector(x + dx, y + dy, under + 0.3))  # the head's countersink
            assert torso.isInside(cq.Vector(x + dx, y + dy, floor - 0.3))
            assert socket.isInside(cq.Vector(x + dx, y + dy, floor + t - 0.2))  # the nut's seat
            assert not socket.isInside(cq.Vector(x + 1.2 * dx, y + 1.2 * dy, floor + t + 0.5))


@pytest.mark.model
def test_the_bearing_carries_the_head_without_loading_a_servo_spline():
    sub = stages.neck_sub()
    plate, bearing, mount = (_shape(sub.parts[n]) for n in ("nod plate:1", "pan bearing:1", "head mount:1"))
    assert plate.distance(bearing) < 1e-6 and bearing.distance(mount) < 1e-6
    assert plate.intersect(bearing).Volume() < 1e-6
    assert bearing.intersect(mount).Volume() < 1e-6
    # Independent contact rings, not a hidden solid shaft down the canal or through the bearing bore.
    py = nk.HEAD_AXES["pan"][0][1]
    assert not bearing.isInside(cq.Vector(0, py, sum(nk.BEARING_Z) / 2))


def _tilt_angle():
    """#978: the bar's worst angle over the servo's whole sweep, against the carrier's arm or the crank, whichever is
    less (the crank's tangent force over its sine is the bar's)."""
    out = []
    for s in nk._sweep("tilt"):
        _, a, b = nk.TILT_LOOP(s)
        bar, crank = np.subtract(b, a)[1:], np.subtract(a, nk.TILT_SHAFT)[1:]
        on_crank = math.degrees(
            math.asin(abs(crank[0] * bar[1] - crank[1] * bar[0]) / np.linalg.norm(crank) / np.linalg.norm(bar))
        )
        out.append(min(nk.transmission("tilt", s), on_crank))
    return min(out)


@pytest.mark.model
def test_the_tilt_reaction_bar_holds_the_actual_standard_servo_at_stall():
    """The bent reaction bar keeps the existing SF2 gate at the standard motor's actual 5 V stall force."""
    from model.printed.test_gimbal import _slice

    solid, mat = _built("tilt reaction bar"), g.MATERIALS[g.PRINTED["tilt reaction bar"][1]]
    angle = _tilt_angle()
    force = sim.limits("tilt horn")["stall_kgf_cm"] * beams.G * 10 / np.linalg.norm(nk.TILT_CRANK)
    force /= math.sin(math.radians(angle))
    joints = [p[1:] for p in nk.TILT_BAR_PATH]
    (y0, z0), (y1, z1) = joints[0], joints[-1]
    for a, b in zip(joints, joints[1:]):
        for t in (0.3, 0.5, 0.7):
            area, _, bend, half = _slice(solid, a, b, t)
            y, z = np.add(a, np.multiply(t, np.subtract(b, a)))
            off = abs((y - y0) * (z1 - z0) - (z - z0) * (y1 - y0)) / math.dist(joints[0], joints[-1])
            stress = force / area + force * off * half / bend
            assert mat["tensile_mpa"]["z"] / stress >= beams.MIN_SF, (a, b, t)


@pytest.mark.model
def test_the_tilt_horn_adapter_holds_the_actual_standard_servo_at_stall():
    from model.printed.test_gimbal import _bending_sf, _slice

    solid, mat = _built("tilt lever"), g.MATERIALS[g.PRINTED["tilt lever"][1]]
    shaft, pin = nk.TILT_SHAFT, nk.TILT_PIN
    radius = np.linalg.norm(nk.TILT_CRANK)
    tangent = sim.limits("tilt horn")["stall_kgf_cm"] * beams.G * 10 / radius
    angle = _tilt_angle()
    force = tangent / math.sin(math.radians(angle))
    for t in (0.25, 0.4, 0.6, 0.8):
        area, _, bend, half = _slice(solid, shaft[1:], pin[1:], t)
        stress = force / area + tangent * radius * (1 - t) * half / bend
        assert mat["tensile_mpa"]["z"] / stress >= beams.MIN_SF, t
    a, b = (shaft[0], *pin[1:]), (sum(nk.REACTION_BAR_X) / 2, *pin[1:])
    assert (
        _bending_sf(solid, a, b, force, "z", math.dist(a, b), ts=(0.05, 0.25, 0.5, 0.65)) >= beams.MIN_SF
    )  # the pin boss ends at the bar


def _bar_pulls():
    """The bar's worst force (the bar's own test's) on the anchor's pin, N, along the bar at each pose of the sweep as
    the fixed carrier sees it: the case's direction, turned back by the head's turn."""
    force = sim.limits("tilt horn")["stall_kgf_cm"] * beams.G * 10 / np.linalg.norm(nk.TILT_CRANK)
    force /= math.sin(math.radians(_tilt_angle()))
    pulls = []
    for s in nk._sweep("tilt"):
        rocker, p, q = nk.TILT_LOOP(s)
        pulls.append(linkage.rotation(g.X, -rocker)[:3, :3] @ np.subtract(p, q) / math.dist(p, q) * force)
    return pulls


@pytest.mark.model
def test_the_reaction_anchor_holds_the_actual_standard_servo_at_stall():
    """#1039: the carrier's strut straight back to the reduction's anchor: SF 2 in PETG across its layers on its actual
    sections. The bar's worst force (the bar's own test's) acts at the bar's middle on the anchor's pin, along the bar
    wherever the sweep leans it: it pulls the strut, and bends it by the bar's lean and by the bar's place inboard of
    it. The run across from the tube that it hangs on has its own test, below."""
    solid, mat = _built("cervical carrier"), g.MATERIALS[g.PRINTED["cervical carrier"][1]]
    _, ay, az = nk.TILT_ANCHOR
    _, rail, low = nk.tube_at(nk.TUBE_SCREWS[1])  # the strut's corner, level with its root on the tube
    x, pin = nk.REACTION_TAP_X[1] - 5.0, np.array((sum(nk.REACTION_BAR_X) / 2, ay, az))  # x: the strut's middle, about
    pulls = _bar_pulls()
    for t in (0.45, 0.55, 0.7, 0.85):  # behind the run across, which has its own test below
        cut = _section(solid, (x, rail + (ay - rail) * t, low), (0, 1, 0), (1, 0, 0), (13, 14))
        box, centre = cut.BoundingBox(), np.array(cut.Center().toTuple())
        inertia = np.asarray(cq.Shape.matrixOfInertia(cut)) / 0.01
        wide, tall = (
            max(hi - c, c - lo) for hi, lo, c in ((box.xmax, box.xmin, centre[0]), (box.zmax, box.zmin, centre[2]))
        )

        def stress(pull):
            about = np.cross(pin - centre, pull)  # the pull's moment at the section: about x it bends it up and down
            return (
                abs(pull[1]) / (cut.Volume() / 0.01)
                + abs(about[0]) * tall / inertia[0, 0]
                + abs(about[2]) * wide / inertia[2, 2]
            )

        assert mat["tensile_mpa"]["z"] / max(map(stress, pulls)) >= beams.MIN_SF, t


LUG = 15.4  # the nod plate's lug's middle on its shank, from the midline


def _stall(case):
    """{where: (its point, its force over the tilt's sweep, N)} on the fixed neck at a head servo's stall, the head
    blocked by a couple, as the other stall tests take it. Tilt: the bar's worst force pulls the anchor's pin, and the
    nod plate pushes back on its two shanks, by its own balance across (the bar between the lugs) 0.89 of it on R.
    Pan (#1063): its case rides the nod plate, which gets the head's torque back about the pan axis (a parallelogram,
    ratio 1) and passes it to the shanks as a couple fore and aft, the pan axis leaning with the tilt."""
    axis = np.array(nk.HEAD_AXES["tilt"][0])
    shank = {side: axis + (sign * LUG, 0, 0) for side, sign in (("R", -1), ("L", 1))}
    if case == "tilt":
        bar, pulls = sum(nk.REACTION_BAR_X) / 2, np.array(_bar_pulls())
        share = {"R": (LUG - bar) / (2 * LUG), "L": (LUG + bar) / (2 * LUG)}
        pin = {"pin": (np.array((bar, *nk.TILT_ANCHOR[1:])), pulls)}
        return pin | {side: (shank[side], -share[side] * pulls) for side in shank}
    force = sim.limits("pan horn")["stall_kgf_cm"] * beams.G * 10 / (2 * LUG)
    tilts = np.radians(np.linspace(*nk.RANGES["tilt"], 41))
    fore = np.c_[np.zeros(41), np.cos(tilts), np.sin(tilts)] * force
    return {"R": (shank["R"], -fore), "L": (shank["L"], fore)}


def _held(solid, at, along, loads, window=(26, 26), on_tube=False):
    """The SF in PETG across its layers of `solid`'s section at `at`, square to `along`, under the `loads` beyond it
    (_stall's): its pull, its bending both ways and its twist (an ellipse's or a thin slab's shear, T c / 2 I),
    together as von Mises, at the worst pose. `on_tube`: a sleeve on the neck tube bends and twists with it, so it
    takes its share of the moment by stiffness, E I of the two."""
    at, along = np.asarray(at, float), np.asarray(along, float) / np.linalg.norm(along)
    u = np.cross(along, g.Y if abs(along[0]) > 0.9 else g.X)
    u /= np.linalg.norm(u)
    v = np.cross(along, u)
    pieces = _section(solid, tuple(at), tuple(along), tuple(v), window).Solids()
    cut = min(pieces, key=lambda piece: np.linalg.norm(np.array(piece.Center().toTuple()) - at))
    area, centre = cut.Volume() / 0.01, np.array(cut.Center().toTuple())
    inertia = np.asarray(cq.Shape.matrixOfInertia(cut)) / 0.01
    fibres = np.abs((np.array([p.toTuple() for p in cut.tessellate(0.05)[0]]) - centre) @ np.array((u, v)).T)
    (cu, cv), iu, iv = fibres.max(axis=0), v @ inertia @ v, u @ inertia @ u
    force = sum(f for _, f in loads)
    moment = sum(np.cross(p - centre, f) for p, f in loads)
    if on_tube:
        own = g.MATERIALS["PETG HF"]["E_mpa"]["z"] * max(iu, iv)
        moment = moment * own / (own + nk.TUBE_E_MPA * math.pi / 4 * (nk.TUBE[0] ** 4 - nk.TUBE[1] ** 4))
    normal = np.abs(force @ along) / area + np.abs(moment @ v) * cu / iu + np.abs(moment @ u) * cv / iv
    twist = np.abs(moment @ along) * min(cu, cv) / (2 * min(iu, iv))
    return float(g.MATERIALS["PETG HF"]["tensile_mpa"]["z"] / np.hypot(normal, math.sqrt(3) * twist).max())


def _carrier_cuts():
    """[(member, where, square to, the loads beyond it)]: the carrier's sections, each wing and its riser by its own
    shank, the strut's run across by the anchor's pin, the sleeve between them by both shanks."""
    _, y, _ = nk.HEAD_AXES["tilt"][0]
    _, ty, tz = nk.tube_at(nk.TUBE_SCREWS[1])
    wy, (z0, _, z2) = sum(neck.WING_Y) / 2, neck.WING_Z
    cuts = []
    for side, sign in (("R", -1), ("L", 1)):
        x = sign * sum(neck.RISER_X) / 2
        cuts += [(f"{side} riser", (x, (y + wy) / 2, z), g.Z, (side,)) for z in (-52.0, -54.5, -57.0)]
        cuts += [(f"{side} wing", (sign * x, wy, (z0 + z2) / 2), (sign, 0, 0), (side,)) for x in (9.0, 12.0, 15.0)]
    cuts += [("strut across", (x, ty, tz), (-1, 0, 0), ("pin",)) for x in (-9.0, -12.0, -14.0)]
    return cuts + [("sleeve", nk.tube_at(s), nk.TUBE_AXIS, ("R", "L")) for s in (74.0, 78.0)]


@pytest.mark.model
@pytest.mark.parametrize("case", ("tilt", "pan"))
def test_the_cervical_carrier_holds_each_head_servo_at_stall(case):
    """#1075, #1063: SF 2 in PETG across its layers on the carrier's actual sections, at the tilt servo's stall and at
    the pan servo's. The tilt's loop closes inside the carrier: the bar pulls the anchor's pin, the nod plate pushes
    back on the two shanks, 0.89 of it on R. The pan's stall loads the two wings alike, one forward and one back,
    and twists the sleeve. The strut's run back to the anchor has its own test above."""
    solid, loads, weak = _built("cervical carrier"), _stall(case), []
    for member, at, along, beyond in _carrier_cuts():
        acting = [loads[n] for n in beyond if n in loads]
        if acting and (sf := _held(solid, at, along, acting, on_tube=member == "sleeve")) < beams.MIN_SF:
            weak.append((member, np.round(at, 1).tolist(), round(sf, 2)))
    assert weak == []


def _on_the_tube(case):
    """(bending about x, bending about the fore-and-aft axis, twist), N.mm, the worst of each over the sweep: what
    the stall's loads (a couple: no net force) put on the neck tube under the carrier."""
    loads, axis = list(_stall(case).values()), np.array(nk.TUBE_AXIS)
    assert np.abs(sum(f for _, f in loads)).max() < 1e-9
    moment = sum(np.cross(p, f) for p, f in loads)
    return tuple(float(np.abs(moment @ way).max()) for way in (g.X, np.cross(axis, g.X), axis))


@pytest.mark.model
@pytest.mark.parametrize("cases", (("tilt",), ("pan",), ("tilt", "pan")))
def test_the_neck_tube_holds_the_head_servos_at_stall(cases):
    """#1075: SF 2 on the tube's lowest cited proof stress (nk.TUBE_PROOF_MPA: any 6060, 6063 or 6061 tube in T6 or
    T66), on its net section at a cross screw's hole, at each servo's stall and at both at once. The tilt's stall
    bends it about x, the hole's own axis, where the hole costs it 2 %; the pan's twists it and, as the pan axis leans
    with the tilt, bends it a little the other way, where the hole costs 40 %. Bending both ways at the worst fibre
    and the twist together as von Mises; no stress concentration is counted."""
    (r, bore, _), hole = nk.TUBE, nk.TUBE_HOLE_R
    w, x = np.meshgrid(*[np.arange(-r, r, 0.01) + 0.005] * 2, indexing="ij")
    ring = (np.hypot(w, x) <= r) & (np.hypot(w, x) >= bore) & (np.abs(w) >= hole)  # the hole runs along x
    about_x, about_w = (float((c[ring] ** 2).sum() * 1e-4) for c in (w, x))
    bend_x, bend_w, twist = (sum(c) for c in zip(*map(_on_the_tube, cases)))
    fibre = np.radians(np.arange(0, 91))
    normal = (bend_x * r * np.sin(fibre) / about_x + bend_w * r * np.cos(fibre) / about_w).max()
    shear = twist * r / (about_x + about_w)
    assert nk.TUBE_PROOF_MPA / math.hypot(normal, math.sqrt(3) * shear) >= beams.MIN_SF


@pytest.mark.model
@pytest.mark.parametrize("stem", ("neck socket", "cervical carrier"))
def test_each_screw_across_the_tube_holds_the_pan_servos_stall(stem):
    """#1075, #1063: one M3 across the tube and each printed part on it holds the part against the pan servo's stall,
    which twists the tube (the tilt's twists nothing: its loop closes in the carrier). SF 2 on the screw's bearing in
    the print each side of the tube, on its bearing in the tube's 1 mm wall (a pin's, 1.5 d t fo: EN 1999-1-1 8.5.14)
    and on its two shear planes (0.5 of its tensile strength on its stress area, its Table 8.5); and each part has the
    screw's clearance hole to the tube's middle, its tapping hole beyond and a seat for its head."""
    twist, (tip, seat), r = _on_the_tube("pan")[2], nk.SCREW_X, nk.TUBE[0]
    held = (seat - r - neck.FIT, -r - neck.FIT - tip)  # the print's length on the screw, L and R of the tube
    arm = (seat + r + neck.FIT) / 2 - (tip - r - neck.FIT) / 2
    strength = g.MATERIALS[g.PRINTED[stem][1]]["tensile_mpa"]["z"]
    assert strength / (twist / arm / (3.0 * min(held))) >= beams.MIN_SF
    wall = twist / (r + nk.TUBE[1]) / (3.0 * (r - nk.TUBE[1]))  # MPa, on each wall, the walls' middles apart
    assert 1.5 * nk.TUBE_PROOF_MPA / wall >= beams.MIN_SF
    assert 0.5 * nk.M3["tensile_mpa"] * nk.M3["stress_mm2"] / (twist / (2 * r)) >= beams.MIN_SF
    solid, (_, y, z) = _built(stem), nk.tube_at(nk.TUBE_SCREWS[stem == "cervical carrier"])
    for x, clear in ((seat - 1.0, True), (-r - 1.5, False)):  # 1.4 mm off the screw's axis, as the shanks' test
        assert solid.isInside(cq.Vector(x, y, z + 1.4)) != clear and solid.isInside(cq.Vector(x, y, z + 2.5))
    assert not solid.isInside(cq.Vector(seat + 1.0, y, z + 2.5))  # the head's room


@pytest.mark.model
@pytest.mark.parametrize("case", ("tilt", "pan"))
def test_the_neck_socket_and_its_fixing_to_the_torso_hold_each_head_servo_at_stall(case):
    """#1075, #1062: SF 2 at each servo's stall, in PETG across its layers but where a screw is named. The stall
    reaches the foot as a couple (the head's torque, no net force). The grip: the tube pushes the tower's top one way
    and its foot the other, 6 M / D L^2 on the bore, which the tower's sides hold as hoop tension. The tower under the
    tube's foot, open to L for the leads, on its actual sections. The fixing: the flange rocks on its edge, fore and
    aft or across, each M3 pulling by its lever from that edge; that pull on the nut's seat on the flange, on the
    flange's sections beside the tower, on the floor under the head's countersink (bearing on the cone, and the ring
    of floor that would shear out round it), and on the screw itself (A2-70's proof stress on its stress area)."""
    from model.printed import base

    solid, loads = _built("neck socket"), list(_stall(case).values())
    strength, axis = g.MATERIALS[g.PRINTED["neck socket"][1]]["tensile_mpa"]["z"], np.array(nk.TUBE_AXIS)
    bend_x, bend_w, _ = _on_the_tube(case)
    floor, (xs, ys, t), (r, _, _) = nk.MOUNT_Z[0], nk.SOCKET_FLANGE, nk.TUBE
    grip = (nk.SOCKET_TOP_Z - nk.TUBE_FOOT[2]) / axis[2]
    push = 6 * math.hypot(bend_x, bend_w) / (2 * r * grip**2)
    hoop = push * 2 * r / (2 * (neck.TOWER[0] - r - neck.FIT))
    assert strength / max(push, hoop) >= beams.MIN_SF
    for z in (nk.TUBE_FOOT[2] - 2.0, floor + t + 1.5):
        assert _held(solid, nk.tube_at((z - nk.TUBE_FOOT[2]) / axis[2]), axis, loads) >= beams.MIN_SF, z
    pulls = []  # each M3's worst pull, in nk.SOCKET_SCREWS' order
    for i in range(len(nk.SOCKET_SCREWS)):
        rocks = []
        for moment, at, edges in ((bend_x, 1, ys), (bend_w, 0, xs)):
            for edge in edges:
                levers = [abs(screw[at] - edge) for screw in nk.SOCKET_SCREWS]
                rocks.append(moment * levers[i] / sum(lever**2 for lever in levers))
        pulls.append(max(rocks))
    pull = max(pulls)
    seat = math.pi / 4 * (nk.M3["nut_flats"] ** 2 - 3.4**2)
    cone = math.pi * (base.SINK[0] ** 2 - base.SINK[1] ** 2)
    ring = 2 * math.pi * base.SINK[0] * (floor - base.nb.TORSO[2][0] - base.SINK[2])
    assert strength / (pull / min(seat, cone)) >= beams.MIN_SF
    assert strength / math.sqrt(3) / (pull / ring) >= beams.MIN_SF
    assert nk.M3["proof_mpa"] * nk.M3["stress_mm2"] / pull >= beams.MIN_SF
    for sign in (-1, 1):
        beside = [
            (np.array((x, y, floor + t)), np.array([(0.0, 0.0, p)]))
            for (x, y), p in zip(nk.SOCKET_SCREWS, pulls)
            if x * sign > 0
        ]
        at = (sign * (neck.TOWER[0] + 0.5), sum(ys) / 2, floor + t / 2)
        assert _held(solid, at, (sign, 0, 0), beside, (ys[1] - ys[0] + 2, t + 2)) >= beams.MIN_SF, sign


@pytest.mark.model
def test_the_leads_have_an_open_way_from_the_torsos_floor_up_the_tubes_bore():
    """#1075: the four leads' bundle, packed square, passes from the Torso's floor in through the socket's L side, up
    under the tube's foot and through the tube and the carrier, out of its top, touching none of them."""
    r, floor = nk.LEAD_OD * (1 + math.sqrt(2)) / 2, nk.MOUNT_Z[0]
    parts = stages.neck_sub().parts
    low = (floor + r + 0.1 - nk.TUBE_FOOT[2]) / nk.TUBE_AXIS[2]
    way = neck._along(nk.tube_at(low), nk.tube_at(nk.TUBE[2] + 2.0), r)
    way = way.union(neck._along(nk.tube_at(low), np.add(nk.tube_at(low), (nk.SOCKET_FLANGE[0][1] + 2.0, 0, 0)), r))
    for name in ("neck socket:1", "neck tube:1", "cervical carrier:1"):
        assert _shape(parts[name]).intersect(way.val()).Volume() < 1e-6, name


@pytest.mark.model
def test_the_nod_plate_tilts_clear_of_the_carrier_but_at_its_trunnions():
    """#1075, #1085: through the tilt the nod plate shares no volume with the carrier, and keeps a moving part's
    clearance and the reach of its own collision pieces (mjcf.FINE_MM) from it everywhere but where it turns on it:
    outboard of the risers' inner faces, its L arm swinging down behind the riser as the face goes up (2.4 mm), and
    between those faces, its underside over the wings (3.9 mm). Exactly (OCCT's distance): the sim's default pieces
    bridged the plate's hollow round each trunnion and read the riser 0.2 mm deeper in it with the face up."""
    from model import mjcf

    carrier, plate = _built("cervical carrier"), _built("nod plate")
    between = envelopes.box((-neck.RISER_X[0], neck.RISER_X[0]), (0, 200), (-200, 100)).val()
    outer, inner, wings = plate.cut(between), plate.intersect(between), carrier.intersect(between)
    room = mjcf.FINE_MM["nod plate"] + LID_CLEAR_MM
    for deg in np.linspace(*nk.RANGES["tilt"], 9):
        turn = gimbal._at(linkage.rotation(g.X, deg, nk.HEAD_AXES["tilt"][0]))
        assert carrier.intersect(plate.moved(turn)).Volume() < 1e-6, deg
        assert min(carrier.distance(outer.moved(turn)), wings.distance(inner.moved(turn))) >= room, deg


@pytest.mark.model
def test_the_tilt_lever_swings_beside_its_case_with_room():
    """#1039: the lever's arm steps inboard round the horn's rim and rides beside the case's face, and its pin passes
    the case's corner in mid-swing, which neither end of the range shows: at 21 poses through the tilt's sweep the
    lever and its bar keep a moving part's clearance from the case, exactly (OCCT's distance, no sampled surface)."""
    stage = stages.STAGES[DOC]
    for deg in np.linspace(*stage.horns["tilt horn"].limits, 21):
        mats = stages.pose(stage, "tilt horn", deg).parts
        case, lever, bar = (
            _shape(stage.parts[n]._replace(matrix=mats[n]))
            for n in ("tilt servo:1", "tilt lever:1", "tilt reaction bar:1")
        )
        assert min(lever.distance(case), bar.distance(case)) >= LID_CLEAR_MM, deg


@pytest.mark.model
def test_the_jaw_carrier_holds_the_mouth_servo_at_stall():
    """#968: SF 2 (beams.MIN_SF) in PETG across its layers along each of the carrier's chains, pivot to chin, the jaw
    blocked anywhere along them: every section carries at most the bar's worst moment about the pivot over the jaw's
    sweep, in the jaw's plane, and pulls with its worst force (the crank's tangent force over the sine of the
    crank-to-bar angle). The moment turns about x: a section square to x bends under all of it, the bar across at the
    chin (along x) twists under all of it, one askew takes its share of each (von Mises; the twist as on an ellipse
    as thick as the section's thin way). Along each span and at each joint between two, and through each magnet's
    pocket in the bar (nk.JAW_HOLD), at its middle and both rims: a pocket alone left SF 1.5 there, so the bar is
    thickened behind each. On the mechanical part (ADR 0020)."""
    # shortcut: the pin's post (r 3.5, 12 mm) is not sectioned: SF 6 by hand as a cantilever under this force. Nor is
    # the twist its 14 mm offset puts on the L chain: 3.8 MPa of shear in the ramus by hand, SF 2.5 with its bending.
    # Add both if the post thins or lengthens
    solid, mat = _built("jaw" + g.MECHANICAL), g.MATERIALS[g.PRINTED["jaw"][1]]
    tangent = sim.limits("jaw horn")["stall_kgf_cm"] * beams.G * 10 / nk.CRANK
    horn, pivot = nk.pins()["jaw"][2], nk.HEAD_AXES["jaw"][0]
    loads = []  # (N, N.mm) at each servo angle
    for s in nk._sweep("jaw"):
        _, a, b = nk.LINKAGES["jaw"](s)
        (cy, cz), (by, bz), (ry, rz) = (np.subtract(p, q)[1:] for p, q in ((a, horn), (b, a), (b, pivot)))
        force = tangent * math.hypot(cy, cz) * math.hypot(by, bz) / abs(cy * bz - cz * by)
        loads.append((force, force * abs(ry * bz - rz * by) / math.hypot(by, bz)))
    force, moment = (max(c) for c in zip(*loads))
    weak = []
    for chain in map(np.asarray, neck.jaw_chains().values()):
        ways = [(b - a) / np.linalg.norm(b - a) for a, b in itertools.pairwise(chain)]
        cuts = [(a + (b - a) * t, w) for (a, b), w in zip(itertools.pairwise(chain), ways) for t in (0.3, 0.5, 0.7)]
        # each joint too, square to its two spans' mean: where Bones ending flat on a bend left a notch
        cuts += [(joint, (v + w) / np.linalg.norm(v + w)) for joint, v, w in zip(chain[1:], ways, ways[1:])]
        bore = sk.MAGNET[0] / 2 + sk.FIT
        (hold,) = (x for x, _, _ in nk.JAW_HOLD if x * chain[0][0] > 0)  # this chain's side's
        cuts += [(np.array((hold + dx, *nk.JAW_CHIN[1:])), ways[-1]) for dx in (-bore, 0.0, bore)]
        for at, along in cuts:
            u = np.subtract(g.X, along * along[0])  # x in the section's plane: the bending axis, its length the share
            bends = float(np.linalg.norm(u))
            u = u / bends if bends > 1e-6 else np.cross(along, g.Z)  # the bar across: nothing bends it, any axis
            v = np.cross(along, u)
            cut = _section(solid, tuple(at), tuple(along), tuple(u), (16, 16))
            area, centre = cut.Volume() / 0.01, np.array(cut.Center().toTuple())
            tensor = np.array(cq.Shape.matrixOfInertia(cut)) / 0.01
            inertia = u @ tensor @ u
            fibre = max(abs((np.array(p.toTuple()) - centre) @ v) for p in cut.Vertices())
            # an ellipse of this area and least second moment is this thick the thin way; its worst shear is 2T/(A b)
            thin = 2 * math.sqrt(
                np.linalg.eigvalsh([[inertia, u @ tensor @ v], [u @ tensor @ v, v @ tensor @ v]])[0] / area
            )
            shear = 2 * moment * abs(along[0]) / (area * thin)
            sf = mat["tensile_mpa"]["z"] / math.hypot(
                force / area + moment * bends * fibre / inertia, math.sqrt(3) * shear
            )
            if sf < beams.MIN_SF:
                weak.append((tuple(np.round(at, 1)), round(sf, 2)))
    assert weak == []


@pytest.mark.model
@pytest.mark.parametrize("style", ("", g.MECHANICAL))
@pytest.mark.parametrize("at", nk.JAW_HOLD, ids=("L", "R"))
def test_the_jaws_bar_has_a_flush_magnet_pocket_for_each_pair_that_holds_the_mandible(style, at):
    """#968 (Cansin, 2026-11-28: the mandible is held on its carrier by two magnet pairs): at each of nk.JAW_HOLD
    the bar across has a magnet's pocket open forward, toward the bone. The magnet's room is empty from a mm in
    front of the pair's face back to a magnet's depth behind it, so its face lies on the bar's front, where the
    bone's magnet meets it. The bar's front is there, beside the pocket along the bar. And behind the pocket the
    bar is as thick again as it is whole: its pad, a magnet's depth out of its back."""
    jaw = _built("jaw" + style)
    x, y, z = at
    bore, depth = sk.MAGNET[0] / 2 + sk.FIT, sk.MAGNET[1]

    def share(shape):
        return jaw.intersect(shape.val()).Volume() / shape.val().Volume()

    assert share(gimbal.cyl("y", (x, 0, z), sk.MAGNET[0] / 2, (y - 1.0, y + depth))) < 1e-4
    for side in (-1, 1):  # on the bar's front line, just under its surface
        beside = (x + side * (bore + 0.6), z)
        assert share(gimbal.cyl("y", (beside[0], 0, beside[1]), 0.2, (y + 0.05, y + 0.5))) > 0.99, side
    thick = 2 * neck.JAW_CHIN_BAR[1]
    assert thick == pytest.approx(2 * (nk.JAW_CHIN[1] - y))
    assert share(gimbal.cyl("y", (x, 0, z), bore, (y + depth + 0.01, y + depth + thick - 0.01))) > 0.99


@pytest.mark.model
@pytest.mark.parametrize("style", ("", g.MECHANICAL))
def test_the_jaw_turns_with_room_from_the_gimbal_frame(style):
    """#968 (Cansin, 2026-11-27: the jaw's pivot bosses get print clearance): over the jaw's range the jaw keeps a
    moving part's room (LID_CLEAR_MM) from the frame it turns on, each pivot boss from its lug's face, as drawn, and
    from the other wall of its notch in the frame's plate, which it stood against (0.00 mm)."""
    jaw, frame, (jy, jz) = _built("jaw" + style), _built("gimbal frame" + style), nk.JAW
    for deg in np.linspace(0.0, max(nk.RANGES["jaw"]), 6):
        turned = jaw.rotate(cq.Vector(0, jy, jz), cq.Vector(1, jy, jz), float(deg))
        assert turned.distance(frame) >= LID_CLEAR_MM - 1e-6, deg


@pytest.mark.model
@pytest.mark.parametrize("side", list(nk.MANDIBLE_CHAIN))
def test_the_jaw_carriers_bar_meets_each_chain_without_a_sliver(side):
    """#850: two chains ending together at the chin met in a 0.015 mm edge, which Linux's OCCT read back from a
    document's STEP as an invalid jaw (model/test_ours.py), once nothing fused onto the chin covered it. One bar runs
    across there now (#968), and no edge of the Bone jaw within 9 mm of where it meets a chain is that marginal."""
    end = np.array(nk.MANDIBLE_CHAIN[side][-1])
    edges = [e for e in _built("jaw").Edges() if np.linalg.norm(np.array(e.Center().toTuple()) - end) < 9.0]
    assert edges and min(e.Length() for e in edges) > 0.5


@pytest.fixture(scope="module")
def saddle():
    return _built("nod plate")


def _section(solid, origin, normal, xdir, size):
    """The solid's 0.01 mm slice in the plane at `origin`, its window `size` (along xdir, then across)."""
    plane = cq.Plane(origin=origin, xDir=xdir, normal=normal)
    return solid.intersect(cq.Workplane(plane).rect(*size).extrude(0.005, both=True).val())


@pytest.mark.model
@pytest.mark.parametrize("member", ("mast", "header", "beam", "pan bar"))
def test_the_standard_servo_cradles_hold_their_actual_stall_reaction(saddle, member):
    """#978: actual CAD sections of the nod plate's cradles at each servo's 5 V stall. Each tab takes half the bar's
    force on its shaft and the case's torque over the tabs' spacing; a member bends that load about its section, the
    mast both cradles' at once."""
    mat = g.MATERIALS[g.PRINTED["nod plate"][1]]
    (sx, sy, sz), (_, py, pz) = nk.TILT_SHAFT, nk.PAN_SHAFT
    holes = sorted({x for x, _ in envelopes.STANDARD_SERVO["holes"]})  # its tabs' hole lines
    spacing = holes[1] - holes[0]
    torque = {d: sim.limits(f"{d} horn")["stall_kgf_cm"] * beams.G * 10 for d in ("tilt", "pan")}
    angle = {d: min(nk.transmission(d, s) for s in np.linspace(-r, r, 41)) for d, r in (("tilt", 20), ("pan", 45))}
    bar = {"tilt": torque["tilt"] / np.linalg.norm(nk.TILT_CRANK), "pan": torque["pan"] / np.linalg.norm(nk.PAN_ARM)}
    force = {d: bar[d] / math.sin(math.radians(angle[d])) for d in bar}
    tab = {d: force[d] / 2 + torque[d] / spacing for d in force}
    if member == "mast":  # both cradles' loads: over the tilt header the mast's alone, under it the frame's two posts
        for z, (x, y), window in (
            (sz + 45.0, (20.5, sy + 6.0), (20, 14)),
            (nk.NOD_Z[1] + 6.0, (8.0, sy - 4.0), (48, 40)),
        ):
            cut = _section(saddle, (x, y, z), (0, 0, 1), (1, 0, 0), window)
            inertia = np.asarray(cq.Shape.matrixOfInertia(cut)) / 0.01
            box, (cx, cy, _) = cut.BoundingBox(), cut.Center().toTuple()
            tilt = tab["tilt"] * max(sz + 41.0 - z, 0.0) * max(box.ymax - cy, cy - box.ymin) / inertia[0, 0]
            pan = tab["pan"] * (pz + 23.0 - z) * max(box.xmax - cx, cx - box.xmin) / inertia[1, 1]
            stress = (tab["tilt"] + tab["pan"]) / (cut.Volume() / 0.01) + tilt + pan
            assert mat["tensile_mpa"]["z"] / stress >= beams.MIN_SF, z
        return
    elif member == "header":  # over the case's top, from the upper tab's block to the mast
        x = 10.0
        cut = _section(saddle, (x, sy, sz + 41.0), (1, 0, 0), (0, 1, 0), (24, 10))
        axis, bend, load, moment = 1, 2, tab["tilt"], tab["tilt"] * abs(x - (sx + 18.4))
    elif member == "beam":  # in front of the case, from the plate's crossbar down to the lower tab's block
        z = (sz + holes[0] + nk.NOD_Z[0]) / 2
        cut = _section(saddle, (-5.0, sy - 17.0, z), (0, 0, 1), (1, 0, 0), (12, 16))
        axis, bend, load, moment = 1, 0, tab["tilt"], tab["tilt"] * abs(z - (sz + holes[0]))
    else:  # the pan cradle's side bar, from the fore tab's block to the mast
        y = py - 12.0
        cut = _section(saddle, (15.0, y, pz + 23.0), (0, 1, 0), (1, 0, 0), (12, 10))
        axis, bend, load, moment = 0, 2, tab["pan"], tab["pan"] * abs(y - (py - holes[1]))
    inertia = np.asarray(cq.Shape.matrixOfInertia(cut))[bend, bend] / 0.01
    box, centre = cut.BoundingBox(), cut.Center().toTuple()[axis]
    half = max(getattr(box, "xyz"[axis] + "max") - centre, centre - getattr(box, "xyz"[axis] + "min"))
    stress = load / (cut.Volume() / 0.01) + moment * half / inertia
    assert mat["tensile_mpa"]["z"] / stress >= beams.MIN_SF


@pytest.fixture(scope="module")
def pan_wire_candidate():
    return {n: p.val() for n, p in neck.pan_wire_candidate().items()}


@pytest.mark.model
def test_the_pitch_drive_clears_the_c0_bearing_and_retains_its_planar_linkage(pan_wire_candidate):
    """#978: free the real C0 bearing volume without changing either eye's pitch kinematics."""
    rest = gimbal.at_rest(mechanical=True)
    parts = {n: rest[n] for n in ("pitch servo:1", "pitch horn:1", "pitch bar:1", "bail:1")}
    assert _overlaps(parts | pan_wire_candidate, list(itertools.product(parts, pan_wire_candidate))) == []


@pytest.mark.model
def test_the_connected_electronics_tray_and_hub_clear_the_c0_bearing(pan_wire_candidate):
    """#978: the USB hub and its real supporting tray leave the retained pan bearing accessible."""
    from model import base
    from model.printed import base as printed_base

    mesh, matrix = base.cranium()["hub"]
    parts = {"tray": printed_base.tray(True).val(), "hub": _built(mesh).moved(gimbal._at(matrix))}
    assert parts["tray"].isValid() and len(parts["tray"].Solids()) == 1
    assert _overlaps(parts | pan_wire_candidate, list(itertools.product(parts, pan_wire_candidate))) == []
    assert parts["tray"].distance(parts["hub"]) < 1e-6


@pytest.mark.model
def test_the_tray_legs_clear_the_lower_rear_standard_case_through_pan():
    """#978 packaging fixture: the full standard case fits between the panning head's actual tray legs."""
    from model.printed import base

    tray = base.tray(True).val()
    motor = envelopes.standard_servo().val().moved(gimbal._at(stages.align(nk.TILT_SHAFT, nk.TILT_CASE, (-1, 0, 0))))
    for pan in (-45, -22.5, 0, 22.5, 45):
        moved = tray.moved(gimbal._at(linkage.rotation(g.Z, pan, (0, 75, -20))))
        assert moved.intersect(motor).Volume() < 0.01, pan


@pytest.mark.model
def test_the_pan_case_clears_the_electronics_tray_and_capacitor_through_pan():
    """#978: the pan case behind the C0 axis, over the tray, clears the panning tray and capacitor."""
    from model import base as layout
    from model.printed import base

    cap, matrix = layout.cranium()["bulk capacitor"]
    parts = {"tray": base.tray(True).val(), "capacitor": _built(cap).moved(gimbal._at(matrix))}
    motor = envelopes.standard_servo().val().moved(gimbal._at(stages.align(nk.PAN_SHAFT, nk.PAN_CASE, (0, 0, -1))))
    for pan in (-45, -22.5, 0, 22.5, 45):
        delta = gimbal._at(linkage.rotation(g.Z, pan, (0, 75, -20)))
        for name, solid in parts.items():
            assert solid.moved(delta).intersect(motor).Volume() < 0.01, (name, pan)


@pytest.mark.model
def test_the_c0_pan_bearing_candidate_has_real_retention_and_an_open_wire_path(pan_wire_candidate):
    """Unaccepted component study: the shaft, caps and bearing leave the allocated 8 mm bore, not the full harness route."""
    assert set(pan_wire_candidate) == {"spindle", "fixed cap", "bearing", "head carrier", "moving cap"}
    for solid in pan_wire_candidate.values():
        assert solid.isValid() and len(solid.Solids()) == 1 and solid.Volume() > 0
    y = nk.HEAD_AXES["tilt"][0][1]
    bottom = min(s.BoundingBox().zmin for s in pan_wire_candidate.values())
    top = max(s.BoundingBox().zmax for s in pan_wire_candidate.values())
    cable = gimbal.cyl("z", (0, y, 0), 4, (bottom - 1, top + 1)).val()
    assert all(s.intersect(cable).Volume() < 1e-6 for s in pan_wire_candidate.values())
    assert _overlaps(pan_wire_candidate, list(itertools.combinations(pan_wire_candidate, 2))) == []
    for a, b in (
        ("spindle", "bearing"),
        ("fixed cap", "bearing"),
        ("head carrier", "bearing"),
        ("moving cap", "bearing"),
    ):
        assert pan_wire_candidate[a].distance(pan_wire_candidate[b]) < 1e-6


@pytest.mark.model
def test_the_c0_pan_bearing_candidate_survives_step_round_trip(pan_wire_candidate, tmp_path):
    for name, solid in pan_wire_candidate.items():
        path = tmp_path / (name + ".step")
        cq.exporters.export(solid, str(path))
        restored = cq.importers.importStep(str(path)).val()
        assert restored.isValid() and len(restored.Solids()) == 1
        assert restored.Volume() == pytest.approx(solid.Volume(), rel=1e-6)


Y, Z = nk.AXIS
JY, JZ = nk.JAW


@pytest.fixture
def pivot(turns, fixed):
    """The turning part's solid and the fixed one's, each built once a worker, in setup: CI's 15 s times the test alone
    (#808)."""
    return _solid(turns), _solid(fixed)


_solid = functools.cache(lambda build: build().val())


@pytest.mark.model
@pytest.mark.parametrize(
    "turns, fixed, at, across",
    [  # (the turning part, the fixed one, a point on the axis inside each, a direction across the axis)
        (
            neck.nod_plate,
            neck.cervical_carrier,
            ((15.4, *nk.HEAD_AXES["tilt"][0][1:]), (20.2, *nk.HEAD_AXES["tilt"][0][1:])),  # mid lug, mid boss
            (0, 1, 0),
        ),
        (  # #978: the reduction's bar on its crank's pin and on the carrier's anchor
            neck.tilt_reaction_bar,
            neck.tilt_lever,
            ((sum(nk.REACTION_BAR_X) / 2, *nk.TILT_PIN[1:]), (sum(nk.REACTION_TAP_X) / 2, *nk.TILT_PIN[1:])),
            (0, 1, 0),
        ),
        (
            neck.tilt_reaction_bar,
            neck.cervical_carrier,
            ((sum(nk.REACTION_BAR_X) / 2, *nk.TILT_ANCHOR[1:]), (sum(nk.REACTION_TAP_X) / 2, *nk.TILT_ANCHOR[1:])),
            (0, 1, 0),
        ),
        (
            neck.jaw,
            gimbal.frame,
            ((sum(nk.JAW_X) / 2, JY, JZ), (sum(nk.JAW_LUG_X) / 2, JY, JZ)),
            (0, 1, 0),
        ),  # its lugs (#838)
    ],
)
def test_each_shank_turns_in_one_part_and_is_threaded_into_the_other(pivot, at, across):
    """1.4 mm off the axis: clear in the turning part's bore (r 1.6), solid in the fixed part's tapping hole (r 1.25);
    2.5 mm off, solid in both (each has a wall round its hole)."""

    def solid(part, p, r):
        return part.isInside(cq.Vector(*(c + r * d for c, d in zip(p, across))))

    t, f = pivot
    assert not solid(t, at[0], 1.4) and solid(t, at[0], 2.5)
    assert solid(f, at[1], 1.4) and solid(f, at[1], 2.5)


ENDS = [(drive, end) for drive in ("tilt", "pan", "jaw") for end in nk.RANGES[drive] if end]
HORN = {"tilt": "tilt horn", "pan": "pan horn", "jaw": "jaw horn"}
DOC = next(d for d in g.MECH if d.endswith(g.MECHANICAL.replace(" ", "-")))  # physics on mechanical alone (#809)


@pytest.fixture(scope="module", params=ENDS, ids=[f"{d} {e:g}" for d, e in ENDS])
def posed(request):
    """(solids, pairs) at a drive's range end in the mechanical Back: every part placed by stages.pose, and the pairs
    whose relative place the drive changed (a horn on its spline, a Core in its Shield aside), built in setup: CI's
    15 s times the test alone."""
    drive, end = request.param
    stage = stages.STAGES[DOC]
    mats = stages.pose(stage, HORN[drive], nk.servo_for(drive, end)).parts
    rest = {n: p.matrix for n, p in stage.parts.items()}
    plugged = {frozenset((f"Core {n}:1", f"Shield {n}:1")) for n in (1, 2)}
    moved = lambda a, b: not np.allclose(np.linalg.inv(rest[a]) @ rest[b], np.linalg.inv(mats[a]) @ mats[b])  # noqa: E731
    pairs = [
        (a, b)
        for a, b in itertools.combinations(stage.parts, 2)
        if frozenset((a, b)) not in ON_SPLINE | plugged and moved(a, b)
    ]
    names = {n for pair in pairs for n in pair}
    return {n: _shape(stage.parts[n]._replace(matrix=mats[n])) for n in names}, pairs


@pytest.mark.model
def test_the_head_clears_the_neck_and_the_jaw_the_head_at_each_end_of_their_ranges(posed):
    """#708: the shorter neck and the jaw under the eyes, at each end of the drive's range, in the mechanical Back (its
    Bones lie inside it): no two parts the drive moves apart overlap, as MuJoCo's sweep checks between them on main."""
    solids, pairs = posed
    assert (overlaps := _overlaps(solids, pairs)) == [], "\n".join(overlaps)


@pytest.fixture(
    scope="module",
    params=list(itertools.product((-45, -22.5, 0, 22.5, 45), (-20, 0, 20), (0, 25))),
    ids=lambda p: f"pan{p[0]:g}-tilt{p[1]:g}-jaw{p[2]:g}",
)
def mechanism_pose(request):
    """Actual new mechanism against every mechanical part over combined commands."""
    from model import skin

    stage = stages.STAGES[DOC]
    rest = {n: p.matrix for n, p in stage.parts.items()}
    pan, tilt, jaw = request.param
    poses = [
        stages.pose(stage, HORN[d], nk.servo_for(d, a)).parts for d, a in (("tilt", tilt), ("pan", pan), ("jaw", jaw))
    ]
    mats = {n: poses[0][n] @ np.linalg.inv(rest[n]) @ poses[1][n] @ np.linalg.inv(rest[n]) @ poses[2][n] for n in rest}
    parts = {n: p for n, p in stage.parts.items() if stages.stem(p.file) not in skin.SHELLS}
    changed = stages.neck_sub().parts.keys() | stages.jaw_sub().parts.keys()
    pairs = [
        (a, b)
        for a, b in itertools.combinations(parts, 2)
        if (a in changed or b in changed) and frozenset((a, b)) not in ON_SPLINE
    ]
    shapes = {n: _shape(p._replace(matrix=mats[n])) for n, p in parts.items()}
    return shapes, pairs


@pytest.mark.model
def test_the_actual_head_mechanism_clears_every_mechanical_part_under_combined_commands(mechanism_pose):
    assert (overlaps := _overlaps(*mechanism_pose)) == [], "\n".join(overlaps)
