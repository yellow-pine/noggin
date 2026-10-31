# robohead

Animatronic eye mech (Bambu Lab CyberBrick) driven from this Mac so the eyes react when Claude Code finishes a response.

## Directives from Cansin

- When interviewing or grilling me (any round of design questions), ALWAYS use the AskUserQuestion tool. Never a freeform markdown list of questions.
- Record important directives I give during a session in this file.
- No remote control build for now: the board is driven over a USB-C cable from the host.

## Layout

- `docs/` — build PDFs and the CyberBrick remote-template JSON exports (reference only).
- Keep it minimal: the `ponytail` plugin (anti-overengineering) and `mattpocock-skills` are installed at user scope and should guide design here. Prefer the smallest thing that works.

## Hardware facts (researched 2026-10-31)

- CyberBrick Core = ESP32-C3 running Bambu's MicroPython. USB-C exposes the REPL (native USB-Serial/JTAG, 115200, shows up as `/dev/cu.usbmodem*` on macOS).
- Use `mpremote` for file upload / REPL. NEVER flash firmware with esptool or third-party tools (bricks the board per official docs).
- Stock `boot.py` runs the RC app forever; a custom project must ship its own `boot.py`.
- Servo ports 1-4 = GPIO3, GPIO2, GPIO1, GPIO0, 50 Hz PWM. Official lib: `bbl.servos.ServosController` (`set_angle(idx, angle)`), or plain `machine.PWM`.
- USB alone powers the Core but not the servos reliably; the X11 shield wants 7.4-12.6 V on its XH2.54 power port.
- Servo ranges from the remote config (`docs/eyes.json`): L lids 75-120, L eye 60-120, R lids 70-120, R eye 75-120, centre 90.

## Design decisions (grilled 2026-10-31)

- Host: this Mac. launchd LaunchAgent runs a Python daemon that owns the serial port and listens on a Unix socket.
- Triggers: Claude Code `Stop` -> "eureka"; `Notification` -> "attention". Hooks live in user-level `~/.claude/settings.json`, each a one-liner that writes to the socket and exits. Claude Code only (no desktop app / web).
- Daemon drops triggers while an animation is playing (no queue). No idle motion: eyes are still between events. Daemon must tolerate the board being unplugged or battery off.
- Animations are named routines in MicroPython on the board; host sends `eureka` / `attention` as newline commands over USB serial.
  - eureka: lids snap wide, eyes dart up-and-aside, hold ~0.6 s, swing to centre, two quick blinks, lids settle. ~2 s.
  - attention: lids to half, eyes sweep slowly side to side twice, hold centre.
- Power: kit 2S 7.4 V Li-ion pack on the X11 shield; USB-C for data (and Core power).
- Firmware: replace stock `boot.py`. Back up stock filesystem first to `firmware/stock-backup/`; provide restore target.
- Layout: `firmware/` (MicroPython), `host/` (daemon, hook, launchd plist), `Makefile` with install / backup-stock / restore-stock. Python both sides; deps: pyserial, mpremote.
- Photo of the actual build: `docs/eye-mech-build-photo.jpg` (Core + X11 shield centre, power/switch board top-right, cell holder top-left, 4 MakerWorld 180° servos: 2 eye, 2 lid).
- Host tooling: system Python is 3.9, `uv` is available at /opt/homebrew/bin/uv. Use `uv` for the host env and to run mpremote.
- Development cycle: grilling is interview-only, never build during it. After grilling, run the work through the mattpocock skills cycle (grilling -> research/prototype/domain-modeling as needed -> plan -> tdd -> code-review -> pr). Do not install anything into ~/.claude or launchd without an explicit go.
- Power plan: first try USB only (USB-C to the Core for data/MCU, plus the USB-A -> XH2.54 lead into the shield's power port for 5 V to servos). That is below the shield's 7.4 V spec; if servos brown out, fall back to two 14500 cells in series (printed 2x14500 case or two holders wired in series). No onboard charger.
- Cycle order agreed 2026-10-31: domain-modeling -> research -> wizard.
