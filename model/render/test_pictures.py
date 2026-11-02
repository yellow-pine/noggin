"""Seam: model/render/pictures.py poses a Stage's pictures from its baked trajectory (#179, model/trajectories.py),
MuJoCo's poses, not the old engine's (#150)."""

import math

import numpy as np
import pytest

from model import stages
from model.render import pictures

pytestmark = pytest.mark.model


@pytest.mark.parametrize("name,bracket", [("stage1", "desk eye bracket"), ("stage3", "eye bracket")])
def test_each_picture_draws_the_eye_bracket_of_its_stage(name, bracket):
    # the desk build (geometry.DESK: stage 1) has the desk bracket; the mouth needs the rail one
    stage = stages.STAGES[f"noggin-{name}"]
    assert stages.stem(stage.parts["eye bracket:1"].file) == bracket


def test_eight_fps_keeps_a_blinks_shut_frame_that_the_nearest_frame_would_skip():
    """Toon blinks hold shut for one trajectory frame (#258): resampled to 8 fps from 10, that frame stays (#276)."""
    angles = [0, 10, 20, 30, 20, 10, 0, 0, 0, 0]  # the lid horn's degrees per 100 ms; frame 3 is the shut one
    frames = []
    for a in angles:
        t = math.radians(a)
        m = np.eye(4)
        m[:2, :2] = [[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]]
        frames.append({"L lid horn:1": m, "base plate:1": np.eye(4)})
    out = pictures.at_fps(frames, 8)
    assert len(out) == 8  # one second at 8 fps
    assert any(f is frames[3] for f in out)  # nearest-frame alone takes 0, 1, 2, 4, 5, 6, 8, 9


def test_the_site_icon_is_one_whole_eye_of_its_stage():
    """The favicon (#603): Stage 1's right eyeball, pupil and both lids, each a part the Stage has."""
    name, _ = pictures.FAVICON
    parts = stages.STAGES[f"noggin-{name}"].parts
    assert set(pictures.FAVICON_PARTS) <= set(parts)
    assert {stages.stem(parts[p].file) for p in pictures.FAVICON_PARTS} == {
        "R eyeball",
        "pupil",
        "upper lid",
        "lower lid",
    }
