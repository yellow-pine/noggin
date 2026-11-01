# Flashing

Our program replaces the Core's stock remote-control program; the firmware stays as it is (ADR 0002).

## First run

```
scripts/setup.sh     # guided first-run: plug in the Core, back up, flash, join the Wi-Fi, calibrate, install hooks + the noggin service
make wifi            # add a Wi-Fi network to the Core on USB (the wizard's Join the Wi-Fi step alone)
make flash           # install the eye program on the Core and reboot it: Wi-Fi while it beacons or no Core is on USB, else USB (USB=1 forces it)
make restore-stock   # put the stock remote-control program back on the Core
```

!!! warning "Type secrets in a Terminal window"
    Secrets (the Wi-Fi password) are typed in a Terminal window (`make wifi`, `scripts/setup.sh`), never at Claude
    Code's `!` prompt: it has no stdin, so a hidden password prompt there cannot be answered.

!!! danger "Never flash firmware"
    Never flash firmware with esptool or any third-party tool: the vendor states this bricks the board. `make flash`
    replaces the program only.

## Talking to the Core

- This board reports `3.4.0; MicroPython e7cd27f2 on 2025-06-09`; stock RC program 01.00.00.13.
- mpremote's own Ctrl-C does not interrupt the stock RC app, and `mpremote soft-reset` waits for a
  raw REPL the eye program never gives. `eyes/interrupt.py` handles both; every Makefile board
  target goes through it, then uses `mpremote resume`.
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
  ever goes that way). Both send the eye program, the files boot.py imports (`make mpy-list`), as .mpy
  (`make mpy`, into eyes/build): less RAM to import than the .py. boot.py stays .py (the Core runs boot.py only).
  A .py shadows its .mpy (import looks for the .py first), so `flash-usb` removes them and Wi-Fi takes only .mpy;
  a Core still on .py files refuses .mpy over Wi-Fi, so the first .mpy install goes over USB.
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
