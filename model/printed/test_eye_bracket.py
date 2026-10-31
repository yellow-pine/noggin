"""Seam: our eye bracket (model/printed/eye_bracket.py) meets the measured interfaces exactly and the designer's
envelope within ENVELOPE_MM, probed on the CadQuery solid (expected numbers: docs/research/2026-10-31-model.md [M])."""

import functools

import cadquery as cq

from model import geometry as g
from model.printed import eye_bracket

ENVELOPE_MM = 1.0


@functools.cache
def solid():
    """Built when the first test runs, not at collection: CadQuery's booleans start OCCT threads, and the engine's gate
    forks its sweep workers (a fork after threads start can deadlock)."""
    return eye_bracket.build().val()


def test_envelope_is_the_designers_box_within_a_millimetre():
    box = solid().BoundingBox()
    lo, hi = (box.xmin, box.ymin, box.zmin), (box.xmax, box.ymax, box.zmax)
    designer = (-28.0, -45.6, -4.0), (87.0, 8.5, 18.0)  # eye bracket bbox
    assert max(abs(a - b) for a, b in zip(lo + hi, designer[0] + designer[1])) <= ENVELOPE_MM


def inside(*p):
    return solid().isInside(cq.Vector(*p))


def test_lid_pins_stand_on_each_lid_pivot_axis():
    """r 1.75 pins along X on the lid axis, from the post faces 24 mm either side of the eye centre in to 20.93."""
    for eye in (g.EYE_L, g.EYE_R):
        assert g.PIVOTS["l_lid"]["axis"] == g.X
        x0, y0, z0 = eye
        for s in (-1, 1):
            assert (
                inside(x0 + s * 21.1, y0, z0)
                and inside(x0 + s * 21.1, y0 + 1.6, z0)
                and inside(x0 + s * 21.1, y0, z0 - 1.6)
            )
            assert not inside(x0 + s * 21.1, y0 + 1.9, z0) and not inside(x0 + s * 21.1, y0, z0 + 1.9)
            assert not inside(x0 + s * 20.8, y0, z0)  # the pin tip


def test_eyeball_forks_take_the_eyeball_pivot_screw_on_each_eye_axis():
    """A fork y 0..4 round about each eyeball pivot (Y through the eye centre), r 4, with the r 1.6 M3 screw hole."""
    assert g.PIVOTS["l_eye"]["axis"] == g.Y
    for x0, _, z0 in (g.EYE_L, g.EYE_R):
        assert not inside(x0, 2, z0) and not inside(x0 + 1.4, 2, z0)
        assert all(inside(x0 + dx, 2, z0 + dz) for dx, dz in ((2.5, 0), (-2.5, 0), (0, 2.5), (0, -3.8)))
        assert not inside(x0, 2, z0 - 4.2) and not inside(x0 + 2.5, -0.3, z0) and not inside(x0 + 2.5, 4.3, z0)


def test_plate_holes_take_the_mounting_screws():
    """r 1.1 holes along Z through the plate: servo bracket feet, the top row, the stem, the bottom rail (jaw servo mount
    feet at 65.92 and 70.92)."""
    feet = [(-13.42, -7.75), (10.24, -0.5), (48.76, -0.5), (72.42, -7.75), (29.5, -31.6)]
    top = [(x, 5.5) for x in (1.5, 6.5, 11.5, 24.5, 34.5, 47.5, 52.5, 57.5)]
    stem = [(29.5, y) for y in (-11.6, -16.6, -21.6, -36.6)]
    rail = [(x, -35.6) for x in (1.5, 6.5, 11.5, 16.5, 42.5, 47.5, 52.5, 57.5, 65.92, 70.92)]
    for x, y in feet + top + stem + rail:
        for z in (13.2, 15.5, 17.8):
            assert not inside(x, y, z) and not inside(x + 1.0, y, z) and not inside(x, y - 1.0, z)
            assert inside(x + 1.3, y, z) and inside(x - 1.3, y, z), (x, y, z)


def test_stem_is_the_neck_clamps_twelve_by_five_section():
    x0, y0, z0 = g.STEM_BOTTOM
    assert inside(x0, y0 + 0.2, z0) and not inside(x0, y0 - 0.2, z0)
    for dx, dz, ok in (
        (5.8, 0, True),
        (6.2, 0, False),
        (-5.8, 0, True),
        (-6.2, 0, False),
        (0, 2.3, True),
        (0, 2.7, False),
    ):
        assert inside(x0 + dx, y0 + 2, z0 + dz) == ok, (dx, dz)


def test_band_top_edge_is_the_rail_the_eyeball_bars_ride():
    for x in (-15.0, -10.0, -6.5, 65.5, 69.0, 74.0):
        assert inside(x, 2.3, 15.5) and not inside(x, 2.7, 15.5), x
