"""Seam: model/engine/cables.py, the cable corridors: a tube's clearance from a part, the union of swept tubes the face
work clears, and every lead's corridor over the sampled poses of a document."""

import os

import numpy as np
import pytest
import trimesh

from model import geometry as g
from model.engine import cables, meshes, run, stages


def cube(at, size=10.0):
    return meshes.Placed(trimesh.creation.box((size, size, size)), stages.translate(at))


def line(a, b):
    return cables.sample([a, b])


def test_clearance_is_the_tube_surface_gap_and_negative_once_the_tube_is_inside_the_part():
    box = cube((0, 0, 0))  # faces at +-5
    beside = line((-20, 8.0, 0), (20, 8.0, 0))  # centreline 3 mm off the +y face
    assert cables.clearance(beside, box, 2.0) == pytest.approx(1.0, abs=0.05)
    grazing = line((-20, 6.0, 0), (20, 6.0, 0))  # 1 mm off: the 2 mm tube is 1 mm into the box
    assert cables.clearance(grazing, box, 2.0) == pytest.approx(-1.0, abs=0.05)
    through = line((-20, 0, 0), (20, 0, 0))  # through the middle: 5 mm deep plus the radius
    assert cables.clearance(through, box, 2.0) == pytest.approx(-7.0, abs=0.05)
    assert cables.clearance(line((-20, 30, 0), (20, 30, 0)), box, 2.0) == meshes.NEAR_MM  # far: not measured


def test_sample_spaces_points_along_the_polyline_and_keeps_its_corners():
    pts = cables.sample([(0, 0, 0), (10, 0, 0), (10, 5, 0)])
    assert cables.length(pts) == pytest.approx(15.0)
    assert len(pts) >= 15 and any(np.allclose(p, (10, 0, 0)) for p in pts)


def test_union_of_swept_tubes_is_one_closed_volume_that_holds_every_tube():
    a, b = line((0, 0, 0), (30, 0, 0)), line((15, -15, 0), (15, 15, 0))  # two crossing tubes
    union = cables.union([a, b], 2.0)
    assert union.is_watertight
    placed = meshes.Placed(union, np.eye(4))
    assert meshes.inside(np.array([(0, 0, 0), (30, 0, 1.8), (15, 15, 0), (15, 0, -1.8)]), placed).all()
    assert not meshes.inside(np.array([(15, 6, 4.0), (40, 0, 0)]), placed).any()
    assert 2 * np.pi * 2.0**2 * 30 * 0.9 < union.volume < 2 * np.pi * 3.5**2 * 30  # two r=2 tubes, voxel-coarse


HAVE_REFERENCES = os.path.isdir(stages.MODELS["eyes"]) and os.path.isfile(stages.step("horn"))
_swept = {}


def swept(doc, routes=None):
    """corridors() of a document at a 30 degree step (cached for the shipped routes)."""
    if routes is not None or doc not in _swept:
        stage = stages.STAGES[doc]
        placed = run.neutral(stage, meshes.load(stage))
        result = cables.corridors(stage, placed, 30, routes)
        if routes is not None:
            return result
        _swept[doc] = result
    return _swept[doc]


@pytest.mark.skipif(not HAVE_REFERENCES, reason="local references only")
def test_every_lead_of_the_full_mech_has_a_corridor_longer_than_its_straight_reach():
    report, _ = swept("noggin-stage3")
    assert len(report) == 7 + 2 + 2
    # static: pack 1's plug (-32.5, 123.5, 14.65) to switch board 1's hole on its standoff (6, 68.5, 13), 67.2 straight
    pack = report["pack 1 -> switch 1"]
    assert 67.2 < pack["min_mm"] == pack["max_mm"] < pack["limit_mm"] == 80
    lid = report["l_lid servo -> Core 1 PWM1"]
    assert lid["limit_mm"] == 230 and lid["min_mm"] < lid["max_mm"]  # the head moves the clipped waypoints
    assert set(lid["at"]) <= {"pan horn (inferred)", "tilt horn (inferred)"}
    assert all("(inferred)" in w for c in report.values() for w in c["waypoints"])


@pytest.mark.skipif(not HAVE_REFERENCES, reason="local references only")
def test_the_desk_build_routes_the_eye_leads_straight_to_the_base_and_skips_core_2():
    report, _ = swept("noggin-stage1")
    assert sorted(report) == sorted(
        [f"{s} servo -> Core 1 PWM{n}" for n, s in g.CHANNELS["core1"].items()]
        + ["pack 1 -> switch 1", "switch 1 -> shield 1"]
    )
    assert not any("tilt arm" in w for w in report["l_lid servo -> Core 1 PWM1"]["waypoints"])


@pytest.mark.skipif(not HAVE_REFERENCES, reason="local references only")
def test_a_corridor_through_a_moving_part_fails_unless_it_is_clipped_to_that_part():
    lead = "l_eye servo -> Core 1 PWM2"

    def through_the_eyeball(part):  # a waypoint at the L eye centre: the tube crosses the eyeball's shell
        return {**cables.ROUTES, lead: [[(part, (0.0, 0.0, 0.0), "at the eye centre (inferred)")]]}

    held = swept("noggin-eyes", through_the_eyeball("main bracket v2:1"))[0][lead]
    assert held["clearance_mm"] < 0
    clipped = swept("noggin-eyes", through_the_eyeball("L eyeball:1"))[0][lead]
    assert clipped["clearance_part"] != "L eyeball:1"  # the part it is clipped to is exempt


@pytest.mark.skipif(not HAVE_REFERENCES, reason="local references only")
def test_the_swept_centrelines_cover_every_lead_at_every_pose():
    report, centrelines = swept("noggin-stage1")
    assert len(centrelines) % len(report) == 0 and len(centrelines) > len(report)


def test_union_stays_closed_where_swept_voxels_meet_only_along_an_edge():
    skew = line((0, 0, 0), (37, 11, 5))  # at r=0.6 its voxels touch diagonally: a non-manifold edge unless filled
    assert cables.union([skew], 0.6).is_watertight
