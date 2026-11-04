# Flashing

Our program replaces the Core's stock remote-control program; the firmware stays as it is (ADR 0002).

## First run

```
scripts/setup.sh     # guided first-run: plug in the Core, back up, flash, join the Wi-Fi, calibrate, install hooks + the noggin service
just wifi            # add a Wi-Fi network to the Core on USB (the wizard's Join the Wi-Fi step alone)
just flash           # install the eye program on the Core and reboot it: Wi-Fi while it beacons or no Core is on USB, else USB (just flash-usb forces it)
just restore-stock   # put the stock remote-control program back on the Core
```

> [!WARNING]
> **Type secrets in a Terminal window.** Secrets (the Wi-Fi password) are typed in a Terminal window (`just wifi`,
> `scripts/setup.sh`), never at Claude Code's `!` prompt: it has no stdin, so a hidden password prompt there cannot be
> answered.

> [!CAUTION]
> **Firmware only from the vendor.** Update the Core's firmware with the vendor's own app or desktop tool only (ADR
> 0012), then `just flash-usb`, since the update replaces the eye program. Never write firmware with esptool or any
> third-party tool: the Core's flash encryption leaves a third-party image unbootable. `just flash` replaces the program
> only.

## Talking to the Core

- The Core is an ESP32-C3 running the vendor's MicroPython build. Its filesystem is LittleFS, so the program's
  writes are wear-levelled. USB-C is the REPL at 115200, enumerating on macOS as `/dev/cu.usbmodem*`.
- The eyes Core's USB-C carries data one way round only: flipped, it powers and boots but the Mac sees no device
  (inferred from one plug each way). If `/dev/cu.usbmodem*` does not appear, turn the plug over.
- Download mode (KEY held at plug-in) shows no USB device on the Mac, so the Core's firmware is updated through the
  vendor's phone app over Bluetooth alone (ADR 0012), then `just flash-usb` over the cable.
- mpremote's own Ctrl-C does not interrupt the stock RC app, and `mpremote soft-reset` waits for a
  raw REPL the eye program never gives. `eyes/interrupt.py` handles both; every board recipe in the justfile
  goes through it, then uses `mpremote resume`.
- Its MicroPython is 1.23.0 preview (`sys.implementation._mpy` 774: .mpy version 6.3, no native arch), pinned once
  as `[tool.noggin] micropython` in pyproject.toml. pyright checks the Core's files against
  `micropython-esp32-esp32_generic_c3-stubs` 1.23 as the standard library (`eyes/test_micropython.py`; the stubs
  still take a tuple in `str.startswith`, so `eyes/test_wifi.py` keeps its own check), and `mpy-cross` 1.23 compiles
  them. Bytecode-only .mpy files load on any 6.x ([mpyfiles](https://docs.micropython.org/en/v1.23.0/reference/mpyfiles.html)).
  The setup wizard warns when the board reports another version.
- Upload files with `just flash`: over the Wi-Fi Link while the Core beacons or when no Core is on USB (the noggin
  service then waits up to 22 s for its beacon), else `mpremote` over USB (`just flash-usb` forces the cable; boot.py only
  ever goes that way). Both send the eye program, the files boot.py imports (`just mpy-list`), as .mpy
  (`just mpy`, into eyes/build): less RAM to import than the .py. boot.py stays .py (the Core runs boot.py only).
  A .py shadows its .mpy (import looks for the .py first), so `flash-usb` removes them and Wi-Fi takes only .mpy;
  a Core still on .py files refuses .mpy over Wi-Fi, so the first .mpy install goes over USB.
- `just mpy` stamps the program with the repo's version and commit (eyes/build/stamp.py, never in git), which its
  beacon reports; `noggin status` shows them beside the noggin service's own (read when it started: `just start` after
  a pull) and warns when the Core runs an older release (`just flash`). The version is git's for the checkout
  (`v0.2.6`, or `v0.2.6-3-gabc1234` three commits past it), and the warning compares the releases alone, so a Core
  flashed from an older commit since the same release shows it but no warning; on USB alone there is no beacon, so no version. A program from before the stamp (#357) beacons without them and the noggin service ignores
  it, so that Core is flashed over USB once (`just flash-usb`, the plug the right way round).
- The stock program's `boot.py` runs the remote-control app forever, so a
  custom program must provide its own `boot.py`.

## Stock program on the Core (from its rc_mpy manifest)

The stock RC program's manifest lists what it expects on the Core: `boot.py`, `app/rc_main.py`, compiled `app/control.mpy`,
`app/devices.mpy`, `app/parser.mpy`, and `bbl/{__init__,buzzer,executor,leds,
motors,servos,sleepModule}.py`. So `bbl` lives on the filesystem, not frozen,
and the file list matches the GitHub repo's `src/app_rc/`. Local copy with
md5s: `docs/references/stock-program-manifest.json`. Still verify on the real
board with `mpremote ls` before replacing anything.
