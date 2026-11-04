# Wiring

## Servo ports

<!--{{ wiring }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
Each Core's ports, GPIOs, servos and ranges are in [the table on the site](https://yellowpine.com/noggin/docs/build/wiring/#servo-ports),
built from the code.
<!-- #}-->

Ports 1 and 2 are the Shield's left header, 3 and 4 the right. The eyes Core drives [Stage 1](stage-1.md)'s eye
gimbal: a lid servo per eye, one yaw servo turning both eyes left and right and one pitch servo turning them up and
down. Its rows are the eye program's calibration ([Calibration](calibration.md)), the model's nominal ranges until a
Stage 1 is calibrated (inferred): the lids in the shared lid frame, the right lid servo's degrees (the Core writes
180 - a to the left, inferred), closed at the low end where the lids meet, open at the high; the yaw and the pitch
rest centred between their ends. The gestures turn the eyes left and right only, so the pitch holds the gaze level.
The neck Core runs the same eye program, which drives its pan alone: its rows' ranges are the neck's in the model and
its rest the model's neutral, 90 (the jaw's closed end), and its GPIOs are the Shield's as on the eyes Core (inferred:
the same Shield). *Upcoming (#929): the neck Core drives the tilt and the jaw, from a calibration of their own.*

> [!WARNING]
> **The lids bind at the ends.** Verify a range on the real Mech before pushing past it.

## Power

- Pack -> power-path board -> switch board -> XH2.54 2-pin lead up the neck -> a Y lead to both Shields' power
  inputs, a 470 µF capacitor across it where it enters them.
- Shield spec: 7.4 to 12.6 V. A single 3.7 V cell is below spec; a 2S pack (two 14500 cells in series, 7.4 V
  800 mAh) is the minimum. Neither the Core nor the Shield charges it: the power-path board in the Torso does, from
  the head's USB-C (docs/research/2026-11-03-usb-c-power.md 7).
- USB-C on a Core powers only that Core, not the servos.
- Servos stay powered at rest: released, the lids and eyes fall under gravity.

## The neck Core (tilt, mouth, pan)

The neck Core sits on its own Shield in the head, at +x beside the eyes Core: port 1 tilt, 2 mouth, 3 pan. Both
Cores join the Wi-Fi and are addressed directly (ADR 0005; radio facts in docs/research/2026-10-31-radio.md), each
antenna 15 mm clear of the Shells, servos, magnets, pack and leads where the build allows. Both lie flat
in the cranium, their USB-C ends back to the hub, whose port at the back of the skull base takes a laptop's cable
(power, flashing, and the USB fallback, which reaches the eyes Core alone) or a USB-C charger (power alone), which
charges the pack through the power-path board in the Torso: check the Wi-Fi link there, inside the skull, on the
built Mech. Use a USB-C source advertising 3 A until the proposed input-limit detector is built and checked
([Stage 2](stage-2.md#wiring)). Both Shields
run off the one pack and switch board through a Y lead
([Stage 2](stage-2.md)); the gestures stay inside the pack's 3 A, since two Shields at stall would draw more
(2 x 2.6 A > 3 A; a pack per Shield was dropped, #51): each Core starts at most two servos at once (the start budget).
Electrical figures: docs/research/2026-10-31-electrical.md.
