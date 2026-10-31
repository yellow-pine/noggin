"""Seam: model/render/scene.py, a Stage posed at the eye program's joint degrees and exported for Blender."""

import numpy as np
import trimesh

from model import geometry
from model.engine import stages
from model.render import scene

STAGE1 = stages.STAGES["noggin-stage1"]
REST = {"l_lid": 0.0, "l_eye": 0.0, "r_lid": 0.0, "r_eye": 0.0}


def test_all_horns_at_zero_is_the_modelled_pose():
    mats = scene.pose(STAGE1, REST)
    assert all(np.allclose(mats[n], p.matrix) for n, p in STAGE1.parts.items())


def test_each_servo_moves_its_own_chain_as_the_engine_poses_it():
    joints = {"l_lid": 20.0, "l_eye": -15.0, "r_lid": 10.0, "r_eye": 12.0}
    mats = scene.pose(STAGE1, joints)
    for name, deg in (("L lid horn", 20.0), ("L eye horn", -15.0)):
        alone = stages.pose(STAGE1, name, deg).parts
        moved = [n for n in alone if not np.allclose(alone[n], STAGE1.parts[n].matrix)]
        assert moved and all(np.allclose(mats[n], alone[n]) for n in moved)
    assert np.allclose(mats["PandT base:1"], STAGE1.parts["PandT base:1"].matrix)
    assert not np.allclose(mats["R inside lid:1"], stages.pose(STAGE1, "L lid horn", 20.0).parts["R inside lid:1"])


def test_a_stage_without_eye_horns_ignores_the_eye_joints():
    stack = stages.assemble("noggin-stack", {"noggin-stack": ((0, 0, 0), (1, 0, 0), (0, 0, 1))}, 2)
    mats = scene.pose(stack, {"l_lid": 20.0})
    assert all(np.allclose(mats[n], p.matrix) for n, p in stack.parts.items())


def test_export_writes_each_part_in_metres_with_its_spool_or_grey(tmp_path):
    manifest = scene.export(STAGE1, tmp_path)
    assert set(manifest) == set(STAGE1.parts)
    assert manifest["L eyeball:1"]["colour"] == "#FFFFFF"  # Pure White
    assert manifest["PandT base:1"]["colour"] == "#000000"  # Absolute Black
    assert manifest["L inside lid:1"]["colour"] == "#F7CED7"  # Milky Pink
    assert manifest["L lid servo:1"]["colour"] not in geometry.SPOOLS.values()
    base = trimesh.load(tmp_path / manifest["PandT base:1"]["ply"])
    assert 0.1 < base.extents.max() < 0.2  # the 120 x 160 mm plate, in metres
