"""Seam: model/engine/stages.py, the Stage tables (parts, neutral placements, chains) and pose(): every part's rigid
transform per horn angle. No meshes are read here."""

import json
import math
import os

import numpy as np
import pytest

from model import geometry as g
from model.engine import stages

REPORTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")


def world(m, p):
    return tuple((m @ np.array([*p, 1.0]))[:3])


@pytest.mark.parametrize("doc", sorted(stages.DOCS))
def test_neutral_placements_land_the_servos_and_boards_where_geometry_says(doc):
    assert stages.placements(stages.STAGES[doc]) == []


def test_stage_documents_place_the_sub_assemblies_once_at_their_frames():
    s1, s3 = stages.STAGES["noggin-stage1"], stages.STAGES["noggin-stage3"]
    assert "PandT base:1" in s1.parts and "L eyeball:1" in s1.parts and "pan base:1" not in s1.parts
    assert world(s1.parts["L eyeball:1"].matrix, g.EYE_L) == pytest.approx(
        g.EYES_ON_BASE[0]
    )  # the eyes frame origin sits where STAGES says
    assert world(s3.parts["L eyeball:1"].matrix, g.EYE_L) == pytest.approx(g.eyes_to_pt(g.EYE_L))
    assert set(s3.horns) == {
        "L lid horn (inferred)",
        "L eye horn (inferred)",
        "R lid horn (inferred)",
        "R eye horn (inferred)",
        "tilt horn (inferred)",
        "pan horn (inferred)",
        "jaw horn (inferred)",
    }
    moved = stages.pose(s3, "L lid horn (inferred)", 20)  # the eyes chain still closes in the PT frame
    assert moved.joints == pytest.approx({"L inside lid pivot": 21.23, "L outside lid pivot": -19.38}, abs=0.01)
    for name in ("L servo bracket:1", "PandT base:1", "tilt arm:1"):
        assert np.allclose(moved.parts[name], s3.parts[name].matrix)


def test_eyes_servo_tab_holes_sit_on_the_measured_pair_within_the_inferred_shaft_offset():
    stage = stages.STAGES["noggin-eyes"]
    m = stage.parts["L lid servo:1"].matrix
    actual = sorted(world(m, p) for p in g.SERVO_STEP["tab_holes"])
    for a, e in zip(actual, sorted(g.SERVOS["l_lid"]["tab_holes"])):
        assert a == pytest.approx(e, abs=0.5)  # the shaft sits on the inferred pivot: the holes land 0.39 mm off


def test_lid_horn_pose_moves_the_crank_bars_and_lids_as_one_closed_loop():
    stage = stages.STAGES["noggin-eyes"]
    neutral = stages.pose(stage, "L lid horn (inferred)", 0)
    moved = stages.pose(stage, "L lid horn (inferred)", 20)
    assert set(neutral.parts) == set(moved.parts) == set(stage.parts)
    for name in ("L servo bracket:1", "L eyeball:1", "main bracket v2:1", "L lid servo:1"):
        assert np.allclose(moved.parts[name], neutral.parts[name])  # not in the chain
    lid_pin = (-25.5, 12.0, 0.0)  # the inside lid pin where the crank joins it, eyes frame
    bar, lid = moved.parts["L eyelid bar crank (inferred):1"], moved.parts["L inside lid:1"]
    bar0, lid0 = neutral.parts["L eyelid bar crank (inferred):1"], neutral.parts["L inside lid:1"]
    local_bar, local_lid = np.linalg.inv(bar0) @ [*lid_pin, 1], np.linalg.inv(lid0) @ [*lid_pin, 1]
    assert np.allclose(bar @ local_bar, lid @ local_lid, atol=1e-6)  # the loop closes
    assert np.allclose(bar @ local_bar, [*lid_pin, 1]) is False  # and it moved
    horn_pin = (-28.5, g.PIVOTS["l_lid_horn"]["point"][1] + g.HORN_STEP["pin"], 40.0)
    assert np.allclose(
        moved.parts["L lid horn (inferred):1"]
        @ (np.linalg.inv(neutral.parts["L lid horn (inferred):1"]) @ [*horn_pin, 1]),
        bar @ (np.linalg.inv(bar0) @ [*horn_pin, 1]),
        atol=1e-6,
    )
    assert moved.joints == pytest.approx({"L inside lid pivot": 21.23, "L outside lid pivot": -19.38}, abs=0.01)


def test_pan_pose_carries_the_whole_tilt_mechanism_round_the_pan_axis():
    stage = stages.STAGES["noggin-pan-tilt"]
    moved = stages.pose(stage, "pan horn (inferred)", 40)
    assert moved.joints == pytest.approx({"pan pivot": -17.69, "tilt pivot": 0.0}, abs=0.01)
    r = moved.parts["pan base:1"]
    for name in ("upright v2:1", "tilt servo:1", "tilt arm:1", "tilt horn (inferred):1", "tilt bar (inferred):1"):
        assert np.allclose(
            moved.parts[name] @ np.linalg.inv(stage.parts[name].matrix),
            r @ np.linalg.inv(stage.parts["pan base:1"].matrix),
        )
    assert np.allclose(moved.parts["PandT base:1"], stage.parts["PandT base:1"].matrix)


def test_recorded_curves_come_out_of_pose(doc="noggin-pan-tilt"):
    report = json.load(open(os.path.join(REPORTS, f"{doc}-report.json")))
    stage = stages.STAGES[doc]
    for horn, curves in report["curves"].items():
        for joint, pts in curves.items():
            for deg, rec in pts:
                if horn.startswith("pan") and deg == -50:
                    continue  # Fusion recorded 0.0: its joint did not solve there (the loop cannot close, see the gate)
                assert stages.pose(stage, horn, deg).joints[joint] == pytest.approx(rec, abs=1.0), (horn, joint, deg)


def test_stage2_eyes_ride_the_tilt_arm_and_the_pan():
    s2 = stages.STAGES["noggin-stage2"]
    for horn, deg in (("tilt horn (inferred)", 40), ("pan horn (inferred)", 30)):
        moved = stages.pose(s2, horn, deg)
        carrier = moved.parts["tilt arm:1"] @ np.linalg.inv(s2.parts["tilt arm:1"].matrix)
        for name in ("L eyeball:1", "main bracket v2:1", "L lid servo:1"):
            assert np.allclose(moved.parts[name] @ np.linalg.inv(s2.parts[name].matrix), carrier), (horn, name)
        assert np.allclose(moved.parts["PandT base:1"], s2.parts["PandT base:1"].matrix)
    s1 = stages.STAGES["noggin-stage1"]  # on the base: nothing carries the eyes
    assert "tilt horn (inferred)" not in s1.horns


def test_horn_limits_follow_geometry():
    assert stages.STAGES["noggin-eyes"].horns["L lid horn (inferred)"].limits == (-20, 30)
    assert stages.STAGES["noggin-pan-tilt"].horns["pan horn (inferred)"].limits == (-50, 70)
    assert stages.STAGES["noggin-pan-tilt"].horns["tilt horn (inferred)"].limits == (-60, 60)
    assert stages.STAGES["noggin-mouth"].horns["jaw horn (inferred)"].limits == (-40, 0)


@pytest.mark.parametrize("s", "LR")
def test_lid_linkage_topology_follows_the_build(s):
    """#48, build photos eyes-lid-linkage*.jpg, guide p.21-23: the cranked bar joins the top (inside) lid by its stepped
    end and sits outermost on the horn pin; the straight bar joins the bottom (outside) lid between the horn and the crank."""
    stage = stages.STAGES["noggin-eyes"]
    loops = {loop.coupler: loop.rockers for loop in stage.horns[f"{s} lid horn (inferred)"].loops}
    crank, bar = f"{s} eyelid bar crank (inferred):1", f"{s} eyelid bar (inferred):1"
    assert loops == {crank: [f"{s} inside lid:1"], bar: [f"{s} outside lid:1"]}
    out = -1 if s == "L" else 1  # outboard along X
    x = (lambda v: v) if s == "L" else (lambda v: 59.0 - v)
    m = stage.parts[crank].matrix
    stepped, plain = world(m, (-20.5, 0, 4.5)), world(m, (20.5, 0, 1.5))  # the crank STL's raised end and plain end
    # the link is placed by its horn hole and aligned toward the lid pin: the holes' 41 mm pitch leaves the far hole
    # within 1 mm of the pin (the joints meet at the pins, as Fusion's do)
    assert plain == pytest.approx((x(-28.5), -0.75, 40.0))  # horn pin, outermost
    assert stepped[0] == pytest.approx(x(-25.5))  # bar 3 thick on the inside lid's ear face (x -24)
    assert math.dist(stepped[1:], (12.0, 0.0)) < 1.0  # at the inside (top) lid's pin
    straight_horn_end = world(stage.parts[bar].matrix, (20.5, 0, 1.5))
    assert straight_horn_end == pytest.approx((x(-25.5), -0.75, 40.0))
    horn_x = world(stage.parts[f"{s} lid horn (inferred):1"].matrix, g.HORN_STEP["hub"])[0]
    assert out * horn_x < out * straight_horn_end[0] < out * plain[0]  # horn, straight bar, crank (under the nut)
