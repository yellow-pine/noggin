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
@pytest.mark.parametrize("stem", ("cervical carrier", "nod plate", "head mount"))
def test_each_head_carrier_is_one_valid_solid(stem):
    shape = _built(stem)
    assert shape.isValid() and len(shape.Solids()) == 1


@pytest.mark.model
def test_the_fixed_cervical_support_clears_the_pack_and_lid_and_bolts_to_the_floor():
    from model.printed import base

    carrier = _built("cervical carrier")
    parts = stages.base_sub().parts
    shapes = {"carrier": carrier, **{n: _shape(p) for n, p in parts.items()}}
    overlaps = _overlaps(shapes, [("carrier", n) for n in parts])
    assert overlaps == [], "\n".join(overlaps)
    lid, torso = base.lid(mechanical=True).val(), base.torso(mechanical=True).val()
    assert carrier.intersect(lid).Volume() < 0.01
    for x, y in nk.CARRIER_FEET:
        assert not carrier.isInside(cq.Vector(x, y, sum(nk.MOUNT_Z) / 2))
        assert not torso.isInside(cq.Vector(x, y, nk.MOUNT_Z[0] - 1))


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


@pytest.mark.model
def test_the_reaction_anchor_holds_the_actual_standard_servo_at_stall():
    """#1039: the carrier's strut from its R rail back to the reduction's anchor, longer since the rails run straight:
    SF 2 in PETG across its layers on its actual sections. The bar's worst force (the bar's own test's) acts at the
    bar's middle on the anchor's pin, along the bar wherever the sweep leans it: it pulls the strut, and bends it by
    the bar's lean and by the bar's place inboard of it. The rails it hangs on are not sectioned here."""
    solid, mat = _built("cervical carrier"), g.MATERIALS[g.PRINTED["cervical carrier"][1]]
    _, ay, az = nk.TILT_ANCHOR
    (y0, z0), (y1, z1) = nk.CERVICAL_PATH[3], nk.CERVICAL_PATH[2]
    t = (az - z0) / (z1 - z0)
    x = nk.REACTION_TAP_X[1] - 5.0
    a, b = np.array((x, y0 + t * (y1 - y0), az)), np.array((x, ay, az))  # as cervical_carrier() draws it
    along, pin = (b - a) / np.linalg.norm(b - a), np.array((sum(nk.REACTION_BAR_X) / 2, ay, az))
    force = sim.limits("tilt horn")["stall_kgf_cm"] * beams.G * 10 / np.linalg.norm(nk.TILT_CRANK)
    force /= math.sin(math.radians(_tilt_angle()))
    pulls = []  # the bar's direction as the fixed carrier sees it: the case's, turned back by the head's turn
    for s in nk._sweep("tilt"):
        rocker, p, q = nk.TILT_LOOP(s)
        pulls.append(linkage.rotation(g.X, -rocker, (0, 0, 0))[:3, :3] @ np.subtract(p, q) / math.dist(p, q) * force)
    across = np.cross(along, g.Z) / np.linalg.norm(np.cross(along, g.Z))
    for t in (0.15, 0.3, 0.5, 0.7, 0.85):
        cut = _section(solid, tuple(a + (b - a) * t), tuple(along), tuple(across), (13, 13))
        area, centre = cut.Volume() / 0.01, np.array(cut.Center().toTuple())
        inertia = np.array(cq.Shape.matrixOfInertia(cut)) / 0.01
        corners = np.array([v.toTuple() for v in cut.Vertices()]) - centre

        def stress(pull):
            moment = np.cross(pin - centre, pull)
            bent = sum(
                abs(moment @ axis) * abs(corners @ np.cross(along, axis)).max() / (axis @ inertia @ axis)
                for axis in (across, np.array(g.Z, float))
            )
            return abs(pull @ along) / area + bent

        assert mat["tensile_mpa"]["z"] / max(map(stress, pulls)) >= beams.MIN_SF, t


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
    blocked anywhere along them: every section bends under at most the bar's worst moment about the pivot over the
    jaw's sweep, in the jaw's plane, and pulls with its worst force (the crank's tangent force over the sine of the
    crank-to-bar angle). Along each span and at each joint between two. On the mechanical part (ADR 0020)."""
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
        for at, along in cuts:
            u = np.subtract(g.X, along * along[0])
            u /= np.linalg.norm(u)  # the bending axis, x in the section's plane
            cut = _section(solid, tuple(at), tuple(along), tuple(u), (16, 16))
            area, centre = cut.Volume() / 0.01, np.array(cut.Center().toTuple())
            inertia = u @ np.array(cq.Shape.matrixOfInertia(cut)) @ u / 0.01
            fibre = max(abs((np.array(v.toTuple()) - centre) @ np.cross(along, u)) for v in cut.Vertices())
            sf = mat["tensile_mpa"]["z"] / (force / area + moment * fibre / inertia)
            if sf < beams.MIN_SF:
                weak.append((tuple(np.round(at, 1)), round(sf, 2)))
    assert weak == []


@pytest.mark.model
def test_the_jaw_carriers_chains_meet_at_the_chin_without_a_sliver():
    """#850: the two chains ending together at the chin met in a 0.015 mm edge, which Linux's OCCT read back from a
    document's STEP as an invalid jaw (model/test_ours.py), once nothing fused onto the chin covered it. No edge of the
    Bone jaw within 9 mm of the chin is that marginal."""
    chin = np.array(nk.JAW_CHIN)
    edges = [e for e in _built("jaw").Edges() if np.linalg.norm(np.array(e.Center().toTuple()) - chin) < 9.0]
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
