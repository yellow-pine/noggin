"""Seam: model/engine/meshes.py, mesh loading per document and the pairwise distance / penetration judgement."""

import pytest
import trimesh

from model.engine import meshes, stages


def cube(at, size=10.0):
    return meshes.Placed(trimesh.creation.box((size, size, size)), stages.translate(at))


def test_gap_between_two_cubes_is_their_face_to_face_distance():
    a, b = cube((0, 0, 0)), cube((10.4, 3.0, 2.0))  # faces 0.4 mm apart, offset so no vertices face each other
    assert meshes.distance(a, b) == pytest.approx(0.4, abs=1e-6)
    assert meshes.bbox_gap(a, b) == pytest.approx(0.4, abs=1e-6)
    assert meshes.distance(a, cube((30, 0, 0))) == meshes.NEAR_MM  # beyond NEAR_MM a pair is not measured


def test_touching_cubes_are_a_contact_and_overlapping_ones_a_penetration():
    a = cube((0, 0, 0))
    touching, overlapping = cube((10.0, 0, 0)), cube((9.0, 1.0, 1.0))
    assert meshes.distance(a, touching) == pytest.approx(0.0, abs=1e-9) and not meshes.penetrates(a, touching)
    assert meshes.distance(a, overlapping) == pytest.approx(0.0, abs=1e-9) and meshes.penetrates(a, overlapping)


def test_eyeball_bar_rides_the_bracket_rail_at_neutral():
    stage = stages.STAGES["noggin-eyes"]
    loaded = meshes.load(stage, ["L eyeball bar:1", "eye bracket:1"])
    bar, bracket = (meshes.Placed(loaded[n], stage.parts[n].matrix) for n in ("L eyeball bar:1", "eye bracket:1"))
    assert meshes.distance(bar, bracket) < 0.1 and not meshes.penetrates(bar, bracket)


@pytest.mark.parametrize("doc", ["noggin-eyes", "noggin-stage1"])
def test_the_desk_eyes_stand_on_the_base_plate_as_the_side_photo_shows(doc):
    """#172: the servo brackets' feet flat on the plate top (docs/build-photos/eyes-side.jpg), the eye bracket's stem
    down its slot, nothing of the eyes inside the plate (docs/research/2026-11-01-eyes-on-plate.md)."""
    stage = stages.STAGES[doc]
    names = ["base plate:1", "eye bracket:1", "L servo bracket:1", "R servo bracket:1"]
    loaded = meshes.load(stage, names)
    plate, bracket, *feet = (meshes.Placed(loaded[n], stage.parts[n].matrix) for n in names)
    for part in (bracket, *feet):
        assert not meshes.penetrates(plate, part)
    for part in feet:
        assert meshes.distance(plate, part) < 0.1


def test_loaded_meshes_are_subdivided_and_the_battery_lead_is_cut():
    stage = stages.STAGES["noggin-pan-tilt"]
    loaded = meshes.load(stage, ["base plate:1", "battery 1:1"])
    assert loaded["base plate:1"].edges_unique_length.max() <= meshes.MAX_EDGE_MM + 1e-6
    assert loaded["battery 1:1"].bounds[1][1] <= 56.0 + 1e-6


def test_the_stack_clears_the_pan_base_at_the_tilt_end_and_the_boards_at_neutral():
    """Engine findings 2026-10-31 (#24): the tilt horn and bar swept into the pan turntable at the config's tilt end, and the
    tilt servo's straight lead stub sank into receiver shield 1 at neutral."""
    stage = stages.STAGES["noggin-pan-tilt"]
    names = ["tilt horn:1", "tilt bar:1", "pan turntable:1", "tilt servo:1", "receiver shield 1:1"]
    loaded = meshes.load(stage, names)
    end = stages.pose(stage, "tilt horn", stage.horns["tilt horn"].limits[0]).parts
    at = lambda name, pose: meshes.Placed(loaded[name], pose[name])
    for name in ("tilt horn:1", "tilt bar:1"):
        assert not meshes.penetrates(at(name, end), at("pan turntable:1", end)), name
    neutral = {n: stage.parts[n].matrix for n in names}
    assert not meshes.penetrates(at("tilt servo:1", neutral), at("receiver shield 1:1", neutral))
