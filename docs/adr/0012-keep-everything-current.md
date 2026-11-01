# Keep everything current, the Core's firmware included, through the vendor's own tools

> Decided with Cansin on 2026-11-01 (grilling after the stack review, #334). Supersedes ADR 0002's "never touch the
> firmware". Research: docs/research/2026-11-01-stack-alternatives.md.
>
> Amended 2026-11-01 (#360): the 14 days are Dependabot's cooldown, not a review rule. Claude's review judges a bump on
> its merits and never rejects or flags it for being newer; a bump that arrives early (a registry with no publication
> date, like some Docker images) goes in on green.

Every dependency, tool, toolchain and firmware is kept at its **newest stable release once that release is at least
14 days old**; a security fix goes in at once. The delay guards against a bad or compromised fresh release.

- **Packages and actions:** Dependabot opens the bumps after its 14-day cooldown and they auto-merge on green (CI and
  Claude's review gate them, on what the bump changes, not its age), majors included.
- **Pins Dependabot cannot see** get a weekly re-pin job that opens a PR (Blender's tarball and its sha256, like the
  reviewer's skills already).
- **Python** is the newest version every dependency ships wheels for.
- **The Core's firmware** is updated with the vendor's own app or desktop tool (Bluetooth, or its wired upgrade tool),
  never with a third-party image. The Core has the ESP32-C3's flash encryption on (community evidence, to be read
  off our Cores), so only the vendor's encrypted builds boot, and a plaintext image soft-bricks it ([Espressif: flash
  encryption](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/security/flash-encryption.html)). A
  weekly job opens an issue when the vendor's firmware release notes change; Cansin updates both Cores, then
  `make flash-usb` reinstalls the eye program (the vendor's update replaces it) and `make backup-stock` refreshes the
  backup.
- **The Core's MicroPython pins follow the Core**, not upstream: mpy-cross, the stubs, the stand-in's tag,
  micropython-lib's `hmac` and `[tool.noggin] micropython` move when a firmware update changes the Core's version, so
  the checks describe what the Core runs.
- **esptool only for read-only queries** (`esptool get-security-info`), never a write.

ADR 0002's other half stands: the eye program replaces the stock program on the Core's filesystem, and the stock
program is backed up and restorable.

## Considered options

- **Never touch the firmware** (ADR 0002): it froze the Core on whatever build it shipped with.
- **Upstream MicroPython on the Core**: flash encryption makes a plaintext image unbootable; rejected.
- **Latest at once, no delay**: rejected for the supply-chain risk of a fresh release.
