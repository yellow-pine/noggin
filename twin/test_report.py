"""Seam: the JSON report twin/check.py writes (twin/build/<doc>-report.json). The live-report test is
skipped until `make twin-check` has run; the fixture test checks the checker itself."""
import glob, json, os, sys, pytest
sys.path.insert(0, os.path.dirname(__file__))

HERE = os.path.dirname(__file__)
CLEARANCE_MM, MAX_INTERFERENCE_MM3 = 3.0, 0.5
ENVELOPE = ((-60, 120), (-120, 60), (-60, 180))  # Mech extent in the eyes frame, mm (x, y, z)
REPORTS = sorted(glob.glob(os.path.join(HERE, "build", "*-report.json")))


def problems(report):
    out = [f"violation: {v}" for v in report["violations"]]
    for name, h in report["horns"].items():
        if h.get("incomplete"):
            out.append(f"{name}: incomplete ({h['incomplete']})")
        elif h["min_mm"] < CLEARANCE_MM - 0.1:
            out.append(f"{name}: {h['min_mm']} mm at {h['at_deg']} deg between {h['pair']}")
    for i in report["interference"]:
        if i["volume_mm3"] > MAX_INTERFERENCE_MM3:
            out.append(f"interference {i['a']} x {i['b']}: {i['volume_mm3']} mm3 at {i['pose']}")
    if not report["bboxes"]:
        out.append("no bboxes")
    for occ, (lo, hi) in report["bboxes"].items():
        if any(a < e[0] or b > e[1] for a, b, e in zip(lo, hi, ENVELOPE)):
            out.append(f"{occ}: bbox {lo}..{hi} outside envelope")
    return out


@pytest.mark.parametrize("path", REPORTS or [None])
def test_live_report_is_clean(path):
    if path is None:
        pytest.skip("no twin/build/*-report.json: run `make twin-check` with Fusion open")
    assert problems(json.load(open(path))) == []


FIXTURE_PROBLEMS = {
    "passing": [],
    "failing": [
        "violation: {'horn': 'L lid horn', 'deg': 120, 'mm': 1.2}",
        "L lid horn: 1.2 mm at 120 deg between ['L inside lid', 'L servo bracket']",
        "interference L eyeball x L pupil: 2.4 mm3 at neutral",
        "L eyeball: bbox [-14, -14, -14]..[14, 14, 200] outside envelope",
    ],
}


@pytest.mark.parametrize("name", sorted(FIXTURE_PROBLEMS))
def test_fixture_reports(name):
    report = json.load(open(os.path.join(HERE, "test_fixtures", f"{name}-report.json")))
    assert problems(report) == FIXTURE_PROBLEMS[name]


def test_merge_per_horn_reports_and_flags_incomplete_horns():
    from sweep import merge
    lid = {"doc": "noggin-eyes", "version": 11, "clearance_mm": 3.0, "step_deg": 10,
           "horns": {"L lid horn": {"min_mm": 4.1, "at_deg": 30, "pair": ["L inside lid", "L servo bracket"]}},
           "interference": [], "violations": [{"horn": "L lid horn", "deg": 30, "mm": 0.0, "pair": ["a", "b"]}],
           "bboxes": {"L eyeball": [[-14, -14, -14], [14, 14, 14]]}, "placements": [{"name": "L eye servo", "ok": True}]}
    eye = {"doc": "noggin-eyes", "version": 11, "clearance_mm": 3.0, "step_deg": 10,
           "horns": {"L eye horn": {"min_mm": None, "at_deg": None, "pair": None, "incomplete": "budget of 180 s spent at 10 deg"}},
           "interference": [], "violations": [], "bboxes": {"L eyeball": [[-14, -14, -14], [14, 14, 14]]}, "placements": []}
    report = merge([lid, eye])
    assert set(report["horns"]) == {"L lid horn", "L eye horn"}
    assert report["violations"] == lid["violations"] and report["bboxes"] == lid["bboxes"] and report["version"] == 11
    assert problems(report) == ["violation: {'horn': 'L lid horn', 'deg': 30, 'mm': 0.0, 'pair': ['a', 'b']}",
                                "L eye horn: incomplete (budget of 180 s spent at 10 deg)"]
