"""Seam: our lid bar and lid crank (model/printed/lid_bar.py) meet the measured interfaces exactly and the
designer's envelope within ENVELOPE_MM, probed on the CadQuery solids (numbers: model/geometry.py STL_LOCAL, the circle
fits on the designer's holes)."""

import functools

import cadquery as cq

from model.printed import lid_bar

ENVELOPE_MM = 1.0


@functools.cache
def solid(crank):
    """Built when the first test runs, not at collection (CadQuery's OCCT threads vs the gate's forks)."""
    return (lid_bar.crank if crank else lid_bar.build)().val()


def bbox(crank):
    b = solid(crank).BoundingBox()
    return b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax


def inside(crank, *p):
    return solid(crank).isInside(cq.Vector(*p))


def test_envelopes_are_the_designers_boxes_within_a_millimetre():
    for crank, designer in ((False, (-23, -2.5, 0, 23, 2.5, 3)), (True, (-23, -2.5, 0, 23, 2.5, 6))):
        assert max(abs(a - b) for a, b in zip(bbox(crank), designer)) <= ENVELOPE_MM


def hole(crank, x, z, r):
    """An r hole along Z at (x, 0): open at its centre and r - 0.2 out, wall at r + 0.2."""
    assert not inside(crank, x, 0, z) and not inside(crank, x + r - 0.2, 0, z) and not inside(crank, x, r - 0.2, z)
    assert inside(crank, x + r + 0.2, 0, z) and inside(crank, x, -r - 0.2, z), (crank, x, z)


def test_holes_are_41_mm_apart_the_horn_screw_small_and_the_lid_screw_large():
    hole(False, 20.5, 1.5, 1.1)
    hole(False, -20.5, 1.5, 1.35)
    hole(True, 20.5, 1.5, 1.1)
    hole(True, -20.5, 4.5, 1.35)


def test_crank_steps_its_lid_end_up_three_millimetres():
    assert inside(True, -20.5, 2, 4.5) and not inside(True, -20.5, 2, 1.5)
    assert inside(True, 10, 0, 1.5) and not inside(True, 10, 0, 4.5)
