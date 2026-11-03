"""Seam: model/render/scene.py, a document's parts exported for Blender in their Theme's colours."""

import pytest
import trimesh

from model import geometry, stages
from model.render import scene

DOC = next(iter(geometry.NEXT))


@pytest.mark.model
def test_export_writes_each_part_in_metres_in_its_themes_colour_or_grey(tmp_path):
    """#805, #819: in the document's Theme, or the one given (a Preset's pictures); each part names its Colour group,
    a hardware envelope its file's name: what the GLB's materials are named by, the viewer's repaint."""
    manifest = scene.export(DOC, tmp_path)
    assert set(manifest) == set(stages.STAGES[DOC].parts)
    assert manifest["next L eyeball cap:1"]["colour"] == "#FFFFFF"  # morty's eye whites, PLA Basic Jade White
    assert manifest["next gimbal frame:1"]["colour"] == "#DBC8B6"  # anatomical Bones, PETG Basic Dark Beige
    assert manifest["next torso:1"]["colour"] == "#000000"  # Mounts, black in every Palette (#838)
    assert manifest["next yaw servo:1"]["colour"] in scene.GREYS.values()
    assert [manifest[n]["group"] for n in ("next gimbal frame:1", "next L eyeball cap:1", "next yaw servo:1")] == [
        "Bones", "eye whites", "servo"
    ]  # fmt: skip
    torso = trimesh.load(tmp_path / manifest["next torso:1"]["ply"])
    assert 0.05 < torso.extents.max() < 0.2  # the 92 x 93.5 mm Torso, in metres
    black = scene.export(DOC, tmp_path, geometry.PRESETS["Cansin's build"])
    assert black["next gimbal frame:1"]["colour"] == "#000000"


def test_a_part_is_coloured_by_its_themes_palette():
    """#805, #819: the same Colour group in another Palette's filament; hardware stays grey."""
    bail, mechanical = stages.stl("next bail"), stages.stl("next bail" + geometry.MECHANICAL)
    assert scene.colour(bail, geometry.theme("next-stage1")) == "#FFFFFF"  # anatomical Joints, PETG Matte White
    assert scene.colour(mechanical, geometry.theme("next-stage1-mechanical")) == "#000000"  # black, PETG Basic Black
    robot = geometry.THEME | {"Skeleton palette": "robot"}
    assert scene.colour(stages.stl("next pitch bar"), robot) == "#7F7E83"  # PETG Basic Gray
    assert scene.colour(stages.stl("servo"), geometry.THEME) == scene.GREYS["servo"]
