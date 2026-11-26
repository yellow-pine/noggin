# Start here

noggin is a Mech on your desk that reacts to Claude Code: a head whose eyes, lids, neck and jaw move as a session
starts, thinks, answers and waits on you. It is printed in PETG and PLA, driven by seven hobby servos on two small
Wi-Fi Cores, and told what to play by a service on your Mac.

## Where it stands

Nothing is printed yet (#51). The Mech is designed in its model, every size in it inferred until it is printed and
built, so you can follow the design and turn each Stage in [the viewer](https://yellowpine.com/noggin/viewer/), but
don't buy parts for a Stage until its guide says it is built. The code runs today: the eye program on a Core, the
noggin service and the hooks on the Mac. What is still to come, and the issue that brings each, is on the
[Roadmap](https://yellowpine.com/noggin/roadmap/).

## What you need

- **A Mac** with macOS, [uv](https://docs.astral.sh/uv/), [just](https://just.systems/) and Claude Code, and this
  repo cloned onto it (`git clone https://github.com/yellow-pine/noggin`, then `just venv` in it): every command on
  these pages runs from there ([On the Mac](build/parts.md#on-the-mac)).
- **A 3D printer** for PETG and PLA, and a few hand tools ([Printer and tools](build/parts.md#printer-and-tools)).
- **The parts each Stage adds**: the Cores, Shields, servos and boards to buy, and the filament
  ([Parts to buy](build/parts.md#parts-to-buy)). Stage 1 needs one Core, one Shield, four servos, and a pack and a
  switch board to power them.
- **A Wi-Fi network** both Cores and the Mac share ([Flashing](build/flashing.md)).

## The order of work

1. **Check your printer's fit**: print the [clearance coupon](build/tests.md#the-clearance-coupon) in PETG and PLA.
2. **Stage 1, the eyes**: print the eye block, fit its four servos and stand it on its test stand with the eyes Core
   ([Stage 1](build/stage-1.md)).
3. **Wire the eyes Core**: its four servos on its Shield's ports, the pack through the switch board
   ([Wiring](build/wiring.md)).
4. **Set it up**: `scripts/setup.sh` walks you through flashing the eye program, joining your Wi-Fi and installing
   the noggin service and the Claude Code hooks on your Mac ([Flashing](build/flashing.md),
   [The noggin service](use/noggin-service.md), [Hooks](use/hooks.md)); the eyes now react to Claude Code.
5. **Calibrate** each servo's ends on your own Mech, with the noggin service running
   ([Calibration](build/calibration.md)).
6. **Stage 2, the neck**: the head on the neck over the Torso, the pack and the power-path board in the Torso, the
   neck Core beside the eyes Core in the head ([Stage 2](build/stage-2.md)).
7. **Stage 3, the mouth**: the jaw, the whole Mech ([Stage 3](build/stage-3.md)), then a Skin's Shells if you want one
   ([Themes](face-design.md)).

Each Stage stands complete on the desk, so you can stop after any of them.

## Where to read on

- [How it works](how-it-works.md): from a Claude Code hook to a servo.
- [Gestures](use/gestures.md): which Claude Code event plays which gesture.
- [Glossary](../GLOSSARY.md): the words these pages use (Core, Shield, Skin, Preset, Seat).
- [Contributing](../CONTRIBUTING.md): the checks, the CI and how a change lands.
