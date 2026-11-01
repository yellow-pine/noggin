"""Seam: `python -m model.stale` (`make sim-if-stale`, CI on PRs), checked on a copy of the repo."""

import os
import shutil

from model import stale
from model.engine import stages


def test_stale_follows_the_inputs(tmp_path, monkeypatch):
    for d in ("model", "eyes"):
        shutil.copytree(
            os.path.join(stages.REPO, d), tmp_path / d, ignore=shutil.ignore_patterns("build", "__pycache__")
        )
    monkeypatch.setattr(stages, "REPO", str(tmp_path))
    assert stale.stale() == []
    lid = tmp_path / "model/printed/lid.py"
    lid.write_text(lid.read_text() + "\n")
    assert stale.stale() == sorted(stages.DOCS)
    lid.write_text(lid.read_text()[:-1])
    assert stale.stale() == []
    os.remove(tmp_path / "model/reports/noggin-mouth-sim.json")
    assert stale.stale() == ["noggin-mouth"]
    os.remove(tmp_path / "model/reports/noggin-eyes.xml")
    assert stale.stale() == ["noggin-eyes", "noggin-mouth"]
