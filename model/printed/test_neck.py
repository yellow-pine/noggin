"""Seam: the next Mech's neck and jaw parts (model/printed/neck.py) as model/stages.py places them at rest, under the eye
gimbal in the head's frame: no two overlap, and the shanks' bores and tapping holes line up across each pivot."""

import functools
import itertools

import cadquery as cq
import pytest

from model import envelopes, stages
from model import neck as nk
from model.printed import PARTS, gimbal, neck
from model.printed.test_gimbal import ON_SPLINE, _overlaps

ON_SPLINE = ON_SPLINE | {frozenset((f"next {d} servo:1", f"next {d} horn:1")) for d in nk.drives()}


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
    return {n: _shape(p) for sub in (stages.next_neck(), stages.next_eyes()) for n, p in sub.parts.items()}


@pytest.mark.model
def test_no_two_parts_overlap_at_rest(shapes):
    pairs = [(a, b) for a, b in itertools.combinations(shapes, 2) if frozenset((a, b)) not in ON_SPLINE]
    assert _overlaps(shapes, pairs) == []


Y, Z = nk.AXIS
JY, JZ = nk.JAW


@pytest.mark.model
@pytest.mark.parametrize(
    "turns, fixed, at, across",
    [  # (the turning part, the fixed one, a point on the axis inside each, a direction across the axis)
        (neck.yoke, neck.mount, ((0, Y, -108), (0, Y, -112)), (1, 0, 0)),
        (neck.head_mount, neck.yoke, ((15, Y, Z), (11, Y, Z)), (0, 1, 0)),
        (neck.jaw, neck.head_mount, ((20, JY, JZ), (16, JY, JZ)), (0, 1, 0)),
    ],
)
def test_each_shank_turns_in_one_part_and_is_threaded_into_the_other(turns, fixed, at, across):
    """1.4 mm off the axis: clear in the turning part's bore (r 1.6), solid in the fixed part's tapping hole (r 1.25);
    2.5 mm off, solid in both (each has a wall round its hole)."""

    def solid(part, p, r):
        return part.val().isInside(cq.Vector(*(c + r * d for c, d in zip(p, across))))

    t, f = turns(), fixed()
    assert not solid(t, at[0], 1.4) and solid(t, at[0], 2.5)
    assert solid(f, at[1], 1.4) and solid(f, at[1], 2.5)
