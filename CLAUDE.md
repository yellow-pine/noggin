# noggin

Animatronic head (Bambu Lab CyberBrick, PurpleShark three-part series: eyes, pan-tilt, mouth). Part 1, the eyes, reacts when Claude Code finishes a response. Public repo: github.com/yellow-pine/noggin, PolyForm Noncommercial 1.0.0.

## Directives from Cansin

- When interviewing or grilling me (any round of design questions), ALWAYS use the AskUserQuestion tool. Never a freeform markdown list of questions.
- Record important directives I give during a session in this file.
- No remote control build for now: the board is driven over a USB-C cable from the host.

## Layout

- `docs/` — original build notes, build photo, ADRs. PurpleShark's PDFs/JSONs are NOT redistributable (MakerWorld Standard Digital File License, no derivatives); they live gitignored in `docs/references/`.
- Keep it minimal: the `ponytail` plugin (anti-overengineering) and `mattpocock-skills` are installed at user scope and should guide design here. Prefer the smallest thing that works.

## Hardware facts (researched 2026-10-31)

- CyberBrick Core = ESP32-C3 running Bambu's MicroPython (this board: `3.4.0; MicroPython e7cd27f2 on 2025-06-09`, stock RC program 01.00.00.13). mpremote's quick Ctrl-C does NOT interrupt the stock RC app; send Ctrl-C and wait ~1 s first (`eyes/interrupt.py`), then use `mpremote resume`. USB-C exposes the REPL (native USB-Serial/JTAG, 115200, shows up as `/dev/cu.usbmodem*` on macOS).
- Use `mpremote` for file upload / REPL. NEVER flash firmware with esptool or third-party tools (bricks the board per official docs).
- Stock `boot.py` runs the RC app forever; a custom project must ship its own `boot.py`.
- Servo ports 1-4 = GPIO3, GPIO2, GPIO1, GPIO0, 50 Hz PWM. Official lib: `bbl.servos.ServosController` (`set_angle(idx, angle)`), or plain `machine.PWM`.
- USB alone powers the Core but not the servos reliably; the X11 shield wants 7.4-12.6 V on its XH2.54 power port.
- Servo ranges from the remote config (the designer's remote config): L lids 75-120, L eye 60-120, R lids 70-120, R eye 75-120, centre 90.

## Design decisions (grilled 2026-10-31)

- Host: this Mac. launchd LaunchAgent runs a Python daemon that owns the serial port and listens on a Unix socket.
- Events (grilled 2026-10-31, supersedes the earlier Stop+Notification-only plan): UserPromptSubmit (silent: starts thinking + timer), Stop -> eureka, Notification permission_prompt -> attention, Notification idle_prompt -> bored, StopFailure -> wince, SessionEnd (silent: ends thinking). Hooks are async one-liners in user-level `~/.claude/settings.json`. Claude Code only.
- Eureka intensity by work duration (UserPromptSubmit to Stop): <20 s small, 20 s to 3 min normal, >3 min big. Other gestures fixed intensity. Mapping lives in the daemon; board gestures take an intensity 1-3.
- Thinking: alive during a turn (lids half, eye drift every 3-6 s, occasional blink, servos released between moves). Ends at Stop, SessionEnd, or 15 min without events from that session. Gestures interrupt thinking and it resumes after if the session is still mid-turn. Rest (still, released) when no session is mid-turn.
- Sessions: per-session timers keyed by session_id; any session's events drive the one mech; Busy drops overlapping gestures (no queue, no pre-emption).
- Mute: `noggin off` / `noggin on` via the daemon socket, persisted across restarts.
- Gestures are named routines in MicroPython on the board; host sends `<gesture> <intensity>` as one newline-terminated line over USB serial.
  - eureka: lids snap wide, eyes dart up-and-aside, hold, swing to centre, two quick blinks, lids settle. Small = glance + blink; big = extra double-take, longer hold.
  - attention: lids to half, eyes sweep slowly side to side twice, hold centre.
  - bored: lids droop, slow sleepy blinks, eyes drift down, then Rest.
  - wince: lids snap shut, eyes squint-twitch, slow reopen.
  - thinking: background state, see above.
- Power (settled 2026-10-31): two official 7.4 V 800 mAh 2S packs (blue heat-shrink, look like one cell). One in the holder -> switch board -> shield; the spare charges on the USB-A dongle with the XH2.54 plug, which is a CHARGER, never a supply. USB-C to the Mac for data. The 3xAAA box is too weak; don't use it.
- Program: replace stock `boot.py`. Back up the stock program first to `eyes/stock-backup/` (gitignored); `make restore-stock` puts it back. Firmware is never touched.
- Layout is feature-first, never function-first (directive 2026-10-31): `eyes/` (the eye mech's board program + its tests; later `pan_tilt/`, `mouth/`), `reactions/` (Claude Code events -> gestures: Director + tests), `daemon/` (serial + socket shell, poke hook, launchd plist, CLI + socket test). Tests live beside the code they test. `Makefile` for install / backup-stock / restore-stock. Python both sides; deps: pyserial, mpremote, pytest.
- Photo of the actual build: `docs/eye-mech-build-photo.jpg` (Core + X11 shield centre, power/switch board top-right, cell holder top-left, 4 MakerWorld 180° servos: 2 eye, 2 lid).
- Host tooling: system Python is 3.9, `uv` is available at /opt/homebrew/bin/uv. Use `uv` for the host env and to run mpremote.
- Development cycle: grilling is interview-only, never build during it. After grilling, run the work through the mattpocock skills cycle (grilling -> research/prototype/domain-modeling as needed -> plan -> tdd -> code-review -> pr). Do not install anything into ~/.claude or launchd without an explicit go.
- Cycle order agreed 2026-10-31: domain-modeling -> research -> wizard.
- Status line shows the current dev-cycle step from `~/.claude/.cycle-step` (one line, e.g. `noggin:tdd`). Update that file whenever a cycle step starts.
- Calibration (grilled 2026-10-31, round 3): lives in `eyes/calibration.json` (committed, this mech's known-good), pushed by the daemon over the Link as `set key value` lines on connect; `noggin set k v` applies live and saves; `noggin pose ...` holds a pose; `noggin exercise N` runs in 15-85% for N minutes. Blink/wince glide to `lid_closed` (10%), never the hard stop; eureka's wide snap is `lid_open` (95%). Gesture timings stay in code. Wizard calibrate stage uses pose/set.
- Process: review fixes and the calibration work go as two separate PRs.
- Directive 2026-10-31: don't spend effort on license checks for datasets/references going forward; Cansin takes that on.
