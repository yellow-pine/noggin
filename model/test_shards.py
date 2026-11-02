"""Seam: `make model-shards-list`, Code Checks' model matrix (#305): every document's tests on one shard, from the code."""

import json
import shlex
import subprocess
import sys

import yaml

from model import geometry as g
from model import stages

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
    args = [a for a in shlex.split(tests) if not a.startswith("--ignore=")]
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--collect-only", "-q", *args],
        cwd=folder,
        capture_output=True,
        text=True,
    ).stdout
    return {line.split("::")[1] for line in out.splitlines() if "::" in line}


def test_the_shards_are_the_hero_the_sweeps_each_stage_the_rest_and_the_sim():
    names = [s["shard"] for s in listed()]
    assert names == ["hero", "sweeps", *(d.removeprefix("noggin-") for d in g.STAGES), "rest", "sim"]


def test_every_test_runs_on_exactly_one_shard(tmp_path):
    (tmp_path / "test_docs.py").write_text(TESTS.format(docs=sorted(stages.DOCS)))
    by_shard = {s["shard"]: collected(s["tests"], tmp_path) for s in listed() if s["shard"] not in ("hero", "sim")}
    everything = [t for ts in by_shard.values() for t in ts]
    assert sorted(everything) == sorted({*everything}), "a test on two shards"
    assert {*everything} == {f"test_by_document[{d}]" for d in stages.DOCS} | {"test_else[mouth]", "test_else[stage1]"}
    assert by_shard["sweeps"] == {f"test_by_document[{d}]" for d in stages.DOCS if d not in g.STAGES}
    assert by_shard["stage2"] == {"test_by_document[noggin-stage2]"}
    assert by_shard["rest"] == {"test_else[mouth]", "test_else[stage1]"}


def test_the_hero_shard_runs_the_hero_sweep_that_the_others_leave_out():
    by_shard = {s["shard"]: s.get("tests", "") for s in listed()}
    assert by_shard.pop("hero") == "model/render/test_hero.py"
    assert by_shard.pop("sim") == ""  # make sim, not make test
    assert all("--ignore=model/render/test_hero.py" in t for t in by_shard.values())


def test_the_model_matrix_is_the_shards_job_s_list():
    """A new document or Stage needs no workflow edit."""
    jobs = yaml.safe_load(open(f"{stages.REPO}/.github/workflows/check.yml"))["jobs"]
    assert "make -s model-shards-list" in jobs["shards"]["steps"][-1]["run"]
    assert jobs["model-shard"]["strategy"]["matrix"] == {"include": "${{ fromJSON(needs.shards.outputs.list) }}"}
    assert "shards" in jobs["model-shard"]["needs"]
