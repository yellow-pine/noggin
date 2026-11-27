"""Seam: Morty's Sculpt as git holds it (docs/adr/0027): one closed surface true to the original, light enough for
git, under its author's licence."""

import os
import subprocess

import numpy as np
import pytest
import trimesh

from model import morty, stages

PATH = os.path.join(stages.REPO, morty.SCULPT)
CAP_MB = 6.0  # the Sculpt's size cap (no LFS: docs/adr/0025, 0027)
# the original (morty-fixed.stl, 909,718 triangles, watertight) as trimesh measured it: what the copy is held to
BOX = ((63.56, 240.18, 0.0), (95.09, 271.23, 123.59))  # mm
VOLUME = 33169.7  # mm3


@pytest.fixture(scope="module")
def sculpt():
    return trimesh.load(PATH, process=False)


def test_the_sculpt_is_committed_binary_under_its_cap_without_lfs():
    with open(PATH, "rb") as f:
        assert f.read(64).startswith(b"ply\nformat binary_little_endian 1.0\n")
    assert os.path.getsize(PATH) <= CAP_MB * 1e6
    attr = subprocess.run(["git", "check-attr", "filter", "--", morty.SCULPT], cwd=stages.REPO, capture_output=True)
    assert b"lfs" not in attr.stdout


def test_the_sculpt_is_one_closed_surface(sculpt):
    """What a wall can be grown inward from: every edge shared by two faces, wound one way, in one piece, facing out."""
    assert sculpt.is_watertight and sculpt.is_winding_consistent and sculpt.body_count == 1
    assert sculpt.volume > 0


def test_the_sculpt_keeps_the_originals_box_and_volume(sculpt):
    """Decimated and nothing else: the original's frame and millimetres, its box to 0.01 mm and its volume to 0.05%
    (adopt.py measures the surfaces' distance; LICENSE.md records it)."""
    assert np.abs(sculpt.bounds - np.array(BOX)).max() <= 0.01
    assert abs(sculpt.volume / VOLUME - 1) <= 5e-4


def test_the_sculpt_sits_under_its_authors_licence(sculpt):
    """docs/adr/0023, 0027: the author, the page and CC BY 4.0 beside the mesh, that it is not under the repo's licence,
    whose character Morty is, and our changes as the file has them; docs/credits.md credits it."""
    notice = open(os.path.join(stages.REPO, "model/morty/LICENSE.md")).read()
    assert "ChelsCCT" in notice and "printables.com/model/13460" in notice
    assert "creativecommons.org/licenses/by/4.0/" in notice and "Adult Swim" in notice
    assert "not under the repo's PolyForm Noncommercial licence" in notice and "sculpt.ply" in notice
    assert f"{len(sculpt.faces):,} triangles" in notice
    credits = open(os.path.join(stages.REPO, "docs/credits.md")).read()
    assert "printables.com/model/13460" in credits and "model/morty/LICENSE.md" in credits
