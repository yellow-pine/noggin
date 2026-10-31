"""Seam: the JSON reports `make sim` writes and commits (model/engine/run.py, model/reports/<doc>-sim.json). CI checks
every committed report: no problems, and its stamp still matches the inputs in the repo (designer meshes are not in the
repo: their fingerprints recorded at sim time are hashed instead). The fixture test checks the checker itself."""

import json
import os

import pytest

from model.engine import run, stages

HERE = os.path.dirname(__file__)


def problems(report):
    """Every threshold the report fails: penetrations and misplaced parts (violations; a 0 mm contact with nothing
    inside is designed), fits, beams, torque, tip-over, clutch, cable corridors (path length, clearance), the electrical cap and the calibrated ends."""
    out = [f"violation: {v}" for v in report["violations"]]
    for f in report.get("fits", []):
        if not f["ok"]:
            out.append(
                f"fit {f['joint']}: {f['clearance']} mm radial clearance (hole r {f['hole_r']}, pin r {f['pin_r']})"
            )
    for b in report.get("beams", []):
        if not b["ok"]:
            out.append(f"beam {b['beam']}: SF {b['sf']} (deflection {b['deflection_mm']} mm)")
    for horn, t in report.get("torque", {}).items():
        if (
            "dynamic_kgf_cm" in t
        ):  # gravity + inertia x peak acceleration (model/engine/mech.py) replaces the static figure
            if t["dynamic_kgf_cm"] > t["limit_kgf_cm"]:
                out.append(
                    f"torque {horn}: {t['dynamic_kgf_cm']} kgf.cm dynamic at {t['dynamic_at_deg']} deg > {t['limit_kgf_cm']}"
                )
        elif t["kgf_cm"] > t["limit_kgf_cm"]:
            out.append(f"torque {horn}: {t['kgf_cm']} kgf.cm at {t['at_deg']} deg > {t['limit_kgf_cm']}")
    tip = report.get("tip_over")
    if tip and tip["margin_mm"] <= 0:
        out.append(
            f"tip-over: centre of mass {-tip['margin_mm']} mm outside the base footprint at pan {tip['at']['pan']} "
            f"tilt {tip['at']['tilt']}"
        )
    for horn, c in report.get("clutch", {}).items():
        if c["flagged"]:
            out.append(
                f"clutch {horn}: holding load over {c['limit_kgf_cm']} kgf.cm (0.9 / 1.5, decalibration risk) at "
                f"{c['flagged']} deg, worst {c['hold_kgf_cm']} at {c['at_deg']}"
            )
    for lead, c in report.get("corridors", {}).items():
        if c["max_mm"] > c["limit_mm"]:
            out.append(
                f"corridor {lead}: {c['max_mm']} mm at {c['at']} > {c['limit_mm']} ({c['length_mm']} mm lead less 20 slack)"
            )
        if c["clearance_mm"] < 0:  # the tube's surface inside a moving part
            out.append(
                f"corridor {lead}: tube {-c['clearance_mm']} mm into {c['clearance_part']} at {c['clearance_at']}"
            )
    e = report.get("electrical")
    for core, a in (e or {}).get("stall_a", {}).items():
        if a >= e["cap_a"]:
            out.append(f"electrical {core}: {a} A with every servo at stall >= the {e['cap_a']} A cap")
    for horn, c in report.get("calibrated", {}).items():
        # the real Mech runs its calibrated ends (eyes/calibration.json); while the pivot is inferred: run.warnings
        for v in c.get("violations", []) if not c["inferred"] else []:
            out.append(f"calibrated {horn}: collision at {v['deg']} deg between {v['pair']}")
    return out


def committed(doc):
    return json.load(open(os.path.join(HERE, "reports", f"{doc}-sim.json")))


@pytest.mark.parametrize("doc", sorted(stages.DOCS))
def test_committed_report_is_clean(doc):
    assert problems(committed(doc)) == []


@pytest.mark.parametrize("doc", sorted(stages.DOCS))
def test_committed_report_is_stamped_with_the_inputs_in_the_repo(doc):
    inputs = committed(doc)["inputs"]
    assert inputs["stamp"] == run.stamp(inputs["sources"]), "stale: run `make sim` and commit model/reports"


def test_stamp_follows_the_recorded_part_fingerprints():
    sources = {"docs/references/a.stl": "0" * 16}
    assert run.stamp(sources) == run.stamp(dict(sources))
    assert run.stamp(sources) != run.stamp({"docs/references/a.stl": "1" * 16})


FIXTURE_PROBLEMS = {
    "passing": [],
    "failing": [
        "violation: {'horn': 'L lid horn', 'deg': 120, 'mm': 1.2}",
        "fit eyeball bar / horn screw: 0.05 mm radial clearance (hole r 1.05, pin r 1.0)",
        "beam eyelid bar: SF 1.65 (deflection 1.939 mm)",
        "torque L lid horn: 0.31 kgf.cm at -20 deg > 0.2",
        "torque R lid horn: 0.25 kgf.cm dynamic at 30 deg > 0.2",
        "tip-over: centre of mass 3.2 mm outside the base footprint at pan -50 tilt 60",
        "clutch L lid horn: holding load over 0.6 kgf.cm (0.9 / 1.5, decalibration risk) at [20, 30] deg, worst 0.7 at 30",
        "corridor l_lid servo -> Core 1 PWM1: 236.0 mm at {'pan horn (inferred)': 70, 'tilt horn (inferred)': 60} > 230"
        " (250 mm lead less 20 slack)",
        "corridor l_lid servo -> Core 1 PWM1: tube 0.8 mm into pan bar (inferred):1 at {'tilt horn (inferred)': -60}",
        "electrical core1: 3.2 A with every servo at stall >= the 3.0 A cap",
        "calibrated L lid horn: collision at 39 deg between ['L outside lid', 'L servo bracket']",
    ],
}


@pytest.mark.parametrize("name", sorted(FIXTURE_PROBLEMS))
def test_fixture_reports(name):
    report = json.load(open(os.path.join(HERE, "test_fixtures", f"{name}-report.json")))
    assert problems(report) == FIXTURE_PROBLEMS[name]


def test_calibrated_end_collisions_warn_while_the_horn_is_inferred_and_fail_once_measured():
    report = json.load(open(os.path.join(HERE, "test_fixtures", "failing-report.json")))
    assert "calibrated L lid horn: collision at 39 deg between ['L outside lid', 'L servo bracket']" in problems(report)
    assert not any("L eye horn" in p for p in problems(report))
    assert run.warnings(report) == [
        "calibrated L eye horn (inferred): collision at -32 deg between ['L eyeball bar', 'main bracket v2']"
        " (pivot inferred: fails once measured)"
    ]
    assert committed("noggin-eyes")["warnings"] == run.warnings(committed("noggin-eyes")) != []
