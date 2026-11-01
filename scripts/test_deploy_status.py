"""deploy_status.py: main's `deploy` commit status from Site Deploy's job results (#292)."""

from scripts.deploy_status import status

SUPERSEDED = ("error", "superseded by a newer commit: nothing deployed", "run")
NOTHING = {"render": "skipped", "viewer": "skipped", "site": "skipped", "deploy": "skipped"}


def run(check="success", render="success", viewer="success", site="success", deploy="success"):
    return status(check, render, viewer, site, deploy)


def test_a_deploy_is_success_linking_the_site():
    assert run() == ("success", "deployed to the site", "site")


def test_red_checks_build_nothing_and_link_the_check_run():  # #295
    assert run(check="failure", **NOTHING) == ("failure", "not deployed: checks failed", "check")
    assert run(check="timed_out", **NOTHING)[1] == "not deployed: checks failed"


def test_a_cancelled_check_run_is_superseded():
    assert run(check="cancelled", **NOTHING) == SUPERSEDED


def test_a_cancelled_job_is_superseded():
    assert run(viewer="cancelled", site="skipped", deploy="skipped") == SUPERSEDED
    assert run(deploy="cancelled") == SUPERSEDED


def test_a_job_skipped_after_the_jobs_before_it_succeeded_is_superseded():  # deploy's !cancelled() skips it on a cancel
    assert run(deploy="skipped") == SUPERSEDED
    assert run(site="skipped", deploy="skipped") == SUPERSEDED


def test_the_first_job_that_did_not_succeed_is_named_linking_the_run():
    assert run(render="failure", site="failure", deploy="skipped") == (
        "failure",
        "render failed: nothing deployed",
        "run",
    )
    assert run(viewer="failure", site="failure", deploy="skipped")[1] == "viewer failed: nothing deployed"
    assert run(site="failure", deploy="skipped")[1] == "site failed: nothing deployed"
    assert run(deploy="failure")[1] == "deploy failed: nothing deployed"
