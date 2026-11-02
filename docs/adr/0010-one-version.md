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
>
> Amended 2026-11-02 (#407): the release PR auto-merges only when a feature or a breaking change is pending; anything
> else waits for one, or for Release Now.
>
> Amended 2026-11-02 (#414): the release PR is a draft until the gate or Release Now marks it ready, so its checks run
> once; Release Docs deploys the site so a release's docs are live at once.
>
> Amended 2026-11-02 (#447): the App is the repo's bot App; the weekly Skills and Blender Updates open their PRs as it
> too, so those PRs get their checks and review.
>
> Amended 2026-11-02 (#453): the squash commit is the title alone, so a body footer never reaches main; a break is the
> title's `!`, and the PR Title check reads no body.
>
> Amended 2026-11-02 (#538, #496): PR Title and PR Issue are one required check, `PR` (`pr-checks.yml`); the
> required checks are PR, Checks, Fetch Skills and Review.
>
> Superseded in part 2026-11-02 (#582): ADR 0017. semantic-release releases main once its Checks pass, with no release
> PR, gate, Release Now or CHANGELOG.md, and the git tag is the version (`pyproject.toml` keeps a placeholder). The one
> version, the 0.x bump rules and the PR titles below still hold; the release-please parts are history.
>
> Amended 2026-11-02 (#742): commitlint checks the title (@commitlint/cli with config-conventional's rules and
> `ci/commitlint.config.mjs`'s derived scopes), replacing amannn/action-semantic-pull-request and scripts/pr_title.py.

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
  release-please's PR. The required `PR` check (`pr-checks.yml`) enforces
  it all (commitlint with `ci/commitlint.config.mjs`, as on main).
- **release-please keeps a release PR** (`Release Please` workflow) that bumps the version and writes CHANGELOG.md,
  generated but committed (ADR 0009, amended) through that reviewed PR, with the version bump; no bot commits to
  main. Only feat, fix and perf (and breaks) open it and fill the changelog; the other types ride along with the next
  release. It passes the required checks, Claude's review included; merged, it tags `vX.Y.Z`
  and creates the GitHub release, its notes the version's CHANGELOG.md section (each entry links its PR, which links
  its issue (#356), and its commit), and the tag starts Release Assets, which attaches the Core program zip as the release's
  deployment in the `release` environment (the Deployments panel links the release; its notes link the run).
- **Features and breaks release themselves; the rest waits (#407).** Every merge to main once released a fix on its own,
  too often. After each update the workflow reads release-please's changelog in the PR body (scripts/release_gate.py): a
  `Features` or `⚠ BREAKING CHANGES` section in the newest version's block turns the PR's auto-merge on, anything else
  turns it off, so fixes and perf ship with the next feature. The `Release Now` workflow (or `/release`) turns it on for
  whatever is pending and labels the PR `release now`, which keeps it on through later updates; only the App's own label
  counts, since anyone with triage rights can add one. Release Now picks the PR by release-please's branch, the App as
  author and the pending label. Both act as the bot App, so the merge still tags and starts Release Assets. Until
  then release-please keeps the PR a draft (`draft-pull-request`), which no check or review runs on while it gathers
  changes; the gate and Release Now mark it ready before turning auto-merge on, so its checks and review run once
  (#414). Release Docs then dispatches Site Deploy, so the release's docs at /noggin/vX.Y/ are live at once, still
  through the one deploy path.
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
- Gating the release PR on a list of commit types (#407): rejected, release-please already sorts the commits into its
  changelog's sections, and a second list would drift from it (ADR 0011).
