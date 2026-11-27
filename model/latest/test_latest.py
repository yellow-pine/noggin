"""Seams of the latest file (#998): the pure candidate pick, on every PR; the written .blend, read back by headless
Blender once `just latest` wrote it (NOGGIN_LATEST names it, as the recipe sets it)."""

import json
import os
import re
import subprocess

import pytest
import trimesh

from model import geometry as g
from model import latest, review, skeleton

MAIN = {"name": "main", "sha": "a" * 40, "date": "2026-11-20T10:00:00Z", "files": [], "checks": [("Checks", "SUCCESS")]}


def pr(n, date, files, checks=(("Review", "SUCCESS"),), contains=()):
    """An open PR's record; `contains`: main's commits its head has (of main's `commits`)."""
    sha = f"{n}".ljust(40, "0")
    record = {"name": f"PR #{n}", "sha": sha, "date": date, "files": files, "checks": list(checks)}
    return record | {"contains": list(contains)} | MEMBER


MEMBER = {"fork": False, "author": "cansin", "association": "MEMBER"}


def test_the_newest_push_touching_a_layer_is_its_candidate():
    old = pr(975, "2026-11-20T11:00:00Z", ["model/gimbal.py"])
    new = pr(999, "2026-11-20T12:00:00Z", ["model/stages.py", "docs/build/parts.md"])
    assert latest.pick(MAIN, [new, old])["Mechanism"]["name"] == "PR #999"
    assert latest.pick(MAIN, [old])["Mechanism"]["name"] == "PR #975"


def test_a_pr_is_a_layers_candidate_only_if_its_head_contains_mains_newest_commit_touching_the_layer():
    """#1066: #1064, pushed after #1032 (the skull refitted inside Morty's skin) merged but from a branch without it,
    took the Mechanism and Skeleton layers back to the old skull; so did #960 before it, a draft three weeks older
    than main's change (#1022). Main's layer it is, and the label says who was passed over and why; a PR that has
    main's change (it merged main, or branched after it) keeps the layer, whatever else merged after."""
    refit = "efed70a7" + "0" * 32
    main = MAIN | {"commits": {"Mechanism": refit, "Skeleton": refit}}
    behind = pr(1064, "2026-11-27T09:00:00Z", ["model/neck.py", "model/skeleton/test_skeleton.py", "model/skin.py"])
    stale = pr(960, "2026-11-04T09:00:00Z", ["model/neck.py"])
    pick = latest.pick(main, [stale, behind])
    assert pick["Skeleton"]["name"] == pick["Mechanism"]["name"] == "main"
    assert pick["Skeleton"]["label"] == "main aaaaaaa 2026-11-20 pass; passed over PR #1064 (without main's efed70a)"
    assert (
        pick["Mechanism"]["label"]
        == "main aaaaaaa 2026-11-20 pass; passed over PR #1064, PR #960 (without main's efed70a)"
    )
    assert pick["Skin Shells"]["label"] == "PR #1064 1064000 2026-11-27 pass"  # main's last 300 commits left it alone
    merged = pr(1030, "2026-11-26T12:00:00Z", ["model/neck.py"], contains=[refit])
    pick = latest.pick(main, [stale, merged, behind])
    assert (
        pick["Mechanism"]["label"] == "PR #1030 1030000 2026-11-26 pass; passed over PR #1064 (without main's efed70a)"
    )
    assert pick["Skeleton"]["name"] == "main"


def test_mains_newest_commit_touching_a_layer_is_read_from_its_log():
    log = "@c2\n\ndocs/adr/0025.md\nmodel/skeleton/fit.py\n@c1\n\nmodel/neck.py\nmodel/skeleton/budget.py\n"
    assert latest.changed(log) == {"Skeleton": "c2", "Mechanism": "c1"}


def test_a_head_contains_a_commit_that_is_its_ancestor_by_git(tmp_path, monkeypatch):
    """A real repo: main's change lands after a branch left main, so the branch has its base and lacks the change."""

    def git(*args):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=tmp_path, check=True)
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True).stdout.strip()

    git("init", "-q", "-b", "main")
    base = git("commit", "-q", "--allow-empty", "-m", "base")
    git("checkout", "-q", "-b", "behind")
    head = git("commit", "-q", "--allow-empty", "-m", "the PR's push")
    git("checkout", "-q", "main")
    change = git("commit", "-q", "--allow-empty", "-m", "main changes the layer")
    monkeypatch.setattr(latest.stages, "REPO", str(tmp_path))
    assert latest.within(base, head) and not latest.within(change, head)
    with pytest.raises(subprocess.CalledProcessError):
        latest.within("0" * 40, head)  # a commit git lacks is an error, never a "no"


def test_a_pr_touching_two_layers_counts_for_both_and_the_skin_is_both_its_collections():
    both = pr(976, "2026-11-20T11:00:00Z", ["model/skeleton/fit.py", "model/printed/skin.py"])
    pick = latest.pick(MAIN, [both])
    assert {k for k, c in pick.items() if c["name"] == "PR #976"} == {"Skeleton", "Skin reference", "Skin Shells"}
    assert pick["Mechanism"]["name"] == "main"


def test_the_shells_candidate_is_one_that_changes_what_cuts_them_not_the_reviews_code():
    """#850: the Shells are cut by model/morty along skin.py's cuts on contours.json, and the reference is placed and
    cut by the same; model/review assembles the reference alone, so a PR that edits only it never takes the Shells'
    layer with what its older base cut (#1032's hand-drawn Shells)."""
    both = {"Skin reference", "Skin Shells"}
    assert latest.layers("model/morty/shells.py") == latest.layers("model/contours.json") == both
    assert latest.layers("model/skin.py") == latest.layers("model/printed/test_skin.py") == both
    assert (
        latest.layers("model/review/test_review.py") == latest.layers("model/review/blender.py") == {"Skin reference"}
    )


def test_a_candidates_cut_shells_are_listed_with_their_filaments_colour_and_none_where_it_cut_none(tmp_path):
    """Each Shell a candidate's own `just ours` cut from the Sculpt, by its STL, in its Colour group's filament (the
    review's Preset); a commit from before the Sculpt's Shells lists none."""
    assert latest.shells(str(tmp_path)) == []
    ours = tmp_path / "model/build/ours"
    ours.mkdir(parents=True)
    for name in ("morty hair", "morty shirt", "gimbal frame"):
        (ours / f"{name}.stl").write_bytes(b"")
    palette = g.THEMES["Skin palette"]["default"]  # Cansin's owned filaments, the review's
    assert latest.shells(str(tmp_path)) == [
        ["morty hair", str(ours / "morty hair.stl"), palette["hair"][3]],
        ["morty shirt", str(ours / "morty shirt.stl"), palette["clothes"][3]],
    ]


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
        "colour": {o.name: [round(x, 3) for x in o.color] for o in meshes},
        "hidden": bpy.context.view_layer.layer_collection.children[c.name].hide_viewport,
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
    # the candidate's own cut Shell, in the head's frame as cut, shown though its assemble failed
    hair = tmp_path / "morty hair.stl"
    trimesh.creation.box((2, 2, 2)).apply_translation((0, 0, 50)).export(hair)
    layers["Skin Shells"] |= {"shells": [["morty hair", str(hair), "#F7CED7"]]}
    (tmp_path / "latest.json").write_text(json.dumps({"layers": layers, "alpha": review.ALPHA["Skin"]}))
    out = str(tmp_path / "latest.blend")
    review._blender(["-P", latest.SCRIPT, "--", str(tmp_path / "latest.json"), out])
    got = inspect(out)["layers"]
    assert got["Mechanism"]["at"] == {"Cube": pytest.approx([10, 0, 0])}
    assert got["Mechanism"]["label"] == label and got["Mechanism"]["name"] == f"Mechanism: {label}"
    assert got["Skin reference"]["meshes"] == 0 and "no Morty reference" in got["Skin reference"]["label"]
    assert got["Skeleton"]["reason"] == "export.py failed: boom"
    assert got["Skin Shells"]["at"] == {"morty hair": pytest.approx([0, 0, 0])} and got["Skin Shells"]["meshes"] == 1
    # #F7CED7 as scene-linear, not as typed: (247, 206, 215) / 255 through sRGB's curve
    assert got["Skin Shells"]["colour"] == {
        "morty hair": pytest.approx([0.930, 0.617, 0.680, review.ALPHA["Skin"]], abs=2e-3)
    }
    assert got["Skin Shells"]["reason"] == "export.py failed: boom"  # the caps are missing, and the label says why
    # the private reference shares the Shells' surface: a toggle, off when the file opens
    assert [k for k, c in got.items() if c["hidden"]] == ["Skin reference"]


def test_a_fork_or_an_outside_authors_pr_is_never_picked_its_code_never_runs_here():
    """Only a branch of this repo by a member or a trusted bot: anyone can open a PR on a public repo."""
    fork = pr(1, "2026-11-22T00:00:00Z", ["model/gimbal.py"]) | {"fork": True}
    outside = pr(2, "2026-11-22T00:00:00Z", ["model/skeleton/fit.py"]) | {"author": "someone", "association": "NONE"}
    assert {c["name"] for c in latest.pick(MAIN, [fork, outside]).values()} == {"main"}
    bot = pr(3, "2026-11-22T00:00:00Z", ["model/skin.py"]) | {"author": "dependabot", "association": "CONTRIBUTOR"}
    assert latest.pick(MAIN, [bot])["Skin Shells"]["name"] == "PR #3"
