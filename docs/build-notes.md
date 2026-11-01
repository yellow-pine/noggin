# Build notes: eyes (part 1 of 3)

Original notes in our own words. The mechanism, its assembly instructions and
remote-control config are the designer's (credits: README "Acknowledgements"); those
files are not redistributed here. Parts 2 and 3 of the series are the pan & tilt base
and the mouth. What to buy: "Parts to buy" below.

## What we built

Photo: `eye-mech-build-photo.jpg`. Two eyeballs with eyelids on a base plate,
four 180° 9 g servos, a Core on a Shield, a switch
board and a 14500 cell holder. Our board is mounted rotated 90° relative
to the designer's photos, which changes nothing electrically.

## Servo ports (Shield)

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
  end in blue heat-shrink, so each looks like a single cell) and the kit's USB
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

- ESP32-C3 running the vendor's MicroPython build. USB-C is the REPL at 115200,
  enumerating on macOS as `/dev/cu.usbmodem*`.
- Its MicroPython is 1.23.0 preview (`sys.implementation._mpy` 774: .mpy version 6.3, no native arch), pinned once
  as `[tool.noggin] micropython` in pyproject.toml. pyright checks the Core's files against
  `micropython-esp32-esp32_generic_c3-stubs` 1.23 as the standard library (`eyes/test_micropython.py`; the stubs
  still take a tuple in `str.startswith`, so `eyes/test_wifi.py` keeps its own check), and `mpy-cross` 1.23 compiles
  them. Bytecode-only .mpy files load on any 6.x ([mpyfiles](https://docs.micropython.org/en/v1.23.0/reference/mpyfiles.html)).
  The setup wizard warns when the board reports another version.
- Upload files with `make flash`: over the Wi-Fi Link while the Core beacons or when no Core is on USB (the noggin
  service then waits up to 22 s for its beacon), else `mpremote` over USB (`USB=1` forces the cable; boot.py only
  ever goes that way). Both send `eyes.mpy`, `gaze_trace.mpy` and `wifi.mpy`
  (`make mpy`, into eyes/build): less RAM to import than the .py. boot.py stays .py (the Core runs boot.py only).
  A .py shadows its .mpy (import looks for the .py first), so `flash-usb` removes them and Wi-Fi takes only .mpy;
  a Core still on .py files refuses .mpy over Wi-Fi, so the first .mpy install goes over USB. Never flash firmware with esptool or any
  third-party tool: the vendor states this bricks the board.
- The stock program's `boot.py` runs the remote-control app forever, so a
  custom program must provide its own `boot.py`.

## Stock program on the Core (from the designer's rc_mpy manifest)

The designer's project page ships a manifest of the stock RC program it
expects on the Core: `boot.py`, `app/rc_main.py`, compiled `app/control.mpy`,
`app/devices.mpy`, `app/parser.mpy`, and `bbl/{__init__,buzzer,executor,leds,
motors,servos,sleepModule}.py`. So `bbl` lives on the filesystem, not frozen,
and the file list matches the GitHub repo's `src/app_rc/`. Local copy with
md5s: `docs/references/stock-program-manifest.json`. Still verify on the real
board with `mpremote ls` before replacing anything.

## Servo calibration lessons (2026-10-31)

- The 9 g servos have a slip clutch. Driving a lid into its
  mechanical stop makes the clutch slip and the calibration drifts, which looks
  like the horn sliding on the spline. Keep every range end a few degrees
  inside the stop; the eye program's lid ranges sit 6° inside.
- Fit horns with all servos held at centre (90): lids half open, eyes straight
  ahead. Push fully home, then the short screw from the servo pack. A horn that
  has been refitted several times is worn; use a fresh one.
- The two lid servos are mirror-mounted (a on one is 180 - a on the other).
  Since #213 `eyes/calibration.json` gives both lids in one shared frame, the
  right lid servo's degrees: `<lid>_lo` closed, `<lid>_rest` where it sits at
  `lid_rest`, `<lid>_hi` open. The Core mirrors the left servo itself, so a
  matched pair has identical numbers. A file with the old `<lid>_flip` keys
  still loads, converted.
- 2026-11-01 (#213): the left lid showed only a slit at rest and thinking while
  the right showed half its pupil. Raising the left lid's open end until rest
  matched broke the near-shut wink: the lid bars make equal servo steps unequal
  lid steps, so a straight line between the ends can't fit. Hence the rest
  point: tune closed, rest and open per lid, and compare both eyes at a
  half-open pose, not only at the ends.
- 2026-11-01 (#255): the lids retuned live in the shared frame. Closed 39 on both (the
  edges just touch, quiet: the two lids read 38 and 40, the midpoint taken), rest 61.4
  (left) / 64 (right, which sat a bit more closed in thinking at the same number), open
  102 (the lid stops opening visibly there; no stop or clutch slip up to 133). At
  `lid_closed` 0.1 the blinks left a clear gap, so `lid_closed` is now 0: blinks and the
  wink close at the closed end, and bored's long closure is 1.5 s (with its ramps it
  stays under the 2 s stall cap). Eyes unchanged, 58..118.

## Real eye movements (GazeBase)

`eyes/build_trace.py` pulls GazeBase subject 1001, session 1 (CC BY 4.0) with a 7 MB byte-range
fetch and bakes `eyes/gaze_trace.py`: real saccade velocity profiles at 10/20/25° (used by every
dart and return, undershoot and correction included), a 4 s horizontal-scan clip (attention), and a
60 s video-viewing session (thinking, when `think_trace` is 1). Lids are not in the data; blinks and
lids keep toon timing (#258, `docs/research/2026-11-01-toon-eyes.md`; the human kinematics behind it
are in `2026-10-31-natural-eye-motion.md` and `2026-11-01-blink-kinematics.md`). No write asks more of
a servo than its rated 428°/s: `glide` takes more steps, a big saccade spaces its samples out, a
replayed trace caps each sample's move (`eyes/test_toon.py`). Fixational jitter (±0.5°) is below one
servo step and was dropped.

## Wi-Fi Link timing (2026-10-31, #104)

Seen live on the eyes Core: the Wi-Fi Link gave up on the startup calibration batch every time, and `wink 3` played
but logged `no ack`. Two causes. A gesture blocks the Core for about a second, and the Core used to ack only after the
line had run, past the noggin service's 2 x 200 ms window. And WLAN power save was on (MicroPython's default, ping RTT
about 60 ms), so the access point held the first datagrams and ARP after a quiet spell. The Core now acks on receipt
and sets `pm=PM_NONE`, and a line that Wi-Fi does not deliver goes over USB when the cable is in (ADR 0005). Checked on the
Mech 2026-10-31 (eyes Core at 192.168.68.55, cable out, noggin service restarted): the calibration batch is acked
over Wi-Fi, `wink 3` is acked and the left eye winks, and the six gestures played over Wi-Fi alone (`demo once`).

## Live check on the eyes Core alone (2026-11-01, #177)

Eyes Core on a new network (192.168.178.141; the Core only knew last night's Wi-Fi, so the Link was silent until the
Wi-Fi step ran again, see #195), noggin service and program from main (9075717), `noggin demo` looping:
- Cable out: every gesture kept playing over Wi-Fi. The unplug left the eyes offline for about 12 s and dropped one
  gesture until the next beacon (#196).
- Wi-Fi flash: `noggin flash` installed main's program (back in 3 s). A deliberately broken `eyes.mpy` never reached
  `noggin ready`; the Core went back to its .bak files and its beacon returned. `make flash` once misread the beacon
  as stale, fell back to `flash-usb` with no cable and stopped the noggin service (#196).
- USB fallback: with Wi-Fi unreachable (wrong network) and the cable in, the service found the Core on serial, sent the
  calibration and gestures, and the Core answered.
- Mech off 20 s, cable out: the Link came back by itself (beacon, uptime 11 s), but nothing was logged for the Wi-Fi
  outage (#196).

## Cable-out check of the Link fixes (2026-11-01, #212)

Eyes Core on the home network (192.168.68.61), program and noggin service from main after #196, #200 and #205:
- Cable pulled during a gesture in `noggin demo`: `Link lost` at 14:11:50, the next gesture went `sent eyes` 5 s later,
  nothing dropped (#196).
- Cable out, `bored 2` and `wink 1` 3 s into it: both acked over Wi-Fi, the wink played right after bored (#205).
- Mech off 30 s, cable out: `eyes beacon stale for 22.0 s`, then `eyes beacon back: wifi ... uptime 8s` and the
  calibration resent (#196).
- The Core joined the home network from its list of two (#195).

## Second Core (tilt, mouth, pan)

The designer runs two Cores on two Shields. Ours: Core 2 ports PWM1 tilt, PWM2 mouth, PWM3 pan (the designer's
config JSON; the mouth guide's "3rd position" wording is ambiguous). Both Cores join the Wi-Fi and are addressed
directly (ADR 0005; radio facts in docs/research/2026-10-31-radio.md). Each shield
gets its own pack and switch board (one pack cannot feed two shields at stall: 2 x 2.6 A > 3 A). Electrical figures:
docs/research/2026-10-31-electrical.md.

## Parts to buy

The one place the shop's names and codes appear (2026-10-31, grilled). Electronics are Bambu Lab's CyberBrick
range, filament is Bambu PLA Pure.

- Owned: Beginner Hardware Kit ZK004 (2 Cores, an X11 receiver shield + a transmitter shield, switch module, 2S pack,
  charger, one 180 and one 360 servo), Battery Upgrade Kit ZL003 (second switch module + second pack), 4 PG001
  servos, M3x10, M2x12, M2 nuts (20 each). Used by the eyes: 4 servos, 1 Core, 1 Shield, 1 switch board, 1 pack.
  Unused on the desk: 1 Core (the remote's, becomes Core 2), 1 switch board, 1 pack (spare on charge), one 180
  servo (the 360 one is continuous rotation, not positional). Pan bearing: the printed bearing block (the shop no
  longer lists the F10-18M thrust bearing).
- Ordered 2026-10-31 (Bambu EU store): X11 Receiver Shield XA004 x1; servo PG001 x3 (2 needed + 1 spare); battery
  PC003 x1 (one pack per Shield + a spare on charge); M2x12 screws x1 pack and M2 nuts x1 pack (shell halves and
  mask); one pack of longer M2 (x16 or x20, whichever is listed) for the mask + skull stack on the wings; M2.5x6
  screws x1 pack if listed (the remaining stages need 26 of the kit's M2.5).
- Filament, all owned, Bambu PLA Pure: Milky Pink, Pure White, Absolute Black, Apricot (hex and density:
  docs/research/2026-10-31-filament.md). No more needed: the face shell is a thin hollow skin, about 180 g Apricot
  in total and about 80 g Black.

## Commands

```
scripts/setup.sh     # guided first-run: plug in the Core, back up, flash, join the Wi-Fi, calibrate, install hooks + the noggin service
make wifi            # add a Wi-Fi network to the Core on USB (the wizard's Join the Wi-Fi step alone)
make install         # host side only: hooks + the noggin service
make start / stop    # (re)start or stop the noggin service; stop frees the Link for mpremote
make flash           # install the eye program on the Core and reboot it: Wi-Fi while it beacons or no Core is on USB, else USB (USB=1 forces it)
make restore-stock   # put the stock remote-control program back on the Core
noggin/noggin status # mode (follow, demo or pose), Link (Wi-Fi or USB) per Core
noggin/noggin off    # mute (on to resume); noggin/noggin eureka 2 for a manual gesture
noggin/noggin pose lids 0.3 eyes 95     # pose mode: hold it, hooks ignored, until follow; each set re-sends it
noggin/noggin set l_lid_rest 70          # live calibration, saved to eyes/calibration.json
noggin/noggin exercise 10                # gentle run-in, 10 minutes
make demo            # demo mode: every gesture on a loop, 5 s apart, hooks ignored (ARGS=once, ARGS="bored 2")
make follow          # follow mode: react to Claude Code again, from demo or pose (the default, and the mode after any restart)
make stl / step      # our printed parts as print-ready STLs (model/build/stl); STEP files of every part and Stage
make render / gifs / hero   # the model's pictures (docs/model-notes.md)
```

Secrets (the Wi-Fi password) are typed in a Terminal window (`make wifi`, `scripts/setup.sh`), never at Claude
Code's `!` prompt: it has no stdin, so a hidden password prompt there cannot be answered.

Requirements: macOS, [uv](https://docs.astral.sh/uv/) (Python 3.12 and mpremote come with it), Claude Code.
