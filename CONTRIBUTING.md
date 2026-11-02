# Contributing

Thanks for stopping by. noggin is a small hobby project, run in the open.

## How work runs

- Work starts from a GitHub issue (a ticket). Open one before a big change so the shape can be agreed first.
- The cycle, in order: grilling (interview only, nothing is built) → research and domain modelling as needed → plan/spec → TDD → code review → PR → retro.
- One PR per concern. Keep it small.
- Every ticket is built in its own worktree on its own branch, the worktree at `../noggin-wt/<session>/<branch>` (the
  session's name as ListAgents shows it, e.g. noggin-87, so two sessions never share a path; `make worktrees-clean`
  removes the worktrees of merged, closed or deleted branches), with a normal PR straight against main opened on the first
  push and auto-merge switched on right away (`gh pr merge --auto --squash`): the moment every required check is green
  and every review conversation is resolved, GitHub squash-merges it (the only method the repo allows) straight onto
  main, with no merge queue, then deletes the branch. Whoever works the ticket keeps that PR green and answers each
  review thread (a fix, or a reply saying why not) before resolving it. No integration or feature branches: a spec's
  tickets land on main one PR at a time. Main is protected: a green PR with one approval is the only way in. It need
  not be up to date with main: the rare break two green PRs make together is fixed forward on main (#283). The
  approval comes from Claude's review (claude[bot]) and is dismissed on every push, so each push is re-reviewed; a PR
  that edits review.yml gets no review and needs Cansin's bypass. So rebase a PR onto main only when GitHub reports a
  conflict, a required check was renamed, the PR needs a fix that just landed on main, or main's
  `.github/workflows/review.yml` changed since the branch's base (claude-code-action reviews only a PR whose
  review.yml matches main's, so `Review` fails with no verdict until then). The repo setting "Always suggest updating
  pull request branches" is off (Cansin, 2026-11-02), so GitHub shows no update-branch banner. CI runs on pushes to
  main and on ready (non-draft) PRs; every workflow runs only the latest commit of a PR or of main, cancelling the run
  in progress (main's site deploy included; a release tag's run and Release Please's are never cancelled), so a
  cancelled run means a newer one superseded it. A pushed branch is never merged locally: it lands through its own PR.
  Every branch on GitHub has a PR, except on-hold work.
- A PR's title is its squash commit, so it is a [Conventional Commit](https://www.conventionalcommits.org/en/v1.0.0/):
  `type(scope): subject`, `type(scope)!: subject` for a breaking change (docs/adr/0010), as
  @commitlint/config-conventional has it: types build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test;
  a subject that doesn't start with a capital (a leading acronym goes in backticks) or end with a period; at most 100
  characters. The scope is required, exactly one, derived from the repo: a tracked top-level folder (`eyes`, `web`,
  ...), a folder in docs/ (`adr`, `build`, ...), `deps` and `deps-dev` (dev dependencies) as Dependabot writes them,
  `release` for the release PR; `python3 scripts/pr_title.py` lists them (main's: a new folder is a scope once it
  lands). A body with a `BREAKING CHANGE:` footer needs the `!`. The required `PR Title` check
  (`.github/workflows/pr-checks.yml`) enforces it all (a bot's PR: its title's type and scope); editing the title or
  body re-runs it.
- A PR's body links its issue: `Closes #N` (or Fixes/Resolves, GitHub's closing keywords) for the issue it
  finishes, `Refs #N` for one it only moves along. The required `PR Issue` check (`.github/workflows/pr-checks.yml`,
  `scripts/pr_issue.py` as on main) fails without one; editing the body re-runs it. A bot's PR (release-please,
  Dependabot, the weekly bumps) has no issue and passes.
- Releases: the whole repo has one version, noggin vX.Y.Z, in `pyproject.toml` (docs/adr/0010). The `Release Please`
  workflow keeps a release PR (`chore(release): release noggin vX.Y.Z`) that bumps it and adds the CHANGELOG.md entry
  from the titles merged since the last release; a feat, fix or perf opens it, the other types ride along. It stays a
  draft, so no check runs on it, until it is ready: then it goes through the required checks and review like any PR, and
  auto-merges on green. It is ready when its newest changelog version has a Features or a BREAKING CHANGES section
  (`scripts/release_gate.py`); fixes alone wait for the next feature, or for the `Release Now` workflow (`gh workflow
  run release-now.yml`, or `/release`), which marks it ready, turns auto-merge on for whatever is pending and labels the
  PR `release now` to keep it on (only the App's own label counts). Merged, it tags `vX.Y.Z` and creates the GitHub
  release, and the tag's `Release Assets` run attaches the Core program zip and the release's docs, built under
  /noggin/vX.Y/ (docs/adr/0014), as the release's deployment in the `release` environment (Deployments panel), linked
  from the release's notes, and then deploys the site so those docs are live at once. Never edit the version, the
  manifest or CHANGELOG.md by hand. Both workflows run as the release GitHub App, because what `GITHUB_TOKEN` creates
  starts no workflow: a private App on yellow-pine, installed on this repo only, with Contents, Pull requests and Issues
  read and write and no webhook. Each run mints a short-lived token from the App's Client ID (the
  `RELEASE_APP_CLIENT_ID` variable) and private key (the `RELEASE_APP_PRIVATE_KEY` secret); until the variable exists
  Release Please only leaves a notice. The App's `<slug>[bot]` must be in review.yml's `allowed_bots`, or its release PR
  gets no review.
- Issue state labels, one per state: `ready-for-agent` (can start), `in-progress` (picked up and not in main yet:
  being worked on or waiting on its PR; a spec is in-progress from its first ticket until its
  last ticket reaches main), `blocked` (waits on something else, named in the issue: another ticket, hardware),
  `on-hold` (paused by Cansin). The `Issue Labels` workflow keeps them in step: a PR sets each issue its body links
  `in-progress` (dropping `ready-for-agent` and `blocked`), and closing an issue removes its state label; `blocked` and
  `on-hold` are otherwise set by hand.
- Skills (mattpocock's cycle and ponytail) are pinned in `skills-lock.json` to a commit (`ref`); the `skills` CLI
  (`ci/package.json`, `npm ci --prefix ci`, then `ci/node_modules/.bin/skills experimental_install`)
  restores them into `.agents/skills` (gitignored but for the project's own skill, `release`), which the committed
  `.claude/skills` link points at, and
  `node scripts/verify_skills.mjs` checks each against its `computedHash`. Bumps arrive as PRs: the weekly `skills`
  workflow re-pins to upstream HEAD (close and reopen its PR to start the checks, again after each refresh),
  Dependabot pins actions by SHA and bumps the CLI. Every Dependabot PR, majors too, gets auto-merge (`.github/workflows/dependabot.yml`)
  and merges once the required checks and Claude's review pass.
  Blender is pinned (version and the Linux tarball's sha256) in the workflows that run it; the weekly `blender`
  workflow re-pins it to the newest stable release at least 14 days old (`scripts/blender_pin.py`), the same way.
  Bots never commit to main: the `skills` and `blender` workflows only push their own `skills-bump` and `blender-bump`
  branches and open (or refresh) a PR from each, which goes through review like any other; main's ruleset rejects a
  bot's push.
- Every ready PR gets a Claude review: claude[bot] submits a real Approve or Request changes review, and the
  required `Review` check fails with it when Claude requests changes (a bug, a spec miss, a security issue or a breach
  of a documented rule; ponytail suggestions never block) or decides approve but no approval lands on the head (re-run
  the job; a hook refuses Claude's verdict until its review is on the head, #389) (`.github/workflows/review.yml`:
  mattpocock code-review plus ponytail). It needs the
  `CLAUDE_CODE_OAUTH_TOKEN` secret twice, for Actions and for Dependabot (whose PRs only see Dependabot secrets): run
  `claude setup-token`, then `gh secret set CLAUDE_CODE_OAUTH_TOKEN` and
  `gh secret set CLAUDE_CODE_OAUTH_TOKEN --app dependabot`.
- An agent building a ticket runs as the `implementer` subagent (`.claude/agents/implementer.md`), which carries the
  standing rules, so its brief is just the issue.
- Waiting on CI or a build: `gh pr checks --watch`, `gh run watch`, or a loop on the process's PID. Never `until ! pgrep -f <pattern>` (it matches itself) or a loop on a file count (it hangs when a build stops short).
- A Claude Code hook (`.claude/settings.json`, `.claude/hooks/bash_guard.py`) blocks the commands agents reach for
  against these rules (`git stash`, `gh pr merge --admin`, local heavy builds, a loop on `pgrep` or without a sleep),
  each with a one-line reason naming the allowed alternative.
- CI names follow GitHub's UI: every job a Title Case name (`Fetch Skills`, `Model (hero)`), every step a short
  sentence-case imperative like its `Set up job` (`test_workflows.py`). After renaming a required check, rename it in
  main's ruleset too and run `gh pr update-branch --rebase` on every open PR so it reports the new name.
- Each workflow has one header comment, right under `name:`, whose first line is its one-line purpose; the README's
  CI/CD table is generated from the workflows (`make readme`, #397) and `make check` fails while it is stale. Two PRs
  that conflict on a README table row: take either side, then run `make readme`.
- Vocabulary lives in `GLOSSARY.md` and the decisions in `docs/adr/`; use those words and record a new decision as a new ADR,
  numbered the next free one. When Code fails because main took that number since, run
  `.venv/bin/python scripts/adr_number.py docs/adr/NNNN-slug.md` and commit what it moved (docs/adr/0015).
- Secrets (a Wi-Fi password, a token) are typed in a Terminal window (`make wifi` for a new network), never at
  Claude Code's `!` prompt, which has no stdin.
- Hardware facts and calibration lessons are in the build guide, `docs/build/`. The Core's firmware is updated with the vendor's own tools only; esptool only for read-only queries (ADR 0012).

## Code

- Feature-first layout: `eyes/`, `noggin/`, `reactions/`, `model/`, `web/` (the viewer's GLBs), `mech/`, `ci/` (the CI
  images), `site/` (the site's npm package: its pages, the viewer's page and module, ADR 0013). Tests sit beside the
  code they test (`test_*.py`, `*.test.mjs` in the same folder).
- Smallest thing that works; no options or abstractions nobody asked for.
- Run `make check` before opening a PR: the `Code` set, everything but the tests marked `model`. `make check-all` adds
  those. The heavy targets (`make check-all`'s model tests, `test`, `sim`, `trajectories`, `render`, `gifs`, `hero`,
  `web`, `view`'s MJCF) take a machine-wide lock (`scripts/heavy.py`), so only one runs at a time and the next waits,
  saying for which process: several at once took the Mac to ~30 GB. CI runs everything (a PR what it touches, below), split over three required jobs
  (`.github/workflows/check.yml`): `Code` (`make check`), `Mech` (below) and `Model` (the `model` tests, `make
  view`'s scene rendered offscreen among them, and `make stl step` on main or when the parts changed, split into
  shards the `Shards` job reads from the code with `make model-shards-list`: the hero's sweep, the recorded sweep documents, each Stage and the rest, plus a sim shard), pytest
  on every core (pytest-xdist). The sim shard runs `make sim` only when what the reports are made from changed:
  their cache (`sim-`) is keyed on it, so a PR whose inputs match one of main's runs reuses its reports; otherwise it
  diffs the new reports against main's latest in its job summary. The reports are never committed: main's are on the
  site at /reports (ADR 0009). Site Checks' `Site` job caches npm's downloads by `site/package-lock.json`
  (setup-node), which pins Mermaid, three.js and mermaid-cli (ADR 0013); on a PR whose pictures and viewer are cached
  from the same inputs, neither Blender job runs and `site` restores them (#386). A cold parts cache is first cut part
  by part, one runner per part whose CoACD pieces are stale (`Convex`, `model/convex_parts.py`), so the model shards start warm.
  With a warm cache a run's critical path should stay within 3 min on a PR and 9 min on main; past it the run warns in
  its summary and never fails (#442; `scripts/ci_budget.py`: the longest chain of jobs along their `needs`, each timed
  from when a runner picked it up, so a busy queue never trips it; a "re-run failed jobs" is timed on its own attempt). Each job's
  slowest tests are in its run summary.
- The jobs that need a system tool uv can't install run in our CI images (ADR 0009, #288; ci/): Site Checks' `Site` and
  Code Checks' `Code` in `ci/base.Dockerfile`, `Render` and `Viewer` in `ci/blender.Dockerfile` (base plus Blender),
  pinned by digest (`container: image: ghcr.io/yellow-pine/noggin-ci-…:main@sha256:…`); every other job stays on the
  bare runner with setup-uv and apt, since an image pull costs ~30-40 s a job. The `CI Images` workflow (`images.yml`)
  builds them; only main writes to GHCR: it pushes `:main`, with its build provenance, when a Dockerfile changes and
  every Monday without cache, and Dependabot proposes the new digests within a day (the run's summary has the same pin
  as one command); that PR's checks are the first to run in them. A PR that changes a Dockerfile only builds the images
  (main's layer cache, read only).
- `make mech` runs the Link's live checks on the Mech stand-in (mech/): CI's `Mech` job (`check.yml`, beside `Code`
  and `Model`, so main's Code Checks cover all three, #295), on PRs touching eyes/, noggin/ or mech/ and on main. The
  site's `Site` and `Pictures` (Site Checks, `.github/workflows/site-checks.yml`) are required checks too: `Mech`,
  `Model`, `Site` and `Pictures` run on every PR, and a `Changes` job (dorny/paths-filter) skips the work when nothing
  it is made from changed (`test_derived.py` holds each filter to its inputs), which GitHub counts as passing; main
  runs everything. `Pictures` sums up the `Render` job's runners (one per
  motion of the README's pictures, a matrix the `Motions` job reads from the code with `make pictures-list`, #297)
  under one name.
- A PR runs checks; main runs the same checks, then deploys (#310). Site Checks build and test the site on both and
  upload it as an artifact; Site Deploy (`pages.yml`) runs only on main, once both Code Checks and Site Checks passed
  for the commit (#295), and deploys that very artifact (no rebuild) with main's newest sim reports at /reports and
  every release's docs at /vX.Y/ (`scripts/docs_versions.py`, docs/adr/0014). Main's
  commit carries a `deploy` status (#292): pending while Site Checks build, then success linking the site, failure
  linking the run (or the red check run: "not deployed: checks failed"), or error when a newer commit superseded it
  (`scripts/deploy_status.py`). A main commit is green only once its `deploy` is.

## Licence

noggin is licensed under PolyForm Noncommercial 1.0.0 (`LICENSE.md`). By contributing you agree that your contribution is licensed under the same terms, with Yellow Pine as the licensor.

Questions: hello@yellowpine.com.
