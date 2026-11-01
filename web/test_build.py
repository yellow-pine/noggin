"""The site as the Pages workflow builds it (web/build.py): the page loads only what the build writes and offers every
gesture the model replays (model/traces.py) plus the hero loop; each Stage's GLB (`make web`, read here as `make sim`'s
reports are by model/test_report.py) carries every part and one animation per motion, frame for frame its trajectory."""

import json
import os
import re
import struct
from html.parser import HTMLParser

import numpy as np
import pytest

from model import traces, trajectories
from model.engine import stages
from web import build

STAGES = {"noggin-stage1": "stage1.glb", "noggin-stage2": "stage2.glb", "noggin-stage3": "stage3.glb"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.gestures = set(), []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("src", "href", "data-src"):
            v = a.get(key)
            if v and not re.match(r"https?:|#", v):
                self.refs.add(v)
        if "data-gesture" in a:
            self.gestures.append(a["data-gesture"])


@pytest.fixture(scope="module")
def page():
    p = Page()
    p.feed(open(os.path.join(build.HERE, "index.html")).read())
    return p


def test_the_page_loads_only_the_glbs_the_build_writes(page):
    assert page.refs == set(STAGES.values())
    assert build.GLBS == STAGES


def test_one_button_per_gesture_and_the_hero(page):
    assert sorted(page.gestures) == sorted([*traces.GESTURES, "hero"])


def gltf(path):
    """The GLB's JSON chunk (glTF 2.0 binary: 12-byte header, then chunk length, type 'JSON', the JSON)."""
    with open(path, "rb") as f:
        magic, _, _, length, kind = struct.unpack("<4sIII4s", f.read(20))
        assert (magic, kind) == (b"glTF", b"JSON")
        return json.loads(f.read(length))


@pytest.fixture(scope="module", params=STAGES)
def glb(request):
    path = os.path.join(build.HERE, "build", STAGES[request.param])
    if not os.path.isfile(path):
        pytest.skip(f"{path} not built (make web)")
    return request.param, gltf(path)


def test_every_part_of_the_stage_is_a_node(glb):
    doc, g = glb
    assert {n["name"] for n in g["nodes"] if "mesh" in n} == set(stages.STAGES[doc].parts)


def test_one_animation_per_gesture_and_the_hero_on_stages_with_a_neck(glb):
    doc, g = glb
    expected = [*traces.GESTURES] + ([] if doc == "noggin-stage1" else ["hero"])
    assert sorted(a["name"] for a in g["animations"]) == sorted(expected)


def test_each_animation_has_its_trajectorys_frames_at_its_rate_on_every_part_it_moves(glb):
    """A part the motion leaves still has no channel: it stays at its node's rest pose. The exporter drops a channel
    that varies less than 1e-4 (0.1 mm, its io_scene_gltf2 fcurve_is_constant): MuJoCo jiggles the neck that much
    under the eyes' reactions, so "still" is within half a millimetre (and 5e-4 of a rotation entry, 0.03 deg)."""
    doc, g = glb
    for a in g["animations"]:
        poses = trajectories.poses(doc, a["name"])
        frames = len(poses)
        times = {g["accessors"][s["input"]]["count"] for s in a["samplers"]}
        spans = {(g["accessors"][s["input"]]["min"][0], g["accessors"][s["input"]]["max"][0]) for s in a["samplers"]}
        assert times == {frames}, a["name"]
        assert len(spans) == 1 and spans.pop() == pytest.approx((0, (frames - 1) / trajectories.FPS)), a["name"]
        moved = {g["nodes"][c["target"]["node"]]["name"] for c in a["channels"]}
        still = {n for n in poses[0] if all(np.allclose(p[n], poses[0][n], atol=5e-4) for p in poses)}
        assert set(stages.STAGES[doc].parts) - still <= moved <= set(stages.STAGES[doc].parts), a["name"]
