"""Report-side simulation extras (#20), pure Python: static gravity torque per horn from the centre-of-mass samples
the sweep records at each pose, transmission curves from the driven joints, and the merge of fits, beams, torque
and curves into the document's report that model/test_report.py thresholds. Sweep samples (model/engine/run.py):
horns[name]["poses"] = {deg: {"com": {part: [x, y, z] mm}, "joints": {joint: deg}}}, report["mass"] = {part: g}."""

import math

from model.geometry import EYES_SERVOS, HORN_AT_90

RATED_KGF_CM, TORQUE_SF = 0.4, 2.0  # the 9 g servo rated at 6 V (#20 comment), safety factor 2


def gravity_torque(poses, masses, up=1):
    """kgf.cm at each sampled horn angle from the slope of the chain's potential energy (virtual work, so a
    linkage's ratio is included): central differences, one-sided at the ends."""
    degs = sorted(poses)
    out = {}
    for i, d in enumerate(degs):
        lo, hi = degs[max(i - 1, 0)], degs[min(i + 1, len(degs) - 1)]
        dtheta = math.radians(hi - lo)
        de = sum(masses[p] / 1000 * (poses[hi]["com"][p][up] - poses[lo]["com"][p][up]) / 10 for p in poses[d]["com"])
        out[d] = abs(de / dtheta)
    return out


def worst(torque):
    deg = max(torque, key=torque.get)
    return {"kgf_cm": round(torque[deg], 3), "at_deg": deg}


def curves(poses):
    """{joint: [[horn deg, joint deg], ...]} from the driven joints recorded at each pose."""
    out = {}
    for d in sorted(poses):
        for j, a in poses[d].get("joints", {}).items():
            out.setdefault(j, []).append([d, a])
    return out


def enrich(report, fits, beams, up=1):
    """Fold the sweep's pose samples into torque and curves, attach fits and beams. Returns the report."""
    report["fits"], report["beams"], report["torque"], report["curves"] = fits, beams, {}, {}
    for name, h in report["horns"].items():
        poses = h.pop("poses", None)
        if poses:
            poses = {int(d): p for d, p in poses.items()}  # JSON keys are strings
            report["torque"][name] = {
                **worst(gravity_torque(poses, report["mass"], up)),
                "limit_kgf_cm": RATED_KGF_CM / TORQUE_SF,
            }
            report["curves"][name] = curves(poses)
    return report


def joint_deg(servo, angle):
    """Horn joint angle (relative to the 90-degree neutral the STLs are modelled in) for a servo angle, lids in the
    shared lid frame of eyes/calibration.json (#213: the right lid servo's degrees, the left servo mirrored by the Core,
    so its horn turns the same way), plus the horn's spline tooth (geometry.HORN_AT_90)."""
    return angle - 90 + HORN_AT_90.get(servo, 0)


def calibrated_extremes(cal):
    """(min, max) joint degrees each horn reaches at the calibrated servo ends."""
    return {s: tuple(sorted((joint_deg(s, cal[s + "_lo"]), joint_deg(s, cal[s + "_hi"])))) for s in EYES_SERVOS}
