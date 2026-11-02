#!/usr/bin/env bash
#
# A wizard walks a human through a manual procedure, step by step.
# Started from the /wizard skill's template, its library trimmed by hand to the
# helpers the stages call (#747): regenerating would bring the rest back.
# Author the per-step stages below the "STAGES" marker.

set -euo pipefail

# ──────────────────────────────────────────────────────────────────────────
# Wizard library: the template's UX, only the helpers this wizard uses.
# ──────────────────────────────────────────────────────────────────────────

if [[ -t 1 ]] && command -v tput >/dev/null 2>&1 && [[ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]]; then
  BOLD=$(tput bold); DIM=$(tput dim); RESET=$(tput sgr0)
  BLUE=$(tput setaf 4); GREEN=$(tput setaf 2); YELLOW=$(tput setaf 3)
else
  BOLD=""; DIM=""; RESET=""; BLUE=""; GREEN=""; YELLOW=""
fi

# Author sets this at the top of the stages section.
TOTAL_STAGES=0

_STAGE_INDEX=0

# _clear wipes the terminal so only the current step is on screen. No-op when
# output isn't a terminal, so piped logs stay readable.
_clear() {
  [[ -t 1 ]] || return 0
  if command -v tput >/dev/null 2>&1 && tput clear 2>/dev/null; then return 0; fi
  printf '\033[2J\033[3J\033[H'
}

# stage "Name" clears the screen, then announces a stage and shows progress.
# Clearing keeps only the current step on screen.
stage() {
  _clear
  _STAGE_INDEX=$((_STAGE_INDEX + 1))
  printf '\n%s%s▸ Stage %s/%s · %s%s\n' \
    "$BOLD" "$BLUE" "$_STAGE_INDEX" "$TOTAL_STAGES" "$1" "$RESET"
}

# say "..." prints a plain instruction line.
say()  { printf '  %s\n' "$1"; }
note() { printf '  %s%s%s\n' "$DIM" "$1" "$RESET"; }
warn() { printf '  %s⚠ %s%s\n' "$YELLOW" "$1" "$RESET"; }

# pause "msg" waits for the human to confirm they've done the manual part.
pause() {
  printf '  %s%s%s ' "$DIM" "${1:-Press Enter to continue}" "$RESET"
  read -r _ || true
}

# confirm "question" is a y/N gate; returns success on yes.
confirm() {
  local reply=""
  printf '  %s? %s [y/N] ' "$YELLOW" "$1"
  read -r reply || true
  [[ "$reply" =~ ^[Yy] ]]
}

# ask KEY "Prompt" reads a value into $KEY. Visible input (non-secret), edited
# with Readline. Fails at EOF with no input.
ask() {
  local input s=$'\001' e=$'\002' rc=0
  # Readline needs the colour codes wrapped in \001..\002 to place the cursor.
  read -e -r -p "  $s$BOLD$e$2$s$RESET$e " input || rc=1
  if (( rc )) && [[ -z "$input" ]]; then return 1; fi
  printf -v "$1" '%s' "$input"
}

# ask_secret KEY "Prompt" is like ask, but input is hidden.
ask_secret() {
  local input rc=0
  printf '  %s%s%s ' "$BOLD" "$2" "$RESET"
  read -rs input || rc=1
  printf '\n'
  if (( rc )) && [[ -z "$input" ]]; then return 1; fi
  printf -v "$1" '%s' "$input"
}

# finish clears, then shows the closing line.
finish() {
  _clear
  printf '\n%s%s  ✓ Setup complete%s\n\n' "$BOLD" "$GREEN" "$RESET"
}

# ──────────────────────────────────────────────────────────────────────────
# STAGES: author this section. One stage() per step the human takes.
# Replace the example below. Set TOTAL_STAGES to match the stages you write.
# Keep every stage inside run_wizard and the last line as is: bash then parses
# the whole file before the first prompt, so an edit mid-run can't break it.
# ──────────────────────────────────────────────────────────────────────────

run_wizard() {

[[ "${1:-}" =~ ^(wifi)?$ ]] || { echo "usage: scripts/setup.sh [wifi]   (wifi: only the Join the Wi-Fi step, as just wifi)" >&2; exit 2; }
TOTAL_STAGES=8
cd "$(dirname "$0")/.."            # repo root
PY=.venv/bin/python
MPR=.venv/bin/mpremote
JUST=.venv/bin/just
port() { ls /dev/cu.usbmodem* 2>/dev/null | head -n1; }
# board_send LINE: write one command to the Core over USB and print its reply (before the noggin service is installed)
board_send() {
  "$PY" - "$(port)" "$1" <<'PYEOF'
import serial, sys, time
with serial.Serial(sys.argv[1], 115200, timeout=0.5) as s:
    time.sleep(0.3); s.reset_input_buffer(); s.write((sys.argv[2] + "\n").encode()); time.sleep(0.5)
    print(s.read(200).decode(errors="replace").strip())
PYEOF
}

join_wifi() {
stage "Join the Wi-Fi"
[[ -n "$(port)" ]] || { warn "no Core on USB: plug it in with the USB-C cable and run this again"; exit 1; }
say "Adds this network to the ones the Core knows (wifi.json, over USB); it joins the known one it hears loudest."
CORES=$("$PY" -c 'from noggin.core import CORES; print(*CORES, sep="/")')
say "core.json names the Core ($CORES) and its servo ports. In a new place, run 'just wifi' for each Core."
note "eyes/wifi.json (gitignored, read by the noggin service) keeps every network and the token the second Core shares."
ask WIFI_SSID "Wi-Fi network name (SSID):"
ask_secret WIFI_PASSWORD "Wi-Fi password:"
until [[ -n "${CORE_NAME:-}" && "/$CORES/" == *"/$CORE_NAME/"* ]]; do ask CORE_NAME "Which Core is plugged in? [$CORES]:"; done
# core.json's servo ports (noggin/core.py, from the model's CHANNELS)
PORTS=$("$PY" -c 'import json, sys; from noggin.core import CORES; print(json.dumps({str(p): s for p, s in CORES[sys.argv[1]].items()}))' "$CORE_NAME")
(umask 077; WIFI_SSID="$WIFI_SSID" WIFI_PASSWORD="$WIFI_PASSWORD" "$PY" -c 'import os, pathlib; from noggin.wifi import add_network; add_network(pathlib.Path("eyes/wifi.json"), os.environ["WIFI_SSID"], os.environ["WIFI_PASSWORD"])')
printf '{"name": "%s", "ports": %s}\n' "$CORE_NAME" "$PORTS" > core.json
"$JUST" interrupt                       # stops the noggin service and drops the Core to its REPL, as just flash does
"$MPR" resume cp eyes/wifi.json :wifi.json
"$MPR" resume cp core.json :core.json
rm -f core.json
"$PY" eyes/interrupt.py reset
say "Listening 10 s for the beacon on UDP 4711 (expected: '<tag> noggin $CORE_NAME <ip> <uptime s> <version> <commit>') ..."
"$PY" -c 'import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.bind(("",4711)); s.settimeout(10); print(s.recv(128).decode())' \
  && say "The Core is on the Wi-Fi." || warn "no beacon; joining can take longer than 10 s, the network is out of range, or the SSID/password is wrong: run 'just wifi' again"
pause
}

if [[ "${1:-}" == wifi ]]; then          # just wifi: this step alone, then the noggin service back if it was running
  TOTAL_STAGES=1
  # the installed plist, not just start: that would repoint the service at this checkout; also after a failure or Ctrl-C
  launchctl print "gui/$(id -u)/com.noggin" >/dev/null 2>&1 && trap 'launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.noggin.plist" 2>/dev/null || true' EXIT
  join_wifi
  exit 0
fi

_clear
printf '\n%s%s  noggin eye Mech setup%s\n' "$BOLD" "$BLUE" "$RESET"
printf '%s  %s stages. You handle the cable, battery and screwdriver; this wizard drives the Core\n' "$DIM" "$TOTAL_STAGES"
printf '  and asks you what the Mech did. Ctrl-C any time and re-run.%s\n\n' "$RESET"
pause "Ready to start?"

stage "Plug in the Core"
say "Connect the Core to this Mac with the USB-C cable and switch the battery on."
note "USB powers the Core; the servos need the battery (or the USB-A -> XH2.54 lead)."
until [[ -n "$(port)" ]]; do pause "Waiting for /dev/cu.usbmodem* ... press Enter to re-check"; done
say "Found $(port)"
"$JUST" stop >/dev/null 2>&1 || true   # free the port if a noggin service from an earlier run holds it

stage "What is on the Core"
say "Reading MicroPython version and the file list."
"$JUST" core-info || warn "mpremote could not talk to the Core; is anything else holding the Link?"
want=$("$PY" -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['tool']['noggin']['micropython'])")
have=$("$MPR" resume exec "import sys; print('%d.%d' % sys.implementation.version[:2])" 2>/dev/null | tr -d '\r')
[[ "$have" == "$want" ]] || warn "The Core runs MicroPython ${have:-?}, not the $want this repo type-checks and compiles .mpy for (pyproject.toml [tool.noggin]): the eye program may not load."
note "Stock program looks like: boot.py, app/, bbl/ (see docs/references/stock-program-manifest.json)."
note "If you see eyes.py here, the eye program is already installed and a backup already exists."
pause

stage "Back up the stock program"
if [[ -d eyes/stock-backup && -n "$(ls -A eyes/stock-backup)" ]]; then
  say "eyes/stock-backup already exists; keeping it."
else
  say "Copying every file off the Core into eyes/stock-backup/ (needed to go back to the remote app)."
  confirm "Back up now?" && "$JUST" backup-stock
fi
pause

stage "Flash the eye program"
warn "This replaces boot.py on the Core. The stock remote app stops working until 'just restore-stock'."
confirm "Flash eyes/eyes.py + eyes/boot.py now?" || { warn "stopped before flashing"; exit 1; }
"$JUST" flash-usb                       # the first install carries boot.py and micropython-lib's hmac, which only go over USB
sleep 2
say "Ping reply: $(board_send ping)"
note "Expected: 'noggin ready' and/or 'ok'. If empty, unplug/replug and re-run this wizard."
pause

join_wifi

stage "Calibrate lids and eyes"
say "Calibration is live: eyes/calibration.json is pushed to the Core by the noggin service; nothing is reflashed."
say "Known-good values for this Mech are already in the file. Re-tune only what looks off."
note "Fit horns first with the servos at centre (board_send 'pose lids 0.5 eyes 90'), then the small screws."
board_send "pose lids 0.5 eyes 90" >/dev/null
confirm "With servos at centre: lids about half open, eyes straight? (if not, refit the horns now)" || warn "refit horns, then re-run this stage"
board_send "wince 2" >/dev/null; sleep 4
confirm "Did BOTH lids close and reopen?" || warn "a lid runs backwards: its servo is mounted the other way round (the Core mirrors the left lid's servo); remount it"
board_send "eureka 3" >/dev/null; sleep 6
confirm "Eyes together, straight at the end, nothing binding?" || warn "after install: 'noggin/noggin set l_eye_lo N' / l_eye_hi (centre = their average), r_eye likewise"
note "Tuning by eye after install: 'noggin/noggin pose lids 0.28 eyes 95' holds a pose; 'noggin/noggin set l_lid_rest 70' applies + saves."
note "Each lid: <lid>_lo closed, <lid>_rest at lid_rest, <lid>_hi open, both lids in the right servo's degrees. Never set *_lo/*_hi onto a hard stop: clutch servos slip."
note "Lid levels, fractions 0 closed .. 1 open: lid_closed (blink), lid_think, lid_open (eureka); lid_rest is the level the <lid>_rest points stand for."
pause

stage "Install hooks and the noggin service"
say "Adds async hooks to ~/.claude/settings.json and starts the noggin service (launchd com.noggin)."
confirm "Install now?" && "$JUST" install
sleep 2; "$JUST" status
pause

stage "End-to-end test"
say "Manual gesture through the noggin socket:"
noggin/noggin eureka 2 && say "sent" || warn "noggin not reachable"
say "Now open another terminal, start a Claude Code session, send any prompt."
say "Expected: lids half + slow drifts while it works, eureka when it answers."
note "Mute any time with 'noggin/noggin off', back with 'noggin/noggin on'."
pause "Press Enter when you have seen it (or given up)."

finish
}

run_wizard "$@"; exit
