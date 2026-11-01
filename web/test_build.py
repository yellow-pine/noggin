"""The site as the Pages workflow builds it (web/build.py): the page loads only what the build writes and offers every
gesture the model replays (model/traces.py) plus the hero loop; each Stage's GLB (`make web`, read here as `make sim`'s
reports are by model/test_report.py) carries every part and one glTF clip per motion, frame for frame its trajectory."""

import hashlib
import os
import re
from html.parser import HTMLParser

import numpy as np
import pygltflib
import pytest

from model import stages, traces, trajectories
from web import build

STAGES = {"noggin-stage1": "stage1.glb", "noggin-stage2": "stage2.glb", "noggin-stage3": "stage3.glb"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.gestures, self.look = set(), [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("src", "href", "data-src"):
            v = a.get(key)
            if v and not re.match(r"https?:|#", v):
                self.refs.add(v)
        if "data-gesture" in a:
            self.gestures.append(a["data-gesture"])

    def handle_data(self, data):
        self.look |= set(re.findall(r"\blook\.(\w+)", data))
        self.refs |= set(re.findall(r'setDecoderPath\("([^"]+)"\)', data))


@pytest.fixture(scope="module")
def page():
    p = Page()
    p.feed(open(os.path.join(build.HERE, "index.html")).read())
    return p


def test_the_page_loads_only_the_glbs_the_build_writes(page):
    assert page.refs == {*STAGES.values(), "draco/"}
    assert build.GLBS == STAGES


def test_one_button_per_gesture_and_the_hero(page):
    assert sorted(page.gestures) == sorted([*traces.GESTURES, "hero"])


def test_the_site_serves_the_draco_decoder_it_checked():
    folder = os.path.join(build.HERE, "build", "draco")
    if not os.path.isdir(folder):
        pytest.skip(f"{folder} not built (make web)")
    assert {f: hashlib.sha256(open(os.path.join(folder, f), "rb").read()).hexdigest() for f in os.listdir(folder)} == {
        "draco_wasm_wrapper.js": "8bb2952d2ba7d67e1414f8df819410cb0434a666be53f671fff75f68843d76f6",
        "draco_decoder.wasm": "a680d927bed9cb864ddbd63521868891af2bfbe755092761b4837487618df8ac",
    }


@pytest.fixture(scope="module", params=STAGES)
def glb(request):
    path = os.path.join(build.HERE, "build", STAGES[request.param])
    if not os.path.isfile(path):
        pytest.skip(f"{path} not built (make web)")
    return request.param, pygltflib.GLTF2.load(path)


def test_the_glb_carries_every_look_number_the_page_reads(glb, page):
    """One source for style B: Blender's export writes the look into the scene's extras, the page reads nothing else."""
    _, g = glb
    look = g.scenes[g.scene].extras
    assert page.look and page.look <= set(look)
    assert look["bg"] == "#F7F4EE" and look["line_px"] == 2.5 and look["crease"] == 60  # docs/model-notes.md, style B
    assert look["line_at"] == 640  # lines scale with the canvas: line_px at 640 px wide (Cansin, #211)


def test_every_part_of_the_stage_is_a_node(glb):
    doc, g = glb
    assert {n.name for n in g.nodes if n.mesh is not None} == set(stages.STAGES[doc].parts)


def test_one_clip_per_gesture_and_the_hero_on_stages_with_a_neck(glb):
    doc, g = glb
    expected = [*traces.GESTURES] + ([] if doc == "noggin-stage1" else ["hero"])
    assert sorted(a.name for a in g.animations) == sorted(expected)


def test_each_clip_has_its_trajectorys_frames_at_its_rate_on_every_part_it_moves(glb):
    """A part the motion leaves still has no channel: it stays at its node's rest pose. The exporter drops a channel
    that varies less than 1e-4 (0.1 mm, its io_scene_gltf2 fcurve_is_constant): MuJoCo jiggles the neck that much
    under the eyes' reactions, so "still" is within half a millimetre (and 5e-4 of a rotation entry, 0.03 deg)."""
    doc, g = glb
    for a in g.animations:
        poses = trajectories.poses(doc, a.name)
        frames = len(poses)
        inputs = [g.accessors[s.input] for s in a.samplers]
        assert {i.count for i in inputs} == {frames}, a.name
        spans = {(i.min[0], i.max[0]) for i in inputs}
        assert len(spans) == 1 and spans.pop() == pytest.approx((0, (frames - 1) / trajectories.FPS)), a.name
        moved = {g.nodes[c.target.node].name for c in a.channels}
        still = {n for n in poses[0] if all(np.allclose(p[n], poses[0][n], atol=5e-4) for p in poses)}
        assert set(stages.STAGES[doc].parts) - still <= moved <= set(stages.STAGES[doc].parts), a.name
