"""Seam: our eyeball bar (model/printed/eyeball_bar.py) meets the measured interfaces exactly and the designer's envelope
within ENVELOPE_MM, probed on the CadQuery solid (numbers: docs/research/2026-10-31-model.md [M], geometry.py)."""

import functools

import cadquery as cq

from model import geometry as g
from model.printed import eyeball_bar

ENVELOPE_MM = 1.0


@functools.cache
def solid():
    """Built when the first test runs, not at collection (CadQuery's OCCT threads vs the sweep's forks)."""
    return eyeball_bar.build().val()


def inside(*p):
    return solid().isInside(cq.Vector(*p))


def test_envelope_is_the_designers_box_within_a_millimetre():
    b = solid().BoundingBox()
    designer = (-12.5, 2.5, -2.5, -7.5, 5.5, 29.5)
    assert max(abs(a - d) for a, d in zip((b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax), designer)) <= ENVELOPE_MM


def test_pin_holes_along_y_on_the_eyeball_and_eye_horn_pins():
    """x=-10, y 2.5..5.5: r 1.25 at z 0 (the eyeball end), r 1.05 at z 27 (the eye-horn end)."""
    assert [(p[0], p[2]) for p in g.EYEBALL_BAR_PINS] == [(-10.0, 27.0), (-10.0, 0.0)]
    for z, r in ((0.0, 1.25), (27.0, 1.05)):
        for y in (2.7, 4.0, 5.3):
            assert not inside(-10, y, z) and not inside(-10 + r - 0.2, y, z) and not inside(-10, y, z - r + 0.2)
            assert inside(-10 + r + 0.2, y, z) and inside(-10 - r - 0.2, y, z), (z, y)
        assert not inside(-11.5, 2.3, z) and not inside(-11.5, 5.7, z)
