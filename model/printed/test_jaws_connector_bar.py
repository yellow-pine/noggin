"""Seam: our jaws connector bar (model/printed/jaws_connector_bar.py) meets the measured interfaces exactly and the
designer's envelope within ENVELOPE_MM, probed on the CadQuery solid in the designer's local frame (expected numbers:
docs/research/2026-10-31-model.md [M])."""

import functools

import cadquery as cq

from model.printed import jaws_connector_bar

ENVELOPE_MM = 1.0


@functools.cache
def solid():
    """Built when the first test runs, not at collection (see test_main_bracket.solid)."""
    return jaws_connector_bar.build().val()


def inside(*p):
    return solid().isInside(cq.Vector(*p))


def test_envelope_is_the_designers_box_within_a_millimetre():
    box = solid().BoundingBox()
    lo, hi = (box.xmin, box.ymin, box.zmin), (box.xmax, box.ymax, box.zmax)
    designer = (-25.0, -5.0, -7.75), (25.0, 0.0, 7.75)
    assert max(abs(a - b) for a, b in zip(lo + hi, designer[0] + designer[1])) <= ENVELOPE_MM


def test_end_tabs_take_the_horn_and_jaw_screws():
    """Holes along Z through the 3 mm end tabs: r 1.1 at (-22.05, -2.5) in the tab z 4.75..7.75, r 1.35 at
    (22.05, -2.5) in the tab z -7.75..-4.75."""
    for (x, y), r, tab in (((-22.05, -2.5), 1.1, (4.75, 7.75)), ((22.05, -2.5), 1.35, (-7.75, -4.75))):
        for z in (tab[0] + 0.2, sum(tab) / 2, tab[1] - 0.2):
            assert not inside(x, y, z) and not inside(x + r - 0.2, y, z) and not inside(x, y + r - 0.2, z)
            assert inside(x, y + r + 0.2, z) and inside(x - s(x) * (r + 0.2), y, z), (x, z)
        assert not inside(x - s(x) * 2, y, tab[0] - 0.2) and not inside(x - s(x) * 2, y, tab[1] + 0.2)


def s(x):
    return 1 if x > 0 else -1


def test_band_steps_the_tabs_twelve_and_a_half_apart():
    """A 5 mm thick (y -5..0) Z: the band joins the tab ends at x -13 and 16, its faces 3 apart along Z."""
    for x, z in ((-13.0, 6.25), (1.5, 0.0), (16.0, -6.25)):
        assert inside(x, -2.5, z + 1.3) and inside(x, -2.5, z - 1.3) and not inside(x, -2.5, z + 1.8), (x, z)
        assert inside(x, -0.2, z) and inside(x, -4.8, z) and not inside(x, 0.2, z) and not inside(x, -5.2, z)
