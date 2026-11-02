"""Seam: model/render/pictures.py at_fps(), a baked trajectory (#179, model/trajectories.py) resampled for a picture."""

import math

import numpy as np
import pytest

from model.render import pictures

pytestmark = pytest.mark.model


def test_eight_fps_keeps_a_blinks_shut_frame_that_the_nearest_frame_would_skip():
    """Toon blinks hold shut for one trajectory frame (#258): resampled to 8 fps from 10, that frame stays (#276)."""
    angles = [0, 10, 20, 30, 20, 10, 0, 0, 0, 0]  # the lid horn's degrees per 100 ms; frame 3 is the shut one
    frames = []
    for a in angles:
        t = math.radians(a)
        m = np.eye(4)
        m[:2, :2] = [[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]]
        frames.append({"L lid horn:1": m, "next torso:1": np.eye(4)})
    out = pictures.at_fps(frames, 8)
    assert len(out) == 8  # one second at 8 fps
    assert any(f is frames[3] for f in out)  # nearest-frame alone takes 0, 1, 2, 4, 5, 6, 8, 9
