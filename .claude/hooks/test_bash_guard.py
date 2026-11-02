"""bash_guard.py, the project's PreToolUse hook on Bash: a banned command exits 2 with a one-line reason naming the
allowed alternative (Claude Code shows it to the agent and skips the call); anything else exits 0."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("bash_guard.py")
REPO = Path(__file__).parents[2]


def guard(command: str, cwd: Path = REPO, hook=("python3", SCRIPT), env=None) -> subprocess.CompletedProcess[str]:
    event = {"cwd": str(cwd), "hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}}
    # python3, as .claude/settings.json runs it (the Mac's is 3.9; ruff's py39 target holds its syntax there)
    return subprocess.run(list(hook), input=json.dumps(event), capture_output=True, text=True, env=env)


@pytest.mark.parametrize(
    ("command", "alternative"),
    [
        ("git stash", "commit"),
        ("cd ../wt && git stash push -m wip", "commit"),
        ("git -C ../wt stash pop", "commit"),
        ("until ! pgrep -f 'just sim'; do sleep 5; done", "Waiting on CI"),
        ("while pgrep -f blender >/dev/null; do sleep 5; done", "Waiting on CI"),
        ("gh pr merge 12 --admin --squash", "--auto --squash"),
        ("just sim", "CI"),
        ("uv run just render", "CI"),
        ("cd ../wt && just hero", "CI"),
        ("just lint test", "CI"),
        ("just check", "CI"),
        ("until grep -q done out.txt; do :; done", "Waiting on CI"),
        ("until [ -f out ]\ndo\n  true\ndone", "sleep"),
        ("# rebuild the pictures\njust render", "CI"),
        ("just lint  # quick\njust sim", "CI"),
        ("just BLENDER=/opt/blender pictures hero", "CI"),
        ("nohup just sim > log 2>&1 &", "CI"),
        ("timeout 900 just hero", "CI"),
        ("gh -R yellow-pine/noggin pr merge 12 --admin", "--auto --squash"),
        ("for i in 1 2; do until [ -f out ]; do :; done; done", "sleep"),
        ("until [ -f out ]; do :; done; sleep 1", "sleep"),
        ('until [ -z "$(pgrep -f just)" ]; do sleep 5; done', "Waiting on CI"),
        ("bash <<'EOF'\njust sim\nEOF", "CI"),
        ("python3 - <<EOF\nimport os\nEOF\nbash <<'EOF'\ngit stash\nEOF", "commit"),
        ("cat <<EOF\nok\nEOF\nbash <<X\ngit stash\nX", "commit"),
        ("echo '<<EOF'\ngit stash\nEOF", "commit"),
        ("bash -c 'git stash'", "commit"),
        ('sh -c "cd .. && just render"', "CI"),
        ("eval git stash", "commit"),
        ('echo "$(git stash)"', "commit"),
        ("echo `just sim`", "CI"),
        ("x=$(git stash pop)", "commit"),
        ("gh api -X PUT repos/yellow-pine/noggin/pulls/12/merge", "--auto --squash"),
        ("gh api graphql -f query='mutation { mergePullRequest(input: {}) { clientMutationId } }'", "--auto --squash"),
        ("git -c alias.s=stash s", "alias"),
        ("git config alias.s stash", "alias"),
        ("git -c core.pager=less -c Alias.s=stash s", "alias"),
        ("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.s GIT_CONFIG_VALUE_0=stash git s", "GIT_CONFIG"),
        ("/bin/bash -lc 'just sim'", "CI"),
        ("echo 'git stash' | sh", "pipe"),
        ("gh api graphql -F query=@merge.graphql", "inline"),
        ("echo 'unbalanced", "parse"),
        ("bash <<EOF\necho don't\nEOF", "parse"),
    ],
)
def test_a_banned_command_is_blocked_with_its_alternative(command, alternative):
    result = guard(command)
    assert result.returncode == 2
    assert len(result.stderr.strip().splitlines()) == 1
    assert alternative in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "git status && git commit -m 'no git stash here'",
        "gh pr merge 12 --auto --squash",
        "gh pr create --body 'never gh pr merge --admin'",
        "just lint",
        "just check-light",
        "just mpy-list",
        "until gh pr checks 12 >/dev/null; [ $? != 8 ]; do sleep 60; done",
        "while read -r f; do echo $f; done < files",
        "pgrep -f noggin",
        "cat > notes.md <<'EOF'\ndon't run just sim or git stash here\nEOF",
        "git commit -q -F - <<EOF\nit's done\nEOF",
        "tee out.txt <<< 'git stash'",
        "gh api repos/yellow-pine/noggin/pulls/12/reviews",
        "just lint > sim.log",
        "gh pr list --json number | jq length",
        "gh pr create --body-file - <<'EOF'\njust sim runs in CI\nuntil now nothing blocked git stash\nEOF",
        "git commit -F - <<EOF\nuntil now\nEOF\ngit push",
        "until [ -f out ]; do /bin/sleep 5; done",
        "cat <<< 'until x'",
    ],
)
def test_anything_else_runs(command):
    result = guard(command)
    assert result.returncode == 0, result.stderr


def test_the_heavy_recipes_are_the_justfiles_heavy_group(tmp_path):
    (tmp_path / "justfile").write_text("lint:\n    true\n\n[group('heavy')]\nsim *docs: lint\n    true\n")
    assert guard("just lint", tmp_path).returncode == 0
    assert "just check-light" in guard("just sim noggin-eyes", tmp_path).stderr
    assert guard("just sim", REPO / "docs").returncode == 2  # just finds the justfile above the folder, as it runs it


@pytest.fixture
def without_just(tmp_path):
    """A copy of the hook in a checkout with no .venv, run with no just on the PATH."""
    hooks = tmp_path / "checkout/.claude/hooks"
    hooks.mkdir(parents=True)
    shutil.copy(SCRIPT, hooks)
    python3 = shutil.which("python3")
    return lambda command, cwd: guard(command, cwd, [python3, hooks / SCRIPT.name], {"PATH": str(tmp_path)})


def test_without_just_the_heavy_recipes_come_from_the_justfile(tmp_path, without_just):
    (tmp_path / "justfile").write_text(
        "lint:\n    true\n\n# simulate\n[group('heavy')]\n[private]\nsim *docs: lint\n    true\n\n"
        '[no-cd, group: "heavy"]\n@hero:\n    true\n'
    )
    (tmp_path / "docs").mkdir()
    assert without_just("just lint", tmp_path).returncode == 0
    assert "just check-light" in without_just("just sim noggin-eyes", tmp_path).stderr
    assert without_just("just hero", tmp_path / "docs").returncode == 2  # the justfile above, as just finds it


def test_without_just_or_a_justfile_just_is_blocked(tmp_path, without_just):
    result = without_just("just lint", tmp_path)
    assert result.returncode == 2
    assert "heavy recipes" in result.stderr


def test_every_recipe_under_the_heavy_lock_is_in_the_heavy_group():
    """The guard reads the group, so a recipe that takes the lock (HEAVY, scripts/heavy.py) must be in it."""
    dump = subprocess.run([REPO / ".venv/bin/just", "--dump", "--dump-format", "json"], cwd=REPO, capture_output=True)
    recipes = json.loads(dump.stdout)["recipes"].values()
    locked = {r["name"] for r in recipes if '["variable", "HEAVY"]' in json.dumps(r["body"])}
    heavy = {r["name"] for r in recipes if {"group": "heavy"} in r["attributes"]}
    assert locked and locked <= heavy


def test_without_just_the_guard_reads_our_justfile_as_just_does(without_just):
    dump = subprocess.run([REPO / ".venv/bin/just", "--dump", "--dump-format", "json"], cwd=REPO, capture_output=True)
    recipes = json.loads(dump.stdout)["recipes"].values()
    heavy = [r["name"] for r in recipes if {"group": "heavy"} in r["attributes"]]
    light = [r["name"] for r in recipes if r["name"] not in heavy]
    assert without_just("just " + " ".join(light), REPO).returncode == 0
    assert all(without_just(f"just {name}", REPO).returncode == 2 for name in heavy)


def test_a_hook_that_cannot_read_its_input_blocks():
    result = subprocess.run(["python3", SCRIPT], input="not json", capture_output=True, text=True)
    assert result.returncode == 2
    assert "bash_guard.py failed" in result.stderr
