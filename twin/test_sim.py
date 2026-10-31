"""Seam: twin/sim.py's report-side helpers: gravity torque per horn from the sweep's centre-of-mass samples,
transmission curves, and the merge into the Stage report."""
import importlib.util, math, os, pytest

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location("sim", os.path.join(HERE, "sim.py"))   # by path: twin/ must never shadow eyes/
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
    report = {"doc": "x", "horns": {"L lid horn": {"min_mm": 1.0, "poses": poses_for(20.0, [-20, -10, 0, 10, 20])}},
              "mass": {"m": 10.0}}
    out = sim.enrich(report, fits=[{"joint": "a", "ok": True}], beams=[{"beam": "b", "ok": True}])
    assert out["torque"]["L lid horn"] == {"kgf_cm": 0.02, "at_deg": 0, "limit_kgf_cm": 0.2}
    assert out["curves"]["L lid horn"] == {"lid": [[-20, -40], [-10, -20], [0, 0], [10, 20], [20, 40]]}
    assert out["fits"] == [{"joint": "a", "ok": True}] and out["beams"] == [{"beam": "b", "ok": True}]
    assert "poses" not in out["horns"]["L lid horn"]   # the samples are folded into torque/curves, not kept


def test_enrich_without_poses_adds_nothing_dynamic():
    out = sim.enrich({"doc": "x", "horns": {"h": {"min_mm": 1.0}}}, fits=[], beams=[])
    assert out["torque"] == {} and out["curves"] == {}
