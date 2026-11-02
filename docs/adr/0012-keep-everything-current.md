# Keep everything current, the Core's firmware included, through the vendor's own tools

> Decided with Cansin on 2026-11-01 (grilling after the stack review, #334). Supersedes ADR 0002's "never touch the
> firmware". Research: docs/research/2026-11-01-stack-alternatives.md.
>
> Amended 2026-11-01 (#360): the 14 days are Dependabot's cooldown, not a review rule. Claude's review judges a bump on
> its merits and never rejects or flags it for being newer; a bump that arrives early (a registry with no publication
> date, like some Docker images) goes in on green.
>
> Amended 2026-11-02 (#472, spec #467): the CI images rebuild only on a Dockerfile change, no weekly rebuild.
>
> Amended 2026-11-02 (#529): gh in the CI images comes from GitHub CLI's signed apt repo, unpinned, no cooldown.
>
> Amended 2026-11-02 (#534): reverses #472's "no weekly rebuild": the CI images also rebuild weekly, uncached.

Every dependency, tool, toolchain and firmware is kept at its **newest stable release once that release is at least
14 days old**; a security fix goes in at once. The delay guards against a bad or compromised fresh release.

- **Packages and actions:** Dependabot opens the bumps after its 14-day cooldown and they auto-merge on green (CI and
  Claude's review gate them, on what the bump changes, not its age), majors included.
- **Pins Dependabot cannot see** get a weekly re-pin job that opens a PR (Blender's tarball and its sha256, like the
  reviewer's skills already).
- **CI images** (ci/, ADR 0009) rebuild when a Dockerfile changes (#472), Dependabot's `/ci` bumps of their base
  images among them, and weekly without the layer cache, on Mondays before the image scan (#534): the archive's
  security fixes land within a week, not when Ubuntu republishes its image and that bump clears the cooldown (up to
  about three weeks, which left Grype's weekly scan re-finding fixed issues). They run only CI. One exception to their pinned sources and the cooldown: gh comes
  from GitHub CLI's signed apt repo (keyring sha256-checked), its newest release whenever its build step reruns (a new
  Ubuntu digest, or the weekly uncached build); Ubuntu's archive froze it at 2.45, built with a Go whose stdlib Grype flagged in 120
  alerts (#529).
- **GitHub's runner image** is named (`ubuntu-26.04`), never `ubuntu-latest`, which moves under us (#392); it moves
  to the next LTS by hand, when GitHub announces that as `ubuntu-latest`, two years apart, too rare for a re-pin job.
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
