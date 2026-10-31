"""Seam: our PandT servo mounts (model/printed/servo_mount.py) carry the pan servo's tab screws at mount top z 15 and
screw to the base, PT frame, envelope within ENVELOPE_MM (expected numbers: docs/research/2026-10-31-model.md [M])."""

import functools

import cadquery as cq
import pytest

from model.printed import servo_mount

ENVELOPE_MM = 1.0
# (builder, mount y span, the pan servo's tab hole y, the base screw y)
CASES = {
    "PandT servo mount plain": (servo_mount.plain, (27.0, 32.0), 29.55, 29.5),
    "PandT servo mount cutout": (servo_mount.cutout, (54.9, 59.9), 57.35, 57.4),
}


@functools.cache
def solid(stem):
    """Built when the first test runs, not at collection (see test_main_bracket)."""
    return CASES[stem][0]().val()


def inside(stem, *p):
    return solid(stem).isInside(cq.Vector(*p))


@pytest.mark.parametrize("stem", CASES)
def test_envelope_is_the_designers_box_within_a_millimetre(stem):
    box, (y0, y1) = solid(stem).BoundingBox(), CASES[stem][1]
    got = (box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax)
    assert max(abs(a - b) for a, b in zip(got, (-35.5, y0, 3.0, -5.5, y1, 15.0))) <= ENVELOPE_MM


@pytest.mark.parametrize("stem", CASES)
def test_top_takes_the_pan_servo_tab_screw_at_z_15(stem):
    """r 1.1 tab hole along Z at x -20.5 down from the z 15 top."""
    y = CASES[stem][2]
    assert inside(stem, -20.5 + 1.3, y, 14.8) and not inside(stem, -20.5 + 1.3, y, 15.2)
    for z in (9.0, 12.0, 14.8):
        assert not inside(stem, -20.5, y, z) and not inside(stem, -20.5 + 1.0, y, z)
        assert inside(stem, -20.5 + 1.3, y, z) and inside(stem, -20.5 - 1.3, y, z), z


@pytest.mark.parametrize("stem", CASES)
def test_feet_screw_to_the_base(stem):
    """r 1.35 holes along Z through the z 3..6 feet at x -32.5 and -8.5 over the base's screw holes."""
    y = CASES[stem][3]
    for x in (-32.5, -8.5):
        for z in (3.2, 4.5, 5.8):
            assert not inside(stem, x, y, z) and not inside(stem, x + 1.25, y, z)
            assert inside(stem, x + 1.55, y, z) and inside(stem, x - 1.55, y, z), (x, z)
        assert not inside(stem, x, y, 6.2)


def test_cutout_mount_arches_over_the_base():
    """The cutout mount clears x -25.5..-15.5 up to z 8 under its tab."""
    stem = "PandT servo mount cutout"
    assert not inside(stem, -20.5 + 3, 57.4, 7.8) and inside(stem, -20.5 + 3, 57.4, 8.2)
    assert not inside(stem, -25.3, 57.4, 4.0) and inside(stem, -25.7, 57.4, 4.0)
