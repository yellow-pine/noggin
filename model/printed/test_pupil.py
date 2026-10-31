"""Seam: our pupil (model/printed/pupil.py) is the cap of the eyeball's r 20.5 sphere in front of the eyeball's
flat face (z -18.5) about the R eye centre (the designer's frame), within ENVELOPE_MM of the designer's box (numbers:
measured on the designer's STLs, the eyeball's box x +-20.5, z -18.5..5)."""

import functools

import cadquery as cq

from model import geometry as g
from model.printed import pupil

ENVELOPE_MM = 1.0


@functools.cache
def solid():
    """Built when the first test runs, not at collection (CadQuery's OCCT threads vs the gate's forks)."""
    return pupil.build().val()


def inside(*p):
    return solid().isInside(cq.Vector(*p))


def test_envelope_is_the_designers_box_within_a_millimetre():
    b = solid().BoundingBox()
    designer = (50.17, -8.83, -20.49, 67.83, 8.83, -18.5)
    assert max(abs(a - d) for a, d in zip((b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax), designer)) <= ENVELOPE_MM


def test_front_is_the_eyeball_sphere_and_the_back_sits_on_its_flat_face():
    x0, y0, _ = g.EYE_R
    for r, front in ((0.0, -20.5), (5.0, -19.88), (8.0, -18.88)):
        assert inside(x0 + r, y0, front + 0.1) and not inside(x0 + r, y0, front - 0.1), r
        assert inside(x0, y0 + r, front + 0.1) and not inside(x0, y0 + r, front - 0.1), r
    assert inside(x0, y0, -18.6) and not inside(x0, y0, -18.4)
