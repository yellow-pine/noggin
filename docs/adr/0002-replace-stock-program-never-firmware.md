# Replace the stock program; never touch the firmware

> Firmware half superseded 2026-11-01 by ADR 0012: the Core's firmware is kept current through the vendor's own
> tools, never a third-party image. Replacing the stock program on the filesystem stands.

The stock program (the vendor's remote-control app) owns the servos and runs forever from `boot.py`, so the eye program replaces it on the Core's filesystem via USB serial (mpremote). The vendor's docs state the Core is permanently damaged by third-party firmware flashing (esptool and friends), so the firmware image is never modified; only files on the filesystem are. The stock program is backed up before replacement and restorable, so the mech can go back to remote control.

## Consequences

- The vendor's phone/desktop apps cannot drive the mech while the eye program is installed.
- Any contributor instruction that mentions esptool is wrong and must be removed.
