"""Seam: model/render/scene.py, a document's parts exported for Blender in their Theme's colours."""

import pytest
import trimesh

from model import geometry, stages
from model.render import scene

DOC = next(iter(geometry.NEXT))


@pytest.mark.build
def test_export_writes_each_part_in_metres_in_its_themes_colour_or_grey(tmp_path):
    manifest = scene.export(DOC, tmp_path)
    assert set(manifest) == set(stages.STAGES[DOC].parts)
    assert manifest["next L eyeball cap:1"]["colour"] == "#FFFFFF"  # morty's eye whites, PLA Basic Jade White
    assert manifest["next torso:1"]["colour"] == "#DBC8B6"  # realistic's Bones, PETG Basic Dark Beige
    assert manifest["next yaw servo:1"]["colour"] in scene.GREYS.values()
    torso = trimesh.load(tmp_path / manifest["next torso:1"]["ply"])
    assert 0.05 < torso.extents.max() < 0.2  # the 92 x 93.5 mm Torso, in metres


def test_a_part_is_coloured_by_its_documents_skeleton():
    """#805: the same Colour group in another Skeleton's filament; hardware stays grey."""
    bail, mechanical = stages.stl("next bail"), stages.stl("next bail" + geometry.MECHANICAL)
    assert scene.colour(bail, geometry.theme("next-stage1")) == "#FFFFFF"  # realistic's Joints, PETG Matte White
    assert scene.colour(mechanical, geometry.theme("next-stage1-mechanical")) == "#000000"  # PETG Basic Black
    assert scene.colour(stages.stl("next pitch bar"), geometry.theme("next-stage1-mechanical")) == "#7F7E83"
    assert scene.colour(stages.stl("servo"), geometry.THEME) == scene.GREYS["servo"]
