"""Seam: the realistic Skeleton's bones as the Skeleton scene exports them (model/skeleton finish(), just ours; docs/adr/
0025): on the Mech's eyes and neck, held by the head's box (base.DOME), one piece each; the scene itself committed
light, its one source under its own licence."""

import itertools
import os
import subprocess

import numpy as np
import pytest
import trimesh

from model import base, skeleton, stages
from model import geometry as g
from model import gimbal as gm
from model import neck as nk
from model.skeleton import fit

SCENE = os.path.join(stages.REPO, skeleton.SCENE)
CAP_MB = 12.0  # the scene's size cap: #872's warped scene saved 11 MB without Morty (no LFS: docs/adr/0025)
HEAD = ("skull", "mandible")
# the bare bones the mechanism cuts in two, strict so the fixing PR drops its mark: what rides with each cuts it exactly
SEVERED = {
    "skull": "the lower lids, the gimbal frame's plate and the yaw servo cut the palate (7.7 cm3) off the cranium (#967)",
}  # the bones the head carries; the neck's (g.NECK) stand on the cervical carrier


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
def test_the_skull_stands_the_heads_height_its_eyes_in_its_orbits():
    """The chin to the cranium's top within the head gate's height; each eye's centre inside the cranium's box, the
    brow over the orbits ahead of it by half the cap's radius: Morty's eyes (CAP_R) stand proud of an anatomical brow,
    which the Warp's length budget keeps about 24 mm ahead of the orbits' centres (#874)."""
    bones = _bones()
    cranium, mandible = bones["skull"], bones["mandible"]
    assert gm.HEAD_MM[2] - 4.0 <= cranium.bounds[1][2] - mandible.bounds[0][2] <= gm.HEAD_MM[2]
    lo, hi = cranium.bounds
    assert all((lo <= e).all() and (e <= hi).all() for e in map(np.array, gm.EYE.values()))
    assert lo[1] < -gm.CAP_R / 2


@pytest.mark.model
@pytest.mark.bones
def test_the_heads_box_is_the_bones():
    """base.DOME, the head's shell in the gates, is the bare bones' box (ADR 0011: a copy held to its source), to a
    mm."""
    bones = _bones()
    lo = np.min([bones[s].bounds[0] for s in HEAD], axis=0)
    hi = np.max([bones[s].bounds[1] for s in HEAD], axis=0)
    dome = np.array(base.DOME).T
    assert np.abs(dome[0] - lo).max() <= 1.0 and np.abs(dome[1] - hi).max() <= 1.0


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
@pytest.mark.parametrize(
    "stem",
    [pytest.param(s, marks=pytest.mark.xfail(strict=True, reason=SEVERED[s])) if s in SEVERED else s for s in g.BONES],
)
def test_each_bone_is_finished_into_one_piece_within_the_head(stem):
    """One piece (but crumbs of a voxel or two), inside the head's box; a vertebra between the tilt axis and the Torso's
    lid."""
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
        return
    lo, hi = np.array(base.DOME).T
    assert (mesh.bounds[0] >= lo - 1.6).all() and (mesh.bounds[1] <= hi + 1.6).all()


@pytest.mark.model
@pytest.mark.bones
@pytest.mark.parametrize("side", list(nk.MANDIBLE_CHAIN))
def test_the_mandible_covers_the_jaw_carrier_from_outside(side):
    """#968: along each of the jaw's chains (model/printed/neck.py jaw_chains(), the condyle to the chin), straight
    outboard of the carrier, the finished mandible's bone lies against it (within a voxel: the carrier is let into the
    bone) and stands the print floor thick beyond it, to a voxel. Inboard the carrier may show: its post, and the
    chain where the ramus is thinner than it. nk.MANDIBLE_CHAIN is a copy of the scene's mandible: this holds it to
    the bone (ADR 0011)."""
    from model.printed import neck

    rng = np.random.default_rng(0)
    bone, jaw = (
        np.asarray(trimesh.sample.sample_surface(trimesh.load(stages.stl(stem), force="mesh"), 400_000, seed=rng)[0])
        for stem in ("mandible", "jaw")
    )
    sign = 1.0 if side == "L" else -1.0
    bare = []
    for a, b in itertools.pairwise(np.array(neck.jaw_chains()[side])):
        for t in (0.1, 0.3, 0.5, 0.7, 0.9):
            p = a + (b - a) * t
            # each surface's points straight outboard of the chain here, mm from it
            of_bone, of_jaw = (
                sign * (s[np.linalg.norm(s[:, 1:] - p[1:], axis=1) < 1.0, 0] - p[0]) for s in (bone, jaw)
            )
            face = of_jaw[
                (of_jaw > 0) & (of_jaw < 6.0)
            ].max()  # the carrier's own outboard face (not the other chain's)
            beyond = of_bone[of_bone > face - skeleton.PITCH]
            if not (
                len(beyond)
                and beyond.min() < face + skeleton.PITCH
                and beyond.max() - face >= skeleton.FLOOR - skeleton.PITCH
            ):
                bare.append((tuple(np.round(p, 1)), round(float(face), 2)))
    assert bare == []
