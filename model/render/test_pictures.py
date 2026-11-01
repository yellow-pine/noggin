"""Seam: model/render/pictures.py's stages: the renderer poses the same Mech as the engine (Cansin: "neck still does
not move the head" in the first hero)."""

import numpy as np
import pytest

from model import geometry as g
from model.render import pictures, scene


@pytest.mark.parametrize("servo,deg", [("rotate", -38.0), ("tilt", 50.0)])
def test_on_the_rendered_stage3_the_neck_carries_the_head(servo, deg):
    stage = pictures.assembled("stage3", g.STAGES["noggin-stage3"])
    mats = scene.pose(stage, {servo: deg})
    for n in ("L pupil:1", "eye bracket:1", "bottom jaw:1"):
        assert not np.allclose(mats[n], stage.parts[n].matrix), n
    assert np.allclose(mats["base plate:1"], stage.parts["base plate:1"].matrix)
