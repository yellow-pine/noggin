"""Seam: our upper and lower lids (model/printed/lid.py) turn on the lid pivot (X through the L eye centre, the
designer's frame) clear of the eyeball, take the lid bar's screw and stay within ENVELOPE_MM of the designer's boxes,
probed on the CadQuery solids (numbers: docs/research/2026-10-31-model.md [M], geometry.LID_PINS; the shell radii and
hole sizes measured on the designer's lids)."""

import functools
import math

import cadquery as cq

from model import geometry as g
from model.printed import lid

ENVELOPE_MM = 1.0
DESIGNER = {"upper": (-24, -3.5, -19.02, 24, 24, 5), "lower": (-24, -24, -20.26, 24, 3.5, 5)}


@functools.cache
def solid(which):
    """Built when the first test runs, not at collection (CadQuery's OCCT threads vs the gate's forks)."""
    return lid.build(which).val()


def inside(which, *p):
    return solid(which).isInside(cq.Vector(*p))


def test_envelopes_are_the_designers_boxes_within_a_millimetre():
    for which, designer in DESIGNER.items():
        b = solid(which).BoundingBox()
        got = (b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax)
        assert max(abs(a - d) for a, d in zip(got, designer)) <= ENVELOPE_MM, which


def test_shell_is_concentric_with_the_eyeball_half_a_millimetre_clear():
    """Inner r 21 about the eye centre (the eyeball is r 20.5), outer r 24, toward the lid's own side."""
    for which, s in (("upper", 1), ("lower", -1)):
        for deg in (0, 25, 50):
            y, z = s * math.cos(math.radians(deg)), -math.sin(math.radians(deg))
            assert not inside(which, 0, 20.8 * y, 20.8 * z) and not inside(which, 0, 24.2 * y, 24.2 * z), (which, deg)
            assert inside(which, 0, 21.2 * y, 21.2 * z) and inside(which, 0, 23.8 * y, 23.8 * z), (which, deg)


def test_ears_turn_on_the_bracket_pins_along_the_lid_axis():
    """The bracket's r 1.75 pins reach |x| 20.93..24 on the X axis through an r 1.95 hole; the two lids nest on them,
    each ear walled round the hole on its own layer (the upper lid's |x| 21..22.5, the lower lid's 22.5..24) and
    clear of the other lid's boss (r 3.5) on the other."""
    assert g.PIVOTS["l_lid"]["axis"] == g.X
    for which, boss, clear in (("upper", 21.8, 23.3), ("lower", 23.3, 21.8)):
        for x in (-boss, -clear, clear, boss):
            assert not inside(which, x, 0, 0) and not inside(which, x, 1.75, 0) and not inside(which, x, 0, -1.75)
        for x in (-boss, boss):
            assert all(inside(which, x, 2.15 * c, 2.15 * s) for c, s in ((1, 0), (-1, 0), (0, 1))), (which, x)
        for x in (-clear, clear):
            assert not any(inside(which, x, 3.7 * c, 3.7 * s) for c, s in ((1, 0), (-1, 0), (0, 1))), (which, x)


def test_ears_take_the_lid_bar_screw_on_the_lid_pins():
    """r 1.0 along X at (+-22, +12, 0) on the upper lid, (+-22, -12, 0) on the lower one."""
    for which in ("upper", "lower"):
        x, y, z = g.LID_PINS[which]
        for px in (x, -x):
            assert (
                not inside(which, px, y, z) and not inside(which, px, y + 0.8, z) and not inside(which, px, y, z + 0.8)
            )
            assert inside(which, px, y + 1.2, z) and inside(which, px, y - 1.2, z), (which, px)
