"""Seams of the latest file (#998): the pure candidate pick, on every PR; the written .blend, read back by headless
Blender once `just latest` wrote it (NOGGIN_LATEST names it, as the recipe sets it)."""

import json
import os
import re

import pytest

from model import latest, review, skeleton

MAIN = {"name": "main", "sha": "a" * 40, "date": "2026-11-20T10:00:00Z", "files": [], "checks": [("Checks", "SUCCESS")]}


def pr(n, date, files, checks=(("Review", "SUCCESS"),)):
    sha = f"{n}".ljust(40, "0")
    return {"name": f"PR #{n}", "sha": sha, "date": date, "files": files, "checks": list(checks)} | MEMBER


MEMBER = {"fork": False, "author": "cansin", "association": "MEMBER"}


def test_the_newest_push_touching_a_layer_is_its_candidate():
    old = pr(975, "2026-11-20T11:00:00Z", ["model/gimbal.py"])
    new = pr(999, "2026-11-20T12:00:00Z", ["model/stages.py", "docs/build/parts.md"])
    assert latest.pick(MAIN, [new, old])["Mechanism"]["name"] == "PR #999"
    assert latest.pick(MAIN, [old])["Mechanism"]["name"] == "PR #975"


def test_a_pr_touching_two_layers_counts_for_both_and_the_skin_is_both_its_collections():
    both = pr(976, "2026-11-20T11:00:00Z", ["model/skeleton/fit.py", "model/printed/skin.py"])
    pick = latest.pick(MAIN, [both])
    assert {k for k, c in pick.items() if c["name"] == "PR #976"} == {"Skeleton", "Skin reference", "Skin Shells"}
    assert pick["Mechanism"]["name"] == "main"


def test_main_stands_in_when_nothing_open_touches_a_layer():
    other = pr(988, "2026-11-21T11:00:00Z", ["site/package.json", "uv.lock", "model/latest/__init__.py"])
    assert {c["name"] for c in latest.pick(MAIN, [other]).values()} == {"main"}
    assert set(latest.pick(MAIN, [])) == set(latest.LAYERS)


def test_the_label_carries_the_pr_commit_date_and_gate_status_a_failing_one_too():
    red = pr(969, "2026-11-21T09:30:00Z", ["model/skin.py"], [("Code", "FAILURE"), ("Review", "SUCCESS")])
    pick = latest.pick(MAIN, [red])
    assert pick["Skin Shells"]["label"] == "PR #969 9690000 2026-11-21 fail: Code"
    assert pick["Mechanism"]["label"] == "main aaaaaaa 2026-11-20 pass"
    waiting = pr(978, "2026-11-21T10:00:00Z", ["model/neck.py"], [("Code", "SUCCESS"), ("Review", None)])
    assert latest.pick(MAIN, [waiting])["Mechanism"]["label"] == "PR #978 9780000 2026-11-21 pending: Review"


INSPECT = """
import json, bpy
out = {"scenes": [s.name for s in bpy.data.scenes], "layers": {}}
for c in bpy.data.scenes[0].collection.children:
    meshes = [o for o in c.all_objects if o.type == "MESH"]
    out["layers"][c["layer"]] = {"name": c.name, "label": c["label"], "reason": c["reason"], "meshes": len(meshes),
        "at": {o.name: list(o.matrix_world.translation) for o in meshes},
        "moving": sum(bool(o.animation_data) for o in c.all_objects)}
print("INSPECT " + json.dumps(out))
print("review: done")
"""


def inspect(path):
    log = review._blender([path, "--python-expr", INSPECT])
    return json.loads(next(x for x in log.splitlines() if x.startswith("INSPECT ")).removeprefix("INSPECT "))


@pytest.fixture(scope="module")
def blend():
    path = os.environ.get("NOGGIN_LATEST")
    if not path or not os.path.isfile(path):
        pytest.skip("no latest file to read (NOGGIN_LATEST: just latest sets it)")
    with review.lock(review.SLOT, wait=True):
        return inspect(path)


def test_the_file_holds_one_scene_with_the_four_layers_each_labelled_at_rest(blend):
    assert len(blend["scenes"]) == 1 and list(blend["layers"]) == list(latest.LAYERS)
    for layer, c in blend["layers"].items():
        assert c["name"].startswith(layer + ": ") and re.search(r" [0-9a-f]{7} \d{4}-\d\d-\d\d ", c["label"]), layer
        assert c["meshes"] or c["reason"], layer  # a layer is empty only with its reason
        assert not c["moving"], layer


def test_a_candidate_lands_in_its_head_frame_and_a_missing_one_leaves_its_reason(tmp_path):
    """Small fixture inputs: one candidate whose Mech is a cube at (110, 0, 0), its head at (100, 0, 0); the other
    layers' exports failed or found no Morty."""
    if not os.path.isfile(skeleton.BLENDER):  # a Mac's local check; CI's light jobs have no Blender
        pytest.skip("no Blender on this host")
    cand = str(tmp_path / "assembled.blend")
    make = (
        "import bpy\nbpy.ops.wm.read_factory_settings(use_empty=True)\nc = bpy.data.collections.new('Mech')\n"
        "bpy.context.scene.collection.children.link(c)\nme = bpy.data.meshes.new('Cube')\n"
        "me.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])\n"
        "o = bpy.data.objects.new('Cube', me)\no.location = (110, 0, 0)\nc.objects.link(o)\n"
        f"bpy.ops.wm.save_as_mainfile(filepath={cand!r})\nprint('review: done')\n"
    )
    review._blender(["--python-expr", make])
    job = tmp_path / "job.json"
    job.write_text(json.dumps({"head": [[1, 0, 0, 100], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]}))
    label = "PR #1 abcdef0 2026-11-21 fail: Code"
    layers = {
        k: {"label": label, "blend": None, "job": None, "reason": "export.py failed: boom"} for k in latest.LAYERS
    }
    layers["Mechanism"] |= {"blend": cand, "job": str(job), "reason": None}
    layers["Skin reference"]["reason"] = "no Morty reference at /nowhere"
    (tmp_path / "latest.json").write_text(json.dumps({"layers": layers}))
    out = str(tmp_path / "latest.blend")
    review._blender(["-P", latest.SCRIPT, "--", str(tmp_path / "latest.json"), out])
    got = inspect(out)["layers"]
    assert got["Mechanism"]["at"] == {"Cube": pytest.approx([10, 0, 0])}
    assert got["Mechanism"]["label"] == label and got["Mechanism"]["name"] == f"Mechanism: {label}"
    assert got["Skin reference"]["meshes"] == 0 and "no Morty reference" in got["Skin reference"]["label"]
    assert got["Skeleton"]["reason"] == "export.py failed: boom"


def test_a_fork_or_an_outside_authors_pr_is_never_picked_its_code_never_runs_here():
    """Only a branch of this repo by a member or a trusted bot: anyone can open a PR on a public repo."""
    fork = pr(1, "2026-11-22T00:00:00Z", ["model/gimbal.py"]) | {"fork": True}
    outside = pr(2, "2026-11-22T00:00:00Z", ["model/skeleton/fit.py"]) | {"author": "someone", "association": "NONE"}
    assert {c["name"] for c in latest.pick(MAIN, [fork, outside]).values()} == {"main"}
    bot = pr(3, "2026-11-22T00:00:00Z", ["model/skin.py"]) | {"author": "dependabot", "association": "CONTRIBUTOR"}
    assert latest.pick(MAIN, [bot])["Skin Shells"]["name"] == "PR #3"
