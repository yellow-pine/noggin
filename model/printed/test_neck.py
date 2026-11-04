"""Seam: the Mech's neck and jaw parts (model/printed/neck.py) as model/stages.py places them at rest, under the eye
gimbal in the head's frame: no two overlap, and the shanks' bores and tapping holes line up across each pivot."""

import functools
import itertools
import math

import cadquery as cq
import numpy as np
import pytest

from model import beams, envelopes, sim, stages
from model import geometry as g
from model import neck as nk
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


@pytest.mark.model
def test_the_tilt_reaction_bar_holds_the_actual_standard_servo_at_stall():
    """The bent reaction bar keeps the existing SF2 gate at the standard motor's actual 5 V stall force."""
    from model.printed.test_gimbal import _slice

    solid, mat = _built("tilt reaction bar"), g.MATERIALS[g.PRINTED["tilt reaction bar"][1]]
    angle = min(nk.transmission("tilt", s) for s in np.linspace(-20, 20, 41))
    force = sim.limits("tilt horn")["stall_kgf_cm"] * beams.G * 10 / np.linalg.norm(nk.TILT_ARM)
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
    radius = np.linalg.norm(nk.TILT_ARM)
    tangent = sim.limits("tilt horn")["stall_kgf_cm"] * beams.G * 10 / radius
    angle = min(nk.transmission("tilt", s) for s in np.linspace(-20, 20, 41))
    force = tangent / math.sin(math.radians(angle))
    for t in (0.25, 0.4, 0.6, 0.8):
        area, _, bend, half = _slice(solid, shaft[1:], pin[1:], t)
        stress = force / area + tangent * radius * (1 - t) * half / bend
        assert mat["tensile_mpa"]["z"] / stress >= beams.MIN_SF, t
    a, b = (shaft[0], *pin[1:]), (sum(nk.REACTION_BAR_X) / 2, *pin[1:])
    assert _bending_sf(solid, a, b, force, "z", math.dist(a, b), ts=(0.05, 0.25, 0.5, 0.75)) >= beams.MIN_SF


@pytest.fixture(scope="module")
def saddle():
    return _built("nod plate")


@pytest.mark.model
@pytest.mark.parametrize("member", ("mast", "header", "tab beam"))
def test_the_standard_servo_saddle_holds_its_actual_stall_reaction(saddle, member):
    """Actual CAD sections, including eccentric axial loading; the finished anatomical head load stays on its bearing."""
    shaft, mat = nk.TILT_SHAFT, g.MATERIALS[g.PRINTED["nod plate"][1]]
    torque = sim.limits("tilt horn")["stall_kgf_cm"] * beams.G * 10
    angle = min(nk.transmission("tilt", s) for s in np.linspace(-20, 20, 41))
    force = torque / np.linalg.norm(nk.TILT_ARM) / math.sin(math.radians(angle))
    z = (shaft[2] + nk.HEAD_AXES["tilt"][0][2]) / 2
    mast = saddle.intersect(cq.Workplane("XY", origin=(0, 0, z)).rect(400, 400).extrude(0.005, both=True).val())
    if member == "mast":
        cut, axis, bend = mast, 0, 1
        moment = force * abs(mast.Center().x - shaft[0])
    else:
        # Peak reaction at one tab combines the bar force and the motor's case torque over its tab spacing.
        force = force / 2 + torque / (34.1 + 13.4)
        top = saddle.BoundingBox().zmax
        if member == "header":
            x = mast.BoundingBox().xmin - 1
            plane, axis, bend = cq.Plane(origin=(x, shaft[1], top - 10), xDir=(0, 1, 0), normal=(1, 0, 0)), 2, 1
            moment = force * abs(x - (shaft[0] + 11.9))
            cut = saddle.intersect(cq.Workplane(plane).rect(40, 40).extrude(0.005, both=True).val())
        else:
            y = shaft[1] + 17.05
            plane, axis, bend = cq.Plane(origin=(shaft[0] + 15.4, y, top - 10), xDir=(1, 0, 0), normal=(0, 1, 0)), 2, 0
            moment = force * abs(shaft[1] + 34.1 - y)
            cut = saddle.intersect(cq.Workplane(plane).rect(20, 40).extrude(0.005, both=True).val())
    inertia = np.asarray(cq.Shape.matrixOfInertia(cut))[bend, bend] / 0.01
    box, centre = cut.BoundingBox(), cut.Center().toTuple()[axis]
    half = max(getattr(box, "xyz"[axis] + "max") - centre, centre - getattr(box, "xyz"[axis] + "min"))
    stress = force / (cut.Volume() / 0.01) + moment * half / inertia
    assert mat["tensile_mpa"]["z"] / stress >= beams.MIN_SF


@pytest.fixture(scope="module")
def pan_wire_candidate():
    return {n: p.val() for n, p in neck.pan_wire_candidate().items()}


@pytest.mark.model
def test_the_c0_pan_bearing_candidate_has_real_retention_and_an_open_wire_path(pan_wire_candidate):
    """Unaccepted component study: the shaft, caps and bearing leave a full 6 mm cable corridor."""
    assert set(pan_wire_candidate) == {"spindle", "fixed cap", "bearing", "head carrier", "moving cap"}
    for solid in pan_wire_candidate.values():
        assert solid.isValid() and len(solid.Solids()) == 1 and solid.Volume() > 0
    y, bottom = nk.HEAD_AXES["tilt"][0][1], -36.0
    cable = gimbal.cyl("z", (0, y, 0), 3, (bottom - 5, bottom + 12)).val()
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
            ((12.4, *nk.HEAD_AXES["tilt"][0][1:]), (8, *nk.HEAD_AXES["tilt"][0][1:])),
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
    overlaps = _overlaps(*posed)
    assert overlaps == [], "\n".join(overlaps)


@pytest.fixture(
    scope="module",
    params=list(itertools.product((-45, -22.5, 0, 22.5, 45), (-20, 0, 20), (0, 25))),
    ids=lambda p: f"pan{p[0]:g}-tilt{p[1]:g}-jaw{p[2]:g}",
)
def mechanism_pose(request):
    """Actual new mechanism against every mechanical part over combined commands; the Shell gate above remains."""
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
