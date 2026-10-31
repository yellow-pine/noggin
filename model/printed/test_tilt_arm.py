"""Seam: our PandT tilt arm (model/printed/tilt_arm.py) hangs on the tilt pivot and carries the tilt bar's lever screw, in
the designer's STL frame (PT frame at the v1 height: placed TILT_ARM_SHIFT_Z higher with upright v2), envelope within
ENVELOPE_MM (expected numbers: docs/research/2026-10-31-model.md [M], geometry.PT_LEVER_HOLES)."""

import functools

import cadquery as cq

from model.printed import tilt_arm

ENVELOPE_MM = 1.0


@functools.cache
def solid():
    """Built when the first test runs, not at collection (see test_main_bracket)."""
    return tilt_arm.build().val()


def inside(*p):
    return solid().isInside(cq.Vector(*p))


def test_envelope_is_the_designers_box_within_a_millimetre():
    box = solid().BoundingBox()
    got = (box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax)
    assert max(abs(a - b) for a, b in zip(got, (-14.0, -20.5, 25.9, 14.0, 29.5, 35.9))) <= ENVELOPE_MM


def test_side_ears_take_the_tilt_pivot_screws():
    """r 1.35 holes along X at (y -13, z 28.4) through the ears at x +-13 (the tilt axis z 33.4 once raised 5)."""
    for x in (-13.8, -12.5, 12.5, 13.8):
        assert not inside(x, -13, 28.4) and not inside(x, -13 + 1.25, 28.4) and not inside(x, -13, 28.4 - 1.25)
        assert inside(x, -13 + 1.55, 28.4) and inside(x, -13 - 1.55, 28.4) and inside(x, -13, 28.4 + 1.55), x
    assert not inside(0, -13, 28.4) and not inside(10.8, -13, 28.4)


def test_lever_takes_the_tilt_bar_screw():
    """r 1.1 hole along X through the x 3..8 lever at (y 26.5, z 33.4) (geometry's lever hole less the 5 mm raise)."""
    for x in (3.2, 5.5, 7.8):
        assert not inside(x, 26.5, 33.4) and not inside(x, 26.5 + 1.0, 33.4) and not inside(x, 26.5, 33.4 - 1.0)
        assert inside(x, 26.5 - 1.3, 33.4) and inside(x, 26.5, 33.4 + 1.3) and inside(x, 26.5, 33.4 - 1.3), x
    assert not inside(2.8, 26.5, 31.5) and not inside(8.2, 26.5, 31.5)
