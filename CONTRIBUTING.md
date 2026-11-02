# Contributing

Thanks for stopping by. noggin is a small hobby project, run in the open.

## How work runs

- Work starts from a GitHub issue (a ticket). Open one before a big change so the shape can be agreed first.
- The cycle, in order, on mattpocock's skills: grilling (interview only, nothing is built) → research and domain modelling as needed → plan/spec
  → TDD → code review → PR → retro. An agent building a ticket runs as the `implementer` subagent
  (`.claude/agents/implementer.md`), so its brief is just the issue.
- One PR per concern, kept small, built in its own worktree at `../noggin-wt/<session>/<branch>` (the session's name as
  ListAgents shows it, e.g. noggin-87, so two sessions never share a path; `just worktrees-clean` removes the worktrees
  of merged, closed or deleted branches). Open the PR against main on the first push and turn auto-merge on at once
  (`gh pr merge --auto --squash`): GitHub squash-merges it once every required check is green and every review
  conversation resolved. No integration or feature branches: a spec's tickets land on main one PR at a time. Every
  branch on GitHub has a PR, except on-hold work.
- Whoever works the ticket keeps its PR green and answers each review thread (a fix, or a reply saying why not) before
  resolving it.
- Main is protected: a green PR with Claude's approval is the only way in. A PR need not be up to date with main: the
  rare break two green PRs make together is fixed forward on main (#283). Bring main into a PR as a merge (`gh pr
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
  #388's body forced v0.2.0), so release-please reads the title alone, a body footer never reaches main, and a forced version goes in
  `release-as` in release-please-config.json, taken out once that release lands. The title is a
  [Conventional Commit](https://www.conventionalcommits.org/en/v1.0.0/): `type(scope): subject`,
  `type(scope)!: subject` for a breaking change (docs/adr/0010), as @commitlint/config-conventional has it: types
  build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test;
  a subject that doesn't start with a capital (a leading acronym goes in backticks) or end with a period; at most 100
  characters. The scope is required, exactly one, derived from the repo: a tracked top-level folder (`eyes`, `web`,
  ...), a folder in docs/ (`adr`, `build`, ...), `deps` and `deps-dev` (dev dependencies) as Dependabot writes them,
  `release` for the release PR; `python3 scripts/pr_title.py` lists them (main's: a new folder is a scope once it
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
- Releases: the whole repo has one version, noggin vX.Y.Z, in `pyproject.toml` (docs/adr/0010). Release Please keeps a
  release PR that bumps it and adds the CHANGELOG.md entry from the titles merged since the last release. It stays a
  draft until its newest version has a Features or a BREAKING CHANGES section (`scripts/release_gate.py`); fixes alone
  wait for the next feature, or for `gh workflow run release-now.yml` (or `/release`). Merged, it tags `vX.Y.Z`, and
  `Release Assets` attaches the Core program zip and the release's docs (docs/adr/0014). Never edit the version, the
  manifest or CHANGELOG.md by hand.
- The workflows that open PRs or push (Release Please, Release Now, the weekly `skills` and `blender` ones, `Review`'s
  rebase) run as the repo's bot App, because what `GITHUB_TOKEN` creates starts no workflow: a private App on
  yellow-pine, installed on this repo only, with Contents, Pull requests, Issues and Workflows read and write and no
  webhook, its Client ID in the `RELEASE_APP_CLIENT_ID` variable and its private key in the `RELEASE_APP_PRIVATE_KEY`
  secret. Its `<slug>[bot]` must be in review.yml's `allowed_bots`, or its PRs get no review.
- Skills (mattpocock's cycle and ponytail) are pinned in `skills-lock.json`. Restore them into `.agents/skills`
  (gitignored but for the project's own `release` skill; the committed `.claude/skills` links there) with `npm ci
  --prefix ci`, then `ci/node_modules/.bin/skills experimental_install`; `node scripts/verify_skills.mjs` checks each
  against its `computedHash`.
- Bumps arrive as PRs and merge through checks and review like any other: the weekly `skills` workflow re-pins the
  skills to upstream HEAD, the weekly `blender` one re-pins Blender to the newest stable release at least 14 days old
  (`scripts/blender_pin.py`), each from its own `skills-bump` or `blender-bump` branch, and Dependabot pins actions by
  SHA and gets auto-merge on every PR, majors too. Bots never commit to main.
- Waiting on CI: one background command that exits only on a terminal state (merged, failed, or needs a human). `gh pr
  checks` exits 8 while any check is pending, and the sleeps cover the checks registering and auto-merge landing:
  `sleep 60; until gh pr checks N >/dev/null; [ $? != 8 ]; do sleep 60; done; sleep 60; gh pr view N --json
  state,mergeStateStatus,reviewDecision`. A build: `gh run watch`, or a loop with a sleep on its PID, which ends even when the build stops short.
- A Claude Code hook (`.claude/hooks/bash_guard.py`) blocks the commands these rules ban, each with a one-line reason
  naming the allowed alternative.
- CI names follow GitHub's UI: every job a Title Case name (`Fetch Skills`, `Model (hero)`), every step a short
  sentence-case imperative like its `Set up job` (`test_workflows.py`). After renaming a required check, rename it in
  main's ruleset too (`Code` fails while the ruleset names a check no gate job does: `scripts/required_checks.py`) and
  run `gh pr update-branch` on every open PR so it reports the new name. A required check names a gate job, one
  without a matrix (today `PR`, `Checks`, `Fetch Skills`, `Review`), never a matrix job (#570).
- Each workflow has one header comment, right under `name:`, whose first line is its one-line purpose; the site's
  CI/CD page builds its table from them (docs/ci-cd.md, #425).
- Vocabulary lives in `GLOSSARY.md` and the decisions in `docs/adr/`; use those words and record a new decision as a new ADR,
  numbered the next free one. When Code fails because main took that number since, run
  `.venv/bin/python scripts/adr_number.py docs/adr/NNNN-slug.md` and commit what it moved (docs/adr/0015).
- Secrets (a Wi-Fi password, a token) are typed in a Terminal window (`just wifi` for a new network), never at
  Claude Code's `!` prompt, which has no stdin.

## Code

- The code follows CLAUDE.md's directives.
- The recipes live in the `justfile` (docs/adr/0016; `just --list`). Add a new recipe beside related ones, never at
  the end of the file, where two PRs appending at once clash (#492).
- `just check-light` is the local check (the pre-push hook `just venv` turns on runs it): lint, types and the tests
  marked neither `model` nor `build`, in seconds. Everything heavier is CI's: `just check` is its `Code` job, `just
  check-all` adds the `model` tests. The heavy recipes take a machine-wide lock (`scripts/heavy.py`), so only one runs
  at a time: several at once took the Mac to ~30 GB.
- CI runs on pushes to main, on ready (non-draft) PRs and weekly on main, where it runs everything and deploys nothing.
  Each workflow runs only the newest commit of a PR or of main, so a cancelled run means a newer one superseded it (a
  release tag's run and Release Please's are never cancelled).
- The required `Checks` is the gate of `.github/workflows/checks.yml` (#496): it fails unless every job there passed or
  was skipped. Its `Changes` job (dorny/paths-filter, plus cache lookups) skips the work whose inputs did not change;
  `test_derived.py` holds each filter to its inputs. A push to main filters against main's last commit whose Checks
  passed on a push (#471), but main's `Site` always runs, since it builds the deploy.
- `Model` runs on four shards, `just mech` one of their units, balanced by the seconds CI measured in
  `model/durations.json`; `just model-durations <id>` refreshes it from a run's `durations-*` artifacts. `Blender`
  packs the pictures' motions and the viewer into runners longest first (`just blender-bins`). The sim's reports are
  never committed: main's are on the site at /reports (ADR 0009), and a PR that changes their inputs diffs its reports
  against main's in its job summary.
- With a warm cache a run's critical path should stay within 3 min on a PR and 9 min on main; past it the run warns in
  its summary and never fails (#442; `scripts/ci_budget.py`). Each job's slowest tests are in its run summary.
- The jobs that need a system tool uv can't install run in our CI images (`ci/`, ADR 0009, #288) by their `:main` tag;
  every other job stays on the bare runner, since an image pull costs ~30-40 s a job. Only main pushes the images, when
  a Dockerfile changes and weekly, uncached, before the Monday image scan (#534), so a PR that changes one only builds them and its jobs still run main's.
- `just mech` runs the Link's live checks on the Mech stand-in (mech/), in a `Model` shard.
- Site Deploy deploys the very artifact Checks built, once main's Checks passed (#295, #310).
  Main's commit carries a `deploy` status (#292, `scripts/deploy_status.py`): error when a newer commit superseded it.
  A main commit is green only once its `deploy` is.

## Licence

noggin is licensed under PolyForm Noncommercial 1.0.0 (`LICENSE.md`). By contributing you agree that your contribution is licensed under the same terms, with Yellow Pine as the licensor.

Questions: hello@yellowpine.com.
