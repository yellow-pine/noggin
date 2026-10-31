"""Seam: the JSON reports `make sim` writes and commits (model/engine/run.py, model/reports/<doc>-sim.json). CI checks
every committed report: no problems, and its stamp still matches the inputs in the repo (our meshes are built, not
committed: their fingerprints recorded at sim time are hashed instead). The fixture test checks the checker itself."""

import json
import os

import pytest

from model.engine import mating, run, stages

HERE = os.path.dirname(__file__)
_LID = (
    "the real Mech closes the lid here, past the model's -20 end: the lid crank's step meets eye bracket's outer"
    " edge (x -27..-28) from -38, 1.0 mm deep; the crank's plane needs the calliper"
)
_EYE = (
    "the real Mech runs here, past +-22: the eyeball bar rides on the eye bracket and the model has it 0.26..0.5 mm in"
    " (the eye horn 0.2..0.5 mm into the brackets at -32); the bar and rail heights need the calliper"
)
# (horn, calibrated end): where the model still collides and the real Mech runs. The build wins (CLAUDE.md): these are
# model errors to fix once a build measurement settles which geometry (listed, never loosened silently).
KNOWN_CALIBRATED = {
    ("L lid horn", -54): _LID,
    ("R lid horn", -46): _LID,
    ("L eye horn", -32): _EYE,
}


def problems(report):
    """Every threshold the report fails: penetrations and misplaced parts (violations; a 0 mm contact with nothing
    inside is designed), fits, beams, torque, tip-over, clutch, cable corridors (path length, clearance), the electrical cap, the calibrated ends and the mating check."""
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
            if (horn, v["deg"]) not in KNOWN_CALIBRATED:
                out.append(f"calibrated {horn}: collision at {v['deg']} deg between {v['pair']}")
    for m in report.get("mating", []):  # model/engine/mating.py; an inferred joint warns instead (run.warnings)
        if m["ok"] or m.get("inferred"):
            continue
        if "missing" in m:
            out.append(f"mating {m['joint']}: no hole feature found on {m['missing']}")
        elif m["kind"] == "overlap":
            out.append(f"mating {m['joint']}: {m['mm']} mm into {m['parts'][1]}")
        elif m["kind"] == "lead":
            out.append(f"mating {m['joint']}: the lead runs into {m['parts'][1]}")
        elif m["kind"] == "seat":
            out.append(f"mating {m['joint']}: {m['mm']} mm off {m['parts'][1]}")
        else:
            out.append(f"mating {m['joint']}: axes {m['mm']} mm apart > {mating.COAXIAL_MM}")
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
    sources = {"model/build/ours/a.stl": "0" * 16}
    assert run.stamp(sources) == run.stamp(dict(sources))
    assert run.stamp(sources) != run.stamp({"model/build/ours/a.stl": "1" * 16})


FIXTURE_PROBLEMS = {
    "passing": [],
    "failing": [
        "violation: {'horn': 'L lid horn', 'deg': 120, 'mm': 1.2}",
        "fit eyeball bar / horn screw: 0.05 mm radial clearance (hole r 1.05, pin r 1.0)",
        "beam lid bar: SF 1.65 (deflection 1.939 mm)",
        "torque L lid horn: 0.31 kgf.cm at -20 deg > 0.2",
        "torque R lid horn: 0.25 kgf.cm dynamic at 30 deg > 0.2",
        "tip-over: centre of mass 3.2 mm outside the base footprint at pan -50 tilt 60",
        "clutch L lid horn: holding load over 0.6 kgf.cm (0.9 / 1.5, decalibration risk) at [20, 30] deg, worst 0.7 at 30",
        "corridor l_lid servo -> Core 1 PWM1: 236.0 mm at {'pan horn': 70, 'tilt horn': 60} > 230"
        " (250 mm lead less 20 slack)",
        "corridor l_lid servo -> Core 1 PWM1: tube 0.8 mm into pan bar:1 at {'tilt horn': -60}",
        "electrical core1: 3.2 A with every servo at stall >= the 3.0 A cap",
        "calibrated L lid horn: collision at 39 deg between ['L lower lid', 'L servo bracket']",
        "mating L lid servo / L servo bracket upper tab screw: axes 0.35 mm apart > 0.2",
        "mating L lid servo in its mount: 0.4 mm into L servo bracket:1",
        "mating R lid servo in its mount: 0.3 mm off R servo bracket:1",
        "mating pan servo lead exit: the lead runs into pan servo tail mount:1",
        "mating jaw servo / jaw servo mount lower tab screw: no hole feature found on jaw servo mount:1",
    ],
}


@pytest.mark.parametrize("name", sorted(FIXTURE_PROBLEMS))
def test_fixture_reports(name):
    report = json.load(open(os.path.join(HERE, "test_fixtures", f"{name}-report.json")))
    assert problems(report) == FIXTURE_PROBLEMS[name]


def test_calibrated_end_collisions_warn_while_the_horn_is_inferred_and_fail_once_measured():
    report = json.load(open(os.path.join(HERE, "test_fixtures", "failing-report.json")))
    assert "calibrated L lid horn: collision at 39 deg between ['L lower lid', 'L servo bracket']" in problems(report)
    assert not any("L eye horn" in p for p in problems(report))
    assert run.warnings(report) == [
        "calibrated L eye horn: collision at -32 deg between ['L eyeball bar', 'eye bracket']"
        " (pivot inferred: fails once measured)",
        "mating L eye horn / L eyeball bar pin: coaxial 0.21 mm between ['L eye horn:1', 'L eyeball bar:1'] (inferred:"
        " no source settles it)",
    ]
    assert (
        committed("noggin-eyes")["warnings"] == run.warnings(committed("noggin-eyes")) == []
    )  # no pivot inferred (#62)


def test_known_calibrated_collisions_are_still_there():
    """When the model changes so a KNOWN_CALIBRATED entry no longer collides, drop it."""
    report = committed("noggin-eyes")
    found = {(h, v["deg"]) for h, r in report["calibrated"].items() for v in r.get("violations", [])}
    assert set(KNOWN_CALIBRATED) == found


def test_inferred_mating_joints_still_mismatch():
    """When the model changes so a mating.INFERRED joint lines up, drop it."""
    found = {m["joint"] for doc in stages.DOCS for m in committed(doc).get("mating", []) if not m["ok"]}
    assert set(mating.INFERRED) <= found
