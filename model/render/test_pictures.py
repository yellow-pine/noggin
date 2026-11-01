"""Seam: model/render/pictures.py poses a Stage's pictures from its baked trajectory (#179, model/trajectories.py),
MuJoCo's poses, not the old engine's (#150)."""

import json
import math
import os

import numpy as np
import pytest

from model import stages, traces
from model import trajectories as tj
from model.render import pictures

pytestmark = pytest.mark.model
C = math.sqrt(0.5)  # cos and sin of 45 degrees: a quaternion turning 90 degrees


def test_each_gif_frame_is_one_trajectory_frame_with_its_parts_where_the_trajectory_puts_them(tmp_path, monkeypatch):
    # every part at the origin for 3 frames, the L lid horn moved and turned 90 degrees about Z in frame 1
    rest = {"pos": [[0, 0, 0]] * 3, "quat": [[1, 0, 0, 0]] * 3}
    parts = {n: rest for n in stages.STAGES["noggin-stage1"].parts}
    parts["L lid horn:1"] = {
        "pos": [[0, 0, 0], [0.01, 0.02, 0.03], [0, 0, 0]],
        "quat": [[1, 0, 0, 0], [C, 0, 0, C], [1, 0, 0, 0]],
    }
    os.makedirs(tmp_path / "noggin-stage1")
    for gesture in traces.GESTURES:  # the camera is fitted to every gesture's frames
        json.dump(
            {"parts": parts if gesture == "wink" else {n: rest for n in parts}},
            open(tmp_path / "noggin-stage1" / f"{gesture}.json", "w"),
        )
    monkeypatch.setattr(tj, "OUT", str(tmp_path))
    monkeypatch.setattr(pictures, "OUT", str(tmp_path / "pictures"))
    shots = []
    monkeypatch.setattr(pictures, "blender", lambda name, manifest, s: shots.extend(s))
    monkeypatch.setattr(pictures, "encode", lambda *a, **k: None)
    pictures.gifs(["wink"])
    assert len(shots) == 3
    turned = [[0, -1, 0, 0.01], [1, 0, 0, 0.02], [0, 0, 1, 0.03], [0, 0, 0, 1]]
    assert np.allclose(shots[1]["pose"]["L lid horn:1"], turned)
    assert np.allclose(shots[0]["pose"]["L lid horn:1"], np.eye(4))
    assert set(shots[1]["pose"]) == set(parts)
    # each gesture renders on its own runner in CI (#226): the same camera whichever gestures one renders
    alone = shots[0]["camera"]
    shots.clear()
    pictures.gifs()
    assert shots[0]["camera"] == alone


@pytest.mark.parametrize(
    "name,bracket", [("stage1", "desk eye bracket"), ("eyes", "desk eye bracket"), ("mouth", "eye bracket")]
)
def test_each_picture_draws_the_eye_bracket_of_its_document(name, bracket):
    # the desk build (geometry.DESK: the eyes document and stage 1) has the desk bracket; the mouth needs the rail one
    stage = pictures.assembled(name, pictures.DOCS[name][0])
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
