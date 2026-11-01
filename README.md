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

![noggin](https://yellowpine.com/noggin/images/hero.gif)

> [!TIP]
> ## [Docs, build guide and live 3D viewer → https://yellowpine.com/noggin](https://yellowpine.com/noggin/)
>
> Building the Mech, using it, the gestures, the model and the 3D viewer are all on the site. This README is for
> contributors.

## Setup

macOS or Linux, [uv](https://docs.astral.sh/uv/) and Node (the viewer's tests, the diagrams' renderer).

```
make venv     # .venv from uv.lock, Python 3.12
make check    # what CI's code job runs: the tests not marked model, lint, formatting, types, script syntax
make site     # the site in site/ (python -m http.server -d site)
```

`make check-all` adds the model tests (MuJoCo and the slow mesh sweeps); they and the other heavy targets (`sim`,
`render`, `web`) run one at a time and are best left to CI. On the Mech itself: the
[build guide](https://yellowpine.com/noggin/docs/build/parts/).

## CI/CD at a glance

| Workflow | File | Runs on | Does |
|---|---|---|---|
| Code Checks | `check.yml` | PRs, main | `code`: `make check`; `mech`: the Link's live checks on the Mech stand-in (`make mech`); `model`: the model tests, the sim and the STL/STEP export, sharded |
| Site Deploy | `pages.yml` | PRs, main after Code Checks | `pictures` in Blender, then `site`: the docs, viewer and reports; main deploys to Pages, a PR uploads a preview artifact |
| Claude Review | `review.yml` | PRs | `fetch skills`, then `review`: Claude approves or requests changes |
| PR Title | `pr-title.yml` | PRs | `PR Title`: the title is a Conventional Commit with an area's scope (ADR 0010) |
| Skills Updates | `skills.yml` | weekly | re-pins `skills-lock.json` and opens a PR |
| Release Please | `release-please.yml` | main | keeps the release PR (version bump, CHANGELOG.md), auto-merged on green; merged, tags and releases it |
| Release Assets | `release.yml` | `v*` tags | zips the Core's program and the setup wizard onto the release |

Required checks on main: `code`, `model`, `mech`, `site`, `review`, `fetch skills` and `PR Title`. PRs go straight against main
with auto-merge on; how work runs is in [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

The mechanism is PurpleShark's CyberBrick animatronic series; the full credits are on
[the site](https://yellowpine.com/noggin/docs/credits/).

## Licence

[PolyForm Noncommercial 1.0.0](LICENSE.md), copyright Yellow Pine. You may use, change and share noggin for any
noncommercial purpose; contact hello@yellowpine.com for commercial licensing. The designer's models carry their own
licences and are not redistributed here.
