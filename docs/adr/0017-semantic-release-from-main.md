# semantic-release releases from main once its Checks pass; the git tag is the one version

> Decided with Cansin on 2026-11-02 (grilling, noggin-27), #582. Supersedes ADR 0010's release half: 0010 keeps the
> one version and the PR titles.

Release Please's release PR only delayed releases: a draft waiting for a gate or Release Now, a `release now` label,
and stale merge refs (#543), on a repo where every PR already auto-merges on green. So main releases itself.

- **semantic-release, its default plugins only** (commit-analyzer, release-notes-generator, github;
  `release.config.mjs`), pinned in `ci/package.json` (ADR 0012). The conventionalcommits preset stays on 9.x while release-notes-generator
  bundles conventional-changelog-writer 8, which can't render 10.x; `ci/release.test.mjs` renders notes, so a bump
  past it fails there. The `Release` workflow (`release.yml`) runs when Checks complete for
  this repo's push to main, and acts only on a success, on that push's commit: a red main never releases. When main
  moved on since, semantic-release sees its commit is no longer main's head and releases nothing; the newer commit's
  run releases both. One run at a time, never cancelled.
- **What releases**: feat, fix, perf, revert and a `!` break (the conventionalcommits preset reads the title's `!`).
  Before 1.0 a break bumps the minor and the rest the patch (`releaseRules`, tested in `ci/release.test.mjs` through
  commit-analyzer itself); docs, ci, chore, build, test, style and refactor release nothing. Rules that match nothing
  fall through to commit-analyzer's defaults, which release none of those types either.
- **A manual release** (#802, Cansin 2026-11-03: one that can't be ignored, when main never quiets down). The
  `Release` workflow's dispatch on main, with a bump: `auto` (the default), `patch`, `minor` or `major`. One run does it
  all on main's tip at dispatch: the full Checks (`checks.yml` called with `workflow_call`, its Deploy on), then the tag
  and release of that same commit once they pass; a red commit never tags. When main moved on during the run, it tags
  the commit it checked anyway: semantic-release releases a temporary branch at that commit (`release-<run id>`,
  deleted after), so the version math and the notes stay its own and the tag sits on a commit in main's history.
  semantic-release has no force option by design, so the bump is config: `release.config.mjs` reads it from
  `RELEASE_BUMP` and puts a rule matching every commit at that bump ahead of the others. commit-analyzer takes a
  commit's highest match, so a forced bump is the least it releases (a forced patch over a break is still the minor);
  `auto` leaves the rules as they are, and with no commit since the last tag nothing releases, which the run's summary
  says. The push-triggered release is unchanged.
- **The git tag is the one version.** `noggin/core.py` reads `git describe --tags`: `X.Y.Z` on a release's tag,
  `X.Y.Z-N-gHASH` N commits past it, `0.0.0-untagged` where no tag is reachable (a shallow checkout). The Core's stamp
  and the noggin service carry it; the service compares the base X.Y.Z. The Site's footer links a release only on an
  exact tag. `pyproject.toml` keeps a placeholder `0.0.0`, and nothing commits back to main: no bump, no
  CHANGELOG.md. Each release's notes are on its GitHub release (v0.1.0 to v0.2.5's too). The checkouts that stamp or
  release fetch the tags: Release's and Site's whole history, a tag's run its tag.
- **The bot App's token** (CONTRIBUTING.md), since a tag `GITHUB_TOKEN` pushes starts no workflow: the App's tag starts
  Release Assets as before. Contents write only: the github plugin's success and fail comments and its `released`
  label are off, so a release writes nothing on PRs or issues.

## Considered options

- Keeping Release Please with a lighter gate: rejected, the release PR itself was the friction.
- Releasing on the push to main, before Checks: rejected, a red commit could be tagged.
- Tagging the dispatched commit by hand (`git tag`, `gh release create`) for a forced release: rejected, the version
  and notes would no longer be semantic-release's.
- A forced bump that replaces the rules rather than leading them: rejected, a forced patch would then understate a
  break.
- Writing the version into `pyproject.toml` (and a CHANGELOG.md) on release: rejected, that is a bot commit to main.
