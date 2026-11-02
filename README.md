<h1 align="center">noggin</h1>

<p align="center">An animatronic Mech on the desk that reacts to Claude Code.</p>

<p align="center"><a href="https://yellowpine.com/noggin/docs/pictures/"><img src="https://yellowpine.com/noggin/images/next-mech-back-isometric.webp" height="240" alt="The next Mech in progress, isometric"></a><br><sub>The next Mech, in progress</sub></p>

<p align="center"><a href="https://yellowpine.com/noggin/"><b>Docs</b></a>&emsp;&emsp;&emsp;<a href="https://yellowpine.com/noggin/docs/build/parts/"><b>Build guide</b></a></p>

<p align="center">
<a href="https://github.com/yellow-pine/noggin/actions/workflows/checks.yml"><img alt="Checks" src="https://img.shields.io/github/actions/workflow/status/yellow-pine/noggin/checks.yml?branch=main&label=Checks&labelColor=2B2B2E"></a>
<a href="https://github.com/yellow-pine/noggin/actions/workflows/pages.yml"><img alt="Site Deploy" src="https://img.shields.io/github/actions/workflow/status/yellow-pine/noggin/pages.yml?branch=main&label=Site%20Deploy&labelColor=2B2B2E"></a>
<a href="https://github.com/yellow-pine/noggin/releases/latest"><img alt="Release" src="https://img.shields.io/github/v/release/yellow-pine/noggin?label=Release&labelColor=2B2B2E&color=FFB673"></a>
<a href="https://scorecard.dev/viewer/?uri=github.com/yellow-pine/noggin"><img alt="OpenSSF Scorecard" src="https://img.shields.io/ossf-scorecard/github.com/yellow-pine/noggin?label=OpenSSF%20Scorecard&labelColor=2B2B2E"></a>
<a href="LICENSE.md"><img alt="Licence: PolyForm Noncommercial 1.0.0" src="https://img.shields.io/badge/Licence-PolyForm%20Noncommercial-F7CED7?labelColor=2B2B2E"></a>
</p>

This README is for contributors. Building the Mech, using it and its gestures are on the site.

## Setup

macOS or Linux, with:

| Tool | For |
| --- | --- |
| [uv](https://docs.astral.sh/uv/) | Python 3.14 and the dependencies, from `uv.lock` |
| [just](https://just.systems/) | the recipes: `uv run just` (a dev dependency), or `uv tool install rust-just` |
| Node 24 | the site (`site/.nvmrc`) |
| Chrome | the site's browser tests |

```sh
just venv                      # .venv from uv.lock
just lint                      # ruff (lint, formatting) and pyright: the pre-push hook
just check-light               # the PR gate: just lint and the fast tests
just check                     # main's Code job: adds the workflow linters and the CadQuery build tests
just site                      # the site, built into site/dist
npm --prefix site run preview  # serve it
npm --prefix site test         # its tests; run smoke for the browser ones
```

`just check-all` adds the model tests (MuJoCo and the slow mesh sweeps). They and the other heavy recipes (`sim`,
`render`, `web`) run one at a time and are best left to CI.

## CI/CD

What each workflow in [.github/workflows](.github/workflows) does is on
[the CI/CD page](https://yellowpine.com/noggin/docs/ci-cd/).

Required checks on main: `PR`, `Checks`, `Fetch Skills` and `Review`. PRs go straight against main with auto-merge on;
how work runs is in [CONTRIBUTING.md](CONTRIBUTING.md).

## Built with

| Tool | Here it |
| --- | --- |
| [Claude Code](https://docs.claude.com/en/docs/claude-code) | sends the hook events the Mech reacts to |
| [CadQuery](https://cadquery.readthedocs.io) | models the printed parts |
| [MuJoCo](https://mujoco.org) | simulates the Mech and tests its motions |
| [Blender](https://www.blender.org) | draws every picture and the viewer's look |
| [MicroPython](https://micropython.org) | runs the programs on both Cores |
| [Astro Starlight](https://starlight.astro.build) | builds the site |
| [three.js](https://threejs.org) | draws the 3D viewer |

## Credits

The mechanism is PurpleShark's CyberBrick animatronic series; the full credits are on
[the site](https://yellowpine.com/noggin/docs/credits/).

## Licence

[PolyForm Noncommercial 1.0.0](LICENSE.md), copyright Yellow Pine. You may use, change and share noggin for any
noncommercial purpose; contact hello@yellowpine.com for commercial licensing. The designer's models carry their own
licences and are not redistributed here.
