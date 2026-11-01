"""The servo's numbers the model reads: its rated torque (model/mujoco_report.py holds each servo to it) and the horn
joint degrees a servo angle turns its horn to (the gesture traces, model/traces.py)."""

from model.geometry import EYES_SERVOS, HORN_AT_90

RATED_KGF_CM = 0.4  # the 9 g servo rated at 6 V (#20 comment)


def joint_deg(servo, angle):
    """Horn joint angle (relative to the 90-degree neutral the STLs are modelled in) for a servo angle, lids in the
    shared lid frame of eyes/calibration.json (#213: the right lid servo's degrees, the left servo mirrored by the Core,
    so its horn turns the same way), plus the horn's spline tooth (geometry.HORN_AT_90)."""
    return angle - 90 + HORN_AT_90.get(servo, 0)


def calibrated_extremes(cal):
    """(min, max) joint degrees each horn reaches at the calibrated servo ends."""
    return {s: tuple(sorted((joint_deg(s, cal[s + "_lo"]), joint_deg(s, cal[s + "_hi"])))) for s in EYES_SERVOS}
