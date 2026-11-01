"""Seam: the JSON reports `make sim` writes (model/report.py, model/build/reports/<doc>-sim.json): build outputs, never
committed (docs/adr/0009). Right after make sim (CI's sim shard) every built report must have no problems; a document
not built here is skipped. The fixture test checks the checker itself."""

import json
import os
import subprocess

import pytest

from model import mujoco_report, report, stages

HERE = os.path.dirname(__file__)
# MuJoCo pairs (model/mujoco_report.py) that go deeper than at rest across a sweep, with why. Since #190 the pieces read
# what the exact meshes do (model/test_mjcf.py).
KNOWN_PAIRS = {
    **{
        frozenset((f"{s} eyeball:1", "eye bracket:1")): "the pieces 0.07 mm in at +-20 where the meshes touch with"
        " nothing 0.1 mm inside (model/test_mjcf.py holds the pieces to that)"
        for s in "LR"
    },
}
# (document, horn, end): where a swing at the servo's rated speed does not end where the slow pose does.
KNOWN_FULL_SPEED = {
    ("noggin-stage3", "pan horn", -40): "the stage 3 head's inertia carries the pan four-bar through its toggle"
    " (-43.4, geometry.LIMITS) and it settles on the other branch, 29 deg off. Reported, not a fix: Core 2 has no"
    " choreography yet, and it must not swing the pan to -40 at full speed with the head on",
}


def problems(report):
    """Every threshold the report fails: misplaced parts, fits, beams, the electrical cap and sag, and the MuJoCo half."""
    out = [f"placement: {v}" for v in report["placements"]]
    for f in report.get("fits", []):
        if not f["ok"]:
            out.append(
                f"fit {f['joint']}: {f['clearance']} mm radial clearance (hole r {f['hole_r']}, pin r {f['pin_r']})"
            )
    for b in report.get("beams", []):
        if not b["ok"]:
            out.append(f"beam {b['beam']}: SF {b['sf']} (deflection {b['deflection_mm']} mm)")
    e = report.get("electrical")  # model/electrical.py: a cut-off pack sags the servos (known), never a Core's reset
    if e:
        for core, a in e["nominal"]["shield_a"].items():
            if a >= e["cap_a"]:
                out.append(f"electrical {core}: {a} A with every servo at stall >= the {e['cap_a']} A cap")
        for name, v in e["nominal"]["servo_v"].items():
            if v < e["servo_min_v"]:
                out.append(
                    f"electrical {name} servo: {v} V at stall on a nominal pack < the {e['servo_min_v']} V minimum"
                )
        for case in ("nominal", "cutoff"):
            for core, v in e[case]["core_v"].items():
                if v < e["brownout_v"]:
                    out.append(
                        f"electrical {core}: {v} V on a {e[case]['pack_v']} V pack < the {e['brownout_v']} V brownout"
                    )
    return out + mujoco_problems(report)


def deeper(pair):
    """mm a pair's pieces go deeper than at rest (their own hull error is in the rest reading)."""
    return round(min(pair["rest_mm"] or 0, 0) - pair["min_mm"], 3)


def mujoco_problems(report):
    """The MuJoCo half (model/mujoco_report.py): a pair deeper than at rest, an open four-bar, a servo holding over its rated
    torque, a joint a full-speed swing leaves off the slow pose, the centre of mass off the footprint. Listed exceptions
    (KNOWN_PAIRS, KNOWN_FULL_SPEED) carry their reasons."""
    m, doc, out = report.get("mujoco", {}), report["doc"], []
    for p in m.get("pairs", []):
        if deeper(p) > mujoco_report.PENETRATION_MM and frozenset(p["pair"]) not in KNOWN_PAIRS:
            out.append(
                f"mujoco {' / '.join(p['pair'])}: {p['min_mm']} mm at {p['at']}, {deeper(p)} deeper than at rest"
            )
    for loop, r in m.get("residuals", {}).items():
        if r["max_mm"] > mujoco_report.LOOP_MM:
            out.append(f"mujoco four-bar {loop}: open {r['max_mm']} mm at {r['at']} > {mujoco_report.LOOP_MM}")
    for horn, a in m.get("actuators", {}).items():
        if a["hold_kgf_cm"] > a["rated_kgf_cm"]:
            out.append(
                f"mujoco {horn}: holds {a['hold_kgf_cm']} kgf.cm at {a['at']} > its rated {a['rated_kgf_cm']}"
                f" (stall {a['stall_kgf_cm']})"
            )
    for horn, f in m.get("full_speed", {}).items():
        if f["off_deg"] > mujoco_report.TURN_DEG and (doc, horn, f["at"]) not in KNOWN_FULL_SPEED:
            out.append(
                f"mujoco {horn} at full speed ({f['deg_s']} deg/s) to {f['at']}: its joints settle {f['off_deg']} deg"
                " off the slow pose"
            )
    tip = m.get("tip_over")
    if tip and tip["margin_mm"] <= 0:
        out.append(f"mujoco tip-over: centre of mass {-tip['margin_mm']} mm outside the base footprint at {tip['at']}")
    return out


def built(doc):
    path = os.path.join(report.OUT, f"{doc}-sim.json")
    if not os.path.isfile(path):
        pytest.skip(f"{doc} not simulated here: make sim")
    return json.load(open(path))


def test_reports_are_build_outputs_git_ignores():
    path = os.path.join(report.OUT, "noggin-eyes-sim.json")
    assert subprocess.run(["git", "check-ignore", "-q", path], cwd=stages.REPO).returncode == 0


@pytest.mark.parametrize("doc", sorted(stages.DOCS))
def test_built_report_is_clean(doc):
    assert problems(built(doc)) == []


FIXTURE_PROBLEMS = {
    "passing": [],
    "failing": [
        "placement: {'placement': 'eye bracket:1', 'mm': 5.0, 'tol': 0.5, 'actual': [[0.0, 0.0, 5.0]]}",
        "fit eyeball bar / horn screw: 0.05 mm radial clearance (hole r 1.05, pin r 1.0)",
        "beam lid bar: SF 1.65 (deflection 1.939 mm)",
        "electrical core1: 3.2 A with every servo at stall >= the 3.0 A cap",
        "electrical tilt servo: 4.7 V at stall on a nominal pack < the 4.8 V minimum",
        "electrical core2: 2.4 V on a 5.8 V pack < the 2.51 V brownout",
        "mujoco R eye horn:1 / R servo bracket:1: -0.12 mm at {'R eye horn': -22}, 0.1 deeper than at rest",
        "mujoco pan turntable:1 / tilt bar:1: -0.08 mm at {'tilt horn': -60}, 0.08 deeper than at rest",
        "mujoco four-bar tilt pivot: open 0.07 mm at {'tilt horn': 60} > 0.05",
        "mujoco tilt horn: holds 0.45 kgf.cm at {'tilt horn': -60} > its rated 0.4 (stall 1.0)",
        "mujoco pan horn at full speed (428.6 deg/s) to -40: its joints settle 29.1 deg off the slow pose",
        "mujoco tip-over: centre of mass 2.0 mm outside the base footprint at {'pan horn': 70, 'tilt horn': 60}",
    ],
}


@pytest.mark.parametrize("name", sorted(FIXTURE_PROBLEMS))
def test_fixture_reports(name):
    report = json.load(open(os.path.join(HERE, "test_fixtures", f"{name}-report.json")))
    assert problems(report) == FIXTURE_PROBLEMS[name]


def test_known_mujoco_exceptions_are_still_there():
    """When the model changes so a KNOWN_PAIRS entry no longer goes deeper than at rest at all, or a KNOWN_FULL_SPEED
    swing lands, drop it. (Any depth, not the threshold: CI's Linux pieces may read a little differently.)"""
    going, swings = set(), set()
    for doc in stages.DOCS:
        m = built(doc)["mujoco"]
        going |= {frozenset(p["pair"]) for p in m["pairs"] if deeper(p) > 0}
        swings |= {(doc, h, f["at"]) for h, f in m["full_speed"].items() if f["off_deg"] > mujoco_report.TURN_DEG}
    assert set(KNOWN_PAIRS) <= going
    assert swings == set(KNOWN_FULL_SPEED)
