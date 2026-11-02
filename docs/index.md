# noggin

An animatronic Mech on the desk that reacts to Claude Code. It winks when a session starts, drifts while Claude
thinks, lights up when a response lands, scans the room when Claude needs you and gets bored when you walk away.
Claude Code hooks feed a small Mac service, the noggin service, which tells the Mech's two Cores what to play.

[Build one](build/parts.md) · [Use it](use/noggin-service.md)

## The next Mech, in progress

[![The next Mech in progress, isometric](https://yellowpine.com/noggin/images/next-mech-a-isometric.webp)](pictures.md)
[![Its eyes sweeping, the lids following](https://yellowpine.com/noggin/images/next-eyes-sweep.webp)](pictures.md)

The next Mech (#51), clean-room, as its model has it after the latest merge, and its eyes sweeping. Each part and
motion in [Pictures](pictures.md), turn it in [the viewer](https://yellowpine.com/noggin/viewer/).

## What it does

<!--{{ behaviour }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
Which Claude Code event plays which gesture is in [the table on the site](https://yellowpine.com/noggin/#what-it-does),
built from the code.
<!-- #}-->

More in [Gestures and behaviour](use/gestures.md).

## The three Stages

The Mech grows in three Stages, each a complete Mech on the desk.

- **Stage 1: eyes.** Two eyeballs with lids on the base plate: four servos on one Core. Built here.
  [Build Stage 1](build/stage-1.md)
- **Stage 2: neck.** The eyes on a pan-and-tilt neck: two more servos on a second Core.
  [Build Stage 2](build/stage-2.md)
- **Stage 3: mouth.** A jaw under the eyes: the seventh servo. The full Mech.
  [Build Stage 3](build/stage-3.md)

## Where next

- **Build.** Parts to buy and print, the three Stages, wiring, flashing the Core and calibrating the servos.
  [Build guide](build/parts.md)
- **Use.** The noggin service, the Claude Code hooks, what each gesture means and how to tune them.
  [Use the Mech](use/noggin-service.md)
- **How it works.** The Link, a hook's way to a gesture and the model's pipeline, drawn.
  [How it works](how-it-works.md)
