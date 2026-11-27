"""Seam: the realistic Skeleton's bones as the Skeleton scene exports them (model/skeleton finish(), just ours; docs/adr/
0025): on the Mech's eyes and neck, under Morty's skin (envelope.py), one piece each; the scene itself committed
light, its one source under its own licence."""

import os
import subprocess

import numpy as np
import pytest
import trimesh

from model import geometry as g
from model import gimbal as gm
from model import neck as nk
from model import skeleton, stages
from model.skeleton import envelope, fit

SCENE = os.path.join(stages.REPO, skeleton.SCENE)
CAP_MB = 12.0  # the scene's size cap: #872's warped scene saved 11 MB without Morty (no LFS: docs/adr/0025)
SKIN_TOL = 0.2  # a depth under Morty's skin is good to this (envelope.DENSITY), mm


def test_the_scene_is_committed_compressed_under_its_cap_without_lfs():
    """Blender's compressed .blend (zstd's magic first), at most CAP_MB, and no LFS filter on it."""
    with open(SCENE, "rb") as f:
        assert f.read(4) == b"\x28\xb5\x2f\xfd"
    assert os.path.getsize(SCENE) <= CAP_MB * 1e6
    attr = subprocess.run(["git", "check-attr", "filter", "--", skeleton.SCENE], cwd=stages.REPO, capture_output=True)
    assert b"lfs" not in attr.stdout


def test_the_bones_sit_under_their_sources_licence():
    """docs/adr/0023, 0025: BodyParts3D's licence (treated as CC BY-SA 2.1 JP) beside the scene that holds its bones, and
    the old sources gone."""
    notice = open(os.path.join(stages.REPO, "model/skeleton/LICENSE.md")).read()
    assert "dbarchive.biosciencedbc.jp" in notice and "creativecommons.org/licenses/by-sa/2.1/jp/" in notice
    assert "not under the repo's PolyForm Noncommercial licence" in notice and skeleton.SCENE in notice
    assert not os.path.exists(os.path.join(stages.REPO, "model/skull"))


def _bones():
    return {stem: trimesh.load(stages.stl(stem), force="mesh") for stem in g.BONES}


@pytest.mark.model
@pytest.mark.bones
def test_the_skulls_eyes_sit_in_its_orbits():
    """Each eye's centre, the Mech's and Morty's own, inside the cranium's box, and the forehead over the lids' shell
    ahead of them. No brow stands in front of the eyes any more (ADR 0025's amendment of 2026-11-26): the lids stow in
    a shell 38 mm round each eye centre (#967), which takes the orbits' rims, and Morty's own forehead lies behind
    where an anatomical brow would. The skull's height is Morty's to give
    (test_each_bone_lies_under_mortys_skin), no box's."""
    lo, hi = _bones()["skull"].bounds
    for e in map(np.array, (*gm.EYE.values(), *envelope.EYES.values())):
        assert (lo <= e).all() and (e <= hi).all() and lo[1] < e[1]


@pytest.mark.model
@pytest.mark.bones
def test_the_skull_keeps_out_of_the_lids_shell_and_the_belt_behind_each_eye():
    """#967's re-laid lids stow in a shell of radius skeleton.LID_SHELL all round each of Morty's eye centres
    (envelope.EYES) and their drives leave it through the belt behind the eye (skeleton.BELT): no bone of the finished
    skull within the shell or in the belt, to the Finish's voxel."""
    v = _bones()["skull"].vertices
    for x, y, z in envelope.EYES.values():
        assert np.linalg.norm(v - (x, y, z), axis=1).min() >= skeleton.LID_SHELL + skeleton.CLEAR_MM - skeleton.PITCH
        lo = np.array((x - skeleton.BELT[0], y, z + skeleton.BELT_Z[0])) + skeleton.PITCH
        hi = np.array((x + skeleton.BELT[0], y + skeleton.BELT[1], z + skeleton.BELT_Z[1])) - skeleton.PITCH
        assert not ((v > lo) & (v < hi)).all(axis=1).any()


@pytest.mark.model
@pytest.mark.bones
@pytest.mark.parametrize("stem", g.BONES)
def test_each_bone_lies_under_mortys_skin(stem):
    """Every finished bone at least envelope.ROOM (the Skin's wall and its clearance) under Morty's skin, the sculpt's
    surface, to SKIN_TOL: the skull's limit since 2026-11-27, where the compact head's box was (#893, #874). On main
    before the refit the forehead stood 10.9 mm out of him, the chin 4.6 and C7's spine 8.6."""
    if not os.path.isfile(envelope.sculpt_file()):
        pytest.skip("Morty's sculpt is local until #850 commits it (model/morty, docs/adr/0027)")
    depth = envelope.morty().depth(trimesh.load(stages.stl(stem), force="mesh").vertices)
    assert depth.min() >= envelope.ROOM - SKIN_TOL


@pytest.mark.model
@pytest.mark.bones
def test_the_vertebrae_ring_the_pan_axis_under_the_tilt_axis():
    """The atlas's canal round the pan axis, its top under the tilt axis (C0, the occipital condyles on it), the axis
    under it and each vertebra under the one above."""
    bones = _bones()
    pan, tilt = nk.HEAD_AXES["pan"][0], nk.HEAD_AXES["tilt"][0]
    assert fit.canal(bones["atlas"]) == pytest.approx(pan[:2], abs=1.0)
    assert bones["atlas"].bounds[1][2] < tilt[2]
    assert all(bones[a].bounds[0][2] < bones[b].bounds[0][2] for b, a in zip(g.NECK, g.NECK[1:]))


@pytest.mark.model
@pytest.mark.bones
@pytest.mark.parametrize("stem", g.BONES)
def test_each_bone_is_finished_into_one_piece_within_the_head(stem):
    """One piece (but crumbs of a voxel or two); a vertebra between the tilt axis and the Torso's lid."""
    mesh = trimesh.load(stages.stl(stem), force="mesh")
    pieces = [p for p in mesh.split(only_watertight=False) if abs(p.volume) > skeleton.PITCH**3 * 8]
    assert len(pieces) == 1
    if stem in g.NECK:
        lid = stages.STAGES[skeleton.DOC].parts["torso lid:1"]
        top = (
            trimesh.load(lid.file, force="mesh").apply_transform(lid.matrix).bounds[1][2]
            - stages.DOCS[skeleton.DOC]["eyes"][0][2]
        )
        assert top < mesh.bounds[0][2] and mesh.bounds[1][2] < nk.HEAD_AXES["tilt"][0][2]
