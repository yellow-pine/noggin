"""Seam: the realistic Skeleton's bones as the Skeleton scene exports them (model/skeleton finish(), just ours; docs/adr/
0025): on the Mech's eyes and neck, held by the head's box (base.DOME), one piece each; the scene itself committed
light, its sources under their own licences, scipy for Blender kept in the repo."""

import os
import subprocess

import numpy as np
import pytest
import trimesh
from scipy import ndimage

from model import base, skeleton, stages
from model import geometry as g
from model import gimbal as gm
from model import neck as nk

SCENE = os.path.join(stages.REPO, skeleton.SCENE)
CAP_MB = 12.0  # the scene's size cap: #872's warped scene saved 11 MB without Morty (no LFS: docs/adr/0025)


def test_the_scene_is_committed_compressed_under_its_cap_without_lfs():
    """Blender's compressed .blend (zstd's magic first), at most CAP_MB, and no LFS filter on it."""
    with open(SCENE, "rb") as f:
        assert f.read(4) == b"\x28\xb5\x2f\xfd"
    assert os.path.getsize(SCENE) <= CAP_MB * 1e6
    attr = subprocess.run(["git", "check-attr", "filter", "--", skeleton.SCENE], cwd=stages.REPO, capture_output=True)
    assert b"lfs" not in attr.stdout


def test_blenders_scipy_comes_from_the_repos_gitignored_folder():
    """rewarp.py's scipy: installed into .blender-site, which git ignores, and put on Blender's path from there alone,
    never into Blender.app."""
    ignored = subprocess.run(["git", "check-ignore", "-q", ".blender-site/scipy"], cwd=stages.REPO)
    assert ignored.returncode == 0
    just = open(os.path.join(stages.REPO, "justfile")).read()
    assert "--target .blender-site" in just and "PYTHONPATH=.blender-site" in just
    assert "Blender.app" not in just.split("blender-site: venv", 1)[1].split("\n\n", 1)[0]


@pytest.mark.parametrize("folder", ["model/skull/3demon", "model/skull/atlas-axis"])
def test_each_source_sits_under_its_own_licence(folder):
    """docs/adr/0023: each source's folder carries its licence, its author and where it came from, and names the
    scene that holds it now."""
    notice = open(os.path.join(stages.REPO, f"{folder}/LICENSE.md")).read()  # its folder's own
    assert "printables.com/model/" in notice and "creativecommons.org/licenses/" in notice
    assert "not under the repo's PolyForm Noncommercial licence" in notice and skeleton.SCENE in notice


def _bones():
    return {stem: trimesh.load(stages.stl(stem), force="mesh") for stem in g.BONES}


@pytest.mark.model
def test_the_skull_stands_the_heads_height_its_eyes_in_its_orbits():
    """The chin to the cranium's top within the head gate's height; each eye's centre inside the cranium's box, the
    brow ahead of the caps' fronts."""
    bones = _bones()
    cranium, mandible = bones["skull"], bones["mandible"]
    assert gm.HEAD_MM[2] - 4.0 <= cranium.bounds[1][2] - mandible.bounds[0][2] <= gm.HEAD_MM[2]
    lo, hi = cranium.bounds
    assert all((lo <= e).all() and (e <= hi).all() for e in map(np.array, gm.EYE.values()))
    assert lo[1] < -gm.CAP_R


@pytest.mark.model
def test_the_heads_box_is_the_bones():
    """base.DOME, the head's shell in the gates, is the bare bones' box (ADR 0011: a copy held to its source), to a
    mm."""
    bones = _bones()
    lo = np.min([bones[s].bounds[0] for s in g.SKULL], axis=0)
    hi = np.max([bones[s].bounds[1] for s in g.SKULL], axis=0)
    dome = np.array(base.DOME).T
    assert np.abs(dome[0] - lo).max() <= 1.0 and np.abs(dome[1] - hi).max() <= 1.0


def _canal(atlas, b=0.5):
    """(x, y) of the atlas's vertebral canal: the largest hole in its plan view (its surface sampled, b mm bins)."""
    p = trimesh.sample.sample_surface(atlas, int(atlas.area / b**2 * 4), seed=0)[0][:, :2]
    lo = p.min(axis=0)
    ij = np.floor((p - lo) / b).astype(int)
    occ = np.zeros(ij.max(axis=0) + 1, bool)
    occ[ij[:, 0], ij[:, 1]] = True
    occ = ndimage.binary_closing(occ, iterations=2)
    holes = ndimage.binary_fill_holes(occ) & ~occ
    label, n = ndimage.label(holes)
    biggest = np.argmax(ndimage.sum(holes, label, range(1, n + 1))) + 1
    return np.argwhere(label == biggest).mean(axis=0) * b + lo


@pytest.mark.model
def test_the_vertebrae_ring_the_post_under_the_heads_lugs():
    """The atlas's canal round the pan axis (the post), its top under the head's tilt lugs, the axis under it."""
    bones = _bones()
    atlas, axis = bones["atlas"], bones["axis"]
    assert _canal(atlas) == pytest.approx((0.0, nk.AXIS[0]), abs=1.0)
    assert atlas.bounds[1][2] < nk.AXIS[1] - nk.BOSS_R
    assert axis.bounds[0][2] < atlas.bounds[0][2]


@pytest.mark.model
@pytest.mark.parametrize("stem", g.BONES)
def test_each_bone_is_finished_into_one_piece_within_the_head(stem):
    """One piece (but crumbs of a voxel or two), inside the head's box."""
    mesh = trimesh.load(stages.stl(stem), force="mesh")
    pieces = [p for p in mesh.split(only_watertight=False) if abs(p.volume) > skeleton.PITCH**3 * 8]
    assert len(pieces) == 1
    lo, hi = np.array(base.DOME).T
    assert (mesh.bounds[0] >= lo - 1.6).all() and (mesh.bounds[1] <= hi + 1.6).all()
