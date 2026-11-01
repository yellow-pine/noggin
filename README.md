# noggin

[![check](https://img.shields.io/github/actions/workflow/status/yellow-pine/noggin/check.yml?branch=main&label=check&style=flat)](https://github.com/yellow-pine/noggin/actions/workflows/check.yml)
[![Claude review](https://img.shields.io/github/actions/workflow/status/yellow-pine/noggin/review.yml?event=pull_request&label=Claude%20review&style=flat)](https://github.com/yellow-pine/noggin/actions/workflows/review.yml)
[![last commit](https://img.shields.io/github/last-commit/yellow-pine/noggin?style=flat)](https://github.com/yellow-pine/noggin/commits/main)
[![license](https://img.shields.io/badge/license-PolyForm%20NC%201.0.0-blue?style=flat)](LICENSE.md)
[![python](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fyellow-pine%2Fnoggin%2Fmain%2Fpyproject.toml&style=flat)](https://github.com/yellow-pine/noggin/blob/main/pyproject.toml)

An animatronic Mech on the desk that reacts to Claude Code. It winks when a session starts, drifts while Claude
thinks, lights up when a response lands, scans the room when Claude needs you and gets bored when you walk away.
Claude Code hooks feed a small Mac service, the noggin service, which tells the Mech's two Cores what to play.

![noggin](docs/images/hero.gif)

Turn it around and play its gestures in the browser: [the web viewer](https://yellowpine.com/noggin/viewer/). These
docs are on [the site](https://yellowpine.com/noggin/) too.

## Acknowledgements

The mechanism is [PurpleShark](https://makerworld.com/en/@PurpleShark)'s three-part CyberBrick animatronic series on
MakerWorld: [eyes](https://makerworld.com/en/models/1718839) (1718839),
[pan & tilt](https://makerworld.com/en/models/1766064) (1766064) and
[mouth](https://makerworld.com/en/models/1861301) (1861301). noggin owes its existence to that work; what this repo
adds is the behaviour (the Core program, the noggin service, the hooks) and the model (our own parametric parts and a
simulation of the Mech).

- Bambu Lab's [CyberBrick](https://wiki.bambulab.com/en/cyberbrick) Core, shields and MicroPython build.
- [GazeBase](https://doi.org/10.1038/s41597-021-00959-y) (Griffith et al., CC BY 4.0) for the recorded eye movements.
- Duke Doks' [Morty head](https://makerworld.com/en/models/1455413) (MakerWorld 1455413), the reference for the face.

Built with
[![Claude Code](https://img.shields.io/badge/Claude%20Code-D97757?style=flat&logo=claude&logoColor=white)](https://docs.claude.com/en/docs/claude-code)
[![CadQuery](https://img.shields.io/badge/CadQuery-1E5BA8?style=flat)](https://cadquery.readthedocs.io)
[![Blender](https://img.shields.io/badge/Blender-E87D0D?style=flat&logo=blender&logoColor=white)](https://www.blender.org)
[![MicroPython on the CyberBrick](https://img.shields.io/badge/MicroPython-on%20the%20CyberBrick-2B2728?style=flat&logo=micropython&logoColor=white)](https://micropython.org)

## Gestures

| eureka | attention | bored |
|---|---|---|
| ![eureka](docs/images/eureka.gif) | ![attention](docs/images/attention.gif) | ![bored](docs/images/bored.gif) |
| **wince** | **wink** | **thinking** |
| ![wince](docs/images/wince.gif) | ![wink](docs/images/wink.gif) | ![thinking](docs/images/thinking.gif) |

## What it does

<!--{{ behaviour }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
Which Claude Code event plays which gesture is in [the table on the site](https://yellowpine.com/noggin/#what-it-does),
built from the code.
<!-- #}-->

Several sessions share the one Mech; a gesture already playing wins. Eye movements replay real human recordings
(GazeBase); blink and lid timing follow the literature in `docs/research/`.

## How it works

```mermaid
---
config:
  layout: dagre
  look: classic
---
flowchart LR
    accTitle: How noggin works
    accDescr: On the Mac, Claude Code's hooks write one line per event to a Unix socket; the noggin service times each turn and sends a command over Wi-Fi, as UDP datagrams signed with HMAC, to the Mech's two Cores. Core 1 drives the eyes' 4 servos, Core 2 the neck's 3. USB-C is a fallback to the eyes Core only.
    subgraph Mac
        CC["Claude Code<br/>hooks"] -- "Unix socket<br/>one line per event" --> NS["noggin service<br/>times each turn,<br/>drops Triggers while Busy"]
    end
    subgraph Mech
        C1["Core 1: eyes<br/>ESP32-C3, MicroPython<br/>4 servos: lids and eyes"]
        C2["Core 2: neck<br/>ESP32-C3, MicroPython<br/>3 servos: pan, tilt, mouth"]
    end
    NS -- "Wi-Fi: UDP + HMAC" --> C1
    NS -- "Wi-Fi: UDP + HMAC" --> C2
    NS -. "USB-C fallback" .-> C1
```

Arrows carry commands, the dotted one only when Wi-Fi fails; each Core plays a gesture to its end.

The gestures live on the Core, so motion stays smooth whatever the Mac does; the Mac only says which one. The Link,
a hook's way to a gesture and the model's pipeline are drawn in [`docs/how-it-works.md`](docs/how-it-works.md).
Decisions are in [`docs/adr/`](https://github.com/yellow-pine/noggin/tree/main/docs/adr), the words in
[`GLOSSARY.md`](GLOSSARY.md).

## Quick start

```
scripts/setup.sh       # guided first run: plug in the Core, back up, flash, join the Wi-Fi, calibrate, install
noggin/noggin status   # mode and Link per Core
make demo              # every gesture on a loop
make follow            # react to Claude Code again
```

macOS, [uv](https://docs.astral.sh/uv/) and Claude Code. Every command, the hardware and the calibration lessons are
in [`docs/build-notes.md`](docs/build-notes.md); how work runs in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## The Stages and the model

![The three Stages: stage 1 front (base and eyes), stage 2 side (eyes on the neck), stage 3 side and front (with the mouth)](docs/images/stages.jpg)

![Stage 3 exploded: the base, the neck lifted off it, the eyes above and the mouth forward of them](docs/images/exploded.jpg)

The Mech grows in three Stages: the eyes on the base, then on the pan-and-tilt neck, then with the mouth. `model/` is
the Mech as code: our own parametric CadQuery parts, a simulation (MuJoCo, ADR 0007) that sweeps every linkage,
finds its collisions and the supply's voltage sag (SPICE) before a part is printed, and Blender pictures from
MuJoCo's trajectories (every picture here). How the pictures are made: [`docs/model-notes.md`](docs/model-notes.md).

## Licence

[PolyForm Noncommercial 1.0.0](LICENSE.md), copyright Yellow Pine. You may use, change and share noggin for any
noncommercial purpose; contact hello@yellowpine.com for commercial licensing. The designer's models carry their own
licences and are not redistributed here.
