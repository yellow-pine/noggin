# Contributing

Thanks for stopping by. noggin is a small hobby project, run in the open.

## How work runs

- Work starts from a GitHub issue (a ticket). Open one before a big change so the shape can be agreed first.
- The cycle, in order: grilling (interview only, nothing is built) → research and domain modelling as needed → plan/spec → TDD → code review → PR → retro.
- One PR per concern. Keep it small.
- Every ticket is built in its own worktree on its own branch, with a normal PR straight against main opened on the
  first push and auto-merge switched on right away (`gh pr merge --auto --squash`): GitHub squash-merges it (the only
  method the repo allows) the moment every required check is green and every review conversation is resolved, with no
  approval wait, and deletes the branch. Whoever works the ticket keeps that PR green and answers each review thread
  (a fix, or a reply saying why not) before resolving it. No integration or feature branches: a spec's tickets land on
  main one PR at a time. Main is protected: a green PR with one approval is the only way in (it need not be up to date with main). The
  approval comes from Claude's review (claude[bot]) and is dismissed on every push, so each push is re-reviewed; a PR
  that edits review.yml gets no review and needs Cansin's bypass. CI
  runs on pushes to main and on ready (non-draft) PRs. A pushed branch is never merged locally: it lands through its
  own PR. Every branch on GitHub has a PR, except on-hold work.
- Issue state labels, one per state: `ready-for-agent` (can start), `in-progress` (picked up and not in main yet:
  being worked on or waiting on its PR; a spec is in-progress from its first ticket until its
  last ticket reaches main), `blocked` (waits on something else, named in the issue: another ticket, hardware),
  `on-hold` (paused by Cansin). Closing an issue removes its state label.
- Skills (mattpocock's cycle and ponytail) are pinned in `skills-lock.json` to a commit (`ref`); `npx skills@1.7.4 experimental_install`
  restores them into `.agents/skills` (gitignored), which the committed `.claude/skills` link points at, and
  `node scripts/verify_skills.mjs` checks each against its `computedHash`. Bumps arrive as PRs: the weekly `skills`
  workflow re-pins to upstream HEAD (close and reopen its PR to start the checks), Dependabot pins actions by SHA.
- Every ready PR gets a Claude review: claude[bot] submits a real Approve or Request changes review, and the
  required `claude` check fails with it when Claude requests changes (a bug, a spec
  miss, a security issue or a breach of a documented rule; ponytail suggestions never block) (`.github/workflows/review.yml`: mattpocock code-review plus ponytail). It
  needs the `CLAUDE_CODE_OAUTH_TOKEN` secret twice, for Actions and for Dependabot (whose PRs only see Dependabot
  secrets): run `claude setup-token`, then `gh secret set CLAUDE_CODE_OAUTH_TOKEN` and
  `gh secret set CLAUDE_CODE_OAUTH_TOKEN --app dependabot`.
- Vocabulary lives in `GLOSSARY.md` and the decisions in `docs/adr/`; use those words and record a new decision as a new ADR.
- Hardware facts and calibration lessons are in `docs/build-notes.md`. Never flash firmware with esptool (see ADR 0002).

## Code

- Feature-first layout: `eyes/`, `noggin/`, `reactions/`, `model/`, `web/`. Tests sit beside the code they test (`test_*.py` in the same folder).
- Smallest thing that works; no options or abstractions nobody asked for.
- Run `make check` before opening a PR. CI runs the same.

## Licence

noggin is licensed under PolyForm Noncommercial 1.0.0 (`LICENSE.md`). By contributing you agree that your contribution is licensed under the same terms, with Yellow Pine as the licensor.

Questions: hello@yellowpine.com.
