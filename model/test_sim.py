"""Seam: model/sim.py's report-side helpers: gravity torque per horn from the sweep's centre-of-mass samples,
transmission curves, and the merge into the Stage report."""
import importlib.util, math, os, pytest

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location("sim", os.path.join(HERE, "sim.py"))   # by path: model/ must never shadow eyes/
sim = importlib.util.module_from_spec(spec); spec.loader.exec_module(sim)


def poses_for(lever_mm, degs):
    """A 10 g mass on a lever about an X axis: horizontal at 0 deg, so the gravity torque peaks there."""
    return {d: {"com": {"m": [0.0, lever_mm * math.sin(math.radians(d)), lever_mm * math.cos(math.radians(d))]},
                "joints": {"lid": 2 * d}} for d in degs}


def test_gravity_torque_is_the_potential_energy_slope():
    poses = poses_for(20.0, [-20, -10, 0, 10, 20])
    torque = sim.gravity_torque(poses, {"m": 10.0})
    assert torque[0] == pytest.approx(0.02, abs=0.0005)            # 0.010 kg x 2 cm
    assert torque[20] == pytest.approx(0.02 * math.cos(math.radians(15)), abs=0.002)   # one-sided at the ends
    assert sim.worst(torque) == {"kgf_cm": 0.02, "at_deg": 0}


def test_curves_and_torque_merge_into_the_report():
    poses = {str(d): p for d, p in poses_for(20.0, [-20, -10, 0, 10, 20]).items()}   # as json.load gives them
    report = {"doc": "x", "horns": {"L lid horn": {"min_mm": 1.0, "poses": poses}}, "mass": {"m": 10.0}}
    out = sim.enrich(report, fits=[{"joint": "a", "ok": True}], beams=[{"beam": "b", "ok": True}])
    assert out["torque"]["L lid horn"] == {"kgf_cm": 0.02, "at_deg": 0, "limit_kgf_cm": 0.2}
    assert out["curves"]["L lid horn"] == {"lid": [[-20, -40], [-10, -20], [0, 0], [10, 20], [20, 40]]}
    assert out["fits"] == [{"joint": "a", "ok": True}] and out["beams"] == [{"beam": "b", "ok": True}]
    assert "poses" not in out["horns"]["L lid horn"]   # the samples are folded into torque/curves, not kept


def test_enrich_without_poses_adds_nothing_dynamic():
    out = sim.enrich({"doc": "x", "horns": {"h": {"min_mm": 1.0}}}, fits=[], beams=[])
    assert out["torque"] == {} and out["curves"] == {}


def test_servo_to_joint_mapping_follows_the_calibration_flips():
    cal = {"l_lid_lo": 51, "l_lid_hi": 144, "r_lid_lo": 44, "r_lid_hi": 129, "l_eye_lo": 58, "l_eye_hi": 118,
           "r_eye_lo": 58, "r_eye_hi": 118, "l_lid_flip": 1, "r_lid_flip": 0}
    assert sim.joint_deg("l_eye", 118, cal) == 28 and sim.joint_deg("r_lid", 44, cal) == -46
    assert sim.joint_deg("l_lid", 51, cal) == 39      # flipped lid: the low servo end is the open (positive) side
    assert sim.calibrated_extremes(cal) == {"l_lid": (-54, 39), "r_lid": (-46, 39), "l_eye": (-32, 28), "r_eye": (-32, 28)}
