"""Seam: our bottom jaw (model/printed/bottom_jaw.py) meets the measured interfaces exactly and the designer's
envelope within ENVELOPE_MM, probed on the CadQuery solid (expected numbers: docs/research/2026-10-31-model.md [M])."""

import functools

import cadquery as cq

from model import geometry as g
from model.printed import bottom_jaw

ENVELOPE_MM = 1.0


@functools.cache
def solid():
    """Built when the first test runs, not at collection (see test_main_bracket.solid)."""
    return bottom_jaw.build().val()


def inside(*p):
    return solid().isInside(cq.Vector(*p))


def test_envelope_is_the_designers_box_within_a_millimetre():
    box = solid().BoundingBox()
    lo, hi = (box.xmin, box.ymin, box.zmin), (box.xmax, box.ymax, box.zmax)
    designer = (-8.42, -60.6, -34.92), (70.42, -44.6, 13.0)
    assert max(abs(a - b) for a, b in zip(lo + hi, designer[0] + designer[1])) <= ENVELOPE_MM


def test_ears_turn_on_the_top_jaws_pins_about_the_hinge():
    """r 2.0 holes along X on the jaw hinge through the ears x -8.42..-3.42 and 62.42..67.42, the ears round r 5 about
    the hinge (top z 13)."""
    assert g.PIVOTS["jaw_hinge"]["axis"] == g.X
    _, y0, z0 = g.PIVOTS["jaw_hinge"]["point"]
    for x0, x1 in ((-8.42, -3.42), (62.42, 67.42)):
        for x in (x0 + 0.2, (x0 + x1) / 2, x1 - 0.2):
            assert not inside(x, y0, z0) and not inside(x, y0 + 1.8, z0) and not inside(x, y0, z0 - 1.8)
            assert inside(x, y0 + 2.2, z0) and inside(x, y0, z0 - 2.2) and inside(x, y0, z0 + 4.8), x
            assert not inside(x, y0, z0 + 5.2) and not inside(x, y0 + 3.6, z0 + 3.6), x
        assert not inside(x0 - 0.2, y0 + 3, z0) and not inside(x1 + 0.2, y0 + 3, z0)


def test_lug_takes_the_connector_bar_screw():
    """r 1.1 hole along X at the jaw lever hole (y -58.1, z -10.44) through the lug x 61.42..70.42, z -12.94..-7.94,
    round r 2.5 about the hole."""
    _, y0, z0 = g.PT_LEVER_HOLES["jaw"]
    for x in (61.62, 66.0, 70.22):
        assert not inside(x, y0, z0) and not inside(x, y0 - 0.9, z0) and not inside(x, y0, z0 + 0.9)
        assert inside(x, y0 - 1.3, z0) and inside(x, y0, z0 + 1.3) and inside(x, y0 - 2.3, z0), x
        assert not inside(x, y0 - 2.7, z0) and not inside(x, y0, z0 + 2.7) and not inside(x, y0, z0 - 2.7), x
    assert not inside(61.22, y0 - 1.3, z0) and not inside(70.62, y0 - 1.3, z0)


def test_lip_is_a_five_millimetre_u_round_the_mouth():
    """The lip (y -54.6..-44.6) is a U: arms x -8.42..-3.42 and 62.42..67.42, round below z 3 about x 29.5 between
    r 32.92 and 37.92."""
    for y in (-54.4, -49.6, -44.8):
        for z in (-30.12, -32.4, -34.72):
            assert inside(29.5, y, z), (y, z)
        assert not inside(29.5, y, -29.72) and not inside(29.5, y, -35.12)
        assert inside(-8.22, y, 3.0) and inside(-3.62, y, 3.0) and not inside(-3.22, y, 3.0)
    assert not inside(29.5, -54.8, -32.4) and not inside(29.5, -44.4, -32.4)
