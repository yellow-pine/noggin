"""bash_guard.py, the project's PreToolUse hook on Bash: a banned command exits 2 with a one-line reason naming the
allowed alternative (Claude Code shows it to the agent and skips the call); anything else exits 0."""

import json
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("bash_guard.py")
REPO = Path(__file__).parents[2]


def guard(command: str, cwd: Path = REPO) -> subprocess.CompletedProcess[str]:
    event = {"cwd": str(cwd), "hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}}
    # python3, as .claude/settings.json runs it (the Mac's is 3.9; ruff's py39 target holds its syntax there)
    return subprocess.run(["python3", SCRIPT], input=json.dumps(event), capture_output=True, text=True)


@pytest.mark.parametrize(
    ("command", "alternative"),
    [
        ("git stash", "commit"),
        ("cd ../wt && git stash push -m wip", "commit"),
        ("git -C ../wt stash pop", "commit"),
        ("until ! pgrep -f 'make sim'; do sleep 5; done", "Waiting on CI"),
        ("while pgrep -f blender >/dev/null; do sleep 5; done", "Waiting on CI"),
        ("gh pr merge 12 --admin --squash", "--auto --squash"),
        ("make sim", "CI"),
        ("make -s render", "CI"),
        ("cd ../wt && make hero", "CI"),
        ("make lint test", "CI"),
        ("make check-all", "CI"),
        ("until grep -q done out.txt; do :; done", "Waiting on CI"),
        ("until [ -f out ]\ndo\n  true\ndone", "sleep"),
        ("# rebuild the pictures\nmake render", "CI"),
        ("make lint  # quick\nmake sim", "CI"),
        ("BLENDER=/opt/blender MOTIONS=hero make pictures", "CI"),
        ("nohup make sim > log 2>&1 &", "CI"),
        ("timeout 900 make hero", "CI"),
        ("gh -R yellow-pine/noggin pr merge 12 --admin", "--auto --squash"),
        ("for i in 1 2; do until [ -f out ]; do :; done; done", "sleep"),
        ("until [ -f out ]; do :; done; sleep 1", "sleep"),
        ('until [ -z "$(pgrep -f make)" ]; do sleep 5; done', "Waiting on CI"),
        ("bash <<'EOF'\nmake sim\nEOF", "CI"),
        ("python3 - <<EOF\nimport os\nEOF\nbash <<'EOF'\ngit stash\nEOF", "commit"),
        ("cat <<EOF\nok\nEOF\nbash <<X\ngit stash\nX", "commit"),
        ("echo '<<EOF'\ngit stash\nEOF", "commit"),
        ("bash -c 'git stash'", "commit"),
        ('sh -c "cd .. && make render"', "CI"),
        ("eval git stash", "commit"),
        ('echo "$(git stash)"', "commit"),
        ("echo `make sim`", "CI"),
        ("x=$(git stash pop)", "commit"),
        ("gh api -X PUT repos/yellow-pine/noggin/pulls/12/merge", "--auto --squash"),
        ("gh api graphql -f query='mutation { mergePullRequest(input: {}) { clientMutationId } }'", "--auto --squash"),
        ("git -c alias.s=stash s", "alias"),
        ("git config alias.s stash", "alias"),
        ("git -c core.pager=less -c Alias.s=stash s", "alias"),
        ("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.s GIT_CONFIG_VALUE_0=stash git s", "GIT_CONFIG"),
        ("/bin/bash -lc 'make sim'", "CI"),
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
        "make lint",
        "make check-light",
        "make mpy-list",
        "until gh pr checks 12 >/dev/null; [ $? != 8 ]; do sleep 60; done",
        "while read -r f; do echo $f; done < files",
        "pgrep -f noggin",
        "cat > notes.md <<'EOF'\ndon't run make sim or git stash here\nEOF",
        "git commit -q -F - <<EOF\nit's done\nEOF",
        "tee out.txt <<< 'git stash'",
        "gh api repos/yellow-pine/noggin/pulls/12/reviews",
        "make lint > sim.log",
        "gh pr list --json number | jq length",
        "gh pr create --body-file - <<'EOF'\nmake sim runs in CI\nuntil now nothing blocked git stash\nEOF",
        "git commit -F - <<EOF\nuntil now\nEOF\ngit push",
        "until [ -f out ]; do /bin/sleep 5; done",
        "cat <<< 'until x'",
    ],
)
def test_anything_else_runs(command):
    result = guard(command)
    assert result.returncode == 0, result.stderr


def test_full_make_check_is_blocked_once_make_check_light_exists(tmp_path):
    (tmp_path / "Makefile").write_text("check: lint\n\tpytest\nsim:\n\t$(HEAVY) sim\n")
    assert guard("make check", tmp_path).returncode == 0
    assert "make lint" in guard("make sim", tmp_path).stderr
    (tmp_path / "Makefile").write_text("check: lint\n\tpytest\ncheck-light: lint\n\tpytest -x\n")
    assert "make check-light" in guard("make check", tmp_path).stderr
    assert "make check-light" in guard("make check").stderr  # this repo's Makefile has check-light


def test_a_hook_that_cannot_read_its_input_blocks():
    result = subprocess.run(["python3", SCRIPT], input="not json", capture_output=True, text=True)
    assert result.returncode == 2
    assert "bash_guard.py failed" in result.stderr
