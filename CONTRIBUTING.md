# Contributing

Thanks for stopping by. noggin is a small hobby project, run in the open.

## How work runs

- Work starts from a GitHub issue (a ticket). Open one before a big change so the shape can be agreed first.
- The cycle, in order: grilling (interview only, nothing is built) → research and domain modelling as needed → plan/spec → TDD → code review → PR → retro.
- One PR per concern. Keep it small.
- Every ticket is built in its own worktree on its own branch, with a normal PR straight against main opened on the
  first push and auto-merge switched on right away (`gh pr merge --auto --squash`): the moment every required check is
  green and every review conversation is resolved, GitHub puts it in the merge queue, which runs the checks again on
  it merged onto current main and squash-merges it (the only method the repo allows) when they pass, then deletes the
  branch. Whoever works the ticket keeps that PR green and answers each review thread (a fix, or a reply saying why
  not) before resolving it. No integration or feature branches: a spec's tickets land on main one PR at a time. Main is
  protected: a green PR with one approval is the only way in (it need not be up to date with main: the queue tests the
  merged result). The approval comes from Claude's review (claude[bot]) and is dismissed on every push, so each push is
  re-reviewed; a PR that edits review.yml gets no review and needs Cansin's bypass. CI runs on pushes to main, on ready
  (non-draft) PRs and on merge groups. A pushed branch is never merged locally: it lands through its own PR. Every
  branch on GitHub has a PR, except on-hold work.
- Issue state labels, one per state: `ready-for-agent` (can start), `in-progress` (picked up and not in main yet:
  being worked on or waiting on its PR; a spec is in-progress from its first ticket until its
  last ticket reaches main), `blocked` (waits on something else, named in the issue: another ticket, hardware),
  `on-hold` (paused by Cansin). Closing an issue removes its state label.
- Skills (mattpocock's cycle and ponytail) are pinned in `skills-lock.json` to a commit (`ref`); `npx skills@1.7.4 experimental_install`
  restores them into `.agents/skills` (gitignored), which the committed `.claude/skills` link points at, and
  `node scripts/verify_skills.mjs` checks each against its `computedHash`. Bumps arrive as PRs: the weekly `skills`
  workflow re-pins to upstream HEAD (close and reopen its PR to start the checks, again after each refresh),
  Dependabot pins actions by SHA.
  Bots never commit to main: the `skills` workflow only pushes its own `skills-bump` branch and opens (or refreshes)
  a PR from it, which goes through review and the merge queue like any other; main's ruleset rejects a bot's push.
- Every ready PR gets a Claude review: claude[bot] submits a real Approve or Request changes review, and the
  required `review` check fails with it when Claude requests changes (a bug, a spec miss, a security issue or a breach
  of a documented rule; ponytail suggestions never block) (`.github/workflows/review.yml`: mattpocock code-review plus
  ponytail). In the merge queue `review` passes when claude[bot] approved the PR's head commit (`.github/workflows/queue.yml`). It
  needs the `CLAUDE_CODE_OAUTH_TOKEN` secret twice, for Actions and for Dependabot (whose PRs only see Dependabot
  secrets): run `claude setup-token`, then `gh secret set CLAUDE_CODE_OAUTH_TOKEN` and
  `gh secret set CLAUDE_CODE_OAUTH_TOKEN --app dependabot`.
- Waiting on CI or a build: `gh pr checks --watch`, `gh run watch`, or a loop on the process's PID. Never `until ! pgrep -f <pattern>` (it matches itself) or a loop on a file count (it hangs when a build stops short).
- After renaming a required check, run `gh pr update-branch --rebase` on every open PR so it reports the new name.
- Vocabulary lives in `GLOSSARY.md` and the decisions in `docs/adr/`; use those words and record a new decision as a new ADR.
- Hardware facts and calibration lessons are in `docs/build-notes.md`. Never flash firmware with esptool (see ADR 0002).

## Code

- Feature-first layout: `eyes/`, `noggin/`, `reactions/`, `model/`, `web/`, `mech/`. Tests sit beside the code they test (`test_*.py` in the same folder).
- Smallest thing that works; no options or abstractions nobody asked for.
- Run `make check` before opening a PR. CI runs the same, split over two required jobs (`.github/workflows/check.yml`):
  `code` (everything but the tests marked `model`) and `model` (those, `make view`'s scene rendered offscreen among
  them, `make sim`, and `make stl step` on main or when the parts changed, split over five shards), pytest
  on every core (pytest-xdist). A cold parts cache is first cut part by part, one runner per part whose CoACD pieces
  are stale (`convex`, `model/convex_parts.py`), so the model shards start warm. With a warm cache a run must finish
  within 3 min of its first job's start on a PR or in the merge queue, or it fails; on main, past 9 min it warns in the
  run summary (`scripts/ci_budget.py`; the wait for a runner before the first job starts does not count). Each job's
  slowest tests are in its run summary.
- `make mech` runs the Link's live checks on the Mech stand-in (mech/): CI's `mech` job, on PRs touching eyes/,
  noggin/ or mech/ and on main.

## Licence

noggin is licensed under PolyForm Noncommercial 1.0.0 (`LICENSE.md`). By contributing you agree that your contribution is licensed under the same terms, with Yellow Pine as the licensor.

Questions: hello@yellowpine.com.
