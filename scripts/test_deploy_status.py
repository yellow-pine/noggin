"""deploy_status.py: main's `deploy` commit status from Site Deploy's job results (#292)."""

from scripts.deploy_status import status

SUPERSEDED = ("error", "superseded by a newer commit: nothing deployed")


def run(check="success", render="success", viewer="success", site="success", deploy="success"):
    return status(check, render, viewer, site, deploy)


def test_a_deploy_is_success():
    assert run() == ("success", "deployed to the site")


def test_a_red_code_checks_still_deploys():  # pages.yml builds on a failed check run; only a cancelled one stops it
    assert run(check="failure")[0] == "success"


def test_a_cancelled_check_run_is_superseded():
    assert run(check="cancelled", render="skipped", viewer="skipped", site="skipped", deploy="skipped") == SUPERSEDED


def test_a_cancelled_job_is_superseded():
    assert run(viewer="cancelled", site="skipped", deploy="skipped") == SUPERSEDED
    assert run(deploy="cancelled") == SUPERSEDED


def test_a_job_skipped_after_the_jobs_before_it_succeeded_is_superseded():  # deploy's !cancelled() skips it on a cancel
    assert run(deploy="skipped") == SUPERSEDED
    assert run(site="skipped", deploy="skipped") == SUPERSEDED


def test_the_first_job_that_did_not_succeed_is_named():
    assert run(render="failure", site="failure", deploy="skipped") == ("failure", "render failed: nothing deployed")
    assert run(viewer="failure", site="failure", deploy="skipped") == ("failure", "viewer failed: nothing deployed")
    assert run(site="failure", deploy="skipped") == ("failure", "site failed: nothing deployed")
    assert run(deploy="failure") == ("failure", "deploy failed: nothing deployed")
