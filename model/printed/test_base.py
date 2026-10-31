"""Seam: our PandT base (model/printed/base.py) carries the pan pivot and bearing, the pan servo mounts, the standoffs of
both electronics sets, the wire keeper posts and the battery, PT frame, envelope within ENVELOPE_MM (expected numbers:
docs/research/2026-10-31-model.md [M])."""

import functools

import cadquery as cq

from model.printed import base

ENVELOPE_MM = 1.0
RECEIVERS = [
    (26.0, 40.5),
    (50.0, 40.5),
    (26.0, 63.5),
    (50.0, 63.5),
    (26.0, 73.5),
    (50.0, 73.5),
    (26.0, 96.5),
    (50.0, 96.5),
]
PINNED = [(50.0, 40.5), (26.0, 63.5), (50.0, 73.5), (26.0, 96.5)]  # each shield's diagonal pair


@functools.cache
def solid():
    """Built when the first test runs, not at collection (see test_main_bracket)."""
    return base.build().val()


def inside(*p):
    return solid().isInside(cq.Vector(*p))


def test_envelope_is_the_designers_box_within_a_millimetre():
    box = solid().BoundingBox()
    got = (box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax)
    assert max(abs(a - b) for a, b in zip(got, (-60.0, -25.0, -2.0, 60.0, 135.0, 18.0))) <= ENVELOPE_MM


def test_pan_pivot_and_bearing_recess():
    """r 1.3 pivot hole along Z at (0, 0); the r 9 recess floor at z 0 round an r 4.75 boss up to z 5; plate z -2..3."""
    for z in (-1.8, 2.0, 4.8):
        assert not inside(0, 0, z) and not inside(1.2, 0, z) and inside(1.5, 0, z)
    assert inside(4.6, 0, 4.8) and not inside(4.6, 0, 5.2) and not inside(4.9, 0, 1.0)
    for dx, dy in ((6.0, 0), (0, 8.8), (-6.2, -6.2)):
        assert inside(dx, dy, -0.2) and not inside(dx, dy, 0.2)
    assert inside(9.2, 0, 2.8) and not inside(9.2, 0, 3.2) and inside(9.2, 0, -1.8) and not inside(9.2, 0, -2.2)


def test_pan_servo_mount_screw_holes():
    """r 1.1 holes along Z through the plate under the mount feet."""
    for x, y in ((-32.5, 29.5), (-8.5, 29.5), (-32.5, 57.4), (-8.5, 57.4)):
        assert not inside(x, y, 0.5) and not inside(x + 1.0, y, 0.5) and inside(x + 1.3, y, 0.5), (x, y)


def test_receiver_standoffs_stand_to_z_16_with_a_diagonal_pin_pair():
    """r 3 standoffs to z 16 for both shields; r 1.1 pins up to z 18 on each shield's diagonal, r 1.1 holes on the rest."""
    for x, y in RECEIVERS:
        assert inside(x + 2.8, y, 15.8) and not inside(x + 2.8, y, 16.2) and not inside(x + 3.2, y, 10), (x, y)
        if (x, y) in PINNED:
            assert inside(x, y, 17.5) and inside(x + 1.0, y, 16.5) and not inside(x + 1.3, y, 16.5)
        else:
            assert not inside(x, y, 15.0) and not inside(x + 1.0, y, 8.0) and inside(x + 1.3, y, 8.0)
            assert inside(x, y, 2.8)


def test_switch_standoffs_and_short_posts():
    """r 3 posts with r 1.1 holes: the switch pair to z 13, the back post and the wire keeper posts to z 9."""
    for x, y, top in ((6.0, 68.5, 13.0), (6.0, 92.5, 13.0), (34.5, 108.5, 9.0), (-7.5, 40.5, 9.0), (7.5, 40.5, 9.0)):
        assert inside(x + 2.8, y, top - 0.2) and not inside(x + 2.8, y, top + 0.2) and not inside(x + 3.2, y, 6)
        assert not inside(x, y, top - 1) and not inside(x + 1.0, y, top - 1) and inside(x + 1.3, y, top - 1), (x, y)


def test_battery_pocket_floor_at_z_3():
    """The box's pocket floor is the plate top z 3 down its middle, its walls up to z 13."""
    for y in (75.0, 100.0, 123.0):
        assert inside(-35.75, y, 2.8) and not inside(-35.75, y, 3.2) and not inside(-35.75, y, 12.0)
    assert inside(-51.5, 100, 12.8) and not inside(-51.5, 100, 13.2) and inside(-20.0, 100, 12.8)
