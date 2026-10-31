"""Seam: our PandT bearing block (model/printed/bearing_block.py), the 18 x 5.5 ring in the base's r 9 recess about the
pan axis, PT frame, envelope within ENVELOPE_MM (expected numbers: docs/research/2026-10-31-model.md [M])."""

import functools

import cadquery as cq

from model.printed import bearing_block

ENVELOPE_MM = 1.0


@functools.cache
def solid():
    """Built when the first test runs, not at collection (see test_main_bracket)."""
    return bearing_block.build().val()


def test_envelope_is_the_designers_box_within_a_millimetre():
    box = solid().BoundingBox()
    got = (box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax)
    assert max(abs(a - b) for a, b in zip(got, (-9.0, -9.0, 0.0, 9.0, 9.0, 5.5))) <= ENVELOPE_MM


def test_ring_is_eighteen_across_round_the_pan_axis_over_the_base_boss():
    """Outside r 9 in the base recess, bore r 5 over the base's r 4.75 boss, z 0..5.5."""
    s = solid()
    for z in (0.2, 2.75, 5.3):
        for dx, dy in ((1, 0), (0, 1), (-0.7071, -0.7071)):
            assert not s.isInside(cq.Vector(0, 0, z)) and not s.isInside(cq.Vector(4.8 * dx, 4.8 * dy, z))
            assert s.isInside(cq.Vector(5.2 * dx, 5.2 * dy, z)) and s.isInside(cq.Vector(8.8 * dx, 8.8 * dy, z))
            assert not s.isInside(cq.Vector(9.2 * dx, 9.2 * dy, z))
    assert not s.isInside(cq.Vector(7, 0, 5.7)) and not s.isInside(cq.Vector(7, 0, -0.2))
