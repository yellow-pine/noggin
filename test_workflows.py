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
    """#773, GitHub's starter workflows: the name Title Case ("Claude Review"), the file its kebab-case form."""
    flows = {f.name: yaml.safe_load(f.read_text())["name"] for f in WORKFLOWS}
    wrong = {
        f: n for f, n in flows.items() if not (TITLE.fullmatch(n) and f == re.sub(r"\W+", "-", n).lower() + ".yml")
    }
    assert wrong == {}


def test_every_run_has_a_descriptive_title():
    """#773, #866: GitHub titles a push's run by its commit and a PR's or an issue's by its title, but a scheduled,
    dispatched or workflow_run run by the workflow's name alone. Those set `run-name`, a Conventional Commit
    (ci/commitlint.test.mjs lints it): 'ci(ci): weekly <Workflow> <what>', 'ci(ci): manual <Workflow> run by <actor>',
    or the triggering run's title as-is; an empty result keeps GitHub's title for the other events."""
    wrong = []
    for f in WORKFLOWS:
        flow = yaml.safe_load(f.read_text())
        on, name, title = flow[True], flow["name"], flow.get("run-name", "")
        on = set(on) if isinstance(on, (dict, list)) else {on}
        want = {
            "schedule": f"'ci(ci): weekly {name} ",
            "workflow_dispatch": f"format('ci(ci): manual {name} run by {{0}}', github.actor)",
            "workflow_run": "github.event.workflow_run.display_title",
        }
        parts = [w for e, w in want.items() if e in on]
        if parts and on - set(want) and not title.endswith(" || '' }}"):
            wrong.append((f.name, "keeps GitHub's title"))
        if not all(p in title for p in parts) or bool(parts) != bool(title):
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


def test_every_job_has_a_timeout():
    """#944: a hung Blender or sim never holds a runner for GitHub's six hours. Each limit is at least twice the job's
    longest measured run (its PR lists them); a job calling a reusable workflow takes its jobs' limits."""
    jobs = [(f.name, i, j) for f in WORKFLOWS for i, j in yaml.safe_load(f.read_text())["jobs"].items()]
    assert [(f, i) for f, i, j in jobs if "uses" not in j and not isinstance(j.get("timeout-minutes"), int)] == []


def test_no_workflow_runs_on_ubuntu_latest():
    """#392: `ubuntu-latest` moves under us when GitHub says so (26.04 from 2026-10-19); a named image moves when we
    do (ADR 0012)."""
    assert [f.name for f in WORKFLOWS if "ubuntu-latest" in f.read_text()] == []


def test_no_run_or_job_is_cancelled_early():
    """#944 (docs/adr/0009): a run cancelled early lists its real failures as `cancelled` (#937), so every run on a PR
    and on main runs to its end. No workflow has a concurrency group, which drops a queued run when a newer one comes;
    only Checks' Deploy and Release's Release keep a job's group, never cancelling one in progress, so a newer commit's
    deploy or release replaces a queued older one and an older site never lands after a newer."""
    flows = {f.name: yaml.safe_load(f.read_text()) for f in WORKFLOWS}
    assert [n for n, flow in flows.items() if "concurrency" in flow] == []
    assert [f.name for f in WORKFLOWS if "cancel-in-progress: true" in f.read_text()] == []
    groups = {
        (n, i): j["concurrency"] for n, flow in flows.items() for i, j in flow["jobs"].items() if "concurrency" in j
    }
    assert set(groups) == {("checks.yml", "deploy"), ("release.yml", "release")}
    assert all(g["cancel-in-progress"] is False and "${{" not in g["group"] for g in groups.values()), groups


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
    """claude-review.yml's `Check if the PR edits claude-review.yml`, then `Check the verdict`, with no structured
    output and `git` and `gh` faked: `git diff` lists `changed`, `gh` logs its arguments."""
    for tool, body in [("git", f"printf '%s\\n' {changed}"), ("gh", f'echo "$@" >> {tmp_path}/gh.log')]:
        (tmp_path / tool).write_text(f"#!/bin/sh\n{body}\n")
        (tmp_path / tool).chmod(0o755)
    flow = yaml.safe_load((Path(__file__).resolve().parent / ".github" / "workflows" / "claude-review.yml").read_text())
    run = {s.get("name"): s.get("run") for s in flow["jobs"]["review"]["steps"]}
    env = {"PATH": f"{tmp_path}:/usr/bin:/bin", "BASE": "main", "PR": "7", "GITHUB_OUTPUT": f"{tmp_path}/out"}

    def step(name: str, **more: str):
        return subprocess.run(
            ["bash", "-eo", "pipefail", "-c", run[name]], env=env | more, capture_output=True, text=True
        )

    step("Check if the PR edits claude-review.yml").check_returncode()
    edits = (tmp_path / "out").read_text().removeprefix("review=").strip() if (tmp_path / "out").exists() else ""
    done = step("Check the verdict", RESULT="", CONCLUSION=conclusion, APP_TOKEN=app_token, EDITS_REVIEW=edits)
    log = tmp_path / "gh.log"
    return done.returncode, done.stdout, log.read_text() if log.exists() else ""


@pytest.mark.parametrize(
    ("changed", "conclusion", "app_token", "code", "says", "gh"),
    [
        # the action skipped on validation (no conclusion: Claude never ran), main's claude-review.yml moved on (#433)
        ("noggin/x.py", "", "t", 1, "branch updated, the review re-runs", "pr update-branch 7 --rebase\n"),
        ("noggin/x.py", "", "", 1, "changed since this branch: rebase it", ""),  # Dependabot's: no App token
        # needs Cansin's bypass
        (".github/workflows/claude-review.yml", "", "", 0, "claude-review.yml changed in this PR", ""),
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
    look's approval, its Checks a real one)."""
    flow = yaml.safe_load((WORKFLOWS[0].parent / "checks.yml").read_text())
    assert "cron" in flow[True]["schedule"][0]
    assert "workflow_dispatch" in flow[True]
    steps = {s.get("id"): s for s in flow["jobs"]["changes"]["steps"]}
    assert steps["filter"]["if"] == FULL
    assert steps["filter"]["with"]["base"] == "${{ steps.checked.outputs.sha }}"  # main's last green commit


# a run that looks up the outputs cached for its inputs: a push's and Release's manual one (#839), never the weekly or a
# dispatch on any branch
CACHED = "${{ github.event_name != 'schedule' && (github.event_name != 'workflow_dispatch' || inputs.deploy) }}"


def test_release_s_manual_run_renders_and_simulates_only_what_changed():
    """#839: Release's manual run (workflow_call with deploy, its event the caller's dispatch) looks up the Mech's
    pictures and the sim reports cached for the same inputs, as a push's run does; the weekly run and a dispatch on any
    branch still render and simulate everything, the lookups' safety net."""
    flow = yaml.safe_load((WORKFLOWS[0].parent / "checks.yml").read_text())
    assert flow[True]["workflow_call"]["inputs"]["deploy"]["default"] is False
    steps = {s.get("id"): s for s in flow["jobs"]["changes"]["steps"]}
    assert steps["pictures"]["if"] == steps["sim"]["if"] == CACHED


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


def test_ci_draws_uploads_and_serves_the_mech_alone():
    """#640, #649 (docs/adr/0019): a public repo's artifacts and release assets are anyone's to download, so the
    workflows render and bake the Mech alone (just pictures all, just web all), upload only the site, never a
    part, its cut, a mesh or a frame, put only the pictures and GLBs the Model publishes in the site, and attach none
    of it to a release (no release's docs since #778, docs/adr/0021). The Actions cache carries the parts between
    jobs: nobody outside the repo's workflows reads it."""
    from model.render import pictures

    steps = [
        s for f in WORKFLOWS for job in yaml.safe_load(f.read_text())["jobs"].values() for s in job.get("steps", [])
    ]
    runs = [s.get("run", "") for s in steps]
    drawn = {(m[1], m[2].strip()) for r in runs for m in BLENDER.finditer(r)}
    assert drawn == {("pictures", pictures.ALL), ("web", pictures.ALL)}
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
    # what just pictures and just web make (pictures.published, build.PUBLIC, test_site.py), nothing else
    assert into_site == ["model/build/images/*.webp", "web/build/*.glb"]
    assert not [r for r in runs if re.search(r"gh release upload|curl", r) and DERIVED.search(r)]


def test_render_builds_the_parts_and_trajectories_once_and_saves_what_site_restores():
    """#898: six stills no longer need eight shards: one Render job draws the pictures and the GLBs on the parts and
    trajectories it built once, and saves them under the one key Site restores."""
    jobs = yaml.safe_load((WORKFLOWS[0].parent / "checks.yml").read_text())["jobs"]
    render = jobs["render"]
    assert "strategy" not in render and "blender" not in jobs
    drawn = [m[1] for s in render["steps"] for m in BLENDER.finditer(s.get("run", ""))]
    assert drawn == ["pictures", "web"]
    (saved,) = [s["with"]["key"] for s in render["steps"] if "cache/save" in s.get("uses", "")]
    restored = [s["with"]["key"] for s in jobs["site"]["steps"] if "cache/restore" in s.get("uses", "")]
    assert saved == "pictures-${{ needs.changes.outputs.pictures-hash }}" and saved in restored
    assert "render" in jobs["site"]["needs"]


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
    Checks that wrote; every job reads alone, in main's Checks as in a PR's gate (#722), and main's Deploy writes Pages
    (#795). No job cancels its own run any more (#944)."""
    for f in ("checks.yml", "pr-gate.yml"):
        flow = yaml.safe_load((WORKFLOWS[0].parent / f).read_text())
        jobs = [j for i, j in flow["jobs"].items() if i != "deploy"]
        perms = [flow["permissions"], *(j.get("permissions", {}) for j in jobs)]
        assert not [p for p in perms if "write" in p.values()], f


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
    Dockerfiles in main's Code job, so a broken Dockerfile files a `default branch images failure` issue
    (default-branch-failure.yml)."""
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
    job = flow["jobs"]["release"]
    assert job["concurrency"]["cancel-in-progress"] is False and "${{" not in job["concurrency"]["group"]
    for cond in ("conclusion == 'success'", "event == 'push'", "head_repository.full_name == github.repository"):
        assert f"github.event.workflow_run.{cond}" in job["if"], cond
    steps = {s["name"]: s for s in job["steps"]}
    app = next(s for s in steps.values() if s.get("uses", "").startswith("actions/create-github-app-token@"))
    checkout = next(s for s in steps.values() if s.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["ref"] == "${{ env.SHA }}"
    assert job["env"]["SHA"] == "${{ github.event.workflow_run.head_sha || github.sha }}"
    assert checkout["with"]["fetch-depth"] == 0  # every tag, and the commits since the last
    release = next(s for s in steps.values() if "semantic-release" in s.get("run", ""))
    assert release["env"]["GITHUB_TOKEN"] == f"${{{{ steps.{app['id']}.outputs.token }}}}"
    root = WORKFLOWS[0].parent.parent.parent
    left = ["release-please.yml", "release-now.yml"]
    assert not [f for f in left if (WORKFLOWS[0].parent / f).exists()]
    assert not [f for f in ("release-please-config.json", ".release-please-manifest.json") if (root / f).exists()]


def test_a_manual_release_runs_the_full_checks_then_tags_the_commit_they_passed():
    """#802: Release's dispatch on main runs Checks itself (checks.yml's workflow_call, its Deploy on), and tags only
    once they passed, on main when that commit is still main's tip, else from a branch of its own at it, deleted after,
    so main moving on stops nothing. Its bump is auto, patch, minor or major (release.config.mjs); main's push run is
    unchanged."""
    wf = WORKFLOWS[0].parent
    flow = yaml.safe_load((wf / "release.yml").read_text())
    bump = flow[True]["workflow_dispatch"]["inputs"]["bump"]
    assert (bump["options"], bump["default"]) == (["auto", "patch", "minor", "major"], "auto")
    checks, release = flow["jobs"]["checks"], flow["jobs"]["release"]
    assert checks["uses"] == "./.github/workflows/checks.yml" and checks["with"] == {"deploy": True}
    assert "github.ref == 'refs/heads/main'" in checks["if"]
    assert release["needs"] == "checks" and "needs.checks.result == 'success'" in release["if"]
    called = yaml.safe_load((wf / "checks.yml").read_text())
    assert called[True]["workflow_call"]["inputs"]["deploy"] == {"type": "boolean", "default": False}
    # every scope a called job asks for, granted at least at its level: a nested job asking more makes Release invalid
    level = {"none": 0, "read": 1, "write": 2}
    asked = [(k, v) for j in called["jobs"].values() for k, v in j.get("permissions", {}).items()]
    assert [(k, v) for k, v in asked if level[checks["permissions"].get(k, "none")] < level[v]] == []
    steps = {s["name"]: s for s in release["steps"]}
    assert steps["Check whether main moved on"]["if"] == "${{ github.event_name == 'workflow_dispatch' }}"
    moved = "${{ steps.tip.outputs.branch != '' }}"
    assert steps["Open the release branch"]["if"] == steps["Mint the branch's token"]["if"] == moved
    assert steps["Delete the release branch"]["if"] == "${{ always() && steps.branch.outcome == 'success' }}"
    for name in ("Open the release branch", "Run semantic-release", "Delete the release branch"):
        assert steps[name]["env"]["BRANCH"] == "${{ steps.tip.outputs.branch }}", name
    assert steps["Run semantic-release"]["env"]["RELEASE_BUMP"] == "${{ inputs.bump }}"
    # a ref at a commit with workflow files takes the Workflows permission (run 41579675814's 403), in a token of the
    # branch's own: semantic-release's holds contents alone (#842's security review)
    tokens = {s["id"]: s for s in release["steps"] if s.get("uses", "").startswith("actions/create-github-app-token@")}
    perms = {i: {k: v for k, v in s["with"].items() if k.startswith("permission-")} for i, s in tokens.items()}
    assert perms == {
        "app": {"permission-contents": "write"},
        "branch-app": {"permission-contents": "write", "permission-workflows": "write"},
    }
    token = "${{{{ steps.{}.outputs.token }}}}".format
    assert steps["Run semantic-release"]["env"]["GITHUB_TOKEN"] == token("app")
    for name in ("Open the release branch", "Delete the release branch"):
        assert steps[name]["env"]["GH_TOKEN"] == token("branch-app"), name


@pytest.mark.parametrize(("tip", "opened"), [("abc1234def5678", False), ("fff0000aaa1111", True)])
def test_a_manual_release_opens_its_branch_only_when_main_moved_past_its_commit(tmp_path, tip, opened):
    """#802: on main's tip the manual run releases main as a push does, with no branch; once main moved past the
    commit it checked, it names release-<run id> for the steps after, which open it there. git faked: `git ls-remote`
    prints main's tip `tip` as git does."""
    flow = yaml.safe_load((WORKFLOWS[0].parent / "release.yml").read_text())
    step = next(s for s in flow["jobs"]["release"]["steps"] if s["name"] == "Check whether main moved on")
    (tmp_path / "git").write_text(f'#!/bin/sh\nprintf "{tip}\\trefs/heads/main\\n"\n')
    (tmp_path / "git").chmod(0o755)
    out = tmp_path / "output"
    done = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        env={
            "PATH": f"{tmp_path}:/usr/bin:/bin",
            "GITHUB_OUTPUT": str(out),
            "SHA": "abc1234def5678",
            "GITHUB_RUN_ID": "42",
        },
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr
    assert (out.read_text() if out.exists() else "") == ("branch=release-42\n" if opened else "")


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
        ("There are no relevant changes, so no new version is released.", 0, ""),  # main's push: as before
    ],
)
def test_a_release_main_moved_past_says_so_in_its_summary(tmp_path, says, exit, summary):
    """#773: semantic-release exits green and tags nothing when main moved past the commit, so the run's summary says
    why. Its step runs as GitHub runs a step with no `shell:` (`bash -e`, no pipefail), with semantic-release faked."""
    done, read = release_step(tmp_path, says, exit, {})
    assert (done.returncode, says in done.stdout, "--branches" in done.stdout) == (exit, True, False)
    assert read() == summary


NO_CHANGES = "There are no relevant changes, so no new version is released."


@pytest.mark.parametrize(
    ("says", "bump", "summary"),
    [
        (NO_CHANGES, "minor", "Not released: no commit since the last tag, so nothing to release at a forced minor.\n"),
        (NO_CHANGES, "auto", "Not released: no commit since the last tag is a feat, fix, perf, revert or a break.\n"),
        ("Published release 1.2.3 on default channel", "patch", ""),
    ],
)
@pytest.mark.parametrize("branch", ["release-42", ""])
def test_a_manual_release_releases_its_own_branch_and_says_why_it_tagged_nothing(tmp_path, says, bump, summary, branch):
    """#802: the manual run hands semantic-release its branch when it opened one (`--branches`, and GITHUB_REF, which
    env-ci reads), else main as a push does, and a run that tags nothing says why in its summary."""
    done, read = release_step(tmp_path, says, 0, {"BRANCH": branch, "RELEASE_BUMP": bump})
    ref = f"args: --branches {branch} ref: refs/heads/{branch}" if branch else "args:  ref: refs/heads/main"
    assert done.returncode == 0 and ref in done.stdout
    assert read() == summary


def release_step(tmp_path, says, exit, env):
    """Release's semantic-release step as GitHub runs a step with no `shell:` (`bash -e`, no pipefail), with
    semantic-release faked: it says `says`, echoes its arguments and GITHUB_REF, and exits `exit`."""
    flow = yaml.safe_load((WORKFLOWS[0].parent / "release.yml").read_text())
    step = next(s for s in flow["jobs"]["release"]["steps"] if s["name"] == "Run semantic-release")
    bin_ = tmp_path / "ci" / "node_modules" / ".bin"
    bin_.mkdir(parents=True)
    fake = f'#!/bin/sh\necho "[semantic-release] › ℹ  {says}"\necho "args: $* ref: $GITHUB_REF"\nexit {exit}\n'
    (bin_ / "semantic-release").write_text(fake)
    (bin_ / "semantic-release").chmod(0o755)
    summary = tmp_path / "summary"
    base = {"PATH": "/usr/bin:/bin", "RUNNER_TEMP": str(tmp_path), "GITHUB_STEP_SUMMARY": str(summary)}
    done = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        cwd=tmp_path,
        env=base | {"SHA": "abc1234def5678", "GITHUB_REF": "refs/heads/main"} | env,
        capture_output=True,
        text=True,
    )
    return done, lambda: summary.read_text() if summary.exists() else ""


def test_checks_deploys_the_site_it_built_as_its_last_job_on_mains_push():
    """#795, GitHub's Pages starter workflow: Checks' Deploy job deploys its own run's site after the gate passed, on
    main's push alone, so each github-pages Deployment records the commit built (GITHUB_SHA) and links its run; a
    workflow_run deploy stamped main's tip instead. Pages' permissions on that job alone; one deploy at a time, never
    cancelled. #731: no `deploy` commit status. #778, docs/adr/0021: the latest docs alone, nothing dispatches it."""
    wf = WORKFLOWS[0].parent
    flow = yaml.safe_load((wf / "checks.yml").read_text())
    job = flow["jobs"]["deploy"]
    assert list(flow["jobs"])[-1] == "deploy" and job["needs"] == "checks"
    # main's push, or Release's manual run (#802). Past a job skipped further up (a warm Convex, a cached Blender): an
    # `if` with no status function is `success() && ...`, false when any job before it was skipped, its need passed or
    # not, which skipped the first manual run's Deploy (#802); so the gate's success by name, as Model does Convex's
    assert job["if"] == (
        "${{ !cancelled() && needs.checks.result == 'success' && (github.event_name == 'push' || inputs.deploy) "
        "&& github.ref == 'refs/heads/main' }}"
    )
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


def test_default_branch_failure_watches_checks_and_ci_images_and_files_its_issue_by_label():
    """#697, #729, #745: a renamed workflow would never be watched again, and an issue filed without the label it is
    found by would be filed again on every red run. A few lines of gh in the workflow do it all, no script."""
    flows = {f.name: yaml.safe_load(f.read_text()) for f in WORKFLOWS}
    watched = flows["default-branch-failure.yml"][True]["workflow_run"]["workflows"]  # yaml reads `on:` as True
    assert watched == [flows[f]["name"] for f in ("checks.yml", "ci-images.yml")]
    (job,) = flows["default-branch-failure.yml"]["jobs"].values()
    run = "\n".join(s.get("run", "") for s in job["steps"])
    assert '--label "$label" --json' in run and '--label "$label,' in run  # finds by it, files with it
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


def test_no_job_cancels_its_run_and_a_matrix_keeps_githubs_fail_fast():
    """#944: cancel-on-failure (#769) cancelled the whole run at a job's first failed step, its own job too, so a real
    failure read `cancelled` (#937); it is gone, with the `actions: write` it took. A matrix keeps GitHub's default
    fail-fast, but Image Scan, whose two images are scanned apart."""
    assert not (WORKFLOWS[0].parents[1] / "actions" / "cancel-on-failure").exists()
    assert [f.name for f in WORKFLOWS if "cancel-on-failure" in f.read_text() or "run cancel" in f.read_text()] == []
    jobs = {(f.name, i): j for f in WORKFLOWS for i, j in yaml.safe_load(f.read_text())["jobs"].items()}
    fail_fast = {k: j["strategy"]["fail-fast"] for k, j in jobs.items() if "fail-fast" in j.get("strategy", {})}
    assert fail_fast == {("image-scan.yml", "scan"): False}


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is CI's image's (ci/base.Dockerfile)")
@pytest.mark.parametrize("conclusion", ["cancelled", "timed_out", "startup_failure"])
def test_default_branch_failure_files_a_failed_run_alone(tmp_path, conclusion):
    """#944: no run is cancelled early, so a red run ends as `failure`; any other run, a cancelled one past a failed
    job too, starts no report and, run anyway, files nothing. A success still closes the issue."""
    (job,) = yaml.safe_load((WORKFLOWS[0].parent / "default-branch-failure.yml").read_text())["jobs"].values()
    assert 'contains(fromJSON(\'["failure", "success"]\'), github.event.workflow_run.conclusion)' in job["if"]
    (step,) = job["steps"]
    env = fake_gh(tmp_path, [{"name": "Code", "conclusion": "failure", "steps": [{"conclusion": "failure"}]}])
    env |= {"WORKFLOW": "Checks", "CONCLUSION": conclusion, "RUN_URL": "u", "SHA": "s"}
    subprocess.run(["bash", "-eo", "pipefail", "-c", step["run"]], env=env, check=True, timeout=10)
    assert gh_calls(tmp_path) == ["issue list --label"]


def test_an_issue_title_is_checked_by_mains_commitlint_and_flagged_never_blocked():
    """#767: an issue's title can become its PR's, so commitlint checks it on open and edit with main's config; a
    failing title gets a comment and `needs title` (an issue can't be blocked), a passing one loses both."""
    flow = yaml.safe_load((WORKFLOWS[0].parent / "issue-title.yml").read_text())
    assert flow[True] == {"issues": {"types": ["opened", "edited"]}}
    assert flow["permissions"] == {}
    (job,) = flow["jobs"].values()
    assert job["permissions"] == {"issues": "write"}
    checkout = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout@"))
    assert "ci/commitlint.config.mjs" in checkout["with"]["sparse-checkout"]
    run = "\n".join(s.get("run", "") for s in job["steps"])
    assert "commitlint --config ci/commitlint.config.mjs" in run
    assert '--add-label "needs title"' in run and '--remove-label "needs title"' in run
    assert "github.event.issue.title" not in run  # via env, never inlined into the script


FILED = "issue create --title fix({}): `{}` fail on the default branch at abc1234{} --label {},bug,ready for agent"
FILED += " --body "


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is CI's image's (ci/base.Dockerfile)")
@pytest.mark.parametrize(
    ("workflow", "failed", "open_issue", "gh"),
    [  # a Conventional Commit from the start, scoped by the failed job, named at the end (#791)
        ("Checks", "Model (2)", "", FILED.format("model", "Checks", " (Model)", "default branch failure")),
        ("Checks", "Site", "", FILED.format("site", "Checks", " (Site)", "default branch failure")),
        ("Checks", "Code", "", FILED.format("ci", "Checks", " (Code)", "default branch failure")),
        # its own issue: a deploy says nothing about the images
        ("CI Images", "Push", "", FILED.format("ci", "CI Images", "", "default branch images failure")),
        # the open issue was retitled: still found, by its label (#767), and a later failure only comments on it
        ("Checks", "Site", "default branch failure", "issue comment 771 --body "),
    ],
)
def test_default_branch_failure_files_one_issue_by_label_titled_by_the_failed_job(
    tmp_path, workflow, failed, open_issue, gh
):
    """#767: Default Branch Failure found its issue by title, so retitling one opened a duplicate (#775). #791: its
    title names the workflow and the failed job, its scope that job's. `gh` is faked: the run's jobs, answered with the
    step's own jq filter, and at most one open issue, #771, under any title, listed to a query that asks for no title.
    """
    jobs = [{"name": "Changes", "conclusion": "success"}, {"name": failed, "conclusion": "failure"}]
    (tmp_path / "jobs.json").write_text(json.dumps({"jobs": jobs}))
    (tmp_path / "gh").write_text(
        '#!/bin/sh\ncase "$*" in\n'
        f'  "issue list --label {open_issue} --json number --jq .[0].number // empty") echo 771 ;;\n'
        '  "issue list"*) ;;\n'
        '  "run view"*) shift 2; while [ "$1" != --jq ]; do shift; done;'
        f' exec jq -r "$2" {tmp_path}/jobs.json ;;\n'
        f'  *) echo "$*" >> {tmp_path}/gh.log ;; esac\n'
    )
    (tmp_path / "gh").chmod(0o755)
    (job,) = yaml.safe_load((WORKFLOWS[0].parent / "default-branch-failure.yml").read_text())["jobs"].values()
    env = {"PATH": f"{tmp_path}:{os.environ['PATH']}", "WORKFLOW": workflow, "CONCLUSION": "failure", "RUN_ID": "1"}
    env |= {"RUN_URL": "run", "SHA": "abc1234def"}
    subprocess.run(["bash", "-e", "-c", job["steps"][0]["run"]], env=env, check=True, timeout=10)
    body = f"{workflow} failed on the default branch at abc1234def in {failed}: run"
    assert (tmp_path / "gh.log").read_text() == gh + body + "\n"
