"""The viewer as Site Checks builds it (web/build.py, and MkDocs its page at viewer/): the page loads only what
the build writes and runs scripts from the site alone; each Stage's GLB (`make web`, read here as `make sim`'s reports
are by model/test_report.py) carries every part and one glTF clip per motion, frame for frame its trajectory."""

import base64
import hashlib
import json
import os
import re
import struct
from html.parser import HTMLParser

import numpy as np
import pytest

from model import stages, traces, trajectories
from web import build

STAGES = {"noggin-stage1": "stage1.glb", "noggin-stage2": "stage2.glb", "noggin-stage3": "stage3.glb"}
MODULE = open(os.path.join(build.HERE, "viewer.mjs")).read()


class Page(HTMLParser):
    """The viewer's page as MkDocs built it: its CSP, import map, module scripts and Stage buttons."""

    def __init__(self):
        super().__init__()
        self.csp, self.importmap, self.modules, self.stages = None, None, [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("http-equiv") == "Content-Security-Policy":
            self.csp = a["content"]
        if tag == "script" and a.get("type") == "module":
            self.modules.append(a.get("src"))
        self.importmap = self.importmap or tag == "script" and a.get("type") == "importmap"
        if "data-stage" in a:
            self.stages.add(a["data-stage"])

    def handle_data(self, data):
        if self.importmap is True:
            self.importmap = json.loads(data)


@pytest.fixture(scope="module")
def page(site):
    p = Page()
    p.feed((site / "viewer" / "index.html").read_text())
    return p


def test_the_page_loads_only_what_the_build_writes(page):
    """Its one module and the Stages' GLBs and the Draco decoder beside it (viewer/), which the build writes."""
    decoder = "examples/jsm/libs/draco/gltf/"
    assert page.modules == ["viewer.mjs"] and "viewer.mjs" in build.MODULES
    assert build.GLBS == STAGES and {f"{s}.glb" for s in page.stages} == set(STAGES.values())
    assert re.findall(r'here\("([^"]+)"\)', MODULE) == ["three/" + decoder]
    assert {f for f in build.THREE if f.startswith(decoder)} == {
        decoder + "draco_wasm_wrapper.js",
        decoder + "draco_decoder.wasm",
    }
    assert set(re.findall(r'from "\./([^"]+)"', MODULE)) <= set(build.MODULES)  # the module's own imports are copied


@pytest.fixture(scope="module")
def three():
    folder = os.path.join(build.HERE, "build", "three")
    if not os.path.isdir(folder):
        pytest.skip(f"{folder} not built (make web)")
    return folder


def test_the_site_serves_the_three_it_checked(three):
    """Each file is the pinned one, and only the pinned ones ship."""
    served = {os.path.relpath(os.path.join(d, f), three) for d, _, fs in os.walk(three) for f in fs}
    sha = {
        f: base64.b64encode(hashlib.sha384(open(os.path.join(three, f), "rb").read()).digest()).decode() for f in served
    }
    assert {f: f"sha384-{h}" for f, h in sha.items()} == build.THREE


def test_every_module_the_page_imports_is_one_the_site_serves(page, three):
    """The module's imports through the page's import map (its own modules aside: build.MODULES), then each served
    module's own import statements: all land on a pinned file, and every pinned module is one of them."""
    imports = {k: v.removeprefix("./three/") for k, v in page.importmap["imports"].items()}

    def resolve(m, base):
        return imports.get(m) or (
            m.replace("three/addons/", imports["three/addons/"])
            if m.startswith("three/addons/")
            else os.path.normpath(os.path.join(os.path.dirname(base), m))
        )

    todo, seen = {resolve(m, "") for m in re.findall(r'from "([^".][^"]*)"', MODULE)}, set()  # not its own
    while todo:
        f = todo.pop()
        assert f in build.THREE, f
        seen.add(f)
        statements = re.findall(
            r"""^(?:import|export|\})[^'"\n]*?(?:\bfrom )?['"]([^'"]+)['"]""", open(os.path.join(three, f)).read(), re.M
        )
        todo |= {resolve(m, f) for m in statements} - seen
    assert seen == {f for f in build.THREE if f.endswith(".js") and "/draco/" not in f}


def test_the_page_runs_scripts_from_the_site_alone(page):
    """three.js and its addons come from the site (web/build.py fetched and checked them), through an import map
    relative to the page (viewer/); the CSP blocks any other script, lets the Draco decoder compile its WASM in the Blob
    worker DRACOLoader makes, and blocks nothing else (Material's search runs in a worker from the site)."""
    imports = {"three": "./three/build/three.module.js", "three/addons/": "./three/examples/jsm/"}
    assert page.importmap == {"imports": imports}
    assert page.csp == "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; worker-src 'self' blob:"


@pytest.fixture(scope="module", params=STAGES)
def glb(request):
    path = os.path.join(build.HERE, "build", STAGES[request.param])
    if not os.path.isfile(path):
        pytest.skip(f"{path} not built (make web)")
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
    expected = [*traces.GESTURES] + ([] if doc == "noggin-stage1" else ["hero"])
    assert sorted(a["name"] for a in g["animations"]) == sorted(expected)


def test_each_clip_has_its_trajectorys_frames_at_its_rate_on_every_part_it_moves(glb):
    """A part the motion leaves still has no channel: it stays at its node's rest pose. The exporter drops a channel
    that varies less than 1e-4 (0.1 mm, its io_scene_gltf2 fcurve_is_constant): MuJoCo jiggles the neck that much
    under the eyes' reactions, so "still" is within half a millimetre (and 5e-4 of a rotation entry, 0.03 deg)."""
    doc, g = glb
    for a in g["animations"]:
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
