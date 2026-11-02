"""lock_hash.py: uv.lock's hash without the project's own version, so a release's bump (release-please writes it into
uv.lock) keeps every cache keyed on the lock warm (#403), while any other change to the lock still moves it."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("lock_hash.py")
LOCK = """version = 1

[[package]]
name = "noggin"
version = "{own}"
source = {{ virtual = "." }}
dependencies = [{{ name = "numpy" }}]

[[package]]
name = "numpy"
version = "{numpy}"
"""


def lock_hash(tmp_path: Path, own: str = "0.1.1", numpy: str = "2.3.0") -> str:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "noggin"\nversion = "x"\n')
    (tmp_path / "uv.lock").write_text(LOCK.format(own=own, numpy=numpy))
    out = subprocess.run([sys.executable, SCRIPT], cwd=tmp_path, capture_output=True, text=True, check=True).stdout
    assert len(out.strip()) == 64  # a sha256
    return out


def test_a_version_bump_keeps_the_hash(tmp_path):
    assert lock_hash(tmp_path, own="0.1.1") == lock_hash(tmp_path, own="0.2.0")


def test_a_dependency_change_moves_the_hash(tmp_path):
    assert lock_hash(tmp_path, numpy="2.3.0") != lock_hash(tmp_path, numpy="2.3.1")


def test_a_lock_without_the_project_fails(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "noggin"\n')
    (tmp_path / "uv.lock").write_text('version = 1\n\n[[package]]\nname = "numpy"\nversion = "2.3.0"\n')
    assert subprocess.run([sys.executable, SCRIPT], cwd=tmp_path, capture_output=True).returncode != 0
