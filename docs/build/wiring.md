# Wiring

## Servo ports (Shield)

| Port | GPIO | Servo     | Angle range | Centre  |
|------|------|-----------|-------------|---------|
| 1    | 3    | Left lid  | 75 to 120   | 90      |
| 2    | 2    | Left eye  | 60 to 120   | 90      |
| 3    | 1    | Right lid | 70 to 120   | 90      |
| 4    | 0    | Right eye | 75 to 120   | 90      |

Ports 1 and 2 are the left header, 3 and 4 the right header. Ranges are the
limits the designer's remote config uses; verify on the real mech before
pushing past them, the lids bind at the ends. The ranges the program uses are the calibrated ones
([Calibration](calibration.md)).

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
