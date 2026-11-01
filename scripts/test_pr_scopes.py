"""pr_scopes.py: the PR Title check's scopes are the repo's areas, its top-level directories as git tracks them."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("pr_scopes.py")


def scopes(repo: Path) -> list[str]:
    return subprocess.run(
        [sys.executable, SCRIPT], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.splitlines()


def test_each_tracked_top_level_directory_is_a_scope_and_the_ci_and_site_folders_take_their_names(tmp_path):
    tracked = ("eyes/eyes.py", "web/viewer.mjs", ".github/workflows/x.yml", "overrides/x.html", ".claude/x", "README")
    for f in tracked:
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / f).write_text("")
    (tmp_path / "untracked").mkdir()
    (tmp_path / "untracked/x").write_text("")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", ":!untracked"], cwd=tmp_path, check=True)
    assert scopes(tmp_path) == ["ci", "eyes", "site", "web"]


def test_this_repo_has_its_areas_as_scopes():
    assert {"ci", "docs", "eyes", "mech", "model", "noggin", "reactions", "scripts", "site", "web"} <= set(
        scopes(SCRIPT.parent.parent)
    )
