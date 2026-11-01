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
    cal = {"l_lid_lo": 44, "l_lid_hi": 129, "r_lid_lo": 44, "r_lid_hi": 129}
    cal |= {"l_eye_lo": 58, "l_eye_hi": 118, "r_eye_lo": 58, "r_eye_hi": 118}
    # plus the horn's spline tooth at servo 90 (geometry.HORN_AT_90: lids +6.75 each; eyes +2, centred at servo 88)
    assert sim.joint_deg("l_eye", 118) == 30 and sim.joint_deg("r_lid", 44) == -39.25
    assert sim.joint_deg("l_lid", 129) == 45.75  # the shared frame's high end is open (positive) on both sides
    assert sim.calibrated_extremes(cal) == {
        "l_lid": (-39.25, 45.75),
        "r_lid": (-39.25, 45.75),
        "l_eye": (-30, 30),
        "r_eye": (-30, 30),
    }
