"""deploy_status.py: whether Site Deploy deploys a main commit, and its `deploy` commit status (#292, #310)."""

from pathlib import Path

import yaml

from scripts.deploy_status import CHECKS, gate, status

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
RUN = "https://github.com/o/r/actions/runs/9"
SUPERSEDED = ("error", "superseded by a newer commit: nothing deployed", RUN)


def run(id, name, conclusion="success", state="completed"):
    return {"id": id, "name": name, "status": state, "conclusion": conclusion, "html_url": f"url{id}"}


def test_both_checks_green_deploys_the_site_checks_run():
    assert gate([run(1, "Code Checks"), run(2, "Site Checks")], RUN) == 2


def test_nothing_happens_until_both_check_workflows_are_done():  # the other one's completion runs Site Deploy again
    assert gate([run(1, "Code Checks"), run(2, "Site Checks", None, "in_progress")], RUN) is None
    assert gate([run(1, "Code Checks", "failure")], RUN) is None


def test_a_red_check_workflow_is_not_deployed_linking_it():  # #295
    assert gate([run(1, "Code Checks", "failure"), run(2, "Site Checks")], RUN) == (
        "failure",
        "not deployed: checks failed",
        "url1",
    )
    assert gate([run(1, "Code Checks", "cancelled"), run(2, "Site Checks", "timed_out")], RUN)[2] == "url2"


def test_a_cancelled_check_workflow_is_superseded():  # a newer push to main cancels both
    assert gate([run(1, "Code Checks", "cancelled"), run(2, "Site Checks")], RUN) == SUPERSEDED


def test_the_latest_run_of_each_workflow_counts_and_no_other_workflow():
    runs = [run(3, "Site Checks"), run(1, "Code Checks", "failure"), run(2, "Site Checks", "failure")]
    assert gate([*runs, run(4, "Code Checks"), run(5, "Release Assets", "failure")], RUN) == 3


def test_the_deploy_jobs_result_is_the_status():
    assert status("success", "https://site/", RUN) == ("success", "deployed to the site", "https://site/")
    assert status("failure", "", RUN) == ("failure", "deploy failed: nothing deployed", RUN)
    assert status("cancelled", "", RUN) == SUPERSEDED


def test_site_deploy_runs_on_exactly_the_check_workflows():
    """A renamed check workflow would never deploy again: Site Deploy's trigger names them as they name themselves."""
    names = {yaml.safe_load((WORKFLOWS / f).read_text())["name"] for f in ("check.yml", "site-checks.yml")}
    deploy = yaml.safe_load((WORKFLOWS / "pages.yml").read_text())
    assert set(deploy[True]["workflow_run"]["workflows"]) == set(CHECKS) == names  # yaml reads `on:` as True
