"""CI's names follow GitHub's own UI (#298): every job has a Title Case name ("Fetch Skills", "Model (hero)"), every
step a short sentence-case imperative, like GitHub's built-in "Set up job" ("Set up uv", "Run make check")."""

import re
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOWS = sorted((Path(__file__).resolve().parent / ".github" / "workflows").glob("*.yml"))
TITLE = re.compile(r"[A-Z][\w'-]*( [A-Z][\w'-]*)*( \(.+\))?")  # each word capitalised; a matrix's values in brackets


def sentence_case(name: str) -> bool:
    """Capitalised first word, no full stop; past two words, not every word capitalised (that would be Title Case)."""
    words = name.split()
    return bool(re.fullmatch(r"[A-Z].*[^.]", name)) and (len(words) <= 2 or not all(w[0].isupper() for w in words))


def names():
    for f in WORKFLOWS:
        for id_, job in yaml.safe_load(f.read_text())["jobs"].items():
            yield f.name, id_, job.get("name"), [s.get("name") for s in job.get("steps", [])]


def test_every_job_has_a_title_case_name():
    wrong = [(f, id_, name) for f, id_, name, _ in names() if not (name and TITLE.fullmatch(name))]
    assert wrong == []


def test_every_step_has_a_short_sentence_case_name():
    wrong = [
        (f, id_, n, step)
        for f, id_, _, steps in names()
        for n, step in enumerate(steps, 1)
        if not (step and len(step) <= 40 and sentence_case(step))
    ]
    assert wrong == []


def test_the_convention_itself():
    assert all(TITLE.fullmatch(n) for n in ["Code", "Fetch Skills", "PR Title", "Model (${{ matrix.shard }})"])
    assert not any(TITLE.fullmatch(n) for n in ["code", "fetch skills", "Model hero)", "convex ${{ matrix.part }}"])
    assert all(sentence_case(n) for n in ["Set up uv", "Run make check", "Restore the parts cache", "Verdict"])
    assert not any(sentence_case(n) for n in ["set up uv", "Restore The Parts Cache", "Run make check."])


def test_no_workflow_runs_on_ubuntu_latest():
    """#392: `ubuntu-latest` moves under us when GitHub says so (26.04 from 2026-10-19); a named image moves when we
    do (ADR 0012)."""
    assert [f.name for f in WORKFLOWS if "ubuntu-latest" in f.read_text()] == []


def test_every_pr_workflow_skips_drafts_and_runs_when_ready():
    """#414: the release PR waits as a draft, so a draft runs nothing and marking it ready runs everything once. Each
    job a draft could start skips it: a job with no needs, and one that runs past a skipped need (`always()`,
    `!cancelled()`) unless it needs that one's success. Dependabot's auto-merge acts only on its own PRs, not drafts."""
    wrong = []
    for f in WORKFLOWS:
        flow = yaml.safe_load(f.read_text())
        on = flow[True]  # yaml reads `on:` as True
        if f.name == "dependabot.yml" or "pull_request" not in on:
            continue
        pr = on["pull_request"] if isinstance(on, dict) else None  # a bare trigger has the default types
        if "ready_for_review" not in (pr or {}).get("types", []):
            wrong.append((f.name, "types"))
        for id_, job in flow["jobs"].items():
            cond = str(job.get("if", ""))
            past_skips = any(f in cond for f in ("cancelled()", "always()", "failure()")) and "== 'success'" not in cond
            starts = not job.get("needs") or past_skips
            if starts and "pull_request.draft" not in cond and "event_name != 'pull_request'" not in cond:
                wrong.append((f.name, id_))
    assert wrong == []


def run_check_the_verdict(tmp_path: Path, changed: str, conclusion: str, app_token: str):
    """review.yml's `Check if the PR edits review.yml`, then `Check the verdict`, with no structured output and `git`
    and `gh` faked: `git diff` lists `changed`, `gh` logs its arguments."""
    for tool, body in [("git", f"printf '%s\\n' {changed}"), ("gh", f'echo "$@" >> {tmp_path}/gh.log')]:
        (tmp_path / tool).write_text(f"#!/bin/sh\n{body}\n")
        (tmp_path / tool).chmod(0o755)
    flow = yaml.safe_load((Path(__file__).resolve().parent / ".github" / "workflows" / "review.yml").read_text())
    run = {s.get("name"): s.get("run") for s in flow["jobs"]["review"]["steps"]}
    env = {"PATH": f"{tmp_path}:/usr/bin:/bin", "BASE": "main", "PR": "7", "GITHUB_OUTPUT": f"{tmp_path}/out"}

    def step(name: str, **more: str):
        return subprocess.run(
            ["bash", "-eo", "pipefail", "-c", run[name]], env=env | more, capture_output=True, text=True
        )

    step("Check if the PR edits review.yml").check_returncode()
    edits = (tmp_path / "out").read_text().removeprefix("review=").strip() if (tmp_path / "out").exists() else ""
    done = step("Check the verdict", RESULT="", CONCLUSION=conclusion, APP_TOKEN=app_token, EDITS_REVIEW=edits)
    log = tmp_path / "gh.log"
    return done.returncode, done.stdout, log.read_text() if log.exists() else ""


@pytest.mark.parametrize(
    ("changed", "conclusion", "app_token", "code", "says", "gh"),
    [
        # the action skipped on validation (no conclusion: Claude never ran) and main's review.yml moved on (#433)
        ("noggin/x.py", "", "t", 1, "branch updated, the review re-runs", "pr update-branch 7 --rebase\n"),
        ("noggin/x.py", "", "", 1, "changed since this branch: rebase it", ""),  # Dependabot's: no App token
        (".github/workflows/review.yml", "", "", 0, "review.yml changed in this PR", ""),  # needs Cansin's bypass
        ("noggin/x.py", "success", "", 1, "the review produced no verdict", ""),  # Claude ran and gave none
    ],
)
def test_a_review_with_no_verdict(tmp_path, changed, conclusion, app_token, code, says, gh):
    got_code, out, got_gh = run_check_the_verdict(tmp_path, changed, conclusion, app_token)
    assert (got_code, says in out, got_gh) == (code, True, gh)


def test_main_skips_by_input_as_a_pr_does_and_a_weekly_run_runs_everything():
    """#471: a push to main filters its changed paths against main's last commit whose checks passed and looks its
    Blender outputs up, as a PR does; the weekly scheduled run on main does neither, so every job runs. Its own
    concurrency group, so it never cancels a push's run (whose deploy would then never happen) nor one of those
    cancels it."""
    flows = {f.name: yaml.safe_load(f.read_text()) for f in WORKFLOWS if f.name in ("check.yml", "site-checks.yml")}
    for flow in flows.values():
        assert "cron" in flow[True]["schedule"][0]
        assert "github.event_name" in flow["concurrency"]["group"]
    changes = flows["check.yml"]["jobs"]["changes"]
    assert changes["if"] == "${{ github.event_name != 'schedule' && !github.event.pull_request.draft }}"
    (filter_,) = [s for s in changes["steps"] if s.get("id") == "filter"]
    assert "if" not in filter_
    assert filter_["with"]["base"] == "${{ steps.checked.outputs.sha }}"  # main's last green commit
    # Site Checks' changes runs weekly too, for the keys' hash (#469); main's Site always runs: it builds the deploy
    changes = flows["site-checks.yml"]["jobs"]["changes"]
    assert [s["if"] for s in changes["steps"] if s.get("id") in ("pictures", "viewer")] == [
        "${{ github.event_name != 'schedule' }}"
    ] * 2
