"""Seam: model/sim.py, a servo angle as the horn joint degrees the model poses."""

import importlib.util
import os

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location(
    "sim", os.path.join(HERE, "sim.py")
)  # by path: model/ must never shadow eyes/
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)


def test_servo_to_joint_mapping_takes_the_lids_in_the_shared_frame():
    cal = {"l_lid_lo": 39, "l_lid_hi": 102, "r_lid_lo": 39, "r_lid_hi": 102}
    cal |= {"l_eye_lo": 58, "l_eye_hi": 118, "r_eye_lo": 58, "r_eye_hi": 118}
    # plus the horn's spline tooth at servo 90 (geometry.HORN_AT_90: lids +20.25 each, the closed end 39 on the lips'
    # meeting, #255; eyes +2, centred at servo 88)
    assert sim.joint_deg("l_eye", 118) == 30 and sim.joint_deg("r_lid", 39) == -30.75
    assert sim.joint_deg("l_lid", 102) == 32.25  # the shared frame's high end is open (positive) on both sides
    assert sim.calibrated_extremes(cal) == {
        "l_lid": (-30.75, 32.25),
        "r_lid": (-30.75, 32.25),
        "l_eye": (-30, 30),
        "r_eye": (-30, 30),
    }
