"""The gate (ADR 0006): the engine reproduces the recorded sweeps in model/reports. Per recorded document:
transmission curves within 1 degree, the minimum distances within 0.3 mm at the recorded poses, every part inside its
recorded box.
Known disagreements are listed in KNOWN with their reason (never loosened silently). Skipped without the local
references (docs/references, make model-step-meshes)."""

import glob
import json
import os

import pytest

from model.engine import meshes, run, stages

HERE = os.path.dirname(os.path.dirname(__file__))
RECORDED = sorted(glob.glob(os.path.join(HERE, "reports", "*-report.json")))
HAVE_REFERENCES = stages.HAVE_REFERENCES
CURVE_DEG, DISTANCE_MM = 1.0, 0.3
# (doc, horn, deg): why the engine cannot express what was recorded there.
KNOWN = {
    (
        "noggin-pan-tilt",
        "pan horn",
        -50,
    ): "the pan four-bar cannot close at -50 (crank pin 42.6 mm from the pan axis, bar 15 + lever 26.1 = 41.1): the recorded joint did not solve and recorded the pan at 0.0"
}

# Parts #62 and #67 moved (servo shafts, horn seat and orientation, bar planes from the STEPs, STLs and guide pictures:
# docs/research/2026-10-31-shafts.md) after the recorded builds: their recorded boxes predate the move. Their
# curves and distances still meet the gate. Drop a name once its box is re-recorded.
MOVED = {
    "noggin-eyes": {f"{s} {k} {p}:1" for s in "LR" for k in ("lid", "eye") for p in ("servo", "horn")},
    "noggin-mouth": {"jaw servo:1", "jaw horn:1", "connector bar:1"},
    "noggin-pan-tilt": {f"{k} {p}:1" for k in ("tilt", "pan") for p in ("servo", "horn", "bar")}
    | {"servo mount plain:1", "servo mount cutout:1"}  # swapped by the mating check (#67, geometry.MOUNT_SWAP_Y)
    | {"receiver shield 1:1", "receiver shield 2:1"},  # on the STL's standoff tops, z 16 (#81)
}
# Parts a recorded box still names that the model no longer places (#81: one pack and switch board, the Cores
# under the shields; the switch board 1 rename from #79) or records as one occurrence.
GONE = {
    "noggin-pan-tilt": {
        "switch board 1 (inferred):1",
        "switch board 2 (inferred):1",
        "battery 2 (inferred):1",
        "Core 1 (flipped onto the shield top, per photo):1",
        "Core 2 (flipped onto the shield top, per photo):1",
    },
    "noggin-mouth": {"noggin-eyes:1"},  # the recorded context copy of the eyes, assembled separately by the engine
}

_reports, _scenes = {}, {}


def engine(doc):
    if doc not in _reports:
        _reports[doc] = run.report(doc)
    return _reports[doc]


def distance_at(doc, horn, deg, pair):
    """The engine's distance for one pair at one pose of one horn."""
    if doc not in _scenes:
        stage = stages.STAGES[doc]
        _scenes[doc] = stage, meshes.load(stage)
    stage, loaded = _scenes[doc]
    pose = stages.pose(stage, horn, deg)
    a, b = (meshes.Placed(loaded[n], pose.parts[n]) for n in pair)
    return meshes.distance(a, b)


def docs():
    return [os.path.basename(p)[: -len("-report.json")] for p in RECORDED]


pytestmark = pytest.mark.skipif(
    not HAVE_REFERENCES, reason="local references only (docs/references, model/build/steps)"
)


@pytest.mark.parametrize("doc", docs())
def test_curves_within_a_degree(doc):
    recorded = json.load(open(os.path.join(HERE, "reports", f"{doc}-report.json")))
    mine = engine(doc)["curves"]
    stage = stages.STAGES[doc]
    off = []
    for horn, curves in recorded["curves"].items():
        for joint, pts in curves.items():
            got = dict(mine[horn][joint])
            for deg, rec in pts:
                if (doc, horn, deg) in KNOWN:
                    continue
                if deg not in got:  # recorded past a limit narrowed since (geometry.HORN_LIMITS [I]): pose it directly
                    got[deg] = stages.pose(stage, horn, deg).joints[joint]
                if abs(got[deg] - rec) > CURVE_DEG:
                    off.append((horn, joint, deg, rec, got[deg]))
    assert off == []


@pytest.mark.parametrize("doc", docs())
def test_minimum_distances_within_point_three_mm_at_the_recorded_poses(doc):
    recorded = json.load(open(os.path.join(HERE, "reports", f"{doc}-report.json")))
    mine = engine(doc)
    off = []
    for horn, h in recorded["horns"].items():
        if (doc, horn, h["at_deg"]) in KNOWN:
            continue
        got = distance_at(doc, horn, h["at_deg"], h["pair"])
        if abs(got - h["min_mm"]) > DISTANCE_MM:
            off.append((horn, h["at_deg"], h["pair"], "recorded", h["min_mm"], "engine", round(got, 3)))
        m = mine["horns"][
            horn
        ]  # the engine also measures chain-vs-chain pairs the recorded sweep skipped: never higher, may be lower
        if m["min_mm"] > h["min_mm"] + DISTANCE_MM:
            off.append((horn, "sweep minimum", "recorded", h["min_mm"], "engine", m["min_mm"], m["at_deg"], m["pair"]))
    assert off == []


@pytest.mark.parametrize("doc", docs())
def test_every_part_sits_inside_its_recorded_box(doc):
    """The recorded boxes also hold each part's joint-origin sketches, so they are a bound: every part both documents place
    must lie inside its recorded box within its placement tolerance."""
    recorded = json.load(open(os.path.join(HERE, "reports", f"{doc}-report.json")))["bboxes"]
    mine = engine(doc)["bboxes"]
    off = []
    for name in sorted(set(recorded) & set(mine)):
        if name not in MOVED.get(doc, ()) and _out_of_box(recorded[name], mine[name], name):
            off.append((name, round(_out_of_box(recorded[name], mine[name], name), 2)))
    assert off == [] and set(recorded) - set(mine) <= GONE.get(doc, set())


def _out_of_box(rec, got, name):
    """mm by which a part's box leaves its recorded box past its placement tolerance, else 0."""
    (rlo, rhi), (lo, hi) = rec, got
    out = max([r - e for r, e in zip(rlo, lo)] + [e - r for r, e in zip(rhi, hi)])
    return out if out > (stages.TOL_INFERRED_MM if "(inferred)" in name else stages.TOL_MM) else 0


@pytest.mark.parametrize("doc", sorted(MOVED))
def test_moved_parts_are_still_outside_their_recorded_box(doc):
    """When a moved part's recorded box is re-recorded, drop it from MOVED."""
    recorded = json.load(open(os.path.join(HERE, "reports", f"{doc}-report.json")))["bboxes"]
    mine = engine(doc)["bboxes"]
    assert all(_out_of_box(recorded[n], mine[n], n) for n in MOVED[doc])


def test_known_disagreements_are_still_there():
    """When the model changes so a KNOWN entry no longer applies, drop it."""
    for (doc, horn, deg), why in KNOWN.items():
        if doc in docs():
            assert any(u["deg"] == deg for u in engine(doc)["unreachable"].get(horn, [])), why
