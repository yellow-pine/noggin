"""Seam: the clearance coupon (model/printed/coupon.py, #624), flat on the bed: a 3 mm pin standing in each hole with its
clearance per side as the gap, 0.10 to 0.40 mm in 0.05 mm steps from the notched end, each pin loose (its own solid),
and a pocket per fit for the shells' 4x2 mm magnet disc, 2 mm deep (flush), with a hole under it to push the disc out."""

import functools

import cadquery as cq
import pytest

from model.printed import coupon

PIN_R = 1.5


@functools.cache
def shape():
    """Built when the first test runs, not at collection (CadQuery's OCCT threads vs the sweep's forks)."""
    return coupon.build().val()


def inside(x, y, z):
    return shape().isInside(cq.Vector(x, y, z))


def test_it_lies_flat_on_the_bed_a_plate_and_a_loose_pin_per_clearance():
    assert coupon.PINS == (0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4)
    assert shape().BoundingBox().zmin == pytest.approx(0)
    assert len(shape().Solids()) == 1 + len(coupon.PINS)


@pytest.mark.parametrize("i", range(7))
def test_each_pin_stands_in_its_hole_with_its_clearance_as_the_gap(i):
    (x, y), c, z = coupon.pin(i), coupon.PINS[i], coupon.PLATE / 2
    assert inside(x, y, z) and inside(x + PIN_R - 0.02, y, z), "the pin"
    assert not inside(x + PIN_R + 0.02, y, z) and not inside(x + PIN_R + c - 0.02, y, z), "the gap"
    assert inside(x + PIN_R + c + 0.02, y, z), "the plate"
    assert inside(x, y, coupon.PLATE + 2), "the pin stands proud of the plate"


def test_the_pins_step_up_from_the_notched_corner():
    xs = [coupon.pin(i)[0] for i in range(len(coupon.PINS))]
    assert xs == sorted(xs)
    assert not inside(0.5, 0.5, 1) and inside(0.5, 10, 1), "the notch at x 0, y 0 only"


@pytest.mark.parametrize("i", range(4))
def test_each_magnet_pocket_holds_the_disc_at_its_fit_flush_with_a_push_out_hole(i):
    assert coupon.POCKETS == (0.05, 0.1, 0.15, 0.2)
    (x, y), c, top = coupon.pocket(i), coupon.POCKETS[i], coupon.PLATE
    assert not inside(x + 2 + c - 0.02, y, top - 1) and inside(x + 2 + c + 0.02, y, top - 1), "the pocket's wall"
    assert not inside(x + 1.5, y, top - 1.98) and inside(x + 1.5, y, top - 2.02), "its floor, 2 mm down"
    assert not inside(x, y, 0.5), "the push-out hole"
