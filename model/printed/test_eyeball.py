"""Seam: our L and R eyeballs (model/printed/eyeball.py) turn on the eyeball pivot (Y through the eye centre) inside the
lids, carry the pupil and the eyeball bar's pin, and stay within ENVELOPE_MM of the designer's boxes, probed on the
CadQuery solids (numbers: docs/research/2026-10-31-model.md [M], geometry.py; the radii and hole sizes measured on the
designer's eyeballs)."""

import functools

import cadquery as cq

from model import geometry as g
from model.printed import eyeball

ENVELOPE_MM = 1.0
DESIGNER = {"L": (-20.5, -20.5, -18.5, 20.5, 20.28, 5.0), "R": (38.5, -20.5, -18.5, 79.5, 20.28, 5.0)}


@functools.cache
def solid(side):
    """Built when the first test runs, not at collection (CadQuery's OCCT threads vs the gate's forks)."""
    return eyeball.build(side).val()


def inside(side, *p):
    return solid(side).isInside(cq.Vector(*p))


def eye(side):
    return g.EYE_L if side == "L" else g.EYE_R


def test_envelopes_are_the_designers_boxes_within_a_millimetre():
    for side, designer in DESIGNER.items():
        b = solid(side).BoundingBox()
        got = (b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax)
        assert max(abs(a - d) for a, d in zip(got, designer)) <= ENVELOPE_MM, side


def test_outside_is_the_r_20_5_ball_the_lids_clear_by_half_a_millimetre():
    for side in DESIGNER:
        x0, y0, z0 = eye(side)
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0.6, -0.8), (0, -1, 0), (0.6, -0.8, 0)):
            assert inside(side, x0 + 20.3 * dx, y0 + 20.3 * dy, z0 + 20.3 * dz), (side, dx, dy, dz)
            assert not inside(side, x0 + 20.7 * dx, y0 + 20.7 * dy, z0 + 20.7 * dz), (side, dx, dy, dz)


def test_front_flat_seats_the_pupil_and_the_back_is_flat_at_z_5():
    for side in DESIGNER:
        x0, y0, _ = eye(side)
        assert inside(side, x0, y0 - 5, -18.3) and not inside(side, x0, y0 - 5, -18.7)
        assert inside(side, x0 - 15, y0 + 10, 4.8) and not inside(side, x0 - 15, y0 + 10, 5.2)


def test_pivot_hole_along_y_takes_the_main_brackets_m3_screw():
    """r 1.3 along Y at the eye centre, into the solid lower quadrant."""
    assert g.PIVOTS["l_eye"]["axis"] == g.Y
    for side in DESIGNER:
        x0, y0, z0 = eye(side)
        for y in (-12.0, -6.0, -1.0):
            assert (
                not inside(side, x0, y, z0) and not inside(side, x0 + 1.1, y, z0) and not inside(side, x0, y, z0 - 1.1)
            )
            assert inside(side, x0 + 1.5, y, z0) and inside(side, x0, y, z0 + 1.5), (side, y)


def test_bar_pin_boss_meets_the_eyeball_bar_at_y_2_5():
    """The eyeball bar (y 2.5..5.5) rides on an r 3 boss round its pin at the eyeball end, with the screw's r 1.1 hole."""
    for side in DESIGNER:
        x, _, z = g.EYEBALL_BAR_PINS[1] if side == "L" else g.mirror_x(g.EYEBALL_BAR_PINS[1])
        assert inside(side, x + 2, 2.3, z) and not inside(side, x + 2, 2.7, z) and not inside(side, x + 3.2, 1.0, z)
        for y in (-10.0, 1.0, 2.3):
            assert not inside(side, x, y, z) and not inside(side, x + 0.9, y, z) and inside(side, x + 1.3, y, z), (
                side,
                y,
            )
