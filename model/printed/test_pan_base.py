"""Seam: our PandT pan base (model/printed/pan_base.py) turns on the pan pivot over the bearing and carries the tilt
servo on its tower, PT frame, envelope within ENVELOPE_MM (expected numbers: docs/research/2026-10-31-model.md [M])."""

import functools

import cadquery as cq

from model.printed import pan_base

ENVELOPE_MM = 1.0


@functools.cache
def solid():
    """Built when the first test runs, not at collection (see test_main_bracket)."""
    return pan_base.build().val()


def inside(*p):
    return solid().isInside(cq.Vector(*p))


def test_envelope_is_the_designers_box_within_a_millimetre():
    box = solid().BoundingBox()
    got = (box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax)
    assert max(abs(a - b) for a, b in zip(got, (-25.0, -25.0, 3.5, 25.0, 26.0, 24.26))) <= ENVELOPE_MM


def test_plate_turns_on_the_m3_pan_pivot_over_the_bearing():
    """Plate z 3.5..8.5; the r 1.75 M3 pivot along Z through (0, 0); the r 9 recess underneath takes the bearing to z 5.5."""
    for z in (3.7, 6.0, 8.3):
        assert not inside(0, 0, z) and not inside(1.6, 0, z) and inside(-1.95, 0, 6.0)
    assert inside(12, 0, 3.7) and inside(12, 0, 8.3) and not inside(12, 0, 3.3) and not inside(12, 0, 8.7)
    for dx, dy in ((8.8, 0), (0, 8.8), (-6.2, -6.2)):
        assert not inside(dx, dy, 5.3) and inside(dx, dy, 5.7)
    assert inside(9.2, 0, 3.7)


def test_tower_takes_the_tilt_servo_tab_screws():
    """The x 20..25 tower: r 1.1 tab holes along X at (y -5.04, z 18.38) and (y 22.54, z 18.38)."""
    for y in (-5.04, 22.54):
        for x in (20.2, 22.5, 24.8):
            assert not inside(x, y, 18.38) and not inside(x, y + 1.0, 18.38) and not inside(x, y, 18.38 - 1.0)
            assert inside(x, y + 1.3, 18.38) and inside(x, y - 1.3, 18.38) and inside(x, y, 18.38 + 1.3), (x, y)
        assert not inside(19.8, y, 18.38) and not inside(25.2, y, 18.38)
