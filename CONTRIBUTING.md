# Contributing

Thanks for stopping by. noggin is a small hobby project, run in the open.

## How work runs

- Work starts from a GitHub issue (a ticket). Open one before a big change so the shape can be agreed first.
- The cycle, in order, on mattpocock's skills: grilling (interview only, nothing is built) → research and domain modelling as needed → plan/spec
  → TDD → code review → PR → retro. An agent building a ticket runs as the `implementer` subagent
  (`.claude/agents/implementer.md`), so its brief is just the issue.
- One PR per concern, kept small, built in its own worktree at `../noggin-wt/<session>/<branch>` (the session's name as
  ListAgents shows it, e.g. noggin-87, so two sessions never share a path; `just worktrees-clean` deletes the local
  branches whose PR merged or closed, and their clean worktrees, with gh-poi). Open the PR against main on the first push and turn auto-merge on at once
  (`gh pr merge --auto --squash`): GitHub squash-merges it once every required check is green and every review
  conversation resolved. No integration or feature branches: a spec's tickets land on main one PR at a time. Every
  branch on GitHub has a PR, except on-hold work.
- Whoever works the ticket keeps its PR green and answers each review thread (a fix, or a reply saying why not) before
  resolving it.
- Main is protected: a green PR with Claude's approval is the only way in. A PR merges on the slim gate (#696, #714:
  its title, `just check-light`) and main runs the rest, so what main catches (the site, the workflow linters, the
  model, the sim, Blender) is fixed forward on main by a new PR (#283), as is the rare break two green PRs make
  together: a PR need not be up to date with main. Bring main into a PR as a merge (`gh pr
  update-branch <n>`, or `git fetch && git merge origin/main`) only when GitHub reports a conflict, a required check was
  renamed or the PR needs a fix that just landed on main, and push plain commits, never a force-push: each push
  dismisses the approval and re-runs the review. GitHub shows no update-branch banner (the repo's "Always suggest
  updating pull request branches" is off, Cansin, 2026-11-02). A Dependabot PR gets `@dependabot rebase`.
- Every ready PR gets Claude's review (`.github/workflows/review.yml`: mattpocock code-review plus ponytail):
  claude[bot] approves or requests changes (a bug, a spec miss, a security issue or a breach of a documented rule;
  ponytail suggestions never block), and the required `Review` check fails with a request for changes, or when no
  approval lands on the head (re-run the job, #389). Its approval resolves its own threads a later push outdated
  (`scripts/claude_approved.py`). A PR that edits review.yml gets no review and needs Cansin's bypass. When main's
  review.yml changed since the branch's base, `Review` rebases the branch itself and fails, and the review re-runs on
  the new head (#433): `git pull --rebase` before your next push. It needs the `CLAUDE_CODE_OAUTH_TOKEN` secret twice,
  for Actions and for Dependabot (whose PRs only see Dependabot secrets): run `claude setup-token`, then `gh secret set
  CLAUDE_CODE_OAUTH_TOKEN` and `gh secret set CLAUDE_CODE_OAUTH_TOKEN --app dependabot`.
- A PR's title is its squash commit, with no body (the repo's squash message setting is blank, Cansin, 2026-11-02:
  #388's body forced v0.2.0), so semantic-release reads the title alone and a body footer never reaches main. The title is a
  [Conventional Commit](https://www.conventionalcommits.org/en/v1.0.0/): `type(scope): subject`,
  `type(scope)!: subject` for a breaking change (docs/adr/0010), as @commitlint/config-conventional has it: types
  build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test;
  a subject that doesn't start with a capital (a leading acronym goes in backticks) or end with a period; at most 100
  characters. The scope is required, exactly one, derived from the repo: a tracked top-level folder (`eyes`, `web`,
  ...), a folder in docs/ (`adr`, `build`, ...), `deps` and `deps-dev` (dev dependencies) as Dependabot writes them;
  `python3 scripts/pr_title.py` lists them (main's: a new folder is a scope once it
  lands). The required `PR` check
  (`.github/workflows/pr-checks.yml`) enforces it all (a bot's PR: its title's type and scope); editing the title
  re-runs it.
- A PR's body links its issue: `Closes #N` (or Fixes/Resolves, GitHub's closing keywords) for the issue it finishes,
  `Refs #N` for one it only moves along, or whose proof (measurements, screenshots from CI's run) is not in the body
  yet. The required `PR` check (`scripts/pr_issue.py` as on main) fails without one.
- Issue state labels, one per state: `ready-for-agent` (can start), `in-progress` (picked up and not in main yet; a spec
  from its first ticket until its last reaches main), `blocked` (waits on something named in the issue: another ticket,
  hardware), `on-hold` (paused by Cansin). `blocked` and `on-hold` are set by hand. The implementer sets `in-progress`
  on pickup; the `Issue Labels` workflow sets it too once a PR links the issue (the backstop for a PR opened by hand),
  and clears every state label when the issue closes.
- Releases: the whole repo has one version, noggin vX.Y.Z, and it is the git tag (docs/adr/0010, 0017; `pyproject.toml`
  holds a placeholder). Main releases itself: once a push to main passes Checks, `Release` (semantic-release,
  `.releaserc.json`) tags `vX.Y.Z` and writes the GitHub release's notes when a title merged since the last tag is a
  feat, fix, perf, revert or a `!` break (before 1.0 a break bumps the minor, the rest the patch); docs, ci, chore,
  build, test, style and refactor release nothing. The tag starts `Release Assets`, which attaches the Core program
  zip and the release's docs (docs/adr/0014). No release PR, nothing committed back; tag nothing by hand.
- The workflows that open PRs, push or merge (Release, the weekly `skills` and `blender` ones, `Review`'s
  rebase, Dependabot Auto-merge) run as the repo's bot App, because what `GITHUB_TOKEN` creates starts no workflow: a
  private App on yellow-pine, installed on this repo only, with Contents, Pull requests, Issues and Workflows read and
  write and no webhook, its Client ID in the `RELEASE_APP_CLIENT_ID` variable and its private key in the
  `RELEASE_APP_PRIVATE_KEY` secret, set twice like Claude's token: `gh secret set RELEASE_APP_PRIVATE_KEY` and `gh
  secret set RELEASE_APP_PRIVATE_KEY --app dependabot`. Its `<slug>[bot]` must be in review.yml's `allowed_bots`, or
  its PRs get no review.
- Skills (mattpocock's cycle and ponytail) are pinned in `skills-lock.json`. Restore them into `.agents/skills`
  (gitignored; the committed `.claude/skills` links there) with `npm ci
  --prefix ci`, then `ci/node_modules/.bin/skills experimental_install`; `node scripts/verify_skills.mjs` checks each
  against its `computedHash`.
- Bumps arrive as PRs and merge through checks and review like any other: the weekly `skills` workflow re-pins the
  skills to upstream HEAD, the weekly `blender` one re-pins Blender to the newest stable release at least 14 days old
  (`scripts/blender_pin.py`), each from its own `skills-bump` or `blender-bump` branch, opened or refreshed by
  peter-evans/create-pull-request (#748), and Dependabot pins actions by
  SHA and gets auto-merge on every PR, majors too. Bots never commit to main.
- Waiting on CI: one background command that exits only on a terminal state (merged, failed, or needs a human). `gh pr
  checks` exits 8 while any check is pending, and the sleeps cover the checks registering and auto-merge landing:
  `sleep 60; until gh pr checks N >/dev/null; [ $? != 8 ]; do sleep 60; done; sleep 60; gh pr view N --json
  state,mergeStateStatus,reviewDecision`. A build: `gh run watch`, or a loop with a sleep on its PID, which ends even when the build stops short.
- Claude Code's deny list (`permissions.deny` in `.claude/settings.json`) refuses `git stash` (work waits in commits),
  `gh pr merge --admin` and a push to main (a PR lands through auto-merge), and each heavy recipe as `just X` or `uv
  run just X` (`test_derived.py` holds it to the justfile's heavy group). It matches the command as written, so it
  catches a slip, not a workaround (#611); every other rule here holds because you follow it.
- Main's ruleset refuses a direct push, but an admin can still merge a PR with `gh pr merge --admin`; the deny list
  stops agents doing that, and its push-to-main entries are only a backup.
- Keep the session's own checkout clean and detached: `.claude/hooks/sync_checkout.py` fast-forwards it to origin/main
  at session start and before each subagent dispatch, so subagents load main's `.claude/agents/`, and blocks a dispatch
  once when that moved an agent's file (retry it). A dirty or branched checkout stays put, with a warning (#577).
- CI names follow GitHub's UI: every job a Title Case name (`Fetch Skills`, `Model (hero)`), every step a short
  sentence-case imperative like its `Set up job` (`test_workflows.py`). After renaming a required check, rename it in
  main's ruleset too (`Code` fails while the ruleset names a check no gate job does: `scripts/required_checks.py`) and
  run `gh pr update-branch` on every open PR so it reports the new name. A required check names a gate job, one
  without a matrix (today `PR`, `Checks`, `Fetch Skills`, `Review`), never a matrix job (#570).
- Each workflow has one header comment, right under `name:`, whose first line is its one-line purpose; the site's
  CI/CD page builds its table from them (docs/ci-cd.md, #425).
- Vocabulary lives in `GLOSSARY.md` and the decisions in `docs/adr/`; use those words and record a new decision as a new ADR,
  numbered the next free one. When Code fails because main took that number since, `git mv` the
  draft to the next free number and change the old number on the lines your branch added (docs/adr/0015).
- Secrets (a Wi-Fi password, a token) are typed in a Terminal window (`just wifi` for a new network), never at
  Claude Code's `!` prompt, which has no stdin.

## Code

- The code follows CLAUDE.md's directives.
- The recipes live in the `justfile` (docs/adr/0016; `just --list`). Add a new recipe beside related ones, never at
  the end of the file, where two PRs appending at once clash (#492).
- `just lint` (ruff and pyright) is the one local check, which the pre-push hook `just venv` turns on runs (#714).
  `just check-light` is the PR gate's `Code` job: `just lint` and the tests marked neither `model` nor `build`.
  Everything heavier is CI's on main: `just check` is its `Code` job (adding actionlint, zizmor and hadolint),
  `just check-all` adds the `model` tests. The heavy recipes take a machine-wide lock (`scripts/heavy.py`), so only one runs
  at a time: several at once took the Mac to ~30 GB.
- CI runs on pushes to main, on ready (non-draft) PRs and weekly on main, where it runs everything and deploys nothing.
  A ready PR runs the slim gate alone, within about 1.5 min (#696, #714): `PR`, `Review`, and PR Gate (`pr-gate.yml`,
  #722): `Code` (`just check-light`), then its `Checks`. Checks (`checks.yml`: Site, Convex, Model, the sim, Blender,
  the smoke) runs on main after the merge, CodeQL weekly (#728), and a red main files its own 'main red' issue (#697).
  Only the main session runs the full run on a branch (`gh workflow run checks.yml --ref <branch>`, #562), to debug a
  main failure; an implementer's branch runs the slim gate alone.
  Each workflow runs only the newest commit of a PR, so a cancelled PR run means a newer one superseded it: every
  workflow on `pull_request` keys its `concurrency` on itself and the PR with `cancel-in-progress` (#675,
  `test_workflows.py`); one on `pull_request` alone tests no event, so it lists no job every PR skips (#722). What
  Site Deploy and Release wait on (Checks) never cancels: main's runs queue and each finishes, so merges minutes apart
  still deploy; a newer push replaces a run still waiting, never one running (#689).
  Site Deploy, Release and Release Assets never cancel a run mid-way.
- The required `Checks` is PR Gate's gate (`.github/workflows/pr-gate.yml`, #722): it fails unless `Code` passed.
  Main's Checks (`.github/workflows/checks.yml`, #496) ends in a gate of the same name, which fails unless every job
  there passed or was skipped. Its `Changes` job (dorny/paths-filter, plus cache lookups) skips the work whose inputs
  did not change, against main's last commit whose Checks passed on a push (#471); `test_derived.py` holds each filter to its
  inputs. `Site` always runs: it builds the deploy.
- `Model` runs on four shards, `just mech` one of their units, balanced by the seconds CI measured in
  `model/durations.json`; `just model-durations <id>` refreshes it from a run's `durations-*` artifacts. A cold parts
  cache is built and cut in `Convex`, which saves it for the shards. CI renders no picture and bakes no GLB, and no
  workflow uploads an artifact or release asset with the parts, their cut, a picture or a GLB: every artifact of a
  public repo is anyone's, and today's parts derive from the designer's models (ADR 0019, `test_workflows.py`); the
  Actions cache carries them between jobs. The sim's reports are
  never committed: main's are on the site at /reports (ADR 0009), and a run that changes their inputs diffs its reports
  against main's last in its job summary.
- With a warm cache a run's critical path should stay within 2 min on a PR and 9 min on main; past it the run warns in
  its summary and never fails (#442; `scripts/ci_budget.py`). Each job's slowest tests are in its run summary.
- The jobs that need a system tool uv can't install run in our CI images (`ci/`, ADR 0009, #288) by their `:main` tag;
  every other job stays on the bare runner, since an image pull costs ~30-40 s a job. The base image carries the venv
  synced from uv.lock, which its jobs link as `.venv` (#725). Only main pushes the images, when a Dockerfile or the
  venv's inputs (uv.lock, pyproject.toml, .python-version) change and weekly, uncached, before the Monday image scan
  (#534), so a PR that changes a Dockerfile only builds them and its jobs still run main's.
- `just mech` runs the Link's live checks on the Mech stand-in (mech/), in a `Model` shard.
- Site Deploy deploys the very artifact Checks built, once main's Checks passed (#295, #310), from that Checks run
  (#731). The github-pages environment lists every deploy; Main Red reports a red Checks or Site Deploy run.

## Licence

noggin is licensed under PolyForm Noncommercial 1.0.0 (`LICENSE.md`). By contributing you agree that your contribution is licensed under the same terms, with Yellow Pine as the licensor.

Questions: hello@yellowpine.com.
