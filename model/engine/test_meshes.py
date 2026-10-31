"""Seam: model/engine/meshes.py, mesh loading per Stage and the pairwise distance / penetration judgement."""

import os

import pytest
import trimesh

from model.engine import meshes, stages

HAVE_REFERENCES = os.path.isdir(stages.MODELS["eyes"]) and os.path.isfile(stages.step("horn"))


def cube(at, size=10.0):
    return meshes.Placed(trimesh.creation.box((size, size, size)), stages.translate(at))


def test_gap_between_two_cubes_is_their_face_to_face_distance():
    a, b = cube((0, 0, 0)), cube((10.4, 3.0, 2.0))  # faces 0.4 mm apart, offset so no vertices face each other
    assert meshes.distance(a, b) == pytest.approx(0.4, abs=1e-6)
    assert meshes.bbox_gap(a, b) == pytest.approx(0.4, abs=1e-6)
    assert meshes.distance(a, cube((30, 0, 0))) == meshes.NEAR_MM  # beyond NEAR_MM a pair is not measured (check.py)


def test_touching_cubes_are_a_contact_and_overlapping_ones_a_penetration():
    a = cube((0, 0, 0))
    touching, overlapping = cube((10.0, 0, 0)), cube((9.0, 1.0, 1.0))
    assert meshes.distance(a, touching) == pytest.approx(0.0, abs=1e-9) and not meshes.penetrates(a, touching)
    assert meshes.distance(a, overlapping) == pytest.approx(0.0, abs=1e-9) and meshes.penetrates(a, overlapping)


@pytest.mark.skipif(
    not HAVE_REFERENCES, reason="designer STLs and STEP meshes are local only (docs/references, make model-step-meshes)"
)
def test_eyeball_bar_rides_the_bracket_rail_at_neutral():
    stage = stages.STAGES["noggin-eyes"]
    loaded = meshes.load(stage, ["L eyeball bar:1", "main bracket v2:1"])
    bar, bracket = (meshes.Placed(loaded[n], stage.parts[n].matrix) for n in ("L eyeball bar:1", "main bracket v2:1"))
    assert meshes.distance(bar, bracket) < 0.1 and not meshes.penetrates(bar, bracket)


@pytest.mark.skipif(not HAVE_REFERENCES, reason="local references only")
def test_loaded_meshes_are_subdivided_and_the_battery_lead_is_cut():
    stage = stages.STAGES["noggin-pan-tilt"]
    loaded = meshes.load(stage, ["PandT base:1", "battery 1:1"])
    assert loaded["PandT base:1"].edges_unique_length.max() <= meshes.MAX_EDGE_MM + 1e-6
    assert loaded["battery 1:1"].bounds[1][1] <= 56.0 + 1e-6


@pytest.mark.skipif(not HAVE_REFERENCES, reason="local references only")
def test_the_stack_clears_the_pan_base_at_the_tilt_end_and_the_boards_at_neutral():
    """Engine findings 2026-10-31 (#24): the tilt horn and bar swept into the pan base at the config's tilt end, and the
    tilt servo's straight lead stub sank into receiver shield 1 at neutral."""
    stage = stages.STAGES["noggin-pan-tilt"]
    names = ["tilt horn (inferred):1", "tilt bar (inferred):1", "pan base:1", "tilt servo:1", "receiver shield 1:1"]
    loaded = meshes.load(stage, names)
    end = stages.pose(stage, "tilt horn (inferred)", stage.horns["tilt horn (inferred)"].limits[0]).parts
    at = lambda name, pose: meshes.Placed(loaded[name], pose[name])
    for name in ("tilt horn (inferred):1", "tilt bar (inferred):1"):
        assert not meshes.penetrates(at(name, end), at("pan base:1", end)), name
    neutral = {n: stage.parts[n].matrix for n in names}
    assert not meshes.penetrates(at("tilt servo:1", neutral), at("receiver shield 1:1", neutral))
