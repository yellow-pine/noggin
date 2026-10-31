"""Seam: our top jaw plain (model/printed/top_jaw.py) meets the measured interfaces exactly and the designer's envelope
within ENVELOPE_MM, probed on the CadQuery solid (expected numbers: docs/research/2026-10-31-model.md [M])."""

import functools

import cadquery as cq

from model import geometry as g
from model.printed import top_jaw

ENVELOPE_MM = 1.0


@functools.cache
def solid():
    """Built when the first test runs, not at collection (see test_main_bracket.solid)."""
    return top_jaw.build().val()


def inside(*p):
    return solid().isInside(cq.Vector(*p))


def test_envelope_is_the_designers_box_within_a_millimetre():
    box = solid().BoundingBox()
    lo, hi = (box.xmin, box.ymin, box.zmin), (box.xmax, box.ymax, box.zmax)
    designer = (-11.42, -54.6, -34.92), (70.42, -30.6, 13.0)
    assert max(abs(a - b) for a, b in zip(lo + hi, designer[0] + designer[1])) <= ENVELOPE_MM


def test_pins_stand_on_the_jaw_hinge_between_the_cheeks():
    """r 1.75 pins along X on the jaw hinge from the cheeks' inner faces (x -8.42, 67.42) in through the bottom jaw's
    ears (to x -4.25 and 63.25 at full radius, then domed to a flat r 0.75 tip at x -3.42 and 62.42); the cheeks are 3
    thick and round r 5 about the hinge."""
    assert g.PIVOTS["jaw_hinge"]["axis"] == g.X
    _, y0, z0 = g.PIVOTS["jaw_hinge"]["point"]
    for x, inward in ((-6.3, 1), (65.3, -1)):
        for dx in (-2.0, 0.0, 1.8):
            p = x + inward * dx
            assert inside(p, y0, z0) and inside(p, y0 + 1.6, z0) and inside(p, y0, z0 - 1.6), p
            assert not inside(p, y0 + 1.9, z0) and not inside(p, y0, z0 + 1.9), p
    for tip, inward in ((-3.42, 1), (62.42, -1)):
        p = tip - inward * 0.1
        assert inside(p, y0 + 0.7, z0) and not inside(p, y0 + 1.2, z0) and not inside(tip + inward * 0.1, y0, z0), tip
    for x in (-9.92, 68.92):  # the cheeks
        assert inside(x, y0, z0) and inside(x, y0, z0 + 4.8) and not inside(x, y0 - 3.6, z0 + 3.6), x
        assert inside(x, -54.4, 7.0) and not inside(x, -54.8, 7.0) and inside(x, -30.8, 12.8), x
    assert not inside(-8.22, -47.0, 8.0) and not inside(67.22, -47.0, 8.0)
    assert inside(-8.62, -47.0, 8.0) and inside(67.62, -47.0, 8.0)


def test_flanges_screw_under_the_bracket_rail_either_side_of_the_stem():
    """Flanges z 10..13 (against the rail's front face, z 13) with r 1.35 holes along Z at (6.5, 16.5, 42.5, 52.5;
    y -35.6), the stem passing between them (x 19.58..39.42)."""
    for x in (6.5, 16.5, 42.5, 52.5):
        for z in (10.2, 11.5, 12.8):
            assert not inside(x, -35.6, z) and not inside(x + 1.15, -35.6, z) and not inside(x, -34.45, z)
            assert inside(x + 1.55, -35.6, z) and inside(x, -37.15, z), (x, z)
    for x in (0.0, 24.0, 59.0):
        assert not inside(x, -35.6, 13.2)
    for x in (19.38, 39.62):
        assert inside(x, -35.6, 11.5), x
    for x in (19.78, 29.5, 39.22):
        assert not inside(x, -35.6, 11.5), x
    assert inside(0.0, -35.6, 10.2) and not inside(0.0, -35.6, 9.8)


def test_lip_is_a_five_millimetre_u_round_the_mouth():
    """The lip (y -40.6..-30.6) is a U: arms x -8.42..-3.42 and 62.42..67.42, round below z 3 about x 29.5 between
    r 32.92 and 37.92."""
    for y in (-40.4, -35.6, -30.8):
        for z in (-30.12, -32.4, -34.72):
            assert inside(29.5, y, z), (y, z)
        assert not inside(29.5, y, -29.72) and not inside(29.5, y, -35.12)
        assert inside(-8.22, y, 3.0) and inside(-3.62, y, 3.0) and not inside(-3.22, y, 3.0)
    assert not inside(29.5, -40.8, -32.4) and not inside(29.5, -30.4, -32.4)
