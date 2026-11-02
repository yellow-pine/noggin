"""CI's names follow GitHub's own UI (#298): every job has a Title Case name ("Fetch Skills", "Model (hero)"), every
step a short sentence-case imperative, like GitHub's built-in "Set up job" ("Set up uv", "Run just check")."""

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
    assert all(TITLE.fullmatch(n) for n in ["Code", "Fetch Skills", "PR", "Model (${{ matrix.shard }})"])
    assert not any(TITLE.fullmatch(n) for n in ["code", "fetch skills", "Model hero)", "convex ${{ matrix.part }}"])
    assert all(sentence_case(n) for n in ["Set up uv", "Run just check", "Restore the parts cache", "Verdict"])
    assert not any(sentence_case(n) for n in ["set up uv", "Restore The Parts Cache", "Run just check."])


def test_no_workflow_runs_on_ubuntu_latest():
    """#392: `ubuntu-latest` moves under us when GitHub says so (26.04 from 2026-10-19); a named image moves when we
    do (ADR 0012)."""
    assert [f.name for f in WORKFLOWS if "ubuntu-latest" in f.read_text()] == []


def test_a_new_push_cancels_a_prs_superseded_runs_but_never_a_deploy_or_release():
    """#675: every workflow on pull_request runs one PR's newest commit only, so a push cancels the run in progress;
    Site Deploy, Release and Release Assets never cancel a run mid-way."""
    wrong = []
    for f in WORKFLOWS:
        flow = yaml.safe_load(f.read_text())
        group = str(flow.get("concurrency", {}).get("group", ""))
        if "pull_request" in flow[True] and not (
            "github.workflow" in group
            and "github.event.pull_request.number" in group
            and flow["concurrency"].get("cancel-in-progress") is True
        ):
            wrong.append(f.name)
    assert wrong == []
    for name in ("pages.yml", "semantic-release.yml", "release.yml"):
        assert "cancel-in-progress: true" not in (WORKFLOWS[0].parent / name).read_text(), name


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


FULL = "${{ github.event_name != 'schedule' && github.event_name != 'workflow_dispatch' }}"  # neither runs everything


def test_main_skips_by_input_as_a_pr_does_and_a_weekly_or_dispatched_run_runs_everything():
    """#471: a push to main filters its changed paths against main's last commit whose checks passed, as a PR does;
    the weekly scheduled run on main does neither, so every job runs, nor does a
    dispatch on any branch (#562: the full render for a look's approval, its Checks a real one). Its own concurrency
    group, so it never cancels a push's run (whose deploy would then never happen) nor one of those cancels it. Main's
    Site always runs: it builds the deploy."""
    flow = yaml.safe_load((WORKFLOWS[0].parent / "checks.yml").read_text())
    assert "cron" in flow[True]["schedule"][0]
    assert "workflow_dispatch" in flow[True]
    assert "github.event_name" in flow["concurrency"]["group"]
    changes = flow["jobs"]["changes"]
    assert changes["if"] == "${{ !github.event.pull_request.draft }}"
    steps = {s.get("id"): s for s in changes["steps"]}
    assert steps["filter"]["if"] == FULL
    assert steps["filter"]["with"]["base"] == "${{ steps.checked.outputs.sha }}"  # main's last green commit
    assert (
        changes["outputs"]["site"]
        == "${{ github.event_name != 'pull_request' || steps.filter.outputs.site == 'true' }}"
    )


# what carries the geometry of a document: the built parts and their cut (STL), the renders' meshes and frames, the
# pictures, the GLBs, the preview and the site that carry them
DERIVED = re.compile(
    r"model/build/(ours|convex|images|pictures|preview)|web/build|site/dist|\.(glb|stl|step|webp|png)\b"
)
# a Blender run in a workflow: the recipe and what it draws
BLENDER = re.compile(r"just (?:\w+=\S+ )*(pictures|web|render|hero|hero-join)\b([^\n|&;]*)")


def test_ci_draws_uploads_and_serves_the_next_mech_alone():
    """#640, #649 (docs/adr/0019): a public repo's artifacts and release assets are anyone's to download, so the
    workflows render and bake the next Mech alone (just pictures next, just web next-mech: documents holding none of
    today's printed parts), upload only the site and the PR's preview, never a part, its cut, a mesh or a frame, put
    only the next-* pictures and GLBs in the site, and a release's docs fetch only the GLBs the site publishes. The
    Actions cache carries the parts between jobs: nobody outside the repo's workflows reads it."""
    from model import geometry as g
    from model import stages
    from model.render import pictures
    from web import build

    steps = [
        s for f in WORKFLOWS for job in yaml.safe_load(f.read_text())["jobs"].values() for s in job.get("steps", [])
    ]
    runs = [s.get("run", "") for s in steps]
    drawn = {(m[1], m[2].strip()) for r in runs for m in BLENDER.finditer(r)}
    assert drawn == {("pictures", pictures.NEXT), ("web", " ".join(build.PUBLIC))}
    assert {m for r in runs for m in re.findall(r"-m (model\.render\.\w+|web\.\w+)( \w+)?", r)} <= {
        ("model.render.pictures", " compare")
    }
    assert [doc for doc in {*g.NEXT, *build.PUBLIC} if stages.todays(doc)] == []
    uploaded = {
        line.strip()
        for s in steps
        if "upload-artifact" in s.get("uses", "") or "upload-pages-artifact" in s.get("uses", "")
        for line in str(s["with"]["path"]).splitlines()
        if DERIVED.search(line)
    }
    assert uploaded == {"site/dist", "model/build/preview"}
    into_site = [c for r in runs for c in re.findall(r"cp (?:-\w+ )?(\S+) site/dist/(?:images|viewer)", r)]
    assert into_site and all(re.search(r"/next-\*(\.glb)?$", c) for c in into_site)
    fetched = [r for r in runs if re.search(r"gh release upload|curl", r) and DERIVED.search(r)]
    viewer, previews = [[r for r in fetched if key in r] for key in (".published.viewer", "gh release upload pr-")]
    assert viewer and len(previews) == 1 and sorted(fetched) == sorted(viewer + previews)
    # a PR's sticky comment (#657): the preview artifact's before/after alone, the next Mech's
    assert re.findall(r"for f in (\S+); do cp", previews[0]) == ["preview/before-after*.webp"]
    assert re.findall(r"gh release upload pr-previews .*", previews[0]) == [
        'gh release upload pr-previews --clobber "$prefix"*.webp'  # only those copies
    ]


def test_a_prs_preview_comment_holds_the_least_and_publishes_no_release():
    """#657: one sticky comment per PR shows the next Mech's before/after inline, its pictures assets of the one
    `pr-previews` pre-release: never latest, nor a v* tag (Release Assets, semantic-release and the docs' versions read
    only those). Its job alone writes, with contents and pull-requests only, and only on this repo's PRs: a fork's
    and Dependabot's tokens are read-only."""
    flow = yaml.safe_load((WORKFLOWS[0].parent / "checks.yml").read_text())
    [job] = [j for j in flow["jobs"].values() if j["name"] == "Preview Comment"]
    assert job["needs"] == "blender"
    for cond in ("event_name == 'pull_request'", "head.repo.full_name == github.repository", "actor != 'dependabot"):
        assert cond in job["if"], cond
    assert job["permissions"] == {"contents": "write", "pull-requests": "write"}
    writers = [j["name"] for j in flow["jobs"].values() if "write" in j.get("permissions", {}).values()]
    assert writers == ["Preview Comment"] and "write" not in flow["permissions"].values()
    run = "\n".join(s.get("run", "") for s in job["steps"])
    assert "gh release create pr-previews --prerelease --latest=false" in run
    [sticky] = [s for s in job["steps"] if s.get("uses", "").startswith("marocchino/sticky-pull-request-comment@")]
    assert sticky["with"]["header"]  # one comment, found again and edited in place on every preview


def test_zizmor_asks_githubs_api_only_off_prs():
    """#561: the online audits (GitHub's API: rate limits, rarely a PR's change) run on main's push and weekly; a PR
    keeps just check's offline zizmor."""
    steps = yaml.safe_load((WORKFLOWS[0].parent / "checks.yml").read_text())["jobs"]["code"]["steps"]
    [online] = [s for s in steps if "zizmor" in s.get("run", "")]
    assert online["if"] == "${{ github.event_name != 'pull_request' }}"


def test_checks_never_run_on_edited():
    """#496: a title or body edit would cancel the running Checks (one run per group), or green a red one."""
    assert (
        "edited" not in yaml.safe_load((WORKFLOWS[0].parent / "checks.yml").read_text())[True]["pull_request"]["types"]
    )


def test_the_ci_images_rebuild_uncached_each_week_before_the_scan():
    """#534: a weekly run pushes both images as a push to main does, but uncached, so the apt layers take the
    distro's security fixes and the newest gh; it starts before image-scan.yml's Monday scan reads them."""
    flows = {f: yaml.safe_load((WORKFLOWS[0].parent / f).read_text()) for f in ("images.yml", "image-scan.yml")}
    build, scan = (flows[f][True]["schedule"][0]["cron"].split() for f in flows)
    assert (build[2:], scan[2:]) == (["*", "*", "1"], ["*", "*", "1"])  # both on Mondays
    assert int(build[1]) < int(scan[1])
    jobs = flows["images.yml"]["jobs"]
    assert jobs["push"]["if"] == "${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' }}"
    assert "pull_request" in jobs["build"]["if"]
    pushes = [s["with"] for s in jobs["push"]["steps"] if s["name"].startswith("Push")]
    assert [p["no-cache"] for p in pushes] == ["${{ github.event_name != 'push' }}"] * 2


def test_codeql_scans_main_and_weekly_never_a_pr():
    """#560: a PR waiting on CodeQL's results stalled merges, so CodeQL scans main and Mondays into the Security tab."""
    on = yaml.safe_load((WORKFLOWS[0].parent / "codeql.yml").read_text())[True]
    assert set(on) == {"push", "schedule"} and on["push"]["branches"] == ["main"]


def test_main_releases_itself_once_its_checks_pass():
    """#582, docs/adr/0017: semantic-release runs after this repo's push to main passed Checks, on that commit, one run
    at a time and never cancelled, as the bot App, so its tag starts Release Assets. No Release Please is left."""
    flow = yaml.safe_load((WORKFLOWS[0].parent / "semantic-release.yml").read_text())
    assert flow[True]["workflow_run"] == {"workflows": ["Checks"], "types": ["completed"], "branches": ["main"]}
    assert flow["concurrency"]["cancel-in-progress"] is False and "${{" not in flow["concurrency"]["group"]
    (job,) = flow["jobs"].values()
    for cond in ("conclusion == 'success'", "event == 'push'", "head_repository.full_name == github.repository"):
        assert f"github.event.workflow_run.{cond}" in job["if"], cond
    steps = {s["name"]: s for s in job["steps"]}
    app = next(s for s in steps.values() if s.get("uses", "").startswith("actions/create-github-app-token@"))
    checkout = next(s for s in steps.values() if s.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["ref"] == "${{ github.event.workflow_run.head_sha }}"
    assert checkout["with"]["fetch-depth"] == 0  # every tag, and the commits since the last
    release = next(s for s in steps.values() if "semantic-release" in s.get("run", ""))
    assert release["env"]["GITHUB_TOKEN"] == f"${{{{ steps.{app['id']}.outputs.token }}}}"
    root = WORKFLOWS[0].parent.parent.parent
    left = ["release-please.yml", "release-now.yml"]
    assert not [f for f in left if (WORKFLOWS[0].parent / f).exists()]
    assert not [f for f in ("release-please-config.json", ".release-please-manifest.json") if (root / f).exists()]
