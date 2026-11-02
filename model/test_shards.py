"""Seams: `just model-shards-list`, Checks' model matrix (#305, #474, #496): four shards balanced on the measured
durations (model/durations.json), every unit (the hero's sweep, each document, the rest, just sim, just mech) on one,
from the code; and `just blender-bins`, Checks' Blender matrix: the cold Blender units packed longest first into bins
no longer than the longest."""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

from model import geometry as g
from model import shards, stages

TESTS = """import pytest
@pytest.mark.parametrize("doc", {docs!r})
def test_by_document(doc): pass
@pytest.mark.parametrize("name", ["mouth", "stage1"])  # a short name is not a document id
def test_else(name): pass
"""


def listed(recipe="model-shards-list", **env):
    out = subprocess.run(
        [Path(sys.executable).with_name("just"), recipe],
        cwd=stages.REPO,
        capture_output=True,
        text=True,
        check=True,
        env=os.environ | env,
    )
    return json.loads(out.stdout)


def collected(tests, folder):
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--collect-only", "-q", *shlex.split(tests)],
        cwd=folder,
        capture_output=True,
        text=True,
    ).stdout
    return {line.split("::")[1] for line in out.splitlines() if "::" in line} if tests else set()


def test_four_shards_hold_every_unit_once():
    units = [u for s in listed() for u in s["units"]]
    assert len(listed()) == shards.N == 4
    assert sorted(units) == sorted(["hero", *(d.removeprefix("noggin-") for d in stages.DOCS), "rest", "sim", "mech"])
    assert [s["shard"] for s in listed()] == [" ".join(s["units"]) for s in listed()]


def test_every_test_runs_on_exactly_one_shard(tmp_path):
    (tmp_path / "test_docs.py").write_text(TESTS.format(docs=sorted(stages.DOCS)))
    (tmp_path / "test_hero.py").write_text("def test_sweep(): pass\n")
    by_shard = {s["shard"]: collected(s["tests"], tmp_path) for s in listed()}
    everything = [t for ts in by_shard.values() for t in ts]
    assert sorted(everything) == sorted({*everything}), "a test on two shards"
    assert {*everything} == {f"test_by_document[{d}]" for d in stages.DOCS} | {
        "test_else[mouth]",
        "test_else[stage1]",
        "test_sweep",
    }
    hero = next(s["shard"] for s in listed() if "hero" in s["units"])
    assert "test_sweep" in by_shard[hero]


def test_the_shards_balance_the_measured_seconds():
    """Longest first onto the lightest shard: the heaviest is over the lightest by no more than the largest unit."""
    took = shards.seconds(json.load(open(shards.DURATIONS)))
    loads = [sum(took[u] for u in s["units"]) for s in listed()]
    assert max(loads) - min(loads) <= max(took.values())


def test_a_pr_touching_only_the_mech_runs_one_shard_of_make_mech_and_one_touching_neither_none():
    """MODEL and MECH are the Changes job's filters: "false" leaves that group's units out (#496)."""
    assert listed(MODEL="false") == [{"shard": "mech", "units": ["mech"], "tests": ""}]
    assert "mech" not in [u for s in listed(MECH="false") for u in s["units"]]
    assert listed(MODEL="false", MECH="false") == []


def test_tests_count_under_the_unit_that_picks_them_and_an_unmeasured_unit_weighs_the_mean():
    took = shards.seconds(
        {
            "model/test_mjcf.py::test_x[noggin-eyes]": 4,
            "model/render/test_hero.py::test_y[3]": 2,
            "just sim": 6,
            "just mech": 8,
        }
    )
    assert (took["eyes"], took["hero"], took["sim"], took["mech"]) == (4, 2, 6, 8)
    assert took["stage1"] == took["rest"] == 5  # the mean of the measured units


def test_the_blender_units_pack_longest_first_into_bins_no_longer_than_the_longest():
    """hero 190 s, viewer 71, views 53 (run 41388039993): views and the viewer share a runner beside the hero's (#496)."""
    assert shards.packed({"hero": 190, "viewer": 71, "views": 53}) == [["hero"], ["viewer", "views"]]
    assert shards.packed({"a": 5, "b": 3, "c": 3, "d": 2}) == [["a"], ["b", "d"], ["c"]]
    assert shards.packed({}) == []


def test_the_blender_bins_are_the_cold_units_with_the_stages_they_bake():
    """PICTURES and VIEWER say whether the pictures and the viewer are cold: each motion of the pictures (the hero in
    its frame shards), the viewer, each in one bin; a bin with the viewer bakes every Stage (TRAJ_DOCS empty), as just
    web does. images: the bin puts site pictures in model/build/images; frames: it holds a hero shard, whose frames
    Hero joins."""
    from model.render import pictures

    def motion(u):
        return u.split(":")[0]

    every = listed("blender-bins")
    units = [u for b in every for u in b["bin"].split()]
    assert sorted({motion(u) for u in units}) == sorted([*pictures.SITE, "viewer"])
    stages_of = {m["motion"]: m["stages"].split() for m in pictures.motions()}
    for b in every:
        assert b["motions"] == " ".join(u for u in b["bin"].split() if motion(u) in pictures.SITE)
        assert b["viewer"] == ("viewer" in b["bin"].split())
        assert b["images"] == any(m in pictures.SITE for m in b["motions"].split())
        assert b["frames"] == any(m not in pictures.SITE for m in b["motions"].split())
        assert b["stages"] == (
            "" if b["viewer"] else " ".join(sorted({s for m in b["motions"].split() for s in stages_of[motion(m)]}))
        )
    assert [b["bin"] for b in listed("blender-bins", PICTURES="false")] == ["viewer"]
    assert sorted({motion(m) for b in listed("blender-bins", VIEWER="false") for m in b["motions"].split()}) == sorted(
        pictures.SITE
    )
    assert listed("blender-bins", PICTURES="false", VIEWER="false") == []


def test_the_hero_s_frames_split_into_ranges_of_about_a_minute_each():
    """#537: as many contiguous ranges as make each about SHARD_SECONDS of render, every frame in one, at least one."""
    assert shards.frame_ranges(64, 1.96) == [(0, 32), (32, 64)]  # 125 s: two of ~63 s
    assert shards.frame_ranges(64, 3.0) == [(0, 21), (21, 42), (42, 64)]  # 192 s: three
    assert shards.frame_ranges(64, 0.5) == [(0, 64)]  # 32 s: one
    assert shards.frame_ranges(5, 60) == [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]


def test_main_renders_the_hero_in_frame_shards_that_hold_every_frame_once():
    """Each shard a bin's motion `hero:<first>-<end>`, together every frame the hero renders, its Stage's trajectory
    baked; each pays the hero's setup, so a shard weighs that plus its frames' seconds."""
    from model.render import pictures

    took = json.load(open(shards.DURATIONS))
    ranges = [m for b in listed("blender-bins") for m in b["motions"].split() if m.startswith("hero:")]
    frames = sorted(f for r in ranges for f in range(*map(int, r.removeprefix("hero:").split("-"))))
    assert frames == list(range(pictures.hero_frames()))
    assert ranges == [f"hero:{a}-{b}" for a, b in shards.frame_ranges(len(frames), took["blender hero frame"])]
    assert all(b["stages"] in ("", "noggin-stage3") for b in listed("blender-bins") if b["motions"].startswith("hero:"))


def test_a_pr_s_bins_render_the_preview_panel_in_place_of_the_site_s_pictures():
    """PREVIEW=true (a PR, #562): one panel of the site's, at its framing, so it bakes every Stage as views does; main
    alone renders SITE."""
    from model.render import pictures

    assert set(pictures.MOTIONS["preview"]) < set(pictures.SITE["views"])
    every = listed("blender-bins", PREVIEW="true")
    assert sorted(u for b in every for u in b["bin"].split()) == ["preview", "viewer"]
    (preview,) = [b for b in every if b["motions"]]
    assert preview["motions"] == "preview"
    assert preview["stages"] in ("", " ".join(sorted(g.STAGES)))  # empty beside the viewer: it bakes them all
    assert listed("blender-bins", PREVIEW="true", PICTURES="false") == listed("blender-bins", PICTURES="false")


def test_the_model_matrix_is_the_changes_job_s_list():
    """A new document needs no workflow edit (CI runs no Blender bin since #640, docs/adr/0018)."""
    jobs = yaml.safe_load(open(f"{stages.REPO}/.github/workflows/checks.yml"))["jobs"]
    (lists,) = [s for s in jobs["changes"]["steps"] if s.get("id") == "lists"]
    assert "just model-shards-list" in lists["run"]
    assert jobs["model"]["strategy"]["matrix"] == {"include": "${{ fromJSON(needs.changes.outputs.shards) }}"}


def test_the_bins_weigh_main_s_measured_seconds_over_the_typed_ones(tmp_path, monkeypatch):
    """#569: Changes downloads the seconds main's last rendering run measured (MEASURED, a file a bin); a key two bins
    measured (the hero's shards) weighs the slower, and a unit none measured keeps model/durations.json's typed one."""
    (tmp_path / "blender-seconds-0").mkdir()
    (tmp_path / "blender-seconds-0" / "seconds.json").write_text(
        '{"blender hero frame": 2.5, "blender hero setup": 30}'
    )
    (tmp_path / "blender-seconds-1").mkdir()
    (tmp_path / "blender-seconds-1" / "seconds.json").write_text('{"blender hero frame": 3.0, "blender viewer": 400}')
    monkeypatch.setattr(shards, "MEASURED", str(tmp_path))

    def heroes():
        return sorted(
            (m for b in shards.blender() for m in b["motions"].split() if m.startswith("hero:")),
            key=lambda m: int(m[5:].split("-")[0]),
        )

    assert heroes() == ["hero:0-21", "hero:21-42", "hero:42-64"]  # 64 frames at 3.0 s: three of ~64 s
    assert shards.blender()[0]["bin"] == "viewer"  # 400 s, the longest: a runner of its own
    monkeypatch.setattr(shards, "MEASURED", str(tmp_path / "none"))
    assert heroes() == ["hero:0-32", "hero:32-64"]  # the typed 1.96 s a frame
