"""Seam: model/render/scene.py, a Stage's parts exported for Blender in their colours."""

import trimesh

from model import geometry, stages
from model.render import scene

STAGE1 = stages.STAGES["noggin-stage1"]


def test_export_writes_each_part_in_metres_with_its_spool_or_grey(tmp_path):
    manifest = scene.export(STAGE1, tmp_path)
    assert set(manifest) == set(STAGE1.parts)
    assert manifest["L eyeball:1"]["colour"] == "#FFFFFF"  # Pure White
    assert manifest["base plate:1"]["colour"] == "#000000"  # Absolute Black
    assert manifest["L upper lid:1"]["colour"] == "#F7CED7"  # Milky Pink
    assert manifest["L lid servo:1"]["colour"] not in geometry.SPOOLS.values()
    base = trimesh.load(tmp_path / manifest["base plate:1"]["ply"])
    assert 0.1 < base.extents.max() < 0.2  # the 120 x 160 mm plate, in metres


def test_the_rail_eye_bracket_is_black_and_the_desk_one_pink_as_printed():
    # Cansin's prints (docs/build-photos/printed-parts.jpg): the rail bracket black, the desk bracket pink
    assert scene.colour("eye bracket.stl") == "#000000"  # Absolute Black
    assert scene.colour("desk eye bracket.stl") == "#F7CED7"  # Milky Pink
