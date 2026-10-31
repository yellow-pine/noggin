"""Report-side simulation extras (#20), pure Python: static gravity torque per horn from the centre-of-mass samples
the sweep records at each pose, transmission curves from the driven joints, and the merge of fits, beams, torque
and curves into the Stage report that twin/test_report.py thresholds. Sweep samples (twin/check.py):
horns[name]["poses"] = {deg: {"com": {part: [x, y, z] mm}, "joints": {joint: deg}}}, report["mass"] = {part: g}."""
import math

RATED_KGF_CM, TORQUE_SF = 0.4, 2.0     # CyberBrick 9 g servo rated at 6 V (#20 comment), safety factor 2
G_UP = 1                               # +Y is up in the eyes frame


def gravity_torque(poses, masses):
    """kgf.cm at each sampled horn angle from the slope of the chain's potential energy (virtual work, so a
    linkage's ratio is included): central differences, one-sided at the ends."""
    degs = sorted(poses)
    out = {}
    for i, d in enumerate(degs):
        lo, hi = degs[max(i - 1, 0)], degs[min(i + 1, len(degs) - 1)]
        dtheta = math.radians(hi - lo)
        de = sum(masses[p] / 1000 * (poses[hi]["com"][p][G_UP] - poses[lo]["com"][p][G_UP]) / 10 for p in poses[d]["com"])
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


def enrich(report, fits, beams):
    """Fold the sweep's pose samples into torque and curves, attach fits and beams. Returns the report."""
    report["fits"], report["beams"], report["torque"], report["curves"] = fits, beams, {}, {}
    for name, h in report["horns"].items():
        poses = h.pop("poses", None)
        if poses:
            report["torque"][name] = {**worst(gravity_torque(poses, report["mass"])), "limit_kgf_cm": RATED_KGF_CM / TORQUE_SF}
            report["curves"][name] = curves(poses)
    return report
