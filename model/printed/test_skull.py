"""Seam: model/printed/skull.py, the realistic skull's bones (#838): placed on the next Mech's eyes and neck, held by the
head's box (base.DOME), each source under its own licence beside it, and carved into one piece each (just ours)."""

import os

import numpy as np
import pytest
import trimesh

from model import base, stages
from model import geometry as g
from model import gimbal as gm
from model.printed import skull


@pytest.fixture(scope="module")
def placed():
    return skull.placed()


def test_the_skull_stands_the_heads_height_its_eyes_in_its_orbits(placed):
    """Chin to top HEIGHT_SPARE under the head gate's height; each eye's centre inside the cranium's box, its cap's
    front SUNK proud of the orbit's rim."""
    cranium, mandible = placed["next skull"], placed["next mandible"]
    assert cranium.vertices[:, 2].max() - mandible.vertices[:, 2].min() == pytest.approx(
        gm.HEAD_MM[2] - skull.HEIGHT_SPARE
    )
    lo, hi = cranium.bounds
    assert all((lo <= e).all() and (e <= hi).all() for e in map(np.array, gm.EYE.values()))
    assert lo[1] < -gm.CAP_R  # the brow ahead of the caps' fronts


def test_the_heads_box_is_the_skulls(placed):
    """base.DOME, the head's shell in the gates, is the placed skull's box (ADR 0011: a copy held to its source), to
    the mm."""
    lo = np.min([m.bounds[0] for m in placed.values()], axis=0)
    hi = np.max([m.bounds[1] for m in placed.values()], axis=0)
    dome = np.array(base.DOME).T
    assert np.abs(dome[0] - lo).max() <= 1.0 and np.abs(dome[1] - hi).max() <= 1.0


def test_the_vertebrae_ring_the_post_under_the_heads_lugs(placed):
    """The atlas's canal round the pan axis (the post), its top under the head's tilt lugs, the axis under it."""
    atlas, axis = placed["next atlas"], placed["next axis"]
    canal = skull._canal(atlas)
    assert canal == pytest.approx((0.0, stages.neck.AXIS[0]), abs=0.5)
    assert atlas.vertices[:, 2].max() < stages.neck.AXIS[1] - stages.neck.BOSS_R
    assert axis.vertices[:, 2].min() < atlas.vertices[:, 2].min()


@pytest.mark.parametrize("source", [skull.CRANIUM, skull.MANDIBLE, skull.ATLAS, skull.AXIS])
def test_each_source_sits_under_its_own_licence(source):
    """docs/adr/0023: each source's folder carries its licence, its author and where it came from."""
    notice = open(os.path.join(stages.REPO, os.path.dirname(source), "LICENSE.md")).read()
    assert "printables.com/model/" in notice and "creativecommons.org/licenses/" in notice
    assert "not under the repo's PolyForm Noncommercial licence" in notice


@pytest.mark.model
@pytest.mark.parametrize("stem", g.SKULL)
def test_each_bone_is_carved_into_one_piece_within_the_head(stem):
    """just ours: one piece (but crumbs of a voxel or two), inside the head's box."""
    mesh = trimesh.load(stages.stl(stem), force="mesh")
    pieces = [p for p in mesh.split(only_watertight=False) if abs(p.volume) > skull.PITCH**3 * 8]
    assert len(pieces) == 1
    lo, hi = np.array(base.DOME).T
    assert (mesh.bounds[0] >= lo - 1.5).all() and (mesh.bounds[1] <= hi + 1.5).all()
