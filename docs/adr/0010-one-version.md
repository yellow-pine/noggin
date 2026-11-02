# One SemVer version for the whole repo, released by release-please from conventional PR titles

> Decided with Cansin on 2026-11-01, #303. Research: docs/research/2026-11-01-releases.md.
>
> Amended 2026-11-01 (#328): the release token comes from a GitHub App, not a fine-grained personal token.
>
> Amended 2026-11-01 (#350): the PR Title check enforces only the type; a scope is free-form, an area recommended.
>
> Amended 2026-11-01 (#358): Release Assets is the release's deployment in the `release` environment, and the
> release's notes link back to it.
>
> Amended 2026-11-02 (#382): a scope is required again, exactly one, derived from the repo; the types and subject
> rules are @commitlint/config-conventional's; a `BREAKING CHANGE:` footer needs `!` in the title.

The Core program, the noggin service, the Model and the Site change together and ship from one repo, so they carry one
version: **noggin vX.Y.Z** ([SemVer 2.0.0](https://semver.org/spec/v2.0.0.html)), starting at 0.1.0. It lives in
`pyproject.toml` (`project.version`); release-please also writes it into `.release-please-manifest.json` and uv.lock's
copy, and the tag is `v` plus it.

- **1.0.0 when both Cores work end to end** on the Mech. Before that (0.x), a breaking change to the Link protocol, the
  calibration format or the CLI bumps the minor; a feat or a fix bumps the patch (release-please's
  `bump-minor-pre-major` and `bump-patch-for-minor-pre-major`). After 1.0.0 the same breaks bump the major.
- **PR titles are Conventional Commits** (`type(scope): subject`, `type(scope)!:` for a break), because each squash
  commit is its PR's title. Types and subject rules are @commitlint/config-conventional's (build, chore, ci, docs,
  feat, fix, perf, refactor, revert, style, test; the subject doesn't start uppercase or end with a period; the header
  is at most 100 characters). The scope is required and is one noun, derived from the repo (ADR 0011): a tracked
  top-level folder, a tracked folder in docs/, `deps` (`deps-dev`) as Dependabot writes, or `release` for
  release-please's PR. A body with a `BREAKING CHANGE:` footer needs the `!`. The required `PR Title` check enforces
  it all (amannn/action-semantic-pull-request, scripts/pr_title.py as on main).
- **release-please keeps a release PR** (`Release Please` workflow) that bumps the version and writes CHANGELOG.md,
  generated but committed (ADR 0009, amended) through that reviewed PR, with the version bump; no bot commits to
  main. Only feat, fix and perf (and breaks) open it and fill the changelog; the other types ride along with the next
  release. It passes the required checks, Claude's review included, and auto-merges on green; merged, it tags `vX.Y.Z`
  and creates the GitHub release, its notes the version's CHANGELOG.md section (each entry links its PR, which links
  its issue (#356), and its commit), and the tag starts Release Assets, which attaches the Core program zip as the release's
  deployment in the `release` environment (the Deployments panel links the release; its notes link the run).
- **A GitHub App's token, not `GITHUB_TOKEN`.** What `GITHUB_TOKEN` creates starts no workflow: the release PR would
  get no checks and its tag no assets. So the workflow mints a short-lived token per run from a small private GitHub
  App on yellow-pine (actions/create-github-app-token), not a personal token tied to one account (#328,
  CONTRIBUTING.md).

## Considered options

- A version per part (Core program, noggin service, Model): rejected, they are released and tested together, and the
  Link ties the program to the service.
- Tags by hand with `--generate-notes`: rejected, no CHANGELOG.md and nothing decides the bump.
- semantic-release: rejected, it releases on every merge with no reviewed PR, so the bump and the changelog land
  unreviewed.
