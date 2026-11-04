# noggin

An animatronic Mech on the desk that reacts to Claude Code. It winks when a session starts, drifts while Claude
thinks, lights up when a response lands, scans the room when Claude needs you and gets bored when you walk away.
Claude Code hooks feed a small Mac service, the noggin service, which tells the Mech's two Cores what to play.

<!--{{ hero }}-->

[Build one](build/parts.md) · [Use it](use/noggin-service.md)

## The next Mech, in progress

<!--{{ front }}-->

<!--{# GitHub shows the line below; the site drops it for the pictures, which it builds from the code -->
Its Stage 1 from the front, its Stage 3 isometric and exploded are on [the site's home](https://yellowpine.com/noggin/).
<!-- #}-->

The next Mech (#51), clean-room, as its model has it after the latest merge, its mechanism bare until a finished Skin
exists: Stage 1 from the front, Stage 3 whole and pulled apart; each opens in
[the viewer](https://yellowpine.com/noggin/viewer/), to turn it and play its gestures. Each part and motion in
[Pictures](pictures.md).

## What it does

<!--{{ behaviour }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
Which Claude Code event plays which gesture is in [the table on the site](https://yellowpine.com/noggin/#what-it-does),
built from the code.
<!-- #}-->

More in [Gestures and behaviour](use/gestures.md).

## The three Stages

The Mech is our own design, being designed and not built yet (#51). It grows in three Stages, each complete on the
desk.

- **Stage 1: eyes.** The eye block on a test stand: both eyes turn together on two servos, each eye's lids on its own,
  four servos on the eyes Core. [Build Stage 1](build/stage-1.md)
- **Stage 2: neck.** The eye block on a pan-and-tilt neck over the Torso, the boards in the back of the head: two more
  servos on the neck Core. [Build Stage 2](build/stage-2.md)
- **Stage 3: mouth.** A jaw under the eyes: the seventh servo, the whole Mech. Then a character's Shells on magnets.
  [Build Stage 3](build/stage-3.md)

## Where next

- **Build.** Parts to buy and print, the three Stages, wiring, flashing the Cores and calibrating the servos.
  [Build guide](build/parts.md)
- **Use.** The noggin service, the Claude Code hooks, what each gesture means and how to tune them.
  [Use the Mech](use/noggin-service.md)
- **How it works.** The Link, a hook's way to a gesture and the model's pipeline, drawn.
  [How it works](how-it-works.md)
