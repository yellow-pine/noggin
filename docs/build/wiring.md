# Wiring

## Servo ports

<!--{{ wiring }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
Each Core's ports, GPIOs, servos and ranges are in [the table on the site](https://yellowpine.com/noggin/docs/build/wiring/#servo-ports),
built from the code.
<!-- #}-->

Ports 1 and 2 are the Shield's left header, 3 and 4 the right. The eyes Core's rows are the eye program's as it runs
today, on today's Mech's calibration ([Calibration](calibration.md)): a servo per eye and per lid, the lids in the
shared lid frame, the right lid servo's degrees (the Core writes 180 - a to the left), closed at the low end, open at
the high; the eyes rest centred between their ends. The Mech's eyes Core drives the eye gimbal instead: left and right,
up and down, and a lid servo per eye ([Stage 1](stage-1.md)), its ports given when the eye program drives the gimbal.
The neck Core has no program yet: its ranges are the neck's in the model and its rest the model's neutral, 90 (the
jaw's closed end), and its GPIOs are the Shield's as on the eyes Core (inferred: the same Shield).

> [!WARNING]
> **The lids bind at the ends.** Verify a range on the real Mech before pushing past it.

## Power

- Battery -> switch board -> XH2.54 2-pin lead -> shield power input (a Y lead
  to both shields, split after the neck joint).
- Shield spec: 7.4 to 12.6 V. A single 3.7 V cell is below spec; two 14500
  cells in series (2S) are the minimum. Neither the Core nor the shield
  charges cells; charge externally.
- USB-C on the Core powers only the Core, not the servos.
- What we have: two official 7.4 V 800 mAh 2S packs (two 14500 cells end to
  end in blue heat-shrink, so each looks like a single cell) and the kit's USB
  charger dongle with an XH2.54 plug. The dongle is a charger only, never a
  supply for the board. One pack in the Torso through the switch board, the
  spare on charge. USB-C to the Mac carries data and powers the Core only.
- Servos stay powered at rest: released, the lids and eyes fall under gravity.

## The neck Core (tilt, mouth, pan)

The neck Core sits on its own Shield in the head's board rack, in the +x cheek: port 1 tilt, 2 mouth, 3 pan. Both
Cores join the Wi-Fi and are addressed directly (ADR 0005; radio facts in docs/research/2026-10-31-radio.md), each
antenna 15 mm clear of the Shells, servos, magnets, pack and leads where the build allows. In the next Mech's cheeks
each antenna end sits about 10.5 mm from its lid servo, the USB-C end facing back to stay reachable (#828): check the
link there on the built Mech. Both Shields run off the one pack and switch board through a Y lead
([Stage 2](stage-2.md)); the gestures stay inside the pack's 3 A, since two Shields at stall would draw more
(2 x 2.6 A > 3 A; a pack per Shield was dropped, #51): each Core starts at most two servos at once (the start budget).
Electrical figures: docs/research/2026-10-31-electrical.md.
