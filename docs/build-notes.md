# Build notes: eyes (part 1 of 3)

Original notes in our own words. The printed parts, assembly instructions and
remote-control config are PurpleShark's **CyberBrick Eyes Animatronic Mechanism**
on MakerWorld (model 1718839, Standard Digital File License). Get those files
there; they are not redistributed here. Parts 2 and 3 of the series are the
Pan & Tilt base (model 1766064) and the mouth (model 1861301).

## What we built

Photo: `eye-mech-build-photo.jpg`. Two eyeballs with eyelids on a base plate,
four MakerWorld 180° 9 g servos, a CyberBrick Core on an X11 shield, a power
switch board and a 14500 cell holder. Our board is mounted rotated 90° relative
to the designer's photos, which changes nothing electrically.

## Servo ports (X11 shield)

| Port | GPIO | Servo     | Angle range | Neutral |
|------|------|-----------|-------------|---------|
| 1    | 3    | Left lid  | 75 to 120   | 90      |
| 2    | 2    | Left eye  | 60 to 120   | 90      |
| 3    | 1    | Right lid | 70 to 120   | 90      |
| 4    | 0    | Right eye | 75 to 120   | 90      |

Ports 1 and 2 are the left header, 3 and 4 the right header. Ranges are the
limits the designer's remote config uses; verify on the real mech before
pushing past them, the lids bind at the ends.

## Power

- Battery -> switch board -> XH2.54 2-pin lead -> shield power input.
- Shield spec: 7.4 to 12.6 V. A single 3.7 V cell is below spec; two 14500
  cells in series (2S) are the minimum. Neither the Core nor the shield
  charges cells; charge externally.
- USB-C on the Core powers only the Core, not the servos.
- What we have: two official 7.4 V 800 mAh 2S packs (two 14500 cells end to
  end in blue heat-shrink, so each looks like a single cell) and Bambu's USB
  charger dongle with an XH2.54 plug. The dongle is a charger only, never a
  supply for the board. One pack in the holder through the switch board, the
  spare on charge. USB-C to the Mac carries data and powers the Core only.

## Host

- `uv` manages `.venv` (Python 3.12) and runs mpremote and pytest; the system Python is 3.9 and is
  not used.

## Talking to the Core

- This board reports `3.4.0; MicroPython e7cd27f2 on 2025-06-09`; stock RC program 01.00.00.13.
- mpremote's own Ctrl-C does not interrupt the stock RC app, and `mpremote soft-reset` waits for a
  raw REPL the eye program never gives. `eyes/interrupt.py` handles both; every Makefile board
  target goes through it, then uses `mpremote resume`.
- Servos stay powered at rest: released, the lids and eyes fall under gravity.

- ESP32-C3 running Bambu's MicroPython build. USB-C is the REPL at 115200,
  enumerating on macOS as `/dev/cu.usbmodem*`.
- Upload files with `mpremote`. Never flash firmware with esptool or any
  third-party tool: Bambu states this bricks the board.
- The stock program's `boot.py` runs the remote-control app forever, so a
  custom program must provide its own `boot.py`.

## Stock program on the Core (from the MakerWorld rc_mpy manifest)

The designer's MakerWorld page ships a manifest of the stock RC program it
expects on the Core: `boot.py`, `app/rc_main.py`, compiled `app/control.mpy`,
`app/devices.mpy`, `app/parser.mpy`, and `bbl/{__init__,buzzer,executor,leds,
motors,servos,sleepModule}.py`. So `bbl` lives on the filesystem, not frozen,
and the file list matches the GitHub repo's `src/app_rc/`. Local copy with
md5s: `docs/references/stock-program-manifest.json`. Still verify on the real
board with `mpremote ls` before replacing anything.

## Servo calibration lessons (2026-10-31)

- The MakerWorld 9 g servos have a slip clutch. Driving a lid into its
  mechanical stop makes the clutch slip and the calibration drifts, which looks
  like the horn sliding on the spline. Keep every range end a few degrees
  inside the stop; the eye program's lid ranges sit 6° inside.
- Fit horns with all servos held at centre (90): lids half open, eyes straight
  ahead. Push fully home, then the short screw from the servo pack. A horn that
  has been refitted several times is worn; use a fresh one.
- The two lid servos are mirror-mounted: open is the low end for the mech's
  left lid and the high end for the right. The eye program handles that with
  `LID_FLIP`.
- Calibrated values live at the top of `eyes/eyes.py` (`RANGE`, `LID_FLIP`,
  `EYE_TRIM`, `LID_REST`, `LID_THINK`).

## Real eye movements (GazeBase)

`eyes/build_trace.py` pulls GazeBase subject 1001, session 1 (CC BY 4.0) with a 7 MB byte-range
fetch and bakes `eyes/gaze_trace.py`: real saccade velocity profiles at 10/20/25° (used by every
dart and return, undershoot and correction included), a 4 s horizontal-scan clip (attention), and a
60 s video-viewing session (thinking, when `think_trace` is 1). Lids are not in the data; blink and
lid timing come from the literature in `docs/research/2026-10-31-natural-eye-motion.md`. Fixational
jitter (±0.5°) is below one servo step and was dropped.

## Second Core (tilt, mouth, pan)

The designer runs two Cores on two X11 shields. Ours: Core 2 ports PWM1 tilt, PWM2 mouth, PWM3 pan (the designer's
config JSON; the mouth guide's "3rd position" wording is ambiguous). Both Cores join the Wi-Fi and are addressed
directly (ADR 0005; radio facts in docs/research/2026-10-31-radio.md). Each shield
gets its own pack and switch board (one pack cannot feed two shields at stall: 2 x 2.6 A > 3 A). Electrical figures:
docs/research/2026-10-31-electrical.md.

Inventory and the remaining buy list: docs/face-design.md "Hardware" (2026-10-31).
