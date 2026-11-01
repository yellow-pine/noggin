"""Seam: the mating joints (model/mating.py) on the features our parts declare (model/printed, model/envelopes.py),
measured on their meshes (make ours); MuJoCo holds each joint's sites together (model/test_mjcf.py)."""

import numpy as np
import pytest

from model import envelopes, fits, mating, printed, stages


def test_every_joint_names_features_our_parts_declare_and_no_declared_feature_goes_unused():
    declared = {**printed.FEATURES, **envelopes.FEATURES}
    parts = [stages.STAGES[doc].parts for doc in ("noggin-eyes", "noggin-pan-tilt", "noggin-mouth")]
    # by mesh: noggin-eyes builds the desk eye bracket, noggin-mouth the rail one
    joints = [feats for _, feats in mating.JOINTS]
    named = {
        (stages.stem(ps[p].file), f)
        for ps in parts
        for feats in joints
        if {p for p, _ in feats} <= set(ps)
        for p, f in feats
    }
    assert named == {(stem, f) for stem, feats in declared.items() for f in feats}


@pytest.mark.parametrize("stem", sorted(mating.FEATURES))
def test_our_mesh_carries_every_feature_its_part_declares(stem):
    for name, (centre, axis, r, half, *band) in mating.FEATURES[stem].items():
        fit = fits.fit_circle(stages.stl(stem), centre, axis, half, r, *band or [fits.HOLE])
        off = np.linalg.norm(np.subtract(fit["centre"], centre))
        assert fit["r"] == pytest.approx(r, abs=0.03) and off < 0.03, (name, fit["r"], off)
