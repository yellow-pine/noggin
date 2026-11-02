# noggin

[![check](https://img.shields.io/github/actions/workflow/status/yellow-pine/noggin/check.yml?branch=main&label=check&style=flat)](https://github.com/yellow-pine/noggin/actions/workflows/check.yml)
[![Claude review](https://img.shields.io/github/actions/workflow/status/yellow-pine/noggin/review.yml?event=pull_request&label=Claude%20review&style=flat)](https://github.com/yellow-pine/noggin/actions/workflows/review.yml)
[![last commit](https://img.shields.io/github/last-commit/yellow-pine/noggin?style=flat)](https://github.com/yellow-pine/noggin/commits/main)
[![license](https://img.shields.io/badge/license-PolyForm%20NC%201.0.0-blue?style=flat)](LICENSE.md)
[![python](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fyellow-pine%2Fnoggin%2Fmain%2Fpyproject.toml&style=flat)](https://github.com/yellow-pine/noggin/blob/main/pyproject.toml)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-D97757?style=flat&logo=claude&logoColor=white)](https://docs.claude.com/en/docs/claude-code)
[![CadQuery](https://img.shields.io/badge/CadQuery-1E5BA8?style=flat)](https://cadquery.readthedocs.io)
[![Blender](https://img.shields.io/badge/Blender-E87D0D?style=flat&logo=blender&logoColor=white)](https://www.blender.org)
[![MicroPython on the Core](https://img.shields.io/badge/MicroPython-on%20the%20Core-2B2728?style=flat&logo=micropython&logoColor=white)](https://micropython.org)

An animatronic Mech on the desk that reacts to Claude Code.

<p align="center"><img src="https://yellowpine.com/noggin/images/hero.gif" width="800" alt="noggin: Stage 3 talking, turning and nodding"></p>

> [!TIP]
> ## [Docs, build guide and live 3D viewer → https://yellowpine.com/noggin](https://yellowpine.com/noggin/)
>
> Building the Mech, using it, the gestures, the model and the 3D viewer are all on the site. This README is for
> contributors.

## Setup

macOS or Linux, [uv](https://docs.astral.sh/uv/), Node 24 (`site/.nvmrc`: the site) and Chrome (the site's browser tests).

```
make venv     # .venv from uv.lock, Python 3.14
make check    # what CI's code job runs: the tests not marked model, lint, formatting, types, script syntax
make site     # the site in site/dist (npm --prefix site run preview); its tests: npm --prefix site test, npm --prefix site run smoke
```

`make check-all` adds the model tests (MuJoCo and the slow mesh sweeps); they and the other heavy targets (`sim`,
`render`, `web`) run one at a time and are best left to CI. On the Mech itself: the
[build guide](https://yellowpine.com/noggin/docs/build/parts/).

## CI/CD at a glance

Generated from `.github/workflows` (`make readme`):

<!-- [[[cog import cog, scripts.workflow_table as w; cog.outl(w.table()) ]]] -->
| Workflow | File | Triggers | Jobs | Does |
|---|---|---|---|---|
| Blender Updates | `blender.yml` | `schedule` (`0 6 * * 1`), `workflow_dispatch` | Re-pin Blender | Re-pins Blender to the newest stable release at least 14 days old and opens (or refreshes) a PR, weekly |
| Code Checks | `check.yml` | `push` (`main`), `pull_request` | Changes, Mech, Images, Code, Convex, Shards, Model | Runs `make check`, the Link's live checks on the Mech stand-in (`make mech`), the model tests, sim and STL/STEP export |
| Dependabot Auto-merge | `dependabot.yml` | `pull_request` | Auto-merge | Turns on auto-merge (squash) for Dependabot's PRs: each merges once the required checks and Claude's review pass |
| Deploy Pending | `deploy-pending.yml` | `push` (`main`) | Deploy Pending | Sets a main commit's `deploy` status pending while Site Checks build its site |
| Firmware Watch | `firmware.yml` | `schedule` (`0 6 * * 1`), `workflow_dispatch` | Watch | Opens an issue for each new Core firmware on the vendor's release notes, weekly |
| CI Images | `images.yml` | `pull_request` (paths: `ci/*.Dockerfile`, `.github/workflows/images.yml`), `push` (`main`; paths: `ci/*.Dockerfile`, `.github/workflows/images.yml`), `schedule` (`0 4 * * 1`), `workflow_dispatch` | Build, Push | Builds the CI images the Chrome and Blender jobs run in; main pushes them to GHCR |
| Issue Labels | `issue-labels.yml` | `pull_request`, `issues` | In Progress, Clear Labels | Keeps issues' state labels in step: a PR sets the issues it links in-progress, and closing an issue clears its labels |
| Site Deploy | `pages.yml` | `workflow_run` (workflows: `Code Checks`, `Site Checks`; `main`), `workflow_dispatch` | Checks, Deploy, Deploy Status | Deploys Site Checks' site artifact to Pages once main's checks pass, with every release's docs beside it |
| PR Checks | `pr-checks.yml` | `pull_request` | PR Title, PR Issue | Checks the PR's title is a Conventional Commit with one of the repo's scopes and its body links its issue |
| Release Now | `release-now.yml` | `workflow_dispatch` | Release Now | Releases whatever is pending: marks the open release PR ready, turns on its auto-merge and labels it `release now` |
| Release Please | `release-please.yml` | `push` (`main`), `workflow_dispatch` | Release Please | Keeps the release PR (version bump, CHANGELOG.md), auto-merged on green; merged, tags and releases it |
| Release Assets | `release.yml` | `push` (`v*`) | Release Assets, Release Docs | Zips the Core's program (stamped with its version and commit) and the setup wizard onto the release, then its docs |
| Claude Review | `review.yml` | `pull_request` | Fetch Skills, Review | Claude reviews the PR and approves or requests changes |
| Site Checks | `site-checks.yml` | `push` (`main`), `pull_request` | Changes, Images, Motions, Render, Pictures, Viewer, Site | Builds and checks the site: the pictures in Blender, then the docs, viewer and reports, uploaded as an artifact |
| Skills Updates | `skills.yml` | `schedule` (`0 6 * * 1`), `workflow_dispatch` | Re-pin Skills, Propose | Re-pins skills-lock.json to each source's HEAD and opens (or refreshes) a PR, weekly |
<!-- [[[end]]] -->

Required checks on main: `Code`, `Model`, `Mech`, `Site`, `Pictures`, `Review`, `Fetch Skills`, `PR Title` and
`PR Issue`. PRs go straight against main with auto-merge on; how work runs is in [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

The mechanism is PurpleShark's CyberBrick animatronic series; the full credits are on
[the site](https://yellowpine.com/noggin/docs/credits/).

## Licence

[PolyForm Noncommercial 1.0.0](LICENSE.md), copyright Yellow Pine. You may use, change and share noggin for any
noncommercial purpose; contact hello@yellowpine.com for commercial licensing. The designer's models carry their own
licences and are not redistributed here.
