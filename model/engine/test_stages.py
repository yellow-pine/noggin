"""Seam: model/engine/stages.py, the document tables (sub-assemblies, sweep documents, Stage configurations: parts, neutral placements, chains) and pose(): every part's rigid
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


def test_every_horn_link_and_the_bracket_stem_has_a_placement_tolerance():
    placed = {name: tol for name, _, _, tol in stages.STAGES["noggin-stage3"].placements}
    for part in stages.STAGES["noggin-stage3"].parts:
        if "horn" in part or (" bar:1" in part and "eyeball" not in part) or "crank" in part or "servo:1" in part:
            assert part in placed, part
    assert placed["eye bracket:1"] == stages.TOL_MM  # the stem in the tilt arm window, its depth measured (#133)
    # its holes on the pins: the lid horn's neutral fits both lid loops within 0.14 (geometry.LID_HORN_ARM)
    assert placed["L lid bar:1"] == stages.TOL_MM


def test_sub_assemblies_place_the_geometry_parts_tables():
    eyes, stack, mouth = (stages.SUBS[f"noggin-{n}"]().parts for n in ("eyes", "stack", "mouth"))
    for parts, table in ((eyes, g.EYES_PARTS), (stack, g.STACK_PARTS), (mouth, g.MOUTH_PARTS)):
        assert {row[0] + ":1" for row in table} <= set(parts)
    assert world(eyes["L pupil:1"].matrix, (59, 0, 0)) == pytest.approx((0, 0, 0))  # the pupil STL sits on the R eye


def test_every_servo_has_a_lead_port_at_its_cable_exit():
    stage = stages.STAGES["noggin-stage3"]
    leads = {n: p for n, p in stage.ports.items() if n.endswith(" servo lead")}
    assert set(leads) == {f"{s} servo lead" for s in ("L lid", "L eye", "R lid", "R eye", "tilt", "pan", "jaw")}
    for name, (part, local) in leads.items():
        assert part == name[: -len(" lead")] + ":1" and local == g.SERVO_STEP["lead"]
    assert stage.ports["Core 2 servo PWM3"] == ("receiver shield 2:1", g.RECEIVER_STEP["headers"]["PWM3"])
    assert stage.ports["battery 1 lead"] == ("battery 1:1", g.BATTERY_STEP["plug"])


def test_a_misplaced_part_is_reported_with_its_tolerance():
    stage = stages.STAGES["noggin-stage1"]
    m = stage.parts["eye bracket:1"].matrix
    shifted = stage._replace(
        parts={
            **stage.parts,
            "eye bracket:1": stage.parts["eye bracket:1"]._replace(matrix=stages.translate((0, 0, 5)) @ m),
        }
    )
    (v,) = [v for v in stages.placements(shifted) if v["placement"] == "eye bracket:1"]
    assert v["mm"] == 5.0 and v["tol"] == stages.TOL_MM


def test_stage_documents_place_the_sub_assemblies_once_at_their_frames():
    s1, s3 = stages.STAGES["noggin-stage1"], stages.STAGES["noggin-stage3"]
    assert "base plate:1" in s1.parts and "L eyeball:1" in s1.parts and "pan turntable:1" not in s1.parts
    assert world(s1.parts["L eyeball:1"].matrix, g.EYE_L) == pytest.approx(
        g.EYES_ON_BASE[0]
    )  # the eyes frame origin sits where STAGES says
    assert world(s3.parts["L eyeball:1"].matrix, g.EYE_L) == pytest.approx(g.eyes_to_pt(g.EYE_L))
    assert set(s3.horns) == {
        "L lid horn",
        "L eye horn",
        "R lid horn",
        "R eye horn",
        "tilt horn",
        "pan horn",
        "jaw horn",
    }
    moved = stages.pose(s3, "L lid horn", 20)  # the eyes chain still closes in the PT frame
    assert moved.joints == pytest.approx({"L upper lid pivot": 21.02, "L lower lid pivot": -19.81}, abs=0.01)
    for name in ("L servo bracket:1", "base plate:1", "tilt arm:1"):
        assert np.allclose(moved.parts[name], s3.parts[name].matrix)


def test_eyes_servo_tab_holes_sit_on_the_lug_holes():
    stage = stages.STAGES["noggin-eyes"]
    m = stage.parts["L lid servo:1"].matrix
    actual = sorted(world(m, p) for p in g.SERVO_STEP["tab_holes"])
    for a, e in zip(actual, sorted(g.SERVOS["l_lid"]["tab_holes"])):
        assert a == pytest.approx(e, abs=0.11)  # near hole exact; the far one 0.1 off (lug pitch 27.7, servo 27.8)


def test_lid_horn_pose_moves_the_crank_bars_and_lids_as_one_closed_loop():
    stage = stages.STAGES["noggin-eyes"]
    neutral = stages.pose(stage, "L lid horn", 0)
    moved = stages.pose(stage, "L lid horn", 20)
    assert set(neutral.parts) == set(moved.parts) == set(stage.parts)
    for name in ("L servo bracket:1", "L eyeball:1", "eye bracket:1", "L lid servo:1"):
        assert np.allclose(moved.parts[name], neutral.parts[name])  # not in the chain
    lid_pin = (-25.5, 12.0, 0.0)  # the upper lid pin where the crank joins it, eyes frame
    bar, lid = moved.parts["L lid crank:1"], moved.parts["L upper lid:1"]
    bar0, lid0 = neutral.parts["L lid crank:1"], neutral.parts["L upper lid:1"]
    local_bar, local_lid = np.linalg.inv(bar0) @ [*lid_pin, 1], np.linalg.inv(lid0) @ [*lid_pin, 1]
    assert np.allclose(bar @ local_bar, lid @ local_lid, atol=1e-6)  # the loop closes
    assert np.allclose(bar @ local_bar, [*lid_pin, 1]) is False  # and it moved
    _, y, z = g.PIVOTS["l_lid_horn"]["point"]
    horn_pin = (-28.5, y + g.HORN_STEP["pin"] * g.LID_HORN_ARM[1], z + g.HORN_STEP["pin"] * g.LID_HORN_ARM[2])
    assert np.allclose(
        moved.parts["L lid horn:1"] @ (np.linalg.inv(neutral.parts["L lid horn:1"]) @ [*horn_pin, 1]),
        bar @ (np.linalg.inv(bar0) @ [*horn_pin, 1]),
        atol=1e-6,
    )
    assert moved.joints == pytest.approx({"L upper lid pivot": 21.02, "L lower lid pivot": -19.81}, abs=0.01)


def test_pan_pose_carries_the_whole_tilt_mechanism_round_the_pan_axis():
    stage = stages.STAGES["noggin-pan-tilt"]
    moved = stages.pose(stage, "pan horn", 40)
    assert moved.joints == pytest.approx({"pan pivot": -17.68, "tilt pivot": 0.0}, abs=0.01)
    r = moved.parts["pan turntable:1"]
    for name in ("upright:1", "tilt servo:1", "tilt arm:1", "tilt horn:1", "tilt bar:1"):
        assert np.allclose(
            moved.parts[name] @ np.linalg.inv(stage.parts[name].matrix),
            r @ np.linalg.inv(stage.parts["pan turntable:1"].matrix),
        )
    assert np.allclose(moved.parts["base plate:1"], stage.parts["base plate:1"].matrix)


def test_recorded_curves_come_out_of_pose(doc="noggin-pan-tilt"):
    report = json.load(open(os.path.join(REPORTS, f"{doc}-report.json")))
    stage = stages.STAGES[doc]
    for horn, curves in report["curves"].items():
        for joint, pts in curves.items():
            for deg, rec in pts:
                if horn.startswith("pan") and deg == -50:
                    continue  # recorded 0.0: the joint did not solve there (the loop cannot close there)
                assert stages.pose(stage, horn, deg).joints[joint] == pytest.approx(rec, abs=1.0), (horn, joint, deg)


def test_stage2_eyes_ride_the_tilt_arm_and_the_pan():
    s2 = stages.STAGES["noggin-stage2"]
    for horn, deg in (("tilt horn", 40), ("pan horn", 30)):
        moved = stages.pose(s2, horn, deg)
        carrier = moved.parts["tilt arm:1"] @ np.linalg.inv(s2.parts["tilt arm:1"].matrix)
        for name in ("L eyeball:1", "eye bracket:1", "L lid servo:1"):
            assert np.allclose(moved.parts[name] @ np.linalg.inv(s2.parts[name].matrix), carrier), (horn, name)
        assert np.allclose(moved.parts["base plate:1"], s2.parts["base plate:1"].matrix)
    s1 = stages.STAGES["noggin-stage1"]  # on the base: nothing carries the eyes
    assert "tilt horn" not in s1.horns


def test_horn_limits_follow_geometry():
    assert stages.STAGES["noggin-eyes"].horns["L lid horn"].limits == (-49, 39)
    assert stages.STAGES["noggin-pan-tilt"].horns["pan horn"].limits == (-40, 70)
    assert stages.STAGES["noggin-pan-tilt"].horns["tilt horn"].limits == (-60, 60)
    assert stages.STAGES["noggin-mouth"].horns["jaw horn"].limits == (-75, 0)


@pytest.mark.parametrize("s", "LR")
def test_lid_linkage_topology_follows_the_build(s):
    """#48, build photos eyes-lid-linkage*.jpg, guide p.21-23: the cranked bar joins the top (inside) lid by its stepped
    end and sits outermost on the horn pin; the straight bar joins the bottom (outside) lid between the horn and the crank."""
    stage = stages.STAGES["noggin-eyes"]
    loops = {loop.coupler: loop.rockers for loop in stage.horns[f"{s} lid horn"].loops}
    crank, bar = f"{s} lid crank:1", f"{s} lid bar:1"
    assert loops == {crank: [f"{s} upper lid:1"], bar: [f"{s} lower lid:1"]}
    out = -1 if s == "L" else 1  # outboard along X
    x = (lambda v: v) if s == "L" else (lambda v: 59.0 - v)
    m = stage.parts[crank].matrix
    stepped, plain = world(m, (-20.5, 0, 4.5)), world(m, (20.5, 0, 1.5))  # the crank STL's raised end and plain end
    # the link is placed by its horn hole and aligned toward the lid pin: the holes' 41 mm pitch leaves the far hole
    # within 0.2 mm of the pin (the joints meet at the pins; geometry.LID_HORN_ARM)
    assert plain == pytest.approx(
        (x(-29.7), -0.485, 39.202), abs=1e-3
    )  # horn pin, outermost, 1.2 out on the screw (#170)
    assert stepped[0] == pytest.approx(x(-26.7))  # 3 thick, 1.2 off the upper lid's ear face (x -24)
    assert math.dist(stepped[1:], (12.0, 0.0)) < 0.2  # at the inside (top) lid's pin
    straight_horn_end = world(stage.parts[bar].matrix, (20.5, 0, 1.5))
    assert straight_horn_end == pytest.approx((x(-25.5), -0.485, 39.202), abs=1e-3)
    horn_x = world(stage.parts[f"{s} lid horn:1"].matrix, g.HORN_STEP["hub"])[0]
    assert out * horn_x < out * straight_horn_end[0] < out * plain[0]  # horn, straight bar, crank (under the nut)


@pytest.mark.parametrize("horn,key", [("pan horn", "rotate"), ("tilt horn", "tilt")])
def test_every_neck_limit_end_poses(horn, key):
    """#133: the pan and tilt four-bars close over the whole of geometry.LIMITS, both ends included."""
    s2 = stages.STAGES["noggin-stage2"]
    lo, hi = g.HORN_LIMITS[key]
    for deg in range(lo - 90, hi - 90 + 1):
        stages.pose(s2, horn, deg)


# The designer's pan-tilt GIF (02-pan-tilt picture-01.gif, a camera fit over all 72 frames, docs/research/2026-10-31-neck.md):
# the head's largest swing either side of rest, +-3 deg. The stick is not known to reach full throw, so these are what the
# mechanism at least does. The mouth GIF (03-mouth picture-01.gif) pans 46 +-6 deg end to end, the fuller throw.
GIF_SIDES = {"pan horn": (12, 19), "tilt horn": (10, 19)}
GIF_MEASURE_DEG = 3
MOUTH_GIF_PAN = (46, 6)


@pytest.mark.parametrize("horn,key", [("pan horn", "rotate"), ("tilt horn", "tilt")])
def test_the_head_swings_at_the_neck_limits_as_far_as_the_designers_gif_shows(horn, key):
    s2 = stages.STAGES["noggin-stage2"]
    lo, hi = g.HORN_LIMITS[key]
    joint = horn.replace("horn", "pivot")
    ends = [stages.pose(s2, horn, d - 90).joints[joint] for d in (lo, hi)]
    assert ends[0] * ends[1] < 0  # one limit each side of rest
    # which servo sense turns the head which way is not in the GIF: compare the sides by size
    for model, gif in zip(sorted(abs(e) for e in ends), GIF_SIDES[horn]):
        assert model >= gif - GIF_MEASURE_DEG, (horn, ends)
    if horn == "pan horn":
        assert abs(sum(abs(e) for e in ends) - MOUTH_GIF_PAN[0]) <= MOUTH_GIF_PAN[1], ends


@pytest.mark.parametrize("doc", ["noggin-stage2", "noggin-stage3"])
def test_neutral_head_sits_on_the_neck_as_the_guide_builds_it(doc):
    """Pan-tilt guide p.23 and p.26, GIF frame 5; the meshes: the eye bracket's stem below its rail is 5.0 long, the tilt
    arm's window 5.0 deep, so the rail lies on the arm top (z 40.9, the arm 5 mm up on the raised upright) and the stem
    bottom is flush with the arm's underside (z 35.9). Eyes frame: L eye centre at the origin, -Z front."""
    m = stages.STAGES[doc].parts["eye bracket:1"].matrix
    assert world(m, (29.5, -45.6, 15.5)) == pytest.approx((0, -13, 35.9))  # stem bottom in the window, flush
    assert world(m, (29.5, -40.6, 15.5)) == pytest.approx((0, -13, 40.9))  # rail on the tilt arm top
    plate_top = 3.0
    left, right = world(m, g.EYE_L), world(m, g.EYE_R)
    assert left[2] - plate_top == pytest.approx(78.5) and right[2] - plate_top == pytest.approx(78.5)
    # facing -Y, away from the boards and the pack: from the front the Mech's L eye is on the viewer's right (+X), the pan
    # servo behind the pan turntable on the viewer's left, the tilt servo on the right (GIF frame 5)
    front = world(m, (0, 0, -24))
    assert front[1] < left[1] < 0 and left[0] > 0 > right[0]
    assert g.PIVOTS["pan_horn"]["point"][0] < 0 < g.PIVOTS["tilt_horn"]["point"][0]
