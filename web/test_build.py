"""The viewer's GLBs as Checks builds them (web/build.py): each document's GLB (`just web`, read here as `just sim`'s
reports are by model/test_report.py) carries every part, the look the page reads and one glTF clip per motion, frame for
frame its trajectory. The page itself is the site's (site/src/pages/viewer.astro, its tests in site/)."""

import json
import os
import re
import struct

import numpy as np
import pytest

from model import stages, trajectories
from web import build

# each Stage (#720; Stage 3 the head variant's, Back since #712) in each Skeleton, realistic and mechanical (#704, #805)
STAGES = {f"{d}{s}": f"{d}{s}.glb" for s in ("", "-mechanical") for d in ("stage1", "stage2", "mech-back")}
# and Stage 3 bare in each (#876): the viewer's Skin shape none, its Shells off and the realistic one's full skull on
STAGES |= {f"mech-back{s}-bare": f"mech-back{s}-bare.glb" for s in ("", "-mechanical")}
# and Stage 3 in Cansin's Skin in each (#813): the viewer's Skin shape cansin, after the Skeleton's suffix
STAGES |= {f"mech-back{s}-cansin": f"mech-back{s}-cansin.glb" for s in ("", "-mechanical")}
MODULE = open(os.path.join(build.HERE, "..", "site", "src", "viewer", "viewer.mjs")).read()


def test_one_glb_per_document():
    assert build.PUBLIC == STAGES


def test_a_bare_glb_is_its_stage_without_the_skin_its_full_bones_on():
    """#876: the stills' bare rule (model/render/pictures.py bare); any other GLB shows its document's parts."""
    worn, bare = parts("mech-back"), parts("mech-back-bare")
    assert {"morty face:1", "worn skull:1", "worn mandible:1"} <= worn - bare
    assert {"skull:1", "mandible:1"} <= bare - worn and "torso:1" in bare
    assert parts("mech-back-mechanical-bare") < parts("mech-back-mechanical")
    assert parts("stage2") == set(stages.STAGES["stage2"].parts)


def parts(name):
    """The part names a GLB carries: its document's, as it shows them (build.shown)."""
    return set(build.shown(name, stages.STAGES[build.document(name)].parts))


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
    # black drawn as Blender's charcoal, its lines in the pictures' grey (#914): blender.py imports bpy, so read as text
    drawn = open(os.path.join(build.HERE, "..", "model", "render", "blender.py")).read()
    for k, name in {"black": "BLACK_LIFT", "ink": "INK"}.items():
        assert look[k] == re.search(rf'^{name} = "(#[0-9A-F]{{6}})"', drawn, re.M)[1], k


def test_every_part_of_the_document_is_a_node(glb):
    doc, g = glb
    assert {n["name"] for n in g["nodes"] if "mesh" in n} == parts(doc)


def test_one_clip_per_motion(glb):
    doc, g = glb
    assert sorted(a["name"] for a in g.get("animations", [])) == sorted(trajectories.motions(build.document(doc)))


def test_each_clip_has_its_trajectorys_frames_at_its_rate_on_every_part_it_moves(glb):
    """A part the motion leaves still has no channel: it stays at its node's rest pose. The exporter drops a channel
    that varies less than 1e-4 (0.1 mm, its io_scene_gltf2 fcurve_is_constant): MuJoCo jiggles the neck that much
    under the eyes' reactions, so "still" is within half a millimetre (and 5e-4 of a rotation entry, 0.03 deg)."""
    doc, g = glb
    for a in g.get("animations", []):
        name = a["name"]
        poses = [build.shown(doc, p) for p in trajectories.poses(build.document(doc), name)]
        frames = len(poses)
        inputs = [g["accessors"][s["input"]] for s in a["samplers"]]
        assert {i["count"] for i in inputs} == {frames}, name
        spans = {(i["min"][0], i["max"][0]) for i in inputs}
        assert len(spans) == 1 and spans.pop() == pytest.approx((0, (frames - 1) / trajectories.FPS)), name
        moved = {g["nodes"][c["target"]["node"]]["name"] for c in a["channels"]}
        still = {n for n in poses[0] if all(np.allclose(p[n], poses[0][n], atol=5e-4) for p in poses)}
        assert parts(doc) - still <= moved <= parts(doc), name


def test_each_part_carries_its_explode_offsets_the_page_moves_it_by(glb):
    """#811: each part's node carries its offsets at Explode's levels past assembled (build.explode)."""
    doc, g = glb
    extras = {n["name"]: n.get("extras", {}).get("explode") for n in g["nodes"] if "mesh" in n}
    want = build.explode(doc)
    assert extras.keys() == want.keys()
    for n, offsets in want.items():
        assert extras[n] == pytest.approx(offsets, abs=1e-6), n


@pytest.mark.model
def test_explode_gives_each_part_its_offsets_in_gltfs_metres_and_y_up():
    """#482, #664: the Sub-assemblies level by model/render/pictures.py EXPLODE, as glTF's (x, z, -y) in metres: the
    Torso stays, the jaw lifts with the neck and goes forward; then the Parts level's (#811)."""
    explode = build.explode("mech-back")
    assert explode.keys() == stages.STAGES["mech-back"].parts.keys()
    assert explode["torso:1"] == [0, 0, 0, 0, 0, 0]
    assert explode["jaw:1"][:3] == pytest.approx([0, 0.045, 0.04])
    assert explode["pack:1"][3:] != pytest.approx([0, 0, 0])
