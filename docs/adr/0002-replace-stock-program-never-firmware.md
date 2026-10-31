# Replace the stock program; never touch the firmware

The stock program (the vendor's remote-control app) owns the servos and runs forever from `boot.py`, so the eye program replaces it on the Core's filesystem via USB serial (mpremote). The vendor's docs state the Core is permanently damaged by third-party firmware flashing (esptool and friends), so the firmware image is never modified; only files on the filesystem are. The stock program is backed up before replacement and restorable, so the mech can go back to remote control.

## Consequences

- The vendor's phone/desktop apps cannot drive the mech while the eye program is installed.
- Any contributor instruction that mentions esptool is wrong and must be removed.
