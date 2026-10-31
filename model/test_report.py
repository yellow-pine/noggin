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
    inside is designed), fits, beams, torque, tip-over, clutch, cable reach, the electrical cap and the calibrated ends."""
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
    for lead, c in report.get("cable_reach", {}).items():
        if c["max_mm"] > c["limit_mm"]:
            out.append(
                f"cable {lead}: {c['max_mm']} mm at pan {c['at']['pan']} tilt {c['at']['tilt']} > {c['limit_mm']} "
                f"({c['length_mm']} mm lead less 20 slack)"
            )
    e = report.get("electrical")
    for core, a in (e or {}).get("stall_a", {}).items():
        if a >= e["cap_a"]:
            out.append(f"electrical {core}: {a} A with every servo at stall >= the {e['cap_a']} A cap")
    for horn, c in report.get("calibrated", {}).items():
        # Collisions at the calibrated servo ends count once the horn's pivot is measured: an inferred pivot (+-4 mm)
        # cannot answer where the real Mech's ends are, and it does run them (eyes/calibration.json).
        for v in c.get("violations", []) if "(inferred)" not in horn else []:
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
        "cable l_lid servo -> Core 1 PWM1: 236.0 mm at pan 70 tilt 60 > 230 (250 mm lead less 20 slack)",
        "electrical core1: 3.2 A with every servo at stall >= the 3.0 A cap",
        "calibrated L lid horn: collision at 39 deg between ['L outside lid', 'L servo bracket']",
    ],
}


@pytest.mark.parametrize("name", sorted(FIXTURE_PROBLEMS))
def test_fixture_reports(name):
    report = json.load(open(os.path.join(HERE, "test_fixtures", f"{name}-report.json")))
    assert problems(report) == FIXTURE_PROBLEMS[name]
