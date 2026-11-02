"""workflow_table.py: the README's CI/CD table is derived from .github/workflows (#397, docs/adr/0011), and the README
holds what it derives now (cog --check, docs/adr/0009)."""

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.workflow_table import table

ROOT = Path(__file__).resolve().parent.parent

WORKFLOW = """name: Site Checks
# Builds the site
# (the rest of the header says how)
on:
  push:
    branches: [main]
  pull_request:
    types: [opened]
    paths: ["ci/*.Dockerfile"]
  workflow_run:
    workflows: [Code Checks]
    branches: [main]
  schedule:
    - cron: "0 6 * * 1"
  workflow_dispatch:
jobs:
  render:
    name: Render (${{ matrix.motion }})
  pictures:
    name: Pictures
  again:
    name: Render
"""


def test_a_row_reads_name_file_triggers_jobs_and_the_one_line_purpose(tmp_path):
    (tmp_path / "site-checks.yml").write_text(WORKFLOW)
    assert table(tmp_path).splitlines()[2] == (
        "| Site Checks | `site-checks.yml` | `push` (`main`), `pull_request` (paths: `ci/*.Dockerfile`),"
        " `workflow_run` (workflows: `Code Checks`; `main`), `schedule` (`0 6 * * 1`),"
        " `workflow_dispatch` | Render, Pictures | Builds the site |"
    )


def test_a_bare_trigger_reads_as_itself(tmp_path):
    (tmp_path / "a.yml").write_text("name: A\n# Does a\non: pull_request\njobs:\n  a:\n    name: A\n")
    assert table(tmp_path).splitlines()[2] == "| A | `a.yml` | `pull_request` | A | Does a |"
    (tmp_path / "a.yml").write_text("name: A\n# Does a\non: [push, pull_request]\njobs:\n  a:\n    name: A\n")
    assert table(tmp_path).splitlines()[2] == "| A | `a.yml` | `push`, `pull_request` | A | Does a |"


def test_a_workflow_without_its_purpose_line_fails(tmp_path):
    (tmp_path / "a.yml").write_text("name: A\non: pull_request\njobs: {}\n")
    with pytest.raises(ValueError, match="a.yml"):
        table(tmp_path)


def test_the_readme_holds_the_table_the_workflows_give():
    """Stale: `make readme` (CONTRIBUTING.md)."""
    run = subprocess.run([sys.executable, "-m", "cogapp", "--check", "README.md"], cwd=ROOT, capture_output=True)
    assert run.returncode == 0, run.stderr.decode()
