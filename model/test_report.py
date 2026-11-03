"""Seam: the JSON reports `just sim` writes (model/report.py, model/build/reports/<doc>-sim.json): build outputs, never
committed (docs/adr/0009). Right after just sim (CI's Sim job) every built report must have no problems; a document
not built here is skipped. Physics runs on the mechanical documents alone (geometry.SIMULATED, #809). The fixture test checks the checker itself."""

import json
import math
import os
import subprocess

import pytest

from model import base, fits, gimbal, mujoco_report, neck, report, sim, stages
from model import geometry as g

HERE = os.path.dirname(__file__)
# MuJoCo pairs (model/mujoco_report.py) that go deeper than at rest across a sweep, with why. Since #190 the pieces read
# what the exact meshes do (model/test_mjcf.py).
KNOWN_PAIRS = {
    frozenset(
        (f"next {s} push-rod:1", "next bail:1")
    ): "the push-rod's cup round the bail arm's ball: its convex pieces"
    " fill the cup (model/test_mjcf.py TOUCH), so they read 0.43 mm deeper as the rod turns on the ball; the exact solids"
    " share no volume at pitch -15, 0 and 15 (#663)"
    for s in "LR"
}


def known(pair):
    """A pair (names) whose depth is no problem: in KNOWN_PAIRS."""
    return frozenset(pair) in KNOWN_PAIRS


# (document, horn, end): where a swing at the servo's rated speed does not end where the slow pose does. None since the
# servos are DC motors (#625).
KNOWN_FULL_SPEED = {}
# (document, servo) whose load peaks over half its stall along a motion, with why.
KNOWN_PEAKS = {
    (doc, horn): "the next hero (#642) turns the next Mech's heavier head on the hero's keys, timed for Stage 3's: each"
    " 20 ms command step saturates the servo (~0.66 kgf.cm, Stage 3's 0.43); its own gestures, minimum jerk under an"
    " acceleration cap (#51), are a later ticket"
    for doc in g.SIMULATED
    if "pan horn" in stages.STAGES[doc].horns  # a Stage with the neck plays it (#720)
    for horn in ("pan horn", "tilt horn")
}
# Four-bars whose bar meets its lever under mujoco_report.TRANSMISSION_DEG somewhere in their range, with why.
KNOWN_TRANSMISSION = {}


def problems(report):
    """Every threshold the report fails: the electrical cap and sag, the MuJoCo half, the gimbal and the neck."""
    out = []
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
    return out + mujoco_problems(report) + gimbal_problems(report) + neck_problems(report) + variant_problems(report)


def variant_problems(report):
    """The next Mech's head variant (model/candidates.py report(), #686): what rides the head fits gimbal.HEAD_MM and its
    eyes sit in its lower half (base.EYES_UP, #708), in each look: a hard gate."""
    v, out = report.get("variant"), []
    if not v:
        return out
    if any(s > h for s, h in zip(v["head_mm"], gimbal.HEAD_MM)):
        size, head = (" x ".join(map(str, x)) for x in (v["head_mm"], gimbal.HEAD_MM))
        out.append(f"variant head: {size} mm (W x D x H) past the compact head's {head}")
    if v["eyes_up"] > base.EYES_UP:
        out.append(f"variant eyes: {v['eyes_up']} of the head's height up > {base.EYES_UP}")
    return out


def gimbal_problems(report):
    """The next Mech's eye gimbal (model/gimbal.py report(), #630): gaze with play and pupil seating, the caps' gap, the
    lids' clearance to what moves inside them and to each other, their servo range, its bounding box in the compact
    head (#684), and the lid drives' sweep (#650, model/printed/gimbal.py sweep())."""
    m, out = report.get("gimbal"), []
    if not m:
        return out
    if m["gaze_deg"] > gimbal.GAZE_DEG:
        out.append(
            f"gimbal gaze: {m['gaze_deg']} deg off with play ({m['play_deg']}) and pupil seating ({m['pupil_deg']})"
            f" > {gimbal.GAZE_DEG}"
        )
    if m["cap_gap_mm"] < gimbal.CAP_GAP_MM:
        out.append(f"gimbal caps: {m['cap_gap_mm']} mm apart < {gimbal.CAP_GAP_MM}")
    lid = m["lid"]
    if min(lid["clearance_mm"], lid["apart_mm"]) < gimbal.LID_CLEAR_MM:
        out.append(
            f"gimbal lids: {lid['clearance_mm']} mm clear of the parts inside them, {lid['apart_mm']} mm apart"
            f" < {gimbal.LID_CLEAR_MM}"
        )
    out += [
        f"gimbal lid servo: {d} deg past its {gimbal.SERVO_DEG}" for d in lid["servo_deg"] if abs(d) > gimbal.SERVO_DEG
    ]
    if any(b > h for b, h in zip(m["block_mm"], gimbal.HEAD_MM)):
        size, head = (" x ".join(map(str, v)) for v in (m["block_mm"], gimbal.HEAD_MM))
        out.append(f"gimbal block: {size} mm (W x D x H) past the compact head's {head}")
    s = m.get("sweep")
    if s and s["clearance_mm"] < gimbal.LID_CLEAR_MM:
        out.append(
            f"gimbal sweep: {' / '.join(s['pair'])} {s['clearance_mm']} mm apart at {s['at']} < {gimbal.LID_CLEAR_MM}"
        )
    return out + [f"gimbal sweep: {' / '.join(o['pair'])} overlap at {o['at']}" for o in (s or {}).get("overlaps", [])]


def neck_problems(report):
    """The next Mech's neck and jaw (model/neck.py report(), #641): each bar's transmission angle and its servo's
    travel, the tilt servo's hold against the rated torque, the flexing spans' bends against their floor."""
    m, out = report.get("neck"), []
    if not m:
        return out
    for drive in neck.RANGES:
        d = m[drive]
        if d["transmission_deg"] < neck.TRANSMISSION_DEG:
            out.append(
                f"neck {drive}: the bar meets its lever at {d['transmission_deg']} deg < {neck.TRANSMISSION_DEG}"
            )
        out += [
            f"neck {drive} servo: {s} deg past its {neck.SERVO_DEG}" for s in d["servo_deg"] if abs(s) > neck.SERVO_DEG
        ]
    if m["tilt"]["hold_kgf_cm"] > sim.RATED_KGF_CM:
        out.append(f"neck tilt: holds the head with {m['tilt']['hold_kgf_cm']} kgf.cm > the rated {sim.RATED_KGF_CM}")
    floor = m["spans"]["floor_mm"]
    out += [
        f"neck {span} span: bends to {m['spans'][span]['bend_mm']} mm < {floor}"
        for span in ("pan", "tilt")
        if m["spans"][span]["bend_mm"] < floor
    ]
    return out


def deeper(pair):
    """mm a pair's pieces go deeper than at rest (their own hull error is in the rest reading)."""
    return round(min(pair["rest_mm"] or 0, 0) - pair["min_mm"], 3)


def mujoco_problems(report):
    """The MuJoCo half (model/mujoco_report.py): a pair deeper than at rest, an open four-bar, a four-bar near its toggle
    (its singularity margin or transmission angle under the gate, #627), a servo holding over its rated torque (in a pose
    of the sweep or along a motion), a servo's load peaking over half its stall torque along a motion, a joint a
    full-speed swing leaves off the slow pose, the centre of mass off the footprint, at rest or moving. Listed exceptions
    (KNOWN_PAIRS, KNOWN_FULL_SPEED, KNOWN_TRANSMISSION, KNOWN_PEAKS) carry their reasons."""
    m, doc, out = report.get("mujoco", {}), report["doc"], []
    for p in m.get("pairs", []):
        if deeper(p) > mujoco_report.PENETRATION_MM and not known(p["pair"]):
            out.append(
                f"mujoco {' / '.join(p['pair'])}: {p['min_mm']} mm at {p['at']}, {deeper(p)} deeper than at rest"
            )
    for loop, r in m.get("residuals", {}).items():
        if r["max_mm"] > mujoco_report.LOOP_MM:
            out.append(f"mujoco four-bar {loop}: open {r['max_mm']} mm at {r['at']} > {mujoco_report.LOOP_MM}")
    for loop, r in m.get("loops", {}).items():
        if r["margin_mm_rad"] < mujoco_report.MARGIN_MM_RAD:
            play = math.degrees(fits.CLEARANCE[0] / r["margin_mm_rad"])
            out.append(
                f"mujoco four-bar {loop}: singularity margin {r['margin_mm_rad']} mm/rad at {r['margin_at']} <"
                f" {mujoco_report.MARGIN_MM_RAD:.2f} (a {fits.CLEARANCE[0]} mm pin fit turns its free pivots"
                f" {play:.1f} deg > {mujoco_report.PLAY_DEG})"
            )
        if r["transmission_deg"] < mujoco_report.TRANSMISSION_DEG and loop not in KNOWN_TRANSMISSION:
            out.append(
                f"mujoco four-bar {loop}: transmission angle {r['transmission_deg']} deg at {r['transmission_at']}"
                f" < {mujoco_report.TRANSMISSION_DEG}"
            )
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
    for horn, a in m.get("motions", {}).get("servos", {}).items():
        if a["hold_kgf_cm"] > a["rated_kgf_cm"]:
            out.append(
                f"mujoco {horn}: holds {a['hold_kgf_cm']} kgf.cm at {a['hold_at']} > its rated {a['rated_kgf_cm']}"
            )
        if a["peak_kgf_cm"] > a["stall_kgf_cm"] / 2 and (doc, horn) not in KNOWN_PEAKS:
            out.append(
                f"mujoco {horn}: peaks at {a['peak_kgf_cm']} kgf.cm at {a['peak_at']} > half its stall {a['stall_kgf_cm']}"
            )
    tip = m.get("tip_over")
    if tip and tip["margin_mm"] <= 0:
        out.append(f"mujoco tip-over: centre of mass {-tip['margin_mm']} mm outside the base footprint at {tip['at']}")
    if tip and tip["moving"]["margin_mm"] <= 0:
        moving = tip["moving"]
        out.append(
            f"mujoco tip-over: the moving centre of mass bears {-moving['margin_mm']} mm outside the base footprint at"
            f" {moving['at']}"
        )
    return out


def built(doc):
    path = os.path.join(report.OUT, f"{doc}-sim.json")
    if not os.path.isfile(path):
        pytest.skip(f"{doc} not simulated here: just sim")
    return json.load(open(path))


def test_reports_are_build_outputs_git_ignores():
    path = report.path(g.SIMULATED[0])
    assert subprocess.run(["git", "check-ignore", "-q", path], cwd=stages.REPO).returncode == 0


@pytest.mark.parametrize("doc", sorted(g.SIMULATED))
def test_built_report_is_clean(doc):
    """The leading head variant (Cansin's pick to be, #51) passes every gate. Another head variant may
    open a four-bar the ranking carries (#705: ranked last, its Viewer button saying so), and only that: whatever else
    it fails, or a loop the ranking misses, fails here."""
    r = built(doc)
    if doc in report.RANKED:
        ranked = base.rank({d: built(d) for d in report.RANKED})
        if doc != ranked["order"][0]:
            for loop in ranked["variants"][doc]["gates"]["loops"]:
                del r["mujoco"]["residuals"][loop]
    assert problems(r) == []


@pytest.mark.parametrize("doc", sorted(report.RANKED))
def test_the_next_mechs_footprint_is_reported_and_is_its_torsos(doc):
    """#685: the shirt is the base, so the footprint the tip-over gate reads is the Torso's foot, x by y mm."""
    (x0, x1), (y0, y1), _ = base.TORSO
    assert built(doc)["mujoco"]["tip_over"]["footprint_mm"] == [x1 - x0, y1 - y0]


FIXTURE_PROBLEMS = {
    "passing": [],
    "failing": [
        "electrical core1: 3.2 A with every servo at stall >= the 3.0 A cap",
        "electrical tilt servo: 4.7 V at stall on a nominal pack < the 4.8 V minimum",
        "electrical core2: 2.4 V on a 5.8 V pack < the 2.51 V brownout",
        "mujoco R eye horn:1 / R servo bracket:1: -0.12 mm at {'R eye horn': -22}, 0.1 deeper than at rest",
        "mujoco pan turntable:1 / tilt bar:1: -0.08 mm at {'tilt horn': -60}, 0.08 deeper than at rest",
        "mujoco four-bar tilt pivot: open 0.07 mm at {'tilt horn': 60} > 0.05",
        "mujoco four-bar pan pivot: singularity margin 1.2 mm/rad at {'pan horn': -40} < 2.86 (a 0.1 mm pin fit turns"
        " its free pivots 4.8 deg > 2.0)",
        "mujoco four-bar tilt pivot: transmission angle 35.0 deg at {'tilt horn': -60} < 40.0",
        "mujoco tilt horn: holds 0.45 kgf.cm at {'tilt horn': -60} > its rated 0.4 (stall 1.0)",
        "mujoco pan horn at full speed (428.6 deg/s) to -40: its joints settle 29.1 deg off the slow pose",
        "mujoco tilt horn: holds 0.42 kgf.cm at {'motion': 'hero', 'ms': 400} > its rated 0.4",
        "mujoco tilt horn: peaks at 0.55 kgf.cm at {'motion': 'hero', 'ms': 410} > half its stall 1.0",
        "mujoco tip-over: centre of mass 2.0 mm outside the base footprint at {'pan horn': 70, 'tilt horn': 60}",
        "mujoco tip-over: the moving centre of mass bears 1.5 mm outside the base footprint at"
        " {'motion': 'hero', 'ms': 410}",
        "gimbal gaze: 2.1 deg off with play (1.4) and pupil seating (0.7) > 2.0",
        "gimbal caps: 0.8 mm apart < 1.0",
        "gimbal lids: 0.3 mm clear of the parts inside them, 0.4 mm apart < 0.5",
        "gimbal lid servo: -95.0 deg past its 90.0",
        "gimbal block: 150.0 x 106.2 x 97.5 mm (W x D x H) past the compact head's 124.6 x 120.0 x 150.0",
        "gimbal sweep: next L lid bar:1 / next L lid shank 0.2 mm apart at {'lid_deg': -65.0, 'pitch_deg': -15.0} < 0.5",
        "gimbal sweep: next L lid bar:1 / next gimbal frame:1 overlap at {'lid_deg': 15.0, 'pitch_deg': -15.0}",
        "neck pan: the bar meets its lever at 35.0 deg < 40.0",
        "neck pan servo: 95.0 deg past its 90.0",
        "neck tilt: holds the head with 0.45 kgf.cm > the rated 0.4",
        "neck tilt span: bends to 12.0 mm < 14.0",
        "variant head: 120.0 x 121.5 x 149.0 mm (W x D x H) past the compact head's 124.6 x 120.0 x 150.0",
        "variant eyes: 0.62 of the head's height up > 0.5",
    ],
}


@pytest.mark.parametrize("name", sorted(FIXTURE_PROBLEMS))
def test_fixture_reports(name):
    report = json.load(open(os.path.join(HERE, "test_fixtures", f"{name}-report.json")))
    assert problems(report) == FIXTURE_PROBLEMS[name]


def test_known_mujoco_exceptions_are_still_there():
    """When the model changes so a KNOWN_PAIRS entry no longer goes deeper than at rest at all, or a KNOWN_FULL_SPEED
    swing lands, or a KNOWN_PEAKS servo peaks under the mark, drop it. (Any depth, not the threshold: CI's Linux pieces may read a little differently.)"""
    going, swings, low, peaks = set(), set(), set(), set()
    for doc in g.SIMULATED:
        m = built(doc)["mujoco"]
        going |= {frozenset(p["pair"]) for p in m["pairs"] if deeper(p) > 0}
        swings |= {(doc, h, f["at"]) for h, f in m["full_speed"].items() if f["off_deg"] > mujoco_report.TURN_DEG}
        low |= {loop for loop, r in m["loops"].items() if r["transmission_deg"] < mujoco_report.TRANSMISSION_DEG}
        servos = m["motions"]["servos"].items()
        peaks |= {(doc, h) for h, a in servos if a["peak_kgf_cm"] > a["stall_kgf_cm"] / 2}
    assert set(KNOWN_PAIRS) <= going
    assert swings == set(KNOWN_FULL_SPEED)
    assert low == set(KNOWN_TRANSMISSION)
    assert peaks == set(KNOWN_PEAKS)
