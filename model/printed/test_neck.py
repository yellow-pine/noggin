"""Seam: the next Mech's neck and jaw parts (model/printed/neck.py) as model/stages.py places them at rest, under the eye
gimbal in the head's frame: no two overlap, and the shanks' bores and tapping holes line up across each pivot."""

import itertools

import cadquery as cq
import pytest

from model import envelopes, stages
from model import neck as nk
from model.printed import PARTS, neck
from model.printed.test_gimbal import ON_SPLINE, _overlaps

ON_SPLINE = ON_SPLINE | {frozenset((f"next {d} servo:1", f"next {d} horn:1")) for d in nk.drives()}


def _shape(p):
    stem = stages.stem(p.file)
    m = cq.Matrix([list(map(float, row)) for row in p.matrix[:3]])
    return (PARTS.get(stem) or envelopes.ENVELOPES[stem])().val().transformGeometry(m)


@pytest.mark.build
def test_no_two_parts_overlap_at_rest():
    shapes = {n: _shape(p) for sub in (stages.next_neck(), stages.next_eyes()) for n, p in sub.parts.items()}
    hits = [
        f"{a} / {b}: {v:.2f} mm3"
        for a, b in itertools.combinations(shapes, 2)
        if frozenset((a, b)) not in ON_SPLINE and (v := _overlaps(shapes[a], shapes[b])) > 0.01
    ]
    assert hits == []


Y, Z = nk.AXIS
JY, JZ = nk.JAW


@pytest.mark.build
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
