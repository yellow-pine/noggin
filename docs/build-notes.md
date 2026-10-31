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
- Plan A is to try USB power alone (USB-C to the Core plus the USB-A to
  XH2.54 lead into the shield's power input for 5 V); plan B is 2S cells.

## Talking to the Core

- ESP32-C3 running Bambu's MicroPython build. USB-C is the REPL at 115200,
  enumerating on macOS as `/dev/cu.usbmodem*`.
- Upload files with `mpremote`. Never flash firmware with esptool or any
  third-party tool: Bambu states this bricks the board.
- The stock program's `boot.py` runs the remote-control app forever, so a
  custom program must provide its own `boot.py`.
