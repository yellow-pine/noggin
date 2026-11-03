"""Seam: `just model-shards-list`, Checks' model matrix (#305, #474, #496): eight shards (#839) balanced on the measured
durations (model/durations.json), every unit (each document, the rest, just sim's parts, just mech) on one, from the code;
and renders(), the Render shards' pictures by their measured Blender seconds (#839)."""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

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


def test_eight_shards_hold_every_unit_once():
    units = [u for s in listed() for u in s["units"]]
    assert len(listed()) == shards.N == 8
    assert sorted(units) == sorted([*stages.DOCS, "rest", *shards.SIM, "mech"])
    assert sorted(p for s in listed() for p in s["sim"].split()) == ["0/3", "1/3", "2/3"]
    assert [s["shard"] for s in listed()] == [" ".join(s["units"]) for s in listed()]


def test_every_test_runs_on_exactly_one_shard(tmp_path):
    (tmp_path / "test_docs.py").write_text(TESTS.format(docs=sorted(stages.DOCS)))
    by_shard = {s["shard"]: collected(s["tests"], tmp_path) for s in listed()}
    everything = [t for ts in by_shard.values() for t in ts]
    assert sorted(everything) == sorted({*everything}), "a test on two shards"
    assert {*everything} == {f"test_by_document[{d}]" for d in stages.DOCS} | {"test_else[mouth]", "test_else[stage1]"}


def test_the_shards_balance_the_measured_seconds():
    """Longest first onto the lightest shard: the heaviest is over the lightest by no more than the largest unit."""
    took = shards.seconds(json.load(open(shards.DURATIONS)))
    loads = [sum(took[u] for u in s["units"]) for s in listed()]
    assert max(loads) - min(loads) <= max(took.values())


def test_a_pr_touching_only_the_mech_runs_one_shard_of_make_mech_and_one_touching_neither_none():
    """MODEL and MECH are the Changes job's filters: "false" leaves that group's units out (#496)."""
    assert listed(MODEL="false") == [{"shard": "mech", "units": ["mech"], "tests": "", "sim": ""}]
    assert "mech" not in [u for s in listed(MECH="false") for u in s["units"]]
    assert not [s for s in listed(SIM="false") if s["sim"]]  # its reports cached (#809)
    assert listed(MODEL="false", MECH="false") == []


def test_tests_count_under_the_unit_that_picks_them_and_an_unmeasured_unit_weighs_the_mean():
    doc = next(iter(stages.DOCS))
    took = shards.seconds({f"model/test_mjcf.py::test_x[{doc}]": 4, "just sim 0/3": 6, "just mech": 8})
    assert (took[doc], took["sim 0/3"], took["mech"]) == (4, 6, 8)
    assert took["rest"] == took["sim 1/3"] == 6  # the mean of the measured units


def test_a_picture_s_render_seconds_weigh_it_alone_and_an_unmeasured_picture_the_mean():
    """#839: Render's units are its pictures, each by the Blender seconds CI measured (`render <picture>`), none of them
    a model unit's."""
    doc = next(iter(stages.DOCS))
    durations = {f"render {doc}-side.webp": 3, "render b.webp": 5, f"model/test_x.py::test_y[{doc}]": 2}
    assert shards.seconds(durations)[doc] == 2
    assert shards.renders(durations, [f"{doc}-side.webp", "b.webp", "c.webp"]) == {
        f"{doc}-side.webp": 3,
        "b.webp": 5,
        "c.webp": 4,
    }


def test_deal_puts_each_unit_longest_first_on_the_lightest_load():
    """A worked example: three long units and four short."""
    weight = {"long": 92, "mid": 56, "short": 50, "a": 1, "b": 1, "c": 1, "d": 1}
    assert shards.deal(weight, 3) == [["long"], ["mid"], ["short", "a", "b", "c", "d"]]


def test_the_model_matrix_is_the_changes_job_s_list():
    """A new document needs no workflow edit."""
    jobs = yaml.safe_load(open(f"{stages.REPO}/.github/workflows/checks.yml"))["jobs"]
    (lists,) = [s for s in jobs["changes"]["steps"] if s.get("id") == "lists"]
    assert "just model-shards-list" in lists["run"]
    assert jobs["model"]["strategy"]["matrix"] == {"include": "${{ fromJSON(needs.changes.outputs.shards) }}"}
