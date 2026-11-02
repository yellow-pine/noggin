"""Seam: `make model-shards-list`, Code Checks' model matrix (#305, #474): three shards balanced on the measured
durations (model/durations.json), every unit (the hero's sweep, each document, the rest, make sim) on one, from the
code."""

import json
import shlex
import subprocess
import sys

import yaml

from model import shards, stages

TESTS = """import pytest
@pytest.mark.parametrize("doc", {docs!r})
def test_by_document(doc): pass
@pytest.mark.parametrize("name", ["mouth", "stage1"])  # a short name is not a document id
def test_else(name): pass
"""


def listed():
    out = subprocess.run(
        ["make", "-s", "model-shards-list"], cwd=stages.REPO, capture_output=True, text=True, check=True
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


def test_three_shards_hold_every_unit_once():
    units = [u for s in listed() for u in s["units"]]
    assert len(listed()) == shards.N == 3
    assert sorted(units) == sorted(["hero", *(d.removeprefix("noggin-") for d in stages.DOCS), "rest", "sim"])
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


def test_tests_count_under_the_unit_that_picks_them_and_an_unmeasured_unit_weighs_the_mean():
    took = shards.seconds(
        {"model/test_mjcf.py::test_x[noggin-eyes]": 4, "model/render/test_hero.py::test_y[3]": 2, "make sim": 6}
    )
    assert (took["eyes"], took["hero"], took["sim"]) == (4, 2, 6)
    assert took["stage1"] == took["rest"] == 4  # the mean of the measured units


def test_the_model_matrix_is_the_shards_job_s_list():
    """A new document or Stage needs no workflow edit."""
    jobs = yaml.safe_load(open(f"{stages.REPO}/.github/workflows/check.yml"))["jobs"]
    assert "make -s model-shards-list" in jobs["shards"]["steps"][-1]["run"]
    assert jobs["model-shard"]["strategy"]["matrix"] == {"include": "${{ fromJSON(needs.shards.outputs.list) }}"}
    assert "shards" in jobs["model-shard"]["needs"]
