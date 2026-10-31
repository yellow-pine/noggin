"""Seam: `python -m model.stale` (`make sim-if-stale`, CI on PRs), checked on a copy of the repo."""

import json
import os
import shutil

import pytest

from model import stale
from model.engine import stages


def sources(doc):
    return json.load(open(os.path.join(stages.REPO, "model", "reports", f"{doc}-sim.json")))["inputs"]["sources"]


def test_stale_follows_the_inputs_and_the_meshes_as_built_now(tmp_path, monkeypatch):
    repo = stages.REPO
    meshes = {s for doc in stages.DOCS for s in sources(doc)}
    if not all(os.path.isfile(os.path.join(stages.REPO, s)) for s in meshes):
        pytest.skip("the meshes the reports were simulated on are not built (make ours)")
    for d in ("model", "eyes"):
        shutil.copytree(
            os.path.join(stages.REPO, d), tmp_path / d, ignore=shutil.ignore_patterns("build", "__pycache__")
        )
    for s in meshes:
        os.makedirs(tmp_path / os.path.dirname(s), exist_ok=True)
        shutil.copy(os.path.join(stages.REPO, s), tmp_path / s)
    monkeypatch.setattr(stages, "REPO", str(tmp_path))
    assert stale.stale() == []
    jaw = tmp_path / "model/build/ours/top jaw.stl"
    jaw.write_bytes(jaw.read_bytes() + b"\n")
    assert stale.stale() == ["noggin-mouth", "noggin-stage3"]
    jaw.write_bytes(jaw.read_bytes()[:-1])
    assert stale.stale() == []
    os.remove(jaw)
    assert stale.stale() == ["noggin-mouth", "noggin-stage3"]
    shutil.copy(os.path.join(repo, "model/build/ours/top jaw.stl"), jaw)
    with open(tmp_path / "eyes/calibration.json", "a") as f:
        f.write(" ")
    assert stale.stale() == sorted(stages.DOCS)
