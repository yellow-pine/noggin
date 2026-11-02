"""The viewer's GLBs as Checks builds them (web/build.py): each Stage's GLB (`just web`, read here as `just sim`'s
reports are by model/test_report.py) carries every part, the look the page reads and one glTF clip per motion, frame for
frame its trajectory. The page itself is the site's (site/src/pages/viewer.astro, its tests in site/)."""

import json
import math
import os
import re
import struct

import numpy as np
import pytest

from model import stages, traces, trajectories
from model.render import camera as render_camera
from model.render import pictures
from web import build

STAGES = {"noggin-stage1": "stage1.glb", "noggin-stage2": "stage2.glb", "noggin-stage3": "stage3.glb"}
STAGES |= {d: f"{d}.glb" for d in ("next-mech-back", "next-mech-crown", "next-mech-split")}  # #649, #686; #663
MODULE = open(os.path.join(build.HERE, "..", "site", "src", "viewer", "viewer.mjs")).read()


def test_one_glb_per_stage():
    assert build.GLBS == STAGES


@pytest.fixture(scope="module", params=STAGES)
def glb(request):
    path = os.path.join(build.HERE, "build", STAGES[request.param])
    if not os.path.isfile(path):
        pytest.skip(f"{path} not built (just web)")
    with open(path, "rb") as f:  # a GLB opens with its glTF JSON chunk (glTF 2.0 spec, GLB File Format)
        magic, _, _, size, kind = struct.unpack("<4sIIII", f.read(20))
        assert magic == b"glTF" and kind == 0x4E4F534A, path  # "JSON"
        return request.param, json.loads(f.read(size))


def test_the_glb_carries_every_look_number_the_page_reads(glb):
    """One source for style B: Blender's export writes the look into the scene's extras, the page reads nothing else."""
    _, g = glb
    look, read = g["scenes"][g["scene"]]["extras"], set(re.findall(r"\blook\.(\w+)", MODULE))
    assert read and read <= set(look)
    assert look["line_px"] == 2.5 and look["crease"] == 60  # docs/model-notes.md, style B
    assert look["line_at"] == 640  # lines scale with the canvas: line_px at 640 px wide (Cansin, #211)


def test_every_part_of_the_stage_is_a_node(glb):
    doc, g = glb
    assert {n["name"] for n in g["nodes"] if "mesh" in n} == set(stages.STAGES[doc].parts)


def test_one_clip_per_gesture_and_the_hero_on_stages_with_a_neck(glb):
    doc, g = glb
    expected = [*traces.GESTURES] + ([] if doc == "noggin-stage1" else ["hero"]) if doc.startswith("noggin-") else []
    expected = expected if doc.startswith("noggin-") else [*traces.NEXT_MOTIONS, "next hero"]
    assert sorted(a["name"] for a in g.get("animations", [])) == sorted(expected)


def test_the_hero_stage_carries_the_hero_pictures_camera(glb):
    """The landing page swaps its poster (the hero picture) for the viewer, which starts from the picture's camera, so
    the Mech neither jumps nor moves (#597): pictures.hero_camera's lens and frame, looking along HERO, glTF's Y-up."""
    doc, g = glb
    if doc != pictures.HERO_STAGE:
        assert "cameras" not in g
        return
    (camera,) = g["cameras"]
    aspect = pictures.HERO_SIZE[0] / pictures.HERO_SIZE[1]
    assert camera["perspective"]["aspectRatio"] == pytest.approx(aspect)
    half = render_camera.SENSOR_MM / 2 / pictures.LENS / aspect  # sensor fitted to the width (model/render/camera.py)
    assert camera["perspective"]["yfov"] == pytest.approx(2 * math.atan(half))
    (node,) = [n for n in g["nodes"] if "camera" in n]
    x, y, z, w = node["rotation"]  # glTF's quaternion; the camera looks down its -Z
    forward = -np.array([2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y)])
    hx, hy, hz = pictures.HERO
    assert forward == pytest.approx(-np.array([hx, hz, -hy]), abs=1e-5)  # Blender's Z-up to glTF's Y-up


def test_each_clip_has_its_trajectorys_frames_at_its_rate_on_every_part_it_moves(glb):
    """A part the motion leaves still has no channel: it stays at its node's rest pose. The exporter drops a channel
    that varies less than 1e-4 (0.1 mm, its io_scene_gltf2 fcurve_is_constant): MuJoCo jiggles the neck that much
    under the eyes' reactions, so "still" is within half a millimetre (and 5e-4 of a rotation entry, 0.03 deg)."""
    doc, g = glb
    for a in g.get("animations", []):
        name = a["name"]
        poses = trajectories.poses(doc, name)
        frames = len(poses)
        inputs = [g["accessors"][s["input"]] for s in a["samplers"]]
        assert {i["count"] for i in inputs} == {frames}, name
        spans = {(i["min"][0], i["max"][0]) for i in inputs}
        assert len(spans) == 1 and spans.pop() == pytest.approx((0, (frames - 1) / trajectories.FPS)), name
        moved = {g["nodes"][c["target"]["node"]]["name"] for c in a["channels"]}
        still = {n for n in poses[0] if all(np.allclose(p[n], poses[0][n], atol=5e-4) for p in poses)}
        assert set(stages.STAGES[doc].parts) - still <= moved <= set(stages.STAGES[doc].parts), name
