"""Seam: the JSON report `make sim` writes (model/engine/run.py, model/build/<doc>-sim.json). The live-report test is
skipped until `make sim` has run; the fixture test checks the checker itself."""

import glob
import json
import os

import pytest

HERE = os.path.dirname(__file__)
MAX_INTERFERENCE_MM3 = 0.5
ENVELOPE = {
    "noggin-eyes": ((-60, 120), (-120, 60), (-60, 180)),  # Mech extent per Stage frame, mm (x, y, z)
    "noggin-pan-tilt": ((-62, 62), (-26, 136), (-3, 60)),  # PandT base 120 x 160, tilt arm top z ~41
    "noggin-mouth": ((-60, 120), (-120, 60), (-60, 180)),  # the eyes envelope: noggin-eyes is referenced in whole
    "noggin-stage1": ((-62, 62), (-40, 136), (-10, 70)),  # PT frame: base + eyes on the pan recess
    "noggin-stage2": ((-62, 62), (-52, 136), (-3, 110)),  # + stack, eyes on the tilt arm
    "noggin-stage3": ((-66, 66), (-66, 136), (-3, 110)),  # + mouth
}
REPORTS = sorted(glob.glob(os.path.join(HERE, "build", "*-sim.json")))


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
        if (
            "dynamic_kgf_cm" in t
        ):  # gravity + inertia x peak acceleration (model/engine/mech.py) replaces the static figure
            if t["dynamic_kgf_cm"] > t["limit_kgf_cm"]:
                out.append(
                    f"torque {horn}: {t['dynamic_kgf_cm']} kgf.cm dynamic at {t['dynamic_at_deg']} deg > {t['limit_kgf_cm']}"
                )
        elif t["kgf_cm"] > t["limit_kgf_cm"]:
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
        pytest.skip("no model/build/*-sim.json: run `make sim`")
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
        "torque R lid horn: 0.25 kgf.cm dynamic at 30 deg > 0.2",
        "calibrated L lid horn: collision at 39 deg between ['L outside lid', 'L servo bracket']",
    ],
}


@pytest.mark.parametrize("name", sorted(FIXTURE_PROBLEMS))
def test_fixture_reports(name):
    report = json.load(open(os.path.join(HERE, "test_fixtures", f"{name}-report.json")))
    assert problems(report) == FIXTURE_PROBLEMS[name]
