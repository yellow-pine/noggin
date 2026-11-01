# Wiring

## Servo ports

<!--{{ wiring }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
Each Core's ports, GPIOs, servos and ranges are in [the table on the site](https://yellowpine.com/noggin/docs/build/wiring/#servo-ports),
built from the code.
<!-- #}-->

Ports 1 and 2 are the Shield's left header, 3 and 4 the right. The eyes Core's ranges are the calibrated ones
([Calibration](calibration.md)): the lids in the shared lid frame, the right lid servo's degrees (the Core writes
180 - a to the left), closed at the low end, open at the high; the eyes rest centred between their ends. The neck Core
has no program yet: its ranges are the model's limits and its rest the model's neutral, 90 (the jaw's closed end), and
its GPIOs are the Shield's as on the eyes Core (inferred: the same Shield).

!!! warning "The lids bind at the ends"
    Verify a range on the real Mech before pushing past it.

## Power

- Battery -> switch board -> XH2.54 2-pin lead -> shield power input.
- Shield spec: 7.4 to 12.6 V. A single 3.7 V cell is below spec; two 14500
  cells in series (2S) are the minimum. Neither the Core nor the shield
  charges cells; charge externally.
- USB-C on the Core powers only the Core, not the servos.
- What we have: two official 7.4 V 800 mAh 2S packs (two 14500 cells end to
  end in blue heat-shrink, so each looks like a single cell) and the kit's USB
  charger dongle with an XH2.54 plug. The dongle is a charger only, never a
  supply for the board. One pack in the holder through the switch board, the
  spare on charge. USB-C to the Mac carries data and powers the Core only.
- Servos stay powered at rest: released, the lids and eyes fall under gravity.

## Second Core (tilt, mouth, pan)

The designer runs two Cores on two Shields. Ours: Core 2 ports 1 tilt, 2 mouth, 3 pan (the designer's
config JSON; the mouth guide's "3rd position" wording is ambiguous). Both Cores join the Wi-Fi and are addressed
directly (ADR 0005; radio facts in docs/research/2026-10-31-radio.md). Each shield
is to get its own pack and switch board, a planned edit ([Model notes](../model-notes.md)): one pack cannot feed two
shields at stall (2 x 2.6 A > 3 A). Electrical figures:
docs/research/2026-10-31-electrical.md.
