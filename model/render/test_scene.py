"""Seam: model/render/scene.py, a document's parts exported for Blender in their colours."""

import pytest
import trimesh

from model import geometry, stages
from model.render import scene

DOC = stages.STAGES[next(iter(geometry.NEXT))]


@pytest.mark.model
def test_export_writes_each_part_in_metres_with_its_spool_or_grey(tmp_path):
    manifest = scene.export(DOC, tmp_path)
    assert set(manifest) == set(DOC.parts)
    assert manifest["next L eyeball cap:1"]["colour"] == "#FFFFFF"  # Pure White
    assert manifest["next torso:1"]["colour"] == "#000000"  # Absolute Black
    assert manifest["next yaw servo:1"]["colour"] not in geometry.SPOOLS.values()
    torso = trimesh.load(tmp_path / manifest["next torso:1"]["ply"])
    assert 0.05 < torso.extents.max() < 0.2  # the 92 x 93.5 mm Torso, in metres
