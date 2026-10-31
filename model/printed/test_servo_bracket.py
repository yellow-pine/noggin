"""Seam: our L and R servo brackets (model/printed/servo_bracket.py) meet the measured interfaces exactly and the
designer's envelopes within ENVELOPE_MM, probed on the CadQuery solids (numbers: docs/research/2026-10-31-model.md [M],
geometry.SERVOS; the R stem foot measured on the designer's R bracket)."""

import functools

import cadquery as cq

from model import geometry as g
from model.printed import servo_bracket

ENVELOPE_MM = 1.0
FEET = {
    "L": [(-13.42, -7.75), (10.24, -0.5), (29.5, -31.6)],
    "R": [(72.42, -7.75), (48.76, -0.5), (29.5, -21.6)],  # the R bracket's stem foot sits 10 mm above the L one's
}


@functools.cache
def solid(side):
    """Built when the first test runs, not at collection (CadQuery's OCCT threads vs the sweep's forks)."""
    return servo_bracket.build(side).val()


def inside(side, *p):
    return solid(side).isInside(cq.Vector(*p))


def test_envelopes_are_the_designers_boxes_within_a_millimetre():
    for side, designer in (("L", (-17.42, -35.6, 18, 35.24, 2.5, 46)), ("R", (23.76, -35.6, 18, 76.42, 2.5, 46))):
        b = solid(side).BoundingBox()
        got = (b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax)
        assert max(abs(a - d) for a, d in zip(got, designer)) <= ENVELOPE_MM, side


def test_feet_take_their_screws_through_the_plate():
    """r 1.35 clearance holes along Z through the plate (z 18..21) onto the eye bracket's tapped holes."""
    for side, feet in FEET.items():
        for x, y in feet:
            for z in (18.2, 19.5, 20.8):
                assert (
                    not inside(side, x, y, z) and not inside(side, x + 1.15, y, z) and not inside(side, x, y - 1.15, z)
                )
                assert inside(side, x + 1.55, y, z) and inside(side, x - 1.55, y, z), (side, x, y, z)


def test_eye_servo_tabs_screw_along_y_into_the_walls():
    """r 1.1 holes along Y at the eye servo's tab holes, through the walls (y -11.5..-6.5)."""
    for side, key in (("L", "l_eye"), ("R", "r_eye")):
        for x, _, z in g.SERVOS[key]["tab_holes"]:
            for y in (-11.3, -9.0, -6.7):
                assert not inside(side, x, y, z) and not inside(side, x + 0.9, y, z) and not inside(side, x, y, z + 0.9)
                assert inside(side, x + 1.3, y, z) and inside(side, x, y, z - 1.3), (side, x, y, z)
            assert inside(side, x + 1.3, -11.3, z) and not inside(side, x + 1.3, -11.7, z)


def test_lid_servo_tabs_screw_along_x_into_the_tongues():
    """r 1.1 holes along X at the lid servo's tab holes (y, z), into the tongues (x -7.42..-3.42 on the L side)."""
    for side, key, x in (("L", "l_lid", -5.42), ("R", "r_lid", g.mirror_x((-5.42, 0, 0))[0])):
        for _, y, z in g.SERVOS[key]["tab_holes"]:
            for dx in (-1.8, 0, 1.8):
                assert not inside(side, x + dx, y, z) and not inside(side, x + dx, y + 0.9, z)
                assert inside(side, x + dx, y, z + 1.3) and inside(side, x + dx, y - 1.3, z), (side, y, dx)
            out = -1 if side == "L" else 1
            assert not inside(side, x + out * 2.2, y, z + 1.3) and inside(side, x + out * 1.8, y, z + 1.3)
