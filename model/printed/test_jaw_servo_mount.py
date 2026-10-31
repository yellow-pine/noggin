"""Seam: our jaw servo mount (model/printed/jaw_servo_mount.py) meets the measured interfaces exactly and the designer's
envelope within ENVELOPE_MM, probed on the CadQuery solid (expected numbers: docs/research/2026-10-31-model.md [M])."""

import functools

import cadquery as cq

from model.printed import jaw_servo_mount

ENVELOPE_MM = 1.0


@functools.cache
def solid():
    """Built when the first test runs, not at collection (see test_main_bracket.solid)."""
    return jaw_servo_mount.build().val()


def inside(*p):
    return solid().isInside(cq.Vector(*p))


def test_envelope_is_the_designers_box_within_a_millimetre():
    box = solid().BoundingBox()
    lo, hi = (box.xmin, box.ymin, box.zmin), (box.xmax, box.ymax, box.zmax)
    designer = (63.42, -52.6, 12.0), (78.42, -30.6, 44.66)
    assert max(abs(a - b) for a, b in zip(lo + hi, designer[0] + designer[1])) <= ENVELOPE_MM


def test_feet_take_the_bracket_rail_screws():
    """r 1.35 holes along Z through the foot (z 18..21) at the bracket rail's (65.92, -35.6) and (70.92, -35.6)."""
    for x, y in ((65.92, -35.6), (70.92, -35.6)):
        for z in (18.2, 19.5, 20.8):
            assert not inside(x, y, z) and not inside(x + 1.2, y, z) and not inside(x, y - 1.2, z)
            assert inside(x + 1.55, y, z) and inside(x, y + 1.55, z), (x, y, z)
    assert inside(68.4, -35.6, 18.2) and not inside(68.4, -35.6, 17.8) and not inside(68.4, -35.6, 21.2)


def test_tabs_take_the_jaw_servo_screws():
    """r 1.1 holes along X through the wall (x 73.42..78.42) at the jaw servo's tab holes (y -48.6, z 14.43 / 42.23)."""
    for y, z in ((-48.6, 14.43), (-48.6, 42.23)):
        for x in (73.6, 75.9, 78.2):
            assert not inside(x, y, z) and not inside(x, y + 0.9, z) and not inside(x, y, z - 0.9)
            assert inside(x, y + 1.3, z) and inside(x, y, z + 1.3), (x, y, z)


def test_wall_leaves_the_servo_window():
    """The servo body sits in the window y < -42.1 between the tabs (z 17..39.66)."""
    for z in (18.0, 28.0, 39.0):
        assert inside(75.9, -41.9, z) and not inside(75.9, -42.3, z), z
    assert inside(75.9, -48.6, 16.8) and not inside(75.9, -48.6, 17.2)
    assert inside(75.9, -48.6, 39.86) and not inside(75.9, -48.6, 39.46)
    assert inside(73.62, -35.0, 30.0) and not inside(73.22, -35.0, 30.0)
