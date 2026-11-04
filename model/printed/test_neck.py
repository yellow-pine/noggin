"""Seam: the Mech's neck and jaw parts (model/printed/neck.py) as model/stages.py places them at rest, under the eye
gimbal in the head's frame: no two overlap, and the shanks' bores and tapping holes line up across each pivot."""

import functools
import itertools

import cadquery as cq
import numpy as np
import pytest

from model import envelopes, stages
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
def test_the_bearing_carries_the_head_without_loading_a_servo_spline():
    sub = stages.neck_sub()
    plate, bearing, mount = (_shape(sub.parts[n]) for n in ("nod plate:1", "pan bearing:1", "head mount:1"))
    assert plate.distance(bearing) < 1e-6 and bearing.distance(mount) < 1e-6
    assert plate.intersect(bearing).Volume() < 1e-6
    assert bearing.intersect(mount).Volume() < 1e-6
    # Independent contact rings, not a hidden solid shaft down the canal or through the bearing bore.
    py = nk.HEAD_AXES["pan"][0][1]
    assert not bearing.isInside(cq.Vector(0, py, sum(nk.BEARING_Z) / 2))


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
            ((20.4, *nk.HEAD_AXES["tilt"][0][1:]), (16, *nk.HEAD_AXES["tilt"][0][1:])),
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
