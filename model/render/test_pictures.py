"""Seam: model/render/pictures.py's stages: the renderer poses the same Mech as the engine (Cansin: "neck still does
not move the head" in the first hero)."""

import numpy as np
import pytest

from model import geometry as g
from model.engine import stages
from model.render import pictures, scene


@pytest.mark.parametrize("servo,deg", [("rotate", -38.0), ("tilt", 50.0)])
def test_on_the_rendered_stage3_the_neck_carries_the_head(servo, deg):
    stage = pictures.assembled("stage3", g.STAGES["noggin-stage3"])
    mats = scene.pose(stage, {servo: deg})
    for n in ("L pupil:1", "eye bracket:1", "bottom jaw:1"):
        assert not np.allclose(mats[n], stage.parts[n].matrix), n
    assert np.allclose(mats["base plate:1"], stage.parts["base plate:1"].matrix)


def test_the_stage1_picture_draws_the_desk_eye_bracket():
    stage = pictures.assembled("stage1", g.STAGES["noggin-stage1"])
    assert stages.stem(stage.parts["eye bracket:1"].file) == "desk eye bracket"
