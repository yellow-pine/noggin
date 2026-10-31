# Research: Claude Code hooks, CyberBrick serial, macOS launchd (2026-10-31)

Primary sources only unless marked. Local checks ran on this Mac (Darwin 25.6, Python 3.9.6, uv 0.12.19, mpremote 1.29.0 via `uvx`). No Core was plugged in, so nothing below was tested against the board.

## A. Claude Code hooks

Source: https://code.claude.com/docs/en/hooks (reference) and https://code.claude.com/docs/en/hooks-guide (guide).

### A1. `Stop`

- Fires "when the main Claude Code agent has finished responding. Does not run if the stoppage occurred due to a user interrupt. API errors fire StopFailure instead." (hooks#stop)
- Once per turn: the lifecycle list says "per turn: `UserPromptSubmit`, `Stop`, and `StopFailure`". No matcher: `Stop` is in the "no matcher support | always fires on every occurrence" row. (hooks#hook-events)
- Subagents do not fire `Stop`; they fire `SubagentStop`, which "Runs when a Claude Code subagent has finished responding." It also fires for Claude Code's internal agents ("prompt suggestions and /btw side questions"). (hooks#subagentstop)
- Stdin JSON: common fields (`session_id`, `prompt_id`, `transcript_path`, `cwd`, `scratchpad_dir`, `permission_mode`, `effort`, `hook_event_name`) plus `stop_hook_active`, `last_assistant_message`, `background_tasks`, `session_crons`. "`stop_hook_active` is `true` when Claude Code is already continuing as a result of a stop hook." (hooks#stop-input)
- Example input (abridged from the docs):
  ```json
  {"session_id":"abc123","transcript_path":"~/.claude/projects/.../x.jsonl","cwd":"/Users/...",
   "permission_mode":"default","hook_event_name":"Stop","stop_hook_active":true,
   "last_assistant_message":"I've completed the refactoring...","background_tasks":[],"session_crons":[]}
  ```
- Blocking: "By default, hooks block Claude's execution until they complete." (hooks#run-hooks-in-the-background) Exit 2 on `Stop` "Prevents Claude from stopping, continues the conversation"; stderr becomes the reason. Exit 0 lets Claude stop. Other non-zero exits are "non-blocking error" and the action proceeds, with a `<hook name> hook error` notice in the transcript. (hooks#exit-code-output; hooks-guide "Any other exit code")
- Timeout: "Seconds before canceling... Defaults: 600 for `command`, `http`, and `mcp_tool`; 30 for `prompt`; 60 for `agent`." (hooks#common-fields) `"async": true` on a command hook makes Claude Code "immediately continue without waiting"; async hooks can't block and their timeout is not enforced. (hooks#run-hooks-in-the-background)
- Loop guard: "after stop hooks have continued the turn eight times in a row, Claude Code overrides the next block and ends the turn." (hooks#stop-input)

### A2. `Notification`

- "Runs when Claude Code sends notifications. Matches on notification type. Omit the matcher to run hooks for all notification types. You receive these hook events even with desktop notifications turned off." (hooks#notification)
- Matcher values: `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog`, `elicitation_url_dialog`, `elicitation_complete`, `elicitation_response`, `agent_needs_input`, `agent_completed`, `quota_auto_resume_fired`, `quota_auto_resume_stale`, `quota_auto_resume_disabled`, `plugin_notification`. (hooks#hook-events matcher table)
- Timing of the two we care about: `permission_prompt`: "Claude needs you to approve a tool use... and the prompt has waited about six seconds"; `idle_prompt`: "Claude finished responding about 60 seconds ago and you haven't typed since". Caveat: these "share their timing with desktop notifications, so in terminal sessions you only see them when you appear to be away from the terminal." (hooks#notification)
- Payload: common fields plus `message`, optional `title`, `notification_type`. Example from the docs:
  ```json
  {"session_id":"abc123","transcript_path":"...","cwd":"/Users/...","hook_event_name":"Notification",
   "message":"Claude needs your permission","title":"Permission needed","notification_type":"permission_prompt"}
  ```
- "Notification hooks can't block or modify notifications." Exit code and stderr are ignored. (hooks#notification)

### A3. Settings file structure and reload

- User-level file: `~/.claude/settings.json` applies to "All your projects". (hooks#configure-hook-location)
- Shape: `hooks` -> event name -> array of matcher groups `{ "matcher": "...", "hooks": [ { "type": "command", "command": "...", "timeout": N, "async": bool } ] }`. Docs example:
  ```json
  {"hooks":{"Notification":[
     {"matcher":"permission_prompt","hooks":[{"type":"command","command":"/path/to/permission-alert.sh"}]},
     {"matcher":"idle_prompt","hooks":[{"type":"command","command":"/path/to/idle-notification.sh"}]}]}}
  ```
  `Stop` groups omit `matcher`. (hooks#notification, hooks-guide "Set up your first hook")
- Reload: "Direct edits to hooks in settings files are normally picked up automatically by the file watcher." Troubleshooting adds: "If they haven't appeared after a few seconds, the file watcher may have missed the change: restart your session to force a reload." (hooks-guide#troubleshooting)
- Dedup/parallel: "When an event fires, its matching hooks run in parallel." "If you define the same handler in more than one settings file, it runs once." (hooks#hook-events)

### A4. Execution environment and stdout

- cwd: "Handlers run in the current directory with Claude Code's environment." If that directory vanished, Claude Code falls back to "the directory the session started in, the project root, your home directory, or the system temp directory." (hooks#hook-execution)
- Env vars exported to the hook process: `CLAUDE_PROJECT_DIR` ("the project root where the session started"), `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_EFFORT`; `CLAUDE_CODE_REMOTE` is `"true"` only in remote web environments. (hooks#reference-scripts-by-path)
- Shell: "Hooks run in non-interactive shells" (profile may still be sourced under some configs; anything it prints lands on stdout). (hooks-guide#troubleshooting)
- stdout on exit 0: "For most events, Claude Code writes stdout to the debug log and doesn't show it in the transcript." Exceptions are `UserPromptSubmit`, `UserPromptExpansion`, `SessionStart`, `PostModelSwitch`. (hooks#exit-code-0) So a `Stop`/`Notification` hook's output is invisible to the user unless it exits non-zero.

## B. CyberBrick Core / MicroPython

Repo: https://github.com/CyberBrick-Official/CyberBrick_Controller_Core (default branch `master`).

### B1. `servos.py` and `boot.py`

`src/app_rc/bbl/servos.py` (https://github.com/CyberBrick-Official/CyberBrick_Controller_Core/blob/master/src/app_rc/bbl/servos.py):

- L8-13 pins: `from machine import Pin, PWM` / `SERVO_CHANNEL1 = 3` / `SERVO_CHANNEL2 = 2` / `SERVO_CHANNEL3 = 1` / `SERVO_CHANNEL4 = 0`.
- L49-52 PWM construction: `self.servo1_pwm = PWM(Pin(SERVO_CHANNEL1), freq=50)` (same for 2-4).
- L84, L93 angle -> duty (10-bit, `duty()`): `duty = (int)(angle * 102 / 180 + 25)` then `self.servos_map[internal_idx].duty(duty)`. So 0 deg = 25/1023 (~0.49 ms at 50 Hz), 180 deg = 127/1023 (~2.48 ms), 90 deg = 76 (~1.49 ms).
- L297 `stop()`: `.duty(0)` releases the servo (no pulse).
- L225 docstring: duty "ranges from 25 to 125 for most servo motors".

`src/app_rc/boot.py` (https://github.com/CyberBrick-Official/CyberBrick_Controller_Core/blob/master/src/app_rc/boot.py), whole file is 24 lines:

- L9 `import bbl_product`; L15-16 `bbl_product.set_app_name("RC")`, `set_app_version("01.00.01.01")`; L21-24 `sys.path.append('/app')` / `import rc_main` / `rc_main.main()`.
- `src/app_rc/app/rc_main.py` L16-20 adds `/app` and `/bbl` to `sys.path` and moves `.frozen` to the end of `sys.path`, which means frozen modules exist in the firmware and the filesystem copies are meant to shadow them.

### B2. Is `bbl` frozen? Does replacing `boot.py` suffice?

- Repo README: "upload the directory contents to the onboard file system directory" to get RC functionality, and the docs' `ServosController.rst` is `.. automodule:: bbl.servos`, i.e. `bbl` is documented as the filesystem package in `src/app_rc/bbl/`. (README.md L30; docs/cyberbrick_core/lib/ServosController.rst L4)
- `bbl_product`, `ulogger`, `rc_module`, `ble_module`, `shutter_module` are imported but absent from the repo, so they are frozen into Bambu's firmware image. `rc_main.py` L18-20 reorders `.frozen` to the end of `sys.path`, confirming frozen modules are present. Whether `bbl` itself is ALSO frozen cannot be confirmed from the repo (see Unverified).
- MicroPython ESP32 port boot chain (https://github.com/micropython/micropython/blob/master/ports/esp32/main.c L158-186): `pyexec_file_if_exists("boot.py")`, then `main.py` (only in friendly REPL mode and when boot.py did not force exit), then the REPL loop. The stock `boot.py` calls `rc_main.main()` which never returns, so `main.py` and the REPL are never reached. Replacing `boot.py` alone therefore stops the RC app; `/app` and `/bbl` can stay on flash (they are only imported by `boot.py`). Note Bambu's stock `boot.py` on the actual board may differ from the repo copy; back it up first.
- Interrupting a running `boot.py` from the host: Ctrl-C bytes on USB-Serial/JTAG schedule a `KeyboardInterrupt` in the ISR (ports/esp32/usb_serial_jtag.c L57-58), and mpremote's `enter_raw_repl` sends `b"\r\x03"` first (tools/mpremote/mpremote/transport_serial.py L179). This is how `mpremote cp` gets in even while the RC app loops.

### B3. Non-blocking stdin, `print()` with no host, DTR/RTS resets

- The Core's REPL is on native USB: "The MicroPython REPL is on the onboard USB-C port (GPIO18=USB_D-, GPIO19=USB_D+) at baudrate 115200. This is a USB simulation UART called USB JTAG/serial debug unit." (CyberBrick docs/cyberbrick_core/quickref.rst L18-19)
- `select.poll()` on `sys.stdin` works: `sys.stdin`'s ioctl maps `MP_STREAM_POLL` to `mp_hal_stdio_poll` (shared/runtime/sys_stdio_mphal.c L88-98), and the ESP32 implementation polls the USB-Serial/JTAG RX FIFO into a ring buffer and reports `POLL_RD` when a byte is waiting (ports/esp32/mphalport.c L108-127). `poll.poll(timeout)` takes milliseconds; "In case of timeout, an empty list is returned." (https://docs.micropython.org/en/latest/library/select.html)
- `print()` with no host attached does not block or raise: `usb_serial_jtag_tx_strn` waits for TX FIFO space at most 200 ms, and only while `terminal_connected`; otherwise it marks the terminal disconnected and drops the data (ports/esp32/usb_serial_jtag.c L109-127). ESP-IDF says the same: output is buffered and after the buffer fills ("for example, if no PC Terminal is connected") there is "a one-time wait of 50 ms". (https://docs.espressif.com/projects/esp-idf/en/latest/esp32c3/api-guides/usb-serial-jtag-console.html)
- Does opening the port reset the board? The USB-Serial/JTAG peripheral does react to DTR/RTS, but only to a specific pulse train: Espressif's reset code "for the USB-Serial-JTAG peripheral" is a sequence of RTS/DTR writes with 100 ms holds (DTR low + RTS high, then RTS low, then both high) (https://github.com/espressif/esp-pylib/blob/master/esp_pylib/serial_reset.py L367-391). pyserial asserts DTR and RTS both high on open (see C2), which is the "Idle" state at the start of that sequence, so a plain open does not perform the reset sequence. mpremote relies on exactly this: "On all other host/driver combinations we keep the default behaviour (pyserial will set DTR and RTS automatically on open)" (transport_serial.py L87-90) and only works around spurious resets on Windows CP210x. Hardware-level guarantee: see Unverified.
- Soft reset (`Ctrl-D` / `mpremote soft-reset`) re-runs `boot.py` (main.c `soft_reset:` label L139, L158).

### B4. `machine.PWM.duty()` availability and firmware version

- The 10-bit `duty()` is a port extension, compiled in when `MICROPY_PY_MACHINE_PWM_DUTY` is set (extmod/machine_pwm.c L132-136). The ESP32 port sets `#define MICROPY_PY_MACHINE_PWM_DUTY (1)` (ports/esp32/mpconfigport.h L139) and implements `duty`, `duty_u16`, `duty_ns` side by side (ports/esp32/machine_pwm.c L766-782). The ESP32 quickref documents all three (https://docs.micropython.org/en/latest/esp32/quickref.html#pwm-pulse-width-modulation); the generic `machine.PWM` page lists only `duty_u16`/`duty_ns` (https://docs.micropython.org/en/latest/library/machine.PWM.html).
- The CyberBrick docs copy the ESP32 quickref with `duty()` present (docs/cyberbrick_core/quickref.rst L275-276), and the stock `servos.py` uses `duty()`, so it exists on the shipped firmware.
- MicroPython version in the Bambu build: not stated anywhere in the repo. The only version strings are app versions (`boot.py` `"01.00.01.01"`) and docs version `V01.00.00.03` (docs/conf.py L27). No GitHub releases or tags exist. Read it from the board: `mpremote exec "import sys; print(sys.version, sys.implementation)"`.
- C3 PWM budget: "ESP32-C2, C3, C5, C6, H2: 1 group, 4 timers, 6 channels, 4 frequencies" (esp32 quickref table). Four servos at one frequency fit.

### B5. mpremote commands

Source: https://docs.micropython.org/en/latest/reference/mpremote.html and tools/mpremote/mpremote/commands.py.

- Remote paths: "The `cp` command uses a convention where a leading `:` represents a remote path." Syntax `cp [-rf] <src...> <dest>`; `-r` recursive; files with matching SHA256 are skipped unless `-f`.
- (a) Backup whole filesystem: `mpremote cp -r :/ firmware/stock-backup/` is the documented shape, but the recursive code strips the trailing `/` from src (`commands.py` L200) leaving `:` with an empty path, then takes `basename("")` (L247, L130-131). Whether that walks the root correctly is not verified here; the safer, explicit form is `mpremote ls :` then `mpremote cp -r :boot.py :app :bbl :rc_config firmware/stock-backup/` (copying into an existing dir copies the named entries into it, L203-204, L248). Confirm with `mpremote tree :` first (`tree` exists, L232 of mpremote.rst).
- (b) One file to the board: `mpremote cp firmware/boot.py :boot.py` (docs example `mpremote fs cp main.py :main.py`).
- (c) Soft reset: `mpremote soft-reset` ("clear out the Python heap and restart the interpreter"). mpremote "does not soft-reset the device on its own"; action commands interrupt a running program but keep the heap.
- (d) Run without saving: `mpremote run gesture_test.py` (runs from RAM after a soft reset; `main.py` is not run). Chain commands with `+`: `mpremote cp boot.py : + soft-reset + repl`.
- Auto-connect picks "the first available USB serial device"; use `mpremote connect port:/dev/cu.usbmodemXXXX ...` to pin it. mpremote opens the port with `exclusive=True` (transport_serial.py L52, L64-65), so it will fail while the daemon holds the port; the Makefile must stop the daemon (or the daemon must release the port) before `cp`.

## C. Host side (macOS)

### C1. launchd LaunchAgents and `/dev/cu.*`

- Device nodes are world-read/write on this Mac: `crw-rw-rw- root wheel /dev/cu.Bluetooth-Incoming-Port` (`ls -l /dev/cu.*`, local). A user LaunchAgent runs as the logged-in user, so no entitlement or group is needed; the usbmodem node should enumerate with the same mode (verify once plugged: `ls -l /dev/cu.usbmodem*`).
- `KeepAlive`: "The default is false and therefore only demand will start the job. The value may be set to true to unconditionally keep the job alive." "The use of this key implicitly implies RunAtLoad." `RunAtLoad`: "whether your job is launched once at the time the job is loaded." Respawn throttle `ThrottleInterval`: "by default, jobs will not be spawned more than once every 10 seconds." (`man launchd.plist`, local)
- Also useful keys: `WorkingDirectory`, `EnvironmentVariables` (strings only), `StandardOutPath`/`StandardErrorPath`, `ExitTimeOut` (SIGTERM to SIGKILL delay). (`man launchd.plist`)
- Commands (`man launchctl`, local): `launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.noggin.daemon.plist`, `launchctl bootout gui/501/com.noggin.daemon`, `launchctl kickstart -k gui/501/com.noggin.daemon` ("-k If the service is already running, kill the running instance before restarting"), `launchctl print gui/501/com.noggin.daemon`. The man page: "domain-target is gui/501/, service-name is com.apple.example, and service-target is gui/501/com.apple.example." Per-user plists under `$HOME/Library/LaunchAgents` "must be owned by... the user loading them" and "must disallow group and world writes." UID here is 501 (`id -u`).

### C2. pyserial on macOS

- DTR/RTS on open: `SerialBase.__init__` sets `_rts_state = True`, `_dtr_state = True` (serial/serialutil.py L210-211); `Serial.open()` on POSIX applies them with `TIOCMBIS` unless `dsrdtr`/`rtscts` are enabled (serial/serialposix.py L347-351, L751-763). Docs: "The state of rts and dtr is applied" on open; they can be set before open. (https://pyserial.readthedocs.io/en/latest/pyserial_api.html)
- `exclusive`: "Set exclusive access mode (POSIX only)", added in 3.3; implemented with `fcntl.flock(fd, LOCK_EX | LOCK_NB)` (serialposix.py L392-398), which works on macOS. The port is opened `O_RDWR | O_NOCTTY | O_NONBLOCK` (L335).
- Use `/dev/cu.usbmodem*` (callout), not `/dev/tty.*`, on macOS; both exist (`ls /dev/cu.* /dev/tty.*`, local).

### C3. `nc -U` on macOS

- `man nc` (local): "-U Specifies to use Unix Domain Sockets." "-w timeout If a connection and stdin are idle for more than timeout seconds, then the connection is silently closed... The default is no timeout." There is no `-q`; macOS nc rejects it (`nc: invalid option -- q`).
- Local test (python3 `AF_UNIX` server + `printf 'eureka\n' | nc -U -w 1 /private/tmp/claude-501/n.sock`): server received `b'eureka\n'`, nc exit 0. With no server: exit 1 in 6 ms. With a server that accepts but never reads or closes: nc exits 0 after 1.0 s (the `-w` idle timeout), so the hook can never hang longer than `-w`.
- Gotcha found while testing: `AF_UNIX path too long` for the scratchpad path. macOS `sun_path` is 104 bytes; the daemon socket must use a short path such as `~/.noggin.sock` or `$TMPDIR/noggin.sock`.
- Hook one-liner that cannot block Claude: `printf 'eureka\n' | nc -U -w 1 ~/.noggin.sock; exit 0` (exit 0 even when the daemon is down, otherwise Claude Code shows a "hook error" notice).

## Implications for noggin

- Hook config: `Stop` (no matcher) -> eureka; `Notification` with matcher `permission_prompt|idle_prompt` -> attention. Both as `type: command`, `timeout: 2`, always `exit 0`. `idle_prompt` fires ~60 s after a response and `permission_prompt` ~6 s into a prompt, both only when the user looks away from the terminal; expect attention to be rarer than eureka.
- Set `"async": true` on both hooks or keep them sub-second: a synchronous hook blocks Claude until it exits.
- `Stop` does not fire on user interrupt or API error, and not for subagents; skip `SubagentStop`.
- Socket path must be short (<104 bytes). Use `~/.noggin.sock`.
- Daemon: pyserial `Serial(port, 115200, exclusive=True, timeout=...)`; default DTR/RTS high on open is the idle state and does not reset the C3. Make the daemon release the port (or be stopped via `launchctl bootout`) before any `mpremote` command, since mpremote also opens exclusively.
- Board program: `boot.py` loop with `select.poll()` on `sys.stdin` (POLLIN, short timeout) reading newline commands; `print()` is safe when nobody is listening. Use `PWM(Pin(n), freq=50)` and `duty()` with the stock formula `int(angle*102/180+25)` so angles match the designer's config; `duty(0)` for Rest.
- Backup: list with `mpremote tree :`, then copy named top-level entries into `firmware/stock-backup/`; do not trust `cp -r :/` until tried.
- Record the firmware's MicroPython version from `sys.version` on first contact and add it to CLAUDE.md.
- launchd plist: `KeepAlive true` (implies RunAtLoad), `StandardErrorPath` to a log, install with `launchctl bootstrap gui/501 <plist>`.

## Unverified

- Whether `bbl` and the stock `boot.py` on the shipped board match the repo (they may be frozen or newer). Check with `mpremote ls :` and `mpremote exec "import sys; print(sys.path)"`.
- The exact MicroPython version of Bambu's firmware (no version string in the repo).
- Hardware guarantee that a plain port open (DTR+RTS high) never resets the ESP32-C3 over USB-Serial/JTAG: inferred from esp-pylib's reset sequence and mpremote's reliance on default open; the Espressif TRM was not consulted.
- `mpremote cp -r :/ dir` root-copy behaviour: reasoned from source, not run.
- That the usbmodem device node is `crw-rw-rw-` like the other `/dev/cu.*` nodes here (no board plugged in).
- `CLAUDE_ENV_FILE` is referenced by the guide but its reference section was not read.
