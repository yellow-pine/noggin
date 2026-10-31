"""Seam: our eyes wire keeper (model/printed/wire_keeper.py) drops over the base's cable holder posts (x 29.5, z 51 and
75) in the eyes base frame, envelope within ENVELOPE_MM (expected numbers: docs/research/2026-10-31-model.md [M])."""

import functools

import cadquery as cq

from model.printed import wire_keeper

ENVELOPE_MM = 1.0


@functools.cache
def solid():
    """Built when the first test runs, not at collection (see test_main_bracket)."""
    return wire_keeper.build().val()


def test_envelope_is_the_designers_box_within_a_millimetre():
    box = solid().BoundingBox()
    got = (box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax)
    assert max(abs(a - b) for a, b in zip(got, (26.5, -22.6, 48.0, 32.5, -19.6, 78.0))) <= ENVELOPE_MM


def test_holes_drop_over_the_cable_holder_posts():
    """r 1.35 holes along Y through the -22.6..-19.6 strap at (29.5, z 51) and (29.5, z 75)."""
    s = solid()
    for z in (51.0, 75.0):
        for y in (-22.4, -21.1, -19.8):
            assert not s.isInside(cq.Vector(29.5, y, z)) and not s.isInside(cq.Vector(29.5, y, z + 1.25))
            assert s.isInside(cq.Vector(29.5, y, z + 1.55)) and s.isInside(cq.Vector(29.5, y, z - 1.55)), (y, z)
