"""Seam: our PandT upright v2 (model/printed/upright.py) stands in the pan base's slot, carries the tilt pivot and the pan
bar's lever, PT frame, envelope within ENVELOPE_MM (expected numbers: docs/research/2026-10-31-model.md [M],
geometry.PT_LEVER_HOLES)."""

import functools

import cadquery as cq

from model.printed import upright

ENVELOPE_MM = 1.0


@functools.cache
def solid():
    """Built when the first test runs, not at collection (see test_main_bracket)."""
    return upright.build().val()


def inside(*p):
    return solid().isInside(cq.Vector(*p))


def test_envelope_is_the_designers_box_within_a_millimetre():
    box = solid().BoundingBox()
    got = (box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax)
    assert max(abs(a - b) for a, b in zip(got, (-11.0, -15.5, 3.5, 11.0, 28.0, 35.9))) <= ENVELOPE_MM


def test_wall_carries_the_tilt_pivot():
    """r 1.1 hole along X through the wall at (y -13, z 33.4), the tilt axis with upright v2."""
    for x in (-10.8, 0.0, 10.8):
        assert not inside(x, -13, 33.4) and not inside(x, -13 + 1.0, 33.4) and not inside(x, -13, 33.4 - 1.0)
        assert inside(x, -13 + 1.3, 33.4) and inside(x, -13, 33.4 - 1.3) and inside(x, -13, 33.4 + 1.3), x


def test_wall_drops_through_the_pan_base_slot_to_its_underside():
    """The wall's x -11..11, y -15.5..-10.5 section goes down to z 3.5, the plate's underside."""
    for x, y in ((-10.8, -15.3), (10.8, -10.7), (0, -13)):
        assert inside(x, y, 3.7) and not inside(x, y, 3.3)
    assert not inside(11.2, -13, 6) and not inside(0, -15.7, 6) and not inside(0, -10.3, 6)


def test_lever_takes_the_pan_bar_screw():
    """r 1.1 hole along Z through the x -8..-3 lever at (-5.5, 25.5), its top z 26.8."""
    for z in (21.0, 24.0, 26.6):
        assert not inside(-5.5, 25.5, z) and not inside(-5.5 + 1.0, 25.5, z)
        assert inside(-5.5 + 1.3, 25.5, z) and inside(-5.5, 25.5 - 1.3, z), z
    assert not inside(-5.5 + 1.3, 25.5, 27.0)
