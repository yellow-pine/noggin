# One SemVer version for the whole repo, released by release-please from conventional PR titles

> Decided with Cansin on 2026-11-01, #303. Research: docs/research/2026-11-01-releases.md.

The Core program, the noggin service, the Model and the Site change together and ship from one repo, so they carry one
version: **noggin vX.Y.Z** ([SemVer 2.0.0](https://semver.org/spec/v2.0.0.html)), starting at 0.1.0. It lives in
`pyproject.toml` (`project.version`); release-please also writes it into `.release-please-manifest.json` and uv.lock's
copy, and the tag is `v` plus it.

- **1.0.0 when both Cores work end to end** on the Mech. Before that (0.x), a breaking change to the Link protocol, the
  calibration format or the CLI bumps the minor; a feat or a fix bumps the patch (release-please's
  `bump-minor-pre-major` and `bump-patch-for-minor-pre-major`). After 1.0.0 the same breaks bump the major.
- **PR titles are Conventional Commits** (`type(scope): subject`, `type!:` for a break), because each squash commit
  is its PR's title. Types: feat, fix, perf, docs, ci, build, refactor, test, chore. Scopes are the repo's areas,
  derived from its top-level directories (`scripts/pr_scopes.py`), never a hand list; a scope is optional. The required
  `PR Title` check enforces both (amannn/action-semantic-pull-request).
- **release-please keeps a release PR** (`Release Please` workflow) that bumps the version and writes CHANGELOG.md,
  generated but committed (ADR 0009, amended) through that reviewed PR, with the version bump; no bot commits to main. Only feat, fix and
  perf (and breaks) open it and fill the changelog; the other types ride along with the next release. It passes the
  required checks, Claude's review included, and auto-merges on green; merged, it tags `vX.Y.Z` and creates the GitHub
  release, and the tag starts Release Assets, which attaches the Core program zip.
- **A token, not `GITHUB_TOKEN`.** What `GITHUB_TOKEN` creates starts no workflow: the release PR would get no checks
  and its tag no assets. So the workflow runs on `RELEASE_PLEASE_TOKEN`, a fine-grained token on this repo
  (CONTRIBUTING.md).

## Considered options

- A version per part (Core program, noggin service, Model): rejected, they are released and tested together, and the
  Link ties the program to the service.
- Tags by hand with `--generate-notes`: rejected, no CHANGELOG.md and nothing decides the bump.
- semantic-release: rejected, it releases on every merge with no reviewed PR, so the bump and the changelog land
  unreviewed.
