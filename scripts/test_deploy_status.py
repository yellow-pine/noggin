"""deploy_status.py: whether Site Deploy deploys a main commit, and its `deploy` commit status (#292, #310, #496)."""

from pathlib import Path

import yaml

from scripts.deploy_status import CHECKS, gate, status

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
RUN = "https://github.com/o/r/actions/runs/9"
SUPERSEDED = ("error", "superseded by a newer commit: nothing deployed", RUN)


def run(id: int, name: str, conclusion: str | None = "success", state: str = "completed") -> dict:
    return {"id": id, "name": name, "status": state, "conclusion": conclusion, "html_url": f"url{id}"}


def test_green_checks_deploy_their_run():
    assert gate([run(1, "Checks")], RUN) == 1


def test_nothing_happens_until_checks_are_done():  # its completion runs Site Deploy again
    assert gate([run(1, "Checks", None, "in_progress")], RUN) is None
    assert gate([run(1, "Release Assets")], RUN) is None


def test_red_checks_are_not_deployed_linking_them():  # #295
    assert gate([run(1, "Checks", "failure")], RUN) == ("failure", "not deployed: checks failed", "url1")
    assert gate([run(2, "Checks", "timed_out")], RUN) == ("failure", "not deployed: checks failed", "url2")


def test_cancelled_checks_are_superseded():  # a newer push to main cancels them
    assert gate([run(1, "Checks", "cancelled")], RUN) == SUPERSEDED


def test_the_latest_run_of_checks_counts_and_no_other_workflow():
    runs = [run(3, "Checks"), run(1, "Checks", "failure"), run(2, "Checks", "failure")]
    assert gate([*runs, run(5, "Release Assets", "failure")], RUN) == 3


def test_the_deploy_jobs_result_is_the_status():
    assert status("success", "https://site/", RUN) == ("success", "deployed to the site", "https://site/")
    assert status("failure", "", RUN) == ("failure", "deploy failed: nothing deployed", RUN)
    assert status("cancelled", "", RUN) == SUPERSEDED


def test_site_deploy_runs_on_exactly_the_checks_workflow():
    """A renamed Checks would never deploy again: Site Deploy's trigger names it as it names itself."""
    name = yaml.safe_load((WORKFLOWS / "checks.yml").read_text())["name"]
    deploy = yaml.safe_load((WORKFLOWS / "pages.yml").read_text())
    assert deploy[True]["workflow_run"]["workflows"] == [CHECKS] == [name]  # yaml reads `on:` as True
