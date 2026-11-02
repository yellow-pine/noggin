"""required_checks.py: a required check main's ruleset names must be a job in .github/workflows, or the Code job fails
(#450)."""

import subprocess
import sys
from pathlib import Path

from scripts.required_checks import stale

SCRIPT = Path(__file__).with_name("required_checks.py")


def workflows(tmp_path: Path) -> Path:
    (tmp_path / "check.yml").write_text(
        "jobs:\n  code:\n    name: Code\n  model:\n    name: Model (${{ matrix.shard }})\n"
    )
    (tmp_path / "review.yml").write_text("jobs:\n  review:\n    name: Review\n  unnamed: {}\n")
    return tmp_path


def test_a_required_check_no_job_names_is_stale(tmp_path):
    """A job without a name reports its id, as GitHub does; a matrix job's expanded name isn't matched (shortcut)."""
    required = ["Code", "Review", "unnamed", "Lint", "Model (hero)"]
    assert stale(required, workflows(tmp_path)) == ["Lint", "Model (hero)"]


def test_the_script_fails_on_a_stale_check_and_names_it(tmp_path):
    run = subprocess.run(
        [sys.executable, SCRIPT, workflows(tmp_path)], input="Code\nLint\n", capture_output=True, text=True
    )
    assert run.returncode == 1
    assert "Lint" in run.stdout and "Code" not in run.stdout
    ok = subprocess.run(
        [sys.executable, SCRIPT, workflows(tmp_path)], input="Code\nReview\n", capture_output=True, text=True
    )
    assert ok.returncode == 0
