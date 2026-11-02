"""main_red.py: a red main opens one 'main red' issue, a green one closes it (#697)."""

from pathlib import Path

import yaml

from scripts.main_red import WATCHED, report, verdict

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
DEPLOYED = [{"name": "Checks", "conclusion": "success"}, {"name": "Deploy", "conclusion": "success"}]


def test_a_failed_checks_or_site_deploy_run_is_red():
    for workflow in WATCHED:
        for conclusion in ("failure", "timed_out", "startup_failure"):
            assert verdict(workflow, conclusion, []) == "red", (workflow, conclusion)


def test_main_is_green_once_a_commit_deploys():  # its Checks passed and its site is up
    assert verdict("Site Deploy", "success", DEPLOYED) == "green"


def test_anything_else_says_nothing():
    assert verdict("Checks", "success", []) is None  # its Site Deploy follows and says green
    assert verdict("Checks", "cancelled", []) is None  # superseded by a newer push
    skipped = [{"name": "Checks", "conclusion": "success"}, {"name": "Deploy", "conclusion": "skipped"}]
    assert verdict("Site Deploy", "success", skipped) is None  # red Checks: nothing deployed


LOG = (
    "Model (sim)\tRun just sim\t2026-11-02T20:11:17.0289326Z model/test_report.py:230: AssertionError\n"
    "Model (sim)\tRun just sim\t2026-11-02T20:11:17.0290000Z \x1b[31mFAILED\x1b[0m model/test_report.py::test_x\n"
    "Model (sim)\tRun just sim\t2026-11-02T20:11:17.0291000Z collected 12 items\n"
    "Code\tRun just check\t2026-11-02T20:11:18.0000000Z ##[error]Process completed with exit code 1.\n"
)
JOBS = [{"name": "Code", "conclusion": "success"}, {"name": "Model (sim)", "conclusion": "failure"}]


def test_the_report_names_the_commit_the_failing_jobs_and_their_key_log_lines():
    body = report("Checks", "abc1234def", "https://commit", "https://run", JOBS, LOG)
    assert body == (
        "Main's Checks failed on [abc1234](https://commit): https://run\n\n"
        "Failing jobs: Model (sim)\n\n"
        "```text\n"
        "Model (sim): model/test_report.py:230: AssertionError\n"
        "Model (sim): FAILED model/test_report.py::test_x\n"
        "```\n"
    )


def test_a_long_log_keeps_its_first_key_lines():
    log = "".join(f"J\tS\t2026-11-02T00:00:00.0Z FAILED t{i} {'x' * 500}\n" for i in range(100))
    lines = report("Checks", "abc", "c", "r", [], log).split("```text\n")[1].splitlines()[:-1]
    assert len(lines) == 40 and lines[0].startswith("J: FAILED t0 ") and max(map(len, lines)) <= 300


def test_it_watches_checks_and_site_deploy_by_their_names():
    """A renamed workflow would never be watched again: Main Red's trigger names them as they name themselves."""
    names = [yaml.safe_load((WORKFLOWS / f).read_text())["name"] for f in ("checks.yml", "pages.yml")]
    on = yaml.safe_load((WORKFLOWS / "main-red.yml").read_text())[True]  # yaml reads `on:` as True
    assert on["workflow_run"]["workflows"] == WATCHED == names
