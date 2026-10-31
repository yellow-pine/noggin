"""Seam: our tilt bar and pan bar (model/printed/bars.py) take the horn and lever screws on the measured pitch, in the
designer's local frame (holes along Z, horn end +x), envelope within ENVELOPE_MM (expected numbers: geometry.STL_LOCAL,
docs/research/2026-10-31-model.md [M])."""

import functools

import cadquery as cq
import pytest

from model.printed import bars

ENVELOPE_MM = 1.0
# (builder, half pitch, designer bbox): tilt bar holes 20 apart, pan bar 15 apart, both 5 wide and 3 thick
CASES = {"tilt bar": (bars.tilt, 10.0, 12.5), "PandT bar": (bars.pan, 7.5, 10.0)}


@functools.cache
def solid(stem):
    """Built when the first test runs, not at collection (see test_main_bracket)."""
    return CASES[stem][0]().val()


@pytest.mark.parametrize("stem", CASES)
def test_envelope_is_the_designers_box_within_a_millimetre(stem):
    box, x = solid(stem).BoundingBox(), CASES[stem][2]
    got = (box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax)
    assert max(abs(a - b) for a, b in zip(got, (-x, -2.5, 0.0, x, 2.5, 3.0))) <= ENVELOPE_MM


@pytest.mark.parametrize("stem", CASES)
def test_holes_take_the_m2_horn_screw_and_the_m25_lever_screw(stem):
    """r 1.1 at the +x (horn) end, r 1.35 at the -x (lever) end, along Z through the bar."""
    s, half = solid(stem), CASES[stem][1]
    for x, r in ((half, 1.1), (-half, 1.35)):
        for z in (0.2, 1.5, 2.8):
            assert not s.isInside(cq.Vector(x, 0, z)) and not s.isInside(cq.Vector(x + r - 0.1, 0, z))
            assert s.isInside(cq.Vector(x + r + 0.2, 0, z)) and s.isInside(cq.Vector(x - r - 0.2, 0, z)), (x, z)
