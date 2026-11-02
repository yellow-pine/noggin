"""CI's names follow GitHub's own UI (#298): every job has a Title Case name ("Fetch Skills", "Model (hero)"), every
step a short sentence-case imperative, like GitHub's built-in "Set up job" ("Set up uv", "Run just check")."""

import json
import os
import re
import shutil
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


def test_every_job_id_is_kebab_case():
    assert [(f, id_) for f, id_, _, _ in names() if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", id_)] == []


def test_every_workflow_is_title_case_in_its_kebab_case_file():
    """#773, GitHub's starter workflows: the name Title Case ("Main Red"), the file its kebab-case form."""
    flows = {f.name: yaml.safe_load(f.read_text())["name"] for f in WORKFLOWS}
    wrong = {
        f: n
        for f, n in flows.items()
        if not (TITLE.fullmatch(n) and f == re.sub(r"\W+", "-", n).lower() + ".yml")
        and f != "review.yml"  # #787 renames it, under Cansin's bypass: a PR editing review.yml gets no review
    }
    assert wrong == {}


def test_every_run_has_a_descriptive_title():
    """#773: GitHub titles a push's run by its commit and a PR's or an issue's by its title, but a scheduled,
    dispatched or workflow_run run by the workflow's name alone. Those set `run-name`: '<Workflow>: weekly <what>',
    '<Workflow>: manual by <actor>', '<Workflow>: <triggering run's title>' (a push's: its commit's first line; Main Red
    names the workflow it reports unless that title does); an empty result keeps GitHub's title for the other events."""
    wrong = []
    for f in WORKFLOWS:
        flow = yaml.safe_load(f.read_text())
        on, name, title = flow[True], flow["name"], flow.get("run-name", "")
        on = set(on) if isinstance(on, (dict, list)) else {on}
        want = {
            "schedule": f"'{name}: weekly ",
            "workflow_dispatch": f"format('{name}: manual by {{0}}', github.actor)",
            "workflow_run": "github.event.workflow_run.display_title",
        }
        parts = [w for e, w in want.items() if e in on]
        if parts and on - set(want) and not title.endswith(" || '' }}"):
            wrong.append((f.name, "keeps GitHub's title"))
        if not all(p in title for p in parts) or bool(parts) != bool(title) or (title and f"'{name}: " not in title):
            wrong.append((f.name, title))
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
    Checks' Deploy, Release and Release Assets never cancel a run mid-way. #689: Checks, which deploys (#795) and
    Release waits on (main's alone since #722), runs every push to main to completion, queued, or merges minutes apart
    never deploy."""
    flows = {f.name: yaml.safe_load(f.read_text()) for f in WORKFLOWS}
    wrong = []
    for name, flow in flows.items():
        group = str(flow.get("concurrency", {}).get("group", ""))
        if "pull_request" in flow[True] and not (
            "github.workflow" in group
            and "github.event.pull_request.number" in group
            and flow["concurrency"].get("cancel-in-progress") is True
        ):
            wrong.append(name)
    assert wrong == []
    awaited = set(flows["release.yml"][True]["workflow_run"]["workflows"])
    by_name = {flow["name"]: flow for flow in flows.values()}
    assert awaited and {w: by_name[w]["concurrency"]["cancel-in-progress"] for w in awaited} == dict.fromkeys(
        awaited, False
    )
    assert flows["checks.yml"]["jobs"]["deploy"]["concurrency"]["cancel-in-progress"] is False
    for name in ("checks.yml", "release.yml", "release-assets.yml"):
        assert "cancel-in-progress: true" not in (WORKFLOWS[0].parent / name).read_text(), name


def test_every_pr_workflow_skips_drafts_and_runs_when_ready():
    """#414: the release PR waits as a draft, so a draft runs nothing and marking it ready runs everything once. Each
    job a draft could start skips it: a job with no needs, and one that runs past a skipped need (`always()`,
    `!cancelled()`) unless it needs that one's success. Dependabot's auto-merge acts only on its own PRs, not drafts."""
    wrong = []
    for f in WORKFLOWS:
        flow = yaml.safe_load(f.read_text())
        on = flow[True]  # yaml reads `on:` as True
        if f.name == "dependabot-auto-merge.yml" or "pull_request" not in on:
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


@pytest.mark.skipif(shutil.which("yq") is None, reason="yq is CI's image's (ci/base.Dockerfile)")
def test_a_required_check_names_a_gate_job(tmp_path):
    """#450, #570, #746: checks.yml's `Check the required checks` fails, naming each, on a check main's ruleset requires
    that no job without a matrix in .github/workflows names (a job without a name reports its id), with `gh` faked."""
    flows = tmp_path / ".github" / "workflows"
    flows.mkdir(parents=True)
    (flows / "check.yml").write_text(
        "jobs:\n  code:\n    name: Code\n"
        "  model:\n    name: Model (${{ matrix.shard }})\n    strategy:\n      matrix:\n        shard: [hero]\n"
        "  site:\n    name: Fetch Site\n    strategy:\n      matrix:\n        os: [linux]\n"
    )
    (flows / "review.yml").write_text("jobs:\n  review:\n    name: Review\n  unnamed: {}\n")
    flow = yaml.safe_load((Path(__file__).resolve().parent / ".github" / "workflows" / "checks.yml").read_text())
    run = next(s["run"] for s in flow["jobs"]["code"]["steps"] if s.get("name") == "Check the required checks")

    def step(*required: str) -> subprocess.CompletedProcess[str]:
        (tmp_path / "gh").write_text("#!/bin/sh\nprintf '%s\\n' " + " ".join(f"'{r}'" for r in required) + "\n")
        (tmp_path / "gh").chmod(0o755)
        env = {"PATH": f"{tmp_path}:{os.environ['PATH']}", "GITHUB_REPOSITORY": "o/r"}
        return subprocess.run(
            ["bash", "-eo", "pipefail", "-c", run], cwd=tmp_path, env=env, capture_output=True, text=True
        )

    assert step("Code", "Review", "unnamed").returncode == 0
    stale = ["Lint", "Model (hero)", "Model (${{ matrix.shard }})", "Fetch Site", "model"]
    failed = step("Code", *stale)
    assert failed.returncode == 1
    assert [line.split("'")[1] for line in failed.stdout.splitlines()] == sorted(stale)


FULL = "${{ github.event_name != 'schedule' && github.event_name != 'workflow_dispatch' }}"  # neither runs everything


def test_main_skips_by_input_and_a_weekly_or_dispatched_run_runs_everything():
    """#471: a push to main filters its changed paths against main's last commit whose checks passed; the weekly
    scheduled run on main does not, so every job runs, nor does a dispatch on any branch (#562: the full render for a
    look's approval, its Checks a real one). Its own concurrency group, so it never cancels a push's run (whose deploy
    would then never happen) nor one of those cancels it."""
    flow = yaml.safe_load((WORKFLOWS[0].parent / "checks.yml").read_text())
    assert "cron" in flow[True]["schedule"][0]
    assert "workflow_dispatch" in flow[True]
    assert "github.event_name" in flow["concurrency"]["group"]
    steps = {s.get("id"): s for s in flow["jobs"]["changes"]["steps"]}
    assert steps["filter"]["if"] == FULL
    assert steps["filter"]["with"]["base"] == "${{ steps.checked.outputs.sha }}"  # main's last green commit


def test_a_pr_runs_the_slim_gate_alone():
    """#696, #714, #722: a PR runs PR Gate alone, `just check-light` (Code: ruff, pyright and the fast tests), then its
    `Checks` gate; Checks (checks.yml: the site's build, the workflow and Dockerfile linters, the model, sim, Blender,
    Convex and the site's Chrome smoke) runs on main only, which fixes forward what it catches (#283)."""
    gate = yaml.safe_load((WORKFLOWS[0].parent / "pr-gate.yml").read_text())
    assert set(gate[True]) == {"pull_request"}
    assert "pull_request" not in yaml.safe_load((WORKFLOWS[0].parent / "checks.yml").read_text())[True]
    jobs = gate["jobs"]
    assert {id_: job["name"] for id_, job in jobs.items()} == {"code": "Code", "checks": "Checks"}
    assert [s["name"] for s in jobs["code"]["steps"]] == [
        "Check out the repo",
        "Link the image's venv",
        "Run just check-light",
        "List the slowest tests",
        "Cancel the run on failure",  # #769
    ]
    assert "uv run just check-light " in jobs["code"]["steps"][2]["run"]
    justfile = (WORKFLOWS[0].parents[2] / "justfile").read_text()
    recipes = dict(re.findall(r"(?m)^([\w-]+):[^\n]*\n((?:    [^\n]*\n)+)", justfile))
    assert re.findall(r"-m (\w+)", recipes["lint"] + recipes["check-light"]) == ["ruff", "ruff", "pyright", "pytest"]
    assert [s["name"] for s in jobs["checks"]["steps"]] == ["Check every job passed"]  # no CI budget (#732)


def test_a_pr_lists_no_job_every_pr_skips():
    """#722: a job conditioned off pull_request shows as skipped on every PR, so a workflow on pull_request alone
    tests no event at all. Dependabot Auto-merge runs on Dependabot's PRs and Clear Labels on a closed issue: both
    stay."""
    for f in WORKFLOWS:
        on = yaml.safe_load(f.read_text())[True]
        if on == "pull_request" or set(on) == {"pull_request"}:  # a bare trigger, or its types
            assert "github.event_name" not in f.read_text(), f.name


# what carries the geometry of a document: the built parts and their cut (STL), the renders' meshes and frames, the
# pictures, the GLBs and the site that carry them
DERIVED = re.compile(r"model/build/(ours|convex|images|pictures)|web/build|site/dist|\.(glb|stl|step|webp|png)\b")
# a Blender run in a workflow: the recipe and what it draws
BLENDER = re.compile(r"just (?:\w+=\S+ )*(pictures|web|render)\b([^\n|&;]*)")


def test_ci_draws_uploads_and_serves_the_next_mech_alone():
    """#640, #649 (docs/adr/0019): a public repo's artifacts and release assets are anyone's to download, so the
    workflows render and bake the next Mech alone (just pictures next, just web next), upload only the site, never a
    part, its cut, a mesh or a frame, put only the next-* pictures and GLBs in the site, and attach none of it to a
    release (no release's docs since #778, docs/adr/0021). The Actions cache carries the parts between jobs: nobody
    outside the repo's workflows reads it."""
    from model.render import pictures

    steps = [
        s for f in WORKFLOWS for job in yaml.safe_load(f.read_text())["jobs"].values() for s in job.get("steps", [])
    ]
    runs = [s.get("run", "") for s in steps]
    drawn = {(m[1], m[2].strip()) for r in runs for m in BLENDER.finditer(r)}
    assert drawn == {("pictures", pictures.NEXT), ("web", pictures.NEXT)}
    assert not re.findall(r"-m (model\.render\.\w+|web\.\w+)", "\n".join(runs))  # just recipes alone draw
    uploaded = {
        line.strip()
        for s in steps
        if "upload-artifact" in s.get("uses", "") or "upload-pages-artifact" in s.get("uses", "")
        for line in str(s["with"]["path"]).splitlines()
        if DERIVED.search(line)
    }
    assert uploaded == {"site/dist"}  # #673: no PR preview
    site = re.search(r"(?m)^site:[^\n]*\n((?:    [^\n]*\n)+)", (WORKFLOWS[0].parents[2] / "justfile").read_text())[1]
    into_site = re.findall(r"cp (?:-\w+ )?(\S+) site/dist/(?:images|viewer)", "\n".join([*runs, site]))
    assert into_site and all(re.search(r"/next-\*(\.glb)?$", c) for c in into_site)
    assert not [r for r in runs if re.search(r"gh release upload|curl", r) and DERIVED.search(r)]


def test_blender_joins_every_render_shard():
    """#770: each Render shard saves its share of the pictures, and Blender restores every one of them, so a shard added
    to the matrix is never left out of the site."""
    jobs = yaml.safe_load((WORKFLOWS[0].parent / "checks.yml").read_text())["jobs"]
    saved = [s["with"]["key"] for s in jobs["render"]["steps"] if "cache/save" in s.get("uses", "")]
    restored = [s["with"]["key"] for s in jobs["blender"]["steps"] if "cache/restore" in s.get("uses", "")]
    assert saved == ["next-${{ matrix.shard }}-${{ needs.changes.outputs.next-hash }}"]
    assert restored == [
        saved[0].replace("${{ matrix.shard }}", str(i)) for i in jobs["render"]["strategy"]["matrix"]["shard"]
    ]


def test_a_job_names_an_environment_only_to_deploy():
    """#754: a job naming an environment makes a Deployment record, so an environment with nothing in it (Release
    Assets' `release`, #358) showed every release twice. A job names one only as a real deploy target, or with
    `deployment: false` for its secrets or rules alone."""
    named = {
        (f.name, id_): env if isinstance(env, dict) else {"name": env}
        for f in WORKFLOWS
        for id_, job in yaml.safe_load(f.read_text())["jobs"].items()
        if (env := job.get("environment"))
    }
    assert named and all(e["name"] == "github-pages" or e.get("deployment") is False for e in named.values()), named


def test_no_check_job_writes():
    """#673: the PR preview's sticky comment and its `pr-previews` release are gone, and with them the one job of
    Checks that wrote; every job reads alone, in main's Checks as in a PR's gate (#722), but may cancel its own run
    (`actions: write`, cancel-on-failure, #769), and main's Deploy writes Pages (#795)."""
    for f in ("checks.yml", "pr-gate.yml"):
        flow = yaml.safe_load((WORKFLOWS[0].parent / f).read_text())
        jobs = [j for i, j in flow["jobs"].items() if i != "deploy"]
        perms = [flow["permissions"], *(j.get("permissions", {}) for j in jobs)]
        assert not [p for p in perms if "write" in [v for k, v in p.items() if k != "actions"]], f


def test_zizmor_asks_githubs_api_only_off_prs():
    """#561: the online audits (GitHub's API: rate limits, rarely a PR's change) run on main's push and weekly; a PR
    runs no zizmor at all since #714, and main's Checks never runs on a PR (#722)."""
    flow = yaml.safe_load((WORKFLOWS[0].parent / "checks.yml").read_text())
    assert [s for s in flow["jobs"]["code"]["steps"] if ".venv/bin/zizmor" in s.get("run", "")]
    assert "pull_request" not in flow[True]
    assert "zizmor" not in (WORKFLOWS[0].parent / "pr-gate.yml").read_text()


def test_ci_runs_zizmor_and_parses_the_shell_scripts_once():
    """#732: just check's offline zizmor and bash -n / sh -n run locally alone; in CI the Code job's online zizmor and
    shellcheck (which parses the same scripts) cover them."""
    code = yaml.safe_load((WORKFLOWS[0].parent / "checks.yml").read_text())["jobs"]["code"]["steps"]
    shellcheck = next(s["run"] for s in code if s.get("run", "").startswith("shellcheck "))
    justfile = (WORKFLOWS[0].parents[2] / "justfile").read_text()
    check = re.search(r"(?m)^check:[^\n]*\n((?:    [^\n]*\n)+)", justfile)[1].splitlines()
    local = [line.strip() for line in check if re.search(r"zizmor|\b(ba)?sh -n", line)]
    assert len(local) == 3
    assert all(line.startswith('[ -n "${CI:-}" ] || ') for line in local), local
    parsed = re.findall(r"(?:sh -n|in) ([\w/. ]+?)(?:;|$)", "\n".join(local))
    assert {f for files in parsed for f in files.split()} <= set(shellcheck.split())


def test_the_pr_gate_never_runs_on_edited():
    """#496: a title or body edit would cancel the running gate (one run per group), or green a red one."""
    on = yaml.safe_load((WORKFLOWS[0].parent / "pr-gate.yml").read_text())[True]
    assert "edited" not in on["pull_request"]["types"]


def test_the_ci_images_rebuild_uncached_each_week_before_the_scan():
    """#534: a weekly run pushes both images as a push to main does, but uncached, so the apt layers take the
    distro's security fixes and the newest gh; it starts before image-scan.yml's Monday scan reads them."""
    flows = {f: yaml.safe_load((WORKFLOWS[0].parent / f).read_text()) for f in ("ci-images.yml", "image-scan.yml")}
    build, scan = (flows[f][True]["schedule"][0]["cron"].split() for f in flows)
    assert (build[2:], scan[2:]) == (["*", "*", "1"], ["*", "*", "1"])  # both on Mondays
    assert int(build[1]) < int(scan[1])
    jobs = flows["ci-images.yml"]["jobs"]
    assert jobs["push"]["if"] == "${{ github.ref == 'refs/heads/main' }}"
    pushes = [s["with"] for s in jobs["push"]["steps"] if s["name"].startswith("Push")]
    assert [p["no-cache"] for p in pushes] == ["${{ github.event_name != 'push' }}"] * 2


def test_the_ci_images_build_on_main_alone():
    """#729: a PR never builds the images; main's push build fails without moving :main, and hadolint lints the
    Dockerfiles in main's Code job, so a broken Dockerfile files a `main-red-images` issue (main-red.yml)."""
    images = yaml.safe_load((WORKFLOWS[0].parent / "ci-images.yml").read_text())
    assert "pull_request" not in images[True] and list(images["jobs"]) == ["push"]


def test_the_jobs_in_our_images_use_its_synced_venv():
    """#725: the base image carries uv's Python and the venv synced from uv.lock; main rebuilds it when the venv's
    inputs change, and every job running in our images links it as .venv before uv touches the checkout."""
    images = yaml.safe_load((WORKFLOWS[0].parent / "ci-images.yml").read_text())
    assert {"uv.lock", "pyproject.toml", ".python-version"} <= set(images[True]["push"]["paths"])
    for f in WORKFLOWS:
        for id_, job in yaml.safe_load(f.read_text())["jobs"].items():
            if "container" in job:
                runs = [s.get("run", "") for s in job["steps"]]
                link = next(i for i, r in enumerate(runs) if "ln -s /opt/uv/venv .venv" in r)
                assert all("uv " not in r for r in runs[:link]), (f.name, id_)


def test_codeql_scans_weekly_never_a_push_or_pr():
    """#560: a PR waiting on CodeQL's results stalled merges. #728: a run per push to main cost ~40 runs a day for two
    won't-fix alerts ever, so CodeQL scans Mondays (and on demand) into the Security tab."""
    on = yaml.safe_load((WORKFLOWS[0].parent / "codeql.yml").read_text())[True]
    assert set(on) == {"schedule", "workflow_dispatch"}


def test_dependabot_turns_on_auto_merge_as_the_bot_app():
    """#733: a merge whose auto-merge GITHUB_TOKEN turned on starts no push workflow on main, so Dependabot's bumps
    landed untested. The bot App turns it on, its token holding only what a merge needs (`workflows`: actions bumps
    edit workflow files), and the job's GITHUB_TOKEN gets nothing."""
    (job,) = yaml.safe_load((WORKFLOWS[0].parent / "dependabot-auto-merge.yml").read_text())["jobs"].values()
    assert job.get("permissions", {}) == {}
    app = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/create-github-app-token@"))
    assert {k for k in app["with"] if k.startswith("permission-")} == {
        "permission-contents",
        "permission-pull-requests",
        "permission-workflows",
    }
    merge = next(s for s in job["steps"] if "gh pr merge --auto" in s.get("run", ""))
    assert merge["env"]["GH_TOKEN"] == f"${{{{ steps.{app['id']}.outputs.token }}}}"


def test_bump_prs_open_through_create_pull_request():
    """#748: the weekly bumps open their PR with peter-evans/create-pull-request as the bot App, whose token holds only
    its own branch and the PR; no hand-rolled push or `gh pr` is left."""
    for name in ("blender-updates.yml", "skills-updates.yml"):
        jobs = yaml.safe_load((WORKFLOWS[0].parent / name).read_text())["jobs"].values()
        steps = [s for job in jobs for s in job["steps"]]
        app = next(s for s in steps if s.get("uses", "").startswith("actions/create-github-app-token@"))
        assert {k for k in app["with"] if k.startswith("permission-")} == {
            "permission-contents",
            "permission-pull-requests",
        }
        pr = next(s for s in steps if s.get("uses", "").startswith("peter-evans/create-pull-request@"))
        assert pr["with"]["token"] == f"${{{{ steps.{app['id']}.outputs.token }}}}"
        assert not [s for s in steps if "git push" in s.get("run", "") or "gh pr" in s.get("run", "")], name


def test_main_releases_itself_once_its_checks_pass():
    """#582, docs/adr/0017: semantic-release runs after this repo's push to main passed Checks, on that commit, one run
    at a time and never cancelled, as the bot App, so its tag starts Release Assets. No Release Please is left."""
    flow = yaml.safe_load((WORKFLOWS[0].parent / "release.yml").read_text())
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


@pytest.mark.parametrize(
    ("says", "exit", "summary"),
    [
        (
            "The local branch main is behind the remote one, therefore a new version won't be published.",
            0,
            "Not released: main moved past abc1234; the newer commit's run releases both.\n",
        ),
        ("Published release 1.2.3 on default channel", 0, ""),
        ("EGITNOPERMISSION Cannot push to the Git repository.", 1, ""),  # a failed release still fails the run
    ],
)
def test_a_release_main_moved_past_says_so_in_its_summary(tmp_path, says, exit, summary):
    """#773: semantic-release exits green and tags nothing when main moved past the commit, so the run's summary says
    why. Its step runs as GitHub runs a step with no `shell:` (`bash -e`, no pipefail), with semantic-release faked."""
    flow = yaml.safe_load((WORKFLOWS[0].parent / "release.yml").read_text())
    step = next(s for s in flow["jobs"]["release"]["steps"] if s["name"] == "Run semantic-release")
    bin_ = tmp_path / "ci" / "node_modules" / ".bin"
    bin_.mkdir(parents=True)
    (bin_ / "semantic-release").write_text(f'#!/bin/sh\necho "[semantic-release] › ℹ  {says}"\nexit {exit}\n')
    (bin_ / "semantic-release").chmod(0o755)
    env = {"PATH": "/usr/bin:/bin", "RUNNER_TEMP": str(tmp_path), "GITHUB_STEP_SUMMARY": f"{tmp_path}/summary"}
    done = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        cwd=tmp_path,
        env=env | {"SHA": "abc1234def5678"},
        capture_output=True,
        text=True,
    )
    assert (done.returncode, says in done.stdout) == (exit, True)
    assert (Path(env["GITHUB_STEP_SUMMARY"]).read_text() if summary else "") == summary
    assert step["env"]["SHA"] == "${{ github.event.workflow_run.head_sha }}"


def test_checks_deploys_the_site_it_built_as_its_last_job_on_mains_push():
    """#795, GitHub's Pages starter workflow: Checks' Deploy job deploys its own run's site after the gate passed, on
    main's push alone, so each github-pages Deployment records the commit built (GITHUB_SHA) and links its run; a
    workflow_run deploy stamped main's tip instead. Pages' permissions on that job alone; one deploy at a time, never
    cancelled. #731: no `deploy` commit status. #778, docs/adr/0021: the latest docs alone, nothing dispatches it."""
    wf = WORKFLOWS[0].parent
    flow = yaml.safe_load((wf / "checks.yml").read_text())
    job = flow["jobs"]["deploy"]
    assert list(flow["jobs"])[-1] == "deploy" and job["needs"] == "checks"
    assert job["if"] == "${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}"
    assert job["environment"]["name"] == "github-pages"
    assert job["concurrency"]["cancel-in-progress"] is False
    pages = {"pages": "write", "id-token": "write"}
    assert pages.items() <= job["permissions"].items() and "statuses" not in job["permissions"]
    assert [i for i, j in flow["jobs"].items() if pages.keys() & j.get("permissions", {}).keys()] == ["deploy"]
    download = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/download-artifact@"))
    assert "run-id" not in download["with"]  # this run's
    assert job["steps"][-1]["uses"].startswith("actions/deploy-pages@")
    assert not (wf / "site-deploy.yml").exists()
    release = yaml.safe_load((wf / "release-assets.yml").read_text())
    assert "docs" not in str(release["jobs"]) and "docs" not in str(job)
    assert not (wf.parent.parent / "scripts" / "docs_versions.py").exists()
    assert not (wf / "deploy-pending.yml").exists()
    assert not (wf.parent.parent / "scripts" / "deploy_status.py").exists()


def test_main_red_watches_checks_and_ci_images_and_files_its_issue_by_label():
    """#697, #729, #745: a renamed workflow would never be watched again, and an issue filed without the label it is
    found by would be filed again on every red run. A few lines of gh in the workflow do it all, no script."""
    flows = {f.name: yaml.safe_load(f.read_text()) for f in WORKFLOWS}
    watched = flows["main-red.yml"][True]["workflow_run"]["workflows"]  # yaml reads `on:` as True
    assert watched == [flows[f]["name"] for f in ("checks.yml", "ci-images.yml")]
    (job,) = flows["main-red.yml"]["jobs"].values()
    run = "\n".join(s.get("run", "") for s in job["steps"])
    assert '--label "$label" --json' in run and '--label "$label",' in run  # finds by it, files with it
    assert not (WORKFLOWS[0].parent.parent.parent / "scripts" / "main_red.py").exists()


def fake_gh(tmp_path: Path, jobs: list[dict]) -> dict[str, str]:
    """A `gh` that logs its first three arguments and answers `gh run view ... --json jobs --jq <filter>` with jq on
    `jobs`, so a step's own filter runs; `gh issue list` finds no open issue."""
    (tmp_path / "jobs.json").write_text(json.dumps({"jobs": jobs}))
    (tmp_path / "gh").write_text(
        "#!/bin/sh\n"
        f'echo "$1 $2 $3" >> {tmp_path}/gh.log\n'
        'if [ "$1 $2" = "run view" ]; then shift 2; while [ "$1" != --jq ]; do shift; done; '
        f'exec jq -r "$2" {tmp_path}/jobs.json; fi\n'
    )
    (tmp_path / "gh").chmod(0o755)
    return {"PATH": f"{tmp_path}:{os.environ['PATH']}", "RUN_ID": "41", "GITHUB_STEP_SUMMARY": "/dev/null"}


def gh_calls(tmp_path: Path) -> list[str]:
    log = tmp_path / "gh.log"
    return [c for c in log.read_text().splitlines() if not c.startswith("run view")] if log.exists() else []


CANCEL = {"name": "Cancel the run on failure", "if": "${{ failure() }}", "uses": "./.github/actions/cancel-on-failure"}


def needs(job: dict) -> list[str]:
    n = job.get("needs", [])
    return [n] if isinstance(n, str) else n


def test_a_failed_job_cancels_the_rest_of_its_run():
    """#769 (Cansin: across the board, PR CI too): a failed run can neither pass a PR's gate nor deploy or release main,
    and main's runs queue one at a time (#689; a 15-minute Blender held ~20 merges back), so every job of Checks and PR
    Gate but the gate ends in cancel-on-failure, the one job permission it adds `actions: write`, and a matrix fails
    fast. Every other workflow runs its jobs one after another (each needs the one before) or one per event, so a
    failed job leaves none running."""
    action = yaml.safe_load((WORKFLOWS[0].parents[1] / "actions" / "cancel-on-failure" / "action.yml").read_text())
    assert [s["run"] for s in action["runs"]["steps"]] == ['gh run cancel "$GITHUB_RUN_ID"']
    for f in ("checks.yml", "pr-gate.yml"):
        for id_, job in yaml.safe_load((WORKFLOWS[0].parent / f).read_text())["jobs"].items():
            cancels = id_ not in ("checks", "deploy")  # the gate, every job before it its need, and the deploy after
            assert (job["steps"][-1] == CANCEL) == cancels, (f, id_)
            assert (job.get("permissions", {}).get("actions") == "write") == cancels, (f, id_)
            assert job.get("strategy", {}).get("fail-fast", True) is True, (f, id_)
    side_by_side = []
    for f in WORKFLOWS:
        jobs = yaml.safe_load(f.read_text())["jobs"]
        if f.name in ("checks.yml", "pr-gate.yml", "issue-labels.yml"):  # issue-labels: a PR's job or an issue's
            continue
        before = {j: set(needs(jobs[j])) for j in jobs}
        for _ in jobs:  # every job's needs, theirs and so on
            before = {j: b.union(*(before[n] for n in b)) for j, b in before.items()}
        side_by_side += [
            (f.name, a, b) for a in jobs for b in jobs if a < b and a not in before[b] and b not in before[a]
        ]
    assert side_by_side == []


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is CI's image's (ci/base.Dockerfile)")
@pytest.mark.parametrize(
    ("conclusions", "calls"),
    [
        (["failure", "cancelled"], ["issue list --label", "issue create --title"]),  # its failed step cancelled it
        (["success", "cancelled"], ["issue list --label"]),  # cancelled by hand, nothing failed
        ([], ["issue list --label"]),  # superseded while it waited: no job ran
    ],
)
def test_main_red_files_a_cancelled_run_whose_job_failed(tmp_path, conclusions, calls):
    """#769: a failed step cancels its run (cancel-on-failure), its own job too, so run and job may read cancelled; a
    failed step still makes it red."""
    (job,) = yaml.safe_load((WORKFLOWS[0].parent / "main-red.yml").read_text())["jobs"].values()
    (step,) = job["steps"]
    jobs = [
        {"name": f"Job {i}", "conclusion": "cancelled", "steps": [{"conclusion": c}]} for i, c in enumerate(conclusions)
    ]
    env = fake_gh(tmp_path, jobs)
    env |= {"WORKFLOW": "Checks", "CONCLUSION": "cancelled", "RUN_URL": "u", "SHA": "s"}
    subprocess.run(["bash", "-eo", "pipefail", "-c", step["run"]], env=env, check=True, timeout=10)
    assert gh_calls(tmp_path) == calls


def test_an_issue_title_is_checked_by_mains_commitlint_and_flagged_never_blocked():
    """#767: an issue's title can become its PR's, so commitlint checks it on open and edit with main's config; a
    failing title gets a comment and `needs-title` (an issue can't be blocked), a passing one loses both."""
    flow = yaml.safe_load((WORKFLOWS[0].parent / "issue-title.yml").read_text())
    assert flow[True] == {"issues": {"types": ["opened", "edited"]}}
    assert flow["permissions"] == {}
    (job,) = flow["jobs"].values()
    assert job["permissions"] == {"issues": "write"}
    checkout = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout@"))
    assert "ci/commitlint.config.mjs" in checkout["with"]["sparse-checkout"]
    run = "\n".join(s.get("run", "") for s in job["steps"])
    assert "commitlint --config ci/commitlint.config.mjs" in run
    assert "--add-label needs-title" in run and "--remove-label needs-title" in run
    assert "github.event.issue.title" not in run  # via env, never inlined into the script


@pytest.mark.parametrize(
    ("workflow", "gh"),
    [  # the open `main-red` issue was retitled: still found, by its label (#767)
        ("Checks", "issue comment 771 --body Main's Checks failed on abc1234def: run"),
        # its own issue: a deploy says nothing about the images; titled a Conventional Commit from the start
        (
            "CI Images",
            "issue create --title fix(ci): main red in CI Images on abc1234 --label main-red-images,bug,ready-for-agent"
            " --body Main's CI Images failed on abc1234def: run",
        ),
    ],
)
def test_main_red_finds_its_open_issue_by_label_never_title(tmp_path, workflow, gh):
    """#767: Main Red found its issue by title, so retitling one opened a duplicate (#775). `gh` is faked: one open
    issue, #771, labelled `main-red` under any title, listed to a query that asks for no title."""
    (tmp_path / "gh").write_text(
        f'#!/bin/sh\ncase "$*" in "issue list --label main-red --json number --jq .[0].number // empty") echo 771 ;;\n'
        f'  "issue list"*) ;;\n  *) echo "$*" >> {tmp_path}/gh.log ;; esac\n'
    )
    (tmp_path / "gh").chmod(0o755)
    flow = yaml.safe_load((WORKFLOWS[0].parent / "main-red.yml").read_text())
    (job,) = flow["jobs"].values()
    env = {"PATH": f"{tmp_path}:/usr/bin:/bin", "WORKFLOW": workflow, "CONCLUSION": "failure", "RUN_ID": "1"}
    env |= {"RUN_URL": "run", "SHA": "abc1234def"}
    subprocess.run(["bash", "-e", "-c", job["steps"][0]["run"]], env=env, check=True)
    assert (tmp_path / "gh.log").read_text() == gh + "\n"
