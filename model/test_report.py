"""Seam: the JSON reports `make sim` writes and commits (model/engine/run.py, model/reports/<doc>-sim.json). CI checks
every committed report: no problems, and its stamp still matches the inputs in the repo (our meshes are built, not
committed: their fingerprints recorded at sim time are hashed instead). The fixture test checks the checker itself."""

import json
import os

import pytest

from model import mujoco_report
from model.engine import mating, run, stages

HERE = os.path.dirname(__file__)
_LID_OPEN = (
    "the real Mech's open end with the horn's tooth (geometry.HORN_AT_90): in the model the lower lid's back rim meets the"
    " servo bracket's front face from +39, 1.3 mm deep at 45, 2.0 at 52 (and the upper lid 0.35 mm into the eyeball bar"
    " there). Best guess (#170, docs/research/2026-11-01-best-guesses.md): the build runs it, so the model's lid travel"
    " (88 deg free) is short of the build's (93 / 85 servo deg) by a lid or bracket shape error no tolerance in the sources"
    " reaches: the tooth is held by the shut lids and the rest photo, the servo's 180 +-10 deg spec moves the end 3 deg at"
    " most, a print tolerance of 0.2 mm 1.3 deg. Accepted, not a measurement to wait for"
)
# (horn, calibrated end): where the model still collides and the real Mech runs, each with the reason it is accepted.
# The build wins (CLAUDE.md): listed, never loosened silently.
KNOWN_CALIBRATED = {
    ("L lid horn", 52): _LID_OPEN,
    ("R lid horn", 45): _LID_OPEN,
}
# MuJoCo pairs (model/mujoco_report.py) that go deeper than at rest across a sweep, each with what the exact meshes say
# at the same pose (model/engine/meshes.judge). Two kinds: the convex pieces fill a part's own clearance (the meshes are clear),
# or the meshes overlap too, at a LIMITS end, where the old engine never looked (it skips a lid or eyeball on its bracket
# pivot and a four-bar's two rockers): the build runs those ends, so it is a part shape error as _LID_OPEN, accepted.
_SHELL = "pieces only: the lid shell's pieces fill its 0.48 mm gap to the eyeball; the meshes stay 0.48 mm clear"
_LID_ENDS = (
    "pieces 4.6 mm at -39 (1.7 at rest); the meshes nest at 0.0 there but overlap at the ends, 1.39 mm at -49 (shut) and"
    " 1.03 at +39 (open): the build runs both, accepted"
)
_UPPER_ON_BRACKET = "pieces 0.75 mm deeper at +39; the meshes 0.78 mm in at +39 (open): the build runs it, accepted"
_EYE_ON_BRACKET = (
    "pieces 0.72 mm deeper at the end; the meshes 0.77 mm in at -22 and +22: the build runs both, accepted"
)
_LOWER_ON_BRACKET = (
    "the meshes 1.86 mm in at +39 (open): the build runs it, accepted; the pieces read only 0.16 (L) and 0.03 (R)"
    " deeper than at rest there, so they miss most of it"
)
KNOWN_PAIRS = {
    **{frozenset((f"{s} lower lid:1", f"{s} upper lid:1")): _LID_ENDS for s in "LR"},
    **{frozenset((f"{s} pupil:1", f"{s} {lid} lid:1")): _SHELL for s in "LR" for lid in ("upper", "lower")},
    **{frozenset((f"{s} upper lid:1", "eye bracket:1")): _UPPER_ON_BRACKET for s in "LR"},
    **{frozenset((f"{s} eyeball:1", "eye bracket:1")): _EYE_ON_BRACKET for s in "LR"},
    **{frozenset((f"{s} lower lid:1", "eye bracket:1")): _LOWER_ON_BRACKET for s in "LR"},
    frozenset(("base plate:1", "upright:1")): "pieces only: the plate's pieces fill the recess under the upright; the"
    " meshes stay 0.5 mm clear at pan -40",
    frozenset(("pan turntable:1", "tilt horn:1")): "pieces only: 0.14 mm in at tilt -60; the meshes stay 0.17 mm clear"
    " there (geometry.LIMITS stops the tilt at its lower end for this chord)",
}
# (document, horn, end): where a swing at the servo's rated speed does not end where the slow pose does.
KNOWN_FULL_SPEED = {
    ("noggin-stage3", "pan horn", -40): "the stage 3 head's inertia carries the pan four-bar through its toggle"
    " (-43.4, geometry.LIMITS) and it settles on the other branch, 29 deg off. Reported, not a fix: Core 2 has no"
    " choreography yet (model/engine/mech.py), and it must not swing the pan to -40 at full speed with the head on",
}


def problems(report):
    """Every threshold the report fails: penetrations and misplaced parts (violations; a 0 mm contact with nothing
    inside is designed), fits, beams, torque, tip-over, clutch, cable corridors (path length, clearance), the electrical cap and sag, the calibrated ends and the mating check."""
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
        "electrical tilt servo: 4.7 V at stall on a nominal pack < the 4.8 V minimum",
        "electrical core2: 2.4 V on a 5.8 V pack < the 2.51 V brownout",
        "calibrated L lid horn: collision at 39 deg between ['L lower lid', 'L servo bracket']",
        "mating L lid servo / L servo bracket upper tab screw: axes 0.35 mm apart > 0.2",
        "mating L lid servo in its mount: 0.4 mm into L servo bracket:1",
        "mating R lid servo in its mount: 0.3 mm off R servo bracket:1",
        "mating pan servo lead exit: the lead runs into pan servo tail mount:1",
        "mating jaw servo / jaw servo mount lower tab screw: no hole feature found on jaw servo mount:1",
        "mujoco R eyeball bar:1 / eye bracket:1: -0.12 mm at {'R eye horn': -22}, 0.1 deeper than at rest",
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


def test_no_listed_collision_or_mating_joint_waits_for_a_measurement():
    """Cansin cannot measure (#170): every value is a documented best guess, nothing defers to a calliper."""
    assert not [r for r in [*KNOWN_CALIBRATED.values(), *mating.INFERRED.values()] if "calliper" in r]
    assert mating.INFERRED == {}  # the jaw bar seats flush (geometry.PT_BAR_PLANES)


def test_known_mujoco_exceptions_are_still_there():
    """When the model changes so a KNOWN_PAIRS entry no longer goes deeper than at rest at all, or a KNOWN_FULL_SPEED
    swing lands, drop it. (Any depth, not the threshold: CI's Linux pieces may read a little differently.)"""
    going, swings = set(), set()
    for doc in stages.DOCS:
        m = committed(doc)["mujoco"]
        going |= {frozenset(p["pair"]) for p in m["pairs"] if deeper(p) > 0}
        swings |= {(doc, h, f["at"]) for h, f in m["full_speed"].items() if f["off_deg"] > mujoco_report.TURN_DEG}
    assert set(KNOWN_PAIRS) <= going
    assert swings == set(KNOWN_FULL_SPEED)


def test_mujoco_holds_what_the_old_engine_weighs():
    """Cross-check on the committed reports: each servo's holding force at its worst pose is the old engine's static
    gravity torque (within 0.01 kgf.cm), and the tip-over margin within 1 mm."""
    for doc in stages.DOCS:
        r = committed(doc)
        for horn, t in r["torque"].items():
            assert r["mujoco"]["actuators"][horn]["hold_kgf_cm"] == pytest.approx(t["kgf_cm"], abs=0.01), (doc, horn)
        if "tip_over" in r:
            assert r["mujoco"]["tip_over"]["margin_mm"] == pytest.approx(r["tip_over"]["margin_mm"], abs=1), doc


def test_inferred_mating_joints_still_mismatch():
    """When the model changes so a mating.INFERRED joint lines up, drop it."""
    found = {m["joint"] for doc in stages.DOCS for m in committed(doc).get("mating", []) if not m["ok"]}
    assert set(mating.INFERRED) <= found
