"""Seam: our wire holder (model/printed/wire_holder.py) sits on the base's wire keeper posts (+-7.5, 40.5) in the
PT frame, envelope within ENVELOPE_MM (expected numbers: docs/research/2026-10-31-model.md [M])."""

import functools

import cadquery as cq

from model.printed import wire_holder

ENVELOPE_MM = 1.0


@functools.cache
def solid():
    """Built when the first test runs, not at collection (see test_main_bracket)."""
    return wire_holder.build().val()


def test_envelope_is_the_designers_box_within_a_millimetre():
    box = solid().BoundingBox()
    got = (box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax)
    assert max(abs(a - b) for a, b in zip(got, (-10.5, 37.5, 9.0, 10.5, 43.5, 12.0))) <= ENVELOPE_MM


def test_holes_drop_over_the_wire_keeper_posts():
    """r 1.35 holes along Z through the 9..12 strap at (+-7.5, 40.5)."""
    s = solid()
    for x in (-7.5, 7.5):
        for z in (9.2, 10.5, 11.8):
            assert not s.isInside(cq.Vector(x, 40.5, z)) and not s.isInside(cq.Vector(x + 1.25, 40.5, z))
            assert s.isInside(cq.Vector(x + 1.55, 40.5, z)) and s.isInside(cq.Vector(x - 1.55, 40.5, z)), (x, z)
