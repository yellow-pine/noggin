"""Seam: the JSON report model/check.py writes (model/build/<doc>-report.json). The live-report test is
skipped until `make model-check` has run; the fixture test checks the checker itself."""

import glob
import importlib.util
import json
import os

import pytest

HERE = os.path.dirname(__file__)
MAX_INTERFERENCE_MM3 = 0.5
ENVELOPE = {
    "noggin-eyes": ((-60, 120), (-120, 60), (-60, 180)),  # Mech extent per Stage frame, mm (x, y, z)
    "noggin-pan-tilt": ((-62, 62), (-26, 136), (-3, 60)),  # PandT base 120 x 160, tilt arm top z ~41
    "noggin-mouth": ((-60, 120), (-120, 60), (-60, 180)),
}  # the eyes envelope: noggin-eyes is referenced in whole
REPORTS = sorted(glob.glob(os.path.join(HERE, "build", "*-report.json")))


def problems(report):
    out = [f"violation: {v}" for v in report["violations"]]
    for name, h in report["horns"].items():
        if h.get("incomplete"):
            out.append(f"{name}: incomplete ({h['incomplete']})")
        elif h["min_mm"] < report["clearance_mm"] - 0.1:
            out.append(f"{name}: {h['min_mm']} mm at {h['at_deg']} deg between {h['pair']}")
    for i in report["interference"]:
        if i["volume_mm3"] is None or i["volume_mm3"] > MAX_INTERFERENCE_MM3:
            out.append(f"interference {i['a']} x {i['b']}: {i['volume_mm3']} mm3 at {i['pose']}")
    if not report["bboxes"]:
        out.append("no bboxes")
    for occ, (lo, hi) in report["bboxes"].items():
        if any(a < e[0] or b > e[1] for a, b, e in zip(lo, hi, ENVELOPE[report["doc"]])):
            out.append(f"{occ}: bbox {lo}..{hi} outside envelope")
    for f in report.get("fits", []):  # #20 extras (model/sim.py), absent from older reports
        if not f["ok"]:
            out.append(
                f"fit {f['joint']}: {f['clearance']} mm radial clearance (hole r {f['hole_r']}, pin r {f['pin_r']})"
            )
    for b in report.get("beams", []):
        if not b["ok"]:
            out.append(f"beam {b['beam']}: SF {b['sf']} (deflection {b['deflection_mm']} mm)")
    for horn, t in report.get("torque", {}).items():
        if t["kgf_cm"] > t["limit_kgf_cm"]:
            out.append(f"torque {horn}: {t['kgf_cm']} kgf.cm at {t['at_deg']} deg > {t['limit_kgf_cm']}")
    for horn, c in report.get("calibrated", {}).items():
        # Collisions at the calibrated servo ends count once the horn's pivot is measured: an inferred pivot (+-4 mm)
        # cannot answer where the real Mech's ends are, and it does run them (eyes/calibration.json).
        for v in c.get("violations", []) if "(inferred)" not in horn else []:
            out.append(f"calibrated {horn}: collision at {v['deg']} deg between {v['pair']}")
    return out


@pytest.mark.parametrize("path", REPORTS or [None])
def test_live_report_is_clean(path):
    if path is None:
        pytest.skip("no model/build/*-report.json: run `make model-check` with Fusion open")
    assert problems(json.load(open(path))) == []


FIXTURE_PROBLEMS = {
    "passing": [],
    "failing": [
        "violation: {'horn': 'L lid horn', 'deg': 120, 'mm': 1.2}",
        "L lid horn: 1.2 mm at 120 deg between ['L inside lid', 'L servo bracket']",
        "interference L eyeball x L pupil: 2.4 mm3 at neutral",
        "L eyeball: bbox [-14, -14, -14]..[14, 14, 200] outside envelope",
        "fit eyeball bar / horn screw: 0.05 mm radial clearance (hole r 1.05, pin r 1.0)",
        "beam eyelid bar: SF 1.65 (deflection 1.939 mm)",
        "torque L lid horn: 0.31 kgf.cm at -20 deg > 0.2",
        "calibrated L lid horn: collision at 39 deg between ['L outside lid', 'L servo bracket']",
    ],
}


@pytest.mark.parametrize("name", sorted(FIXTURE_PROBLEMS))
def test_fixture_reports(name):
    report = json.load(open(os.path.join(HERE, "test_fixtures", f"{name}-report.json")))
    assert problems(report) == FIXTURE_PROBLEMS[name]


def test_merge_per_horn_reports_and_flags_incomplete_horns():
    spec = importlib.util.spec_from_file_location(
        "sweep", os.path.join(HERE, "sweep.py")
    )  # not on sys.path: eyes/ has its own `eyes` module
    sweep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sweep)
    merge = sweep.merge
    lid = {
        "doc": "noggin-eyes",
        "version": 11,
        "clearance_mm": 3.0,
        "step_deg": 10,
        "horns": {"L lid horn": {"min_mm": 4.1, "at_deg": 30, "pair": ["L inside lid", "L servo bracket"]}},
        "interference": [],
        "violations": [{"horn": "L lid horn", "deg": 30, "mm": 0.0, "pair": ["a", "b"]}],
        "bboxes": {"L eyeball": [[-14, -14, -14], [14, 14, 14]]},
        "placements": [{"name": "L eye servo", "ok": True}],
    }
    eye = {
        "doc": "noggin-eyes",
        "version": 11,
        "clearance_mm": 3.0,
        "step_deg": 10,
        "horns": {
            "L eye horn": {
                "min_mm": None,
                "at_deg": None,
                "pair": None,
                "incomplete": "budget of 180 s spent at 10 deg",
            }
        },
        "interference": [],
        "violations": [],
        "bboxes": {"L eyeball": [[-14, -14, -14], [14, 14, 14]]},
        "placements": [],
        "calibrated": {"L eye horn": {"lo": -32, "hi": 28}},
    }
    lid["violations"].append({"horn": "L lid horn", "deg": 39, "mm": 0.0, "pair": ["c", "d"], "calibrated": True})
    report = merge([lid, eye])
    assert report["calibrated"] == {
        "L eye horn": {"lo": -32, "hi": 28},
        "L lid horn": {"violations": [{"deg": 39, "pair": ["c", "d"]}]},
    }
    assert set(report["horns"]) == {"L lid horn", "L eye horn"}
    assert (
        report["violations"] == lid["violations"][:1] and report["bboxes"] == lid["bboxes"] and report["version"] == 11
    )
    assert problems(report) == [
        "violation: {'horn': 'L lid horn', 'deg': 30, 'mm': 0.0, 'pair': ['a', 'b']}",
        "L eye horn: incomplete (budget of 180 s spent at 10 deg)",
        "calibrated L lid horn: collision at 39 deg between ['c', 'd']",
    ]
