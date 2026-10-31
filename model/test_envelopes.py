"""Seam: our hardware envelopes (model/envelopes.py) meet each piece's interfaces (mount holes, shaft, connectors) in
its Bambu STEP frame and the STEP's box within ENVELOPE_MM, probed on the CadQuery solid. Expected numbers are
literals read off the STEP files (docs/references/cyberbrick-cad, local only)."""

import functools

import cadquery as cq
import pytest

from model import envelopes

ENVELOPE_MM = 1.0
BOXES = {  # the STEP mesh's box as the engine uses it (servo and battery leads cut, model/engine/stages.py clip)
    "servo": ((-4.9, -0.1, -14.52), (27.6, 11.9, 16.3)),
    "horn": ((-3.63, 16.37, 0.0), (16.05, 23.63, 4.15)),
    "receiver": ((-14.5, -4.3, -15.0), (14.5, 10.78, 15.0)),
    "core": ((-11.6, -10.68, -13.39), (11.6, -2.3, 14.5)),
    "switch": ((-7.25, -4.6, -16.0), (13.25, 15.16, 16.0)),
    "battery": ((-14.18, 0.0, -8.15), (14.18, 51.2, 8.15)),
}


@functools.cache
def solid(key):
    """Built when the first test runs, not at collection (see model/printed/test_main_bracket.py)."""
    return envelopes.ENVELOPES[key]().val()


def inside(key, *p):
    return solid(key).isInside(cq.Vector(*p))


@pytest.mark.parametrize("key", BOXES)
def test_envelope_is_the_steps_box_within_a_millimetre(key):
    box = solid(key).BoundingBox()
    got = (box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax)
    assert max(abs(a - b) for a, b in zip(got, BOXES[key][0] + BOXES[key][1])) <= ENVELOPE_MM


def test_servo_tab_holes_are_open_on_the_tab_plate():
    """r 1.0 holes along Z through the z -2.3..0 tab plate at x -2.55 and 25.25, y 5.9."""
    for x in (-2.55, 25.25):
        assert not inside("servo", x, 5.9, -1.8)
        assert inside("servo", x, 5.9 + 1.5, -1.8)


def test_servo_shaft_is_the_r_2_35_spline_on_x_16_69_to_z_minus_14_52():
    assert inside("servo", 16.69 + 2.0, 5.9, -14.3) and not inside("servo", 16.69 + 2.6, 5.9, -13.0)
    assert not inside("servo", 16.69 + 1.5, 5.9, -14.7)


def test_horn_hub_takes_the_spline_from_z_4_15_and_the_arm_pins_the_bars_at_12_75():
    assert not inside("horn", 1.5, 20.0, 3.0) and inside("horn", 3.0, 20.0, 3.0) and not inside("horn", 3.8, 20.0, 3.0)
    assert not inside("horn", 12.75, 20.0, 0.8) and inside("horn", 12.75, 20.8, 0.8)
    assert inside("horn", 8.0, 21.0, 1.4) and not inside("horn", 8.0, 21.0, 1.7)


def test_shield_mount_holes_header_pins_and_power_socket():
    """r 1.35 holes through the PCB (y 0..1.6) at x +-11.5, z +-12; the servo header pins (0.64 square, up to y 10.78)
    at x +-1.69, +-4.23, +-6.77, z 1.23 and 3.77; the XH power socket (y 1.6..7.6) at z -15..-7.2; the Core's sockets
    under the PCB at x +-7 down to y -4.3."""
    for x in (-11.5, 11.5):
        for z in (-12.0, 12.0):
            assert not inside("receiver", x, 0.8, z) and inside("receiver", x * 0.85, 0.8, z * 0.85)
    for x in (-6.77, -4.23, -1.69, 1.69, 4.23, 6.77):
        for z in (1.23, 3.77):
            assert inside("receiver", x, 10.6, z) and not inside("receiver", x + 0.5, 10.6, z)
    assert inside("receiver", 0.0, 7.4, -9.75) and not inside("receiver", 0.0, 7.8, -9.75)
    assert inside("receiver", 7.0, -4.1, 0.0) and not inside("receiver", 7.0, -4.5, 0.0)


def test_core_pcb_module_and_usb_c():
    """PCB y -7.4..-5.8, the module can down to y -9.4 (x +-9.75, z -2.45..8.05), the USB-C socket to y -10.68 at its
    end (z -13.39..-6.05); its header pins up to the Shield's sockets at y -2.3."""
    assert inside("core", 0.0, -6.6, 0.0) and inside("core", 0.0, -9.2, 3.0) and not inside("core", 0.0, -9.6, 3.0)
    assert inside("core", 0.0, -10.5, -10.0) and not inside("core", 0.0, -10.9, -10.0)
    assert inside("core", 7.0, -2.5, 0.0) and not inside("core", 7.0, -2.1, 0.0)
    assert inside("core", 11.5, -7.35, 0.0) and not inside("core", 11.5, -7.0, 0.0)  # pads past the PCB edge


def test_switch_board_mount_hole_sockets_and_lever():
    """r 1.35 hole through the PCB tab (y 0..1.6) at (10.25, z 0) (geometry.SWITCH_STEP); the two XH sockets up to y 7.6
    at z +-(7.7..15.5); the lever to y 15.16."""
    assert not inside("switch", 10.25, 0.8, 0.0) and inside("switch", 10.25 + 2.0, 0.8, 0.0)
    assert (
        inside("switch", 0.0, 7.4, 12.0) and inside("switch", 0.0, 7.4, -12.0) and not inside("switch", 0.0, 7.8, 12.0)
    )
    assert inside("switch", -1.8, 15.0, 0.0) and not inside("switch", -1.8, 15.4, 0.0)


def test_battery_pack_sits_on_its_floor_and_ends_before_the_lead():
    """Two cells side by side (r 8.15 at x +-6.03), floor z -8.15 (geometry.BATTERY_STEP), pack y 0..51.2."""
    assert inside("battery", 6.03, 25.0, -8.0) and not inside("battery", 6.03, 25.0, -8.3)
    assert inside("battery", 0.0, 51.0, 0.0) and not inside("battery", 0.0, 51.4, 0.0)
    assert not inside("battery", 14.0, 25.0, 7.0)  # rounded, not a box
