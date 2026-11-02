"""required_checks.py: a required check main's ruleset names must be a gate job (one without a matrix) in
.github/workflows, or the Code job fails (#450, #570)."""

import subprocess
import sys
from pathlib import Path

from scripts.required_checks import stale

SCRIPT = Path(__file__).with_name("required_checks.py")


def workflows(tmp_path: Path) -> Path:
    (tmp_path / "check.yml").write_text(
        "jobs:\n  code:\n    name: Code\n"
        "  model:\n    name: Model (${{ matrix.shard }})\n    strategy:\n      matrix:\n        shard: [hero]\n"
        "  site:\n    name: Site\n    strategy:\n      matrix:\n        os: [linux]\n"
    )
    (tmp_path / "review.yml").write_text("jobs:\n  review:\n    name: Review\n  unnamed: {}\n")
    return tmp_path


def test_a_required_check_no_job_names_is_stale(tmp_path):
    """A job without a name reports its id, as GitHub does."""
    assert stale(["Code", "Review", "unnamed", "Lint"], workflows(tmp_path)) == ["Lint"]


def test_a_required_check_naming_a_matrix_job_is_stale(tmp_path):
    """Required checks name only gate jobs (#570): a matrix job fails by its name, its expansion or its id."""
    required = ["Code", "Model (hero)", "Model (${{ matrix.shard }})", "Site", "Site (linux)", "model"]
    assert stale(required, workflows(tmp_path)) == required[1:]


def run(tmp_path: Path, required: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, SCRIPT, workflows(tmp_path)], input=required, capture_output=True, text=True)


def test_the_script_fails_on_a_stale_check_and_names_it(tmp_path):
    failed = run(tmp_path, "Code\nLint\n")
    assert failed.returncode == 1
    assert "Lint" in failed.stdout and "Code" not in failed.stdout
    assert run(tmp_path, "Code\nReview\n").returncode == 0
