# Standards audit: where we hand-roll, and what the standard is (2026-10-31)

Directive (Cansin, 2026-10-31): standards and well-maintained libraries first, always for security, protocols,
parsing and numerics; small glue stays custom. This note walks every hand-rolled piece in the repo, names the
standard or library, checks whether it runs on our platform, and recommends switch or keep.

Platform: the Mac runs CPython 3.12 under uv. Each Core runs the vendor's MicroPython build on an ESP32-C3, reporting
`3.4.0; MicroPython e7cd27f2 on 2025-06-09` (docs/build-notes.md). The setting is LAN only, two Cores, one Mac and one
developer. No device was touched for this note. Repo claims cite `file:line` on main at 810a010. Upstream MicroPython
links are pinned to v1.26.1.

## Ranked recommendations (security first)

| # | Area | Verdict | Value |
|---|---|---|---|
| 1 | CI fetches the reviewer's skills unpinned | **switch**: pin `ref` per lock entry and pin third-party actions to SHAs | security |
| 2 | The Link's HMAC | **switch** to `hmac` (micropython-lib on the Core, stdlib on the Mac); keep the scheme | security |
| 3 | The Link: unauthenticated beacons and acks, replay after a reboot, non-constant-time compare | **keep custom**, fix the gaps | security |
| 4 | DTLS / mTLS / MQTT / CoAP+OSCORE / ESP-NOW / Matter for the Link | **keep custom** for now; decision below | security |
| 5 | noggin service socket: one `recv(65536)` | **fix**: read to EOF (stdlib) | robustness |
| 6 | Hooks installer rewrites `~/.claude/settings.json` in place | **switch** to an atomic write, or a Claude Code plugin; decision below | data loss |
| 7 | STL parsing and mesh volume by hand | **switch** to trimesh (already a dependency) | parsing |
| 8 | Circle fit via normal equations and hand Gaussian elimination | **switch** to `numpy.linalg.lstsq` | numerics |
| 9 | Servo PWM through 10-bit `duty()` | **switch** to `duty_ns()` (standard API), recheck calibration | hardware |
| 10 | Collision: KD-tree, ray parity, pseudo-normals | **prototype** trimesh + `rtree` (or python-fcl); switch if numbers match | numerics |
| 11 | Rodrigues rotation | **switch** to `trimesh.transformations.rotation_matrix` | numerics, trivial |
| 12 | Wi-Fi flashing (#108, PR #124) | **keep custom**: no standard runs on this build | protocol |
| 13 | UDP beacon discovery vs mDNS | **keep** the beacon (it is our liveness signal), authenticate it (#3) | protocol |
| 14 | Everything else (four-bar solver, report stamps, easing, JSON, mpremote, launchd, Blender, CadQuery) | **keep** | none |

## 1. CI: the reviewer's skills and action pins (security)

- What we do: `review.yml:24` runs `npx -y skills@1.7.4 experimental_install` against the base branch's
  `skills-lock.json`, then the Claude reviewer runs those skills with `pull-requests: write` and posts approve or
  request-changes reviews (`review.yml:35, 68`).
- Finding: `experimental_install` never checks `computedHash`. `runInstallFromLock` builds each source with
  `buildLocalUpdateSource(entry)`, which appends `entry.ref` only when one is set, and then installs
  (skills@1.7.4 `dist/cli.mjs` L7003-7066). `computedHash` is written when skills are added (L5003-5008, L6844-6851)
  and is compared only by the update check (L8117). None of our 20 entries has a `ref`, so every review run installs
  whatever is at HEAD of `mattpocock/skills` and `DietrichGebert/ponytail`. An upstream change, or a compromise of
  either repo, silently changes the reviewer's instructions. Merge-on-green trusts that reviewer.
- Standard: pin to an immutable commit. The lock format already supports `ref`. GitHub's hardening guide says "Pin
  references to actions to a commit SHA" and warns that "a tag can be moved or deleted if a bad actor gains access"
  (https://docs.github.com/en/actions/reference/security/secure-use, "Using third-party actions"). `claude-code-action`
  is already pinned by SHA (`review.yml:50`). `astral-sh/setup-uv@v7` (`check.yml:18`) and the `actions/*@v7/@v8` steps
  are pinned by tag. Dependabot already watches `github-actions` (`.github/dependabot.yml`), so SHA pins still get
  bump PRs.
- Cost: add `"ref": "<sha>"` to each lock entry (or check `computedHash` after install: the hash is sha256 over sorted
  relative paths and contents, cli.mjs L1137-1147). Bumps become deliberate PRs.

## 2-4. The Link (eyes/wifi.py, noggin/wifi.py)

What we do: datagrams `<tag> <seq> <line>`, where the tag is HMAC-SHA256 truncated to 128 bits over
`<core> <seq> <line>` with a shared 128-bit token (`eyes/wifi.py:26-37`; token from `openssl rand -hex 16`,
`scripts/setup.sh:262`). The Core drops a seq below its highest and re-acks a repeated one (`eyes/wifi.py:93-119`).
The Mac retries with growing ack windows and falls back to USB (`noggin/wifi.py`). There is no confidentiality, and
none is needed: commands are not secret and the Wi-Fi password never travels on the Link.

### 2. The HMAC itself

- The hand-rolled `tag()` is correct. On this Mac it matched `hmac.new(k, m, hashlib.sha256).hexdigest()[:32]` for
  keys of 0, 1, 64, 65 and 200 bytes and messages of 0, 11 and 300 bytes. Truncating to 128 bits is within RFC 2104
  §5 (https://www.rfc-editor.org/rfc/rfc2104#section-5). `eyes/test_wifi.py:226` checks only self-consistency, not
  against a reference.
- Standard on the Core: micropython-lib `python-stdlib/hmac` v3.4.4 needs only `hashlib` and `binascii`
  (https://github.com/micropython/micropython-lib/blob/master/python-stdlib/hmac/hmac.py). The vendor documents both
  modules as present (CyberBrick_Controller_Core docs/library/index.rst L60-122). `mpremote mip install` installs from
  the host over USB, so the Core needs no network to get it
  (https://github.com/micropython/micropython/blob/master/docs/reference/packages.rst L82-90). On the Mac: stdlib
  `hmac`. The call `hmac.new(key, msg, hashlib.sha256).hexdigest()[:32]` reads the same on both sides.
- Cost: one more file on the Core (`make flash` and the release zip), and ~8 lines of crypto deleted. Add a test that
  pins `tag()` to stdlib `hmac`. **Switch.**

### 3. Gaps in the scheme (keep it custom, fix these)

- **Constant-time compare.** `eyes/wifi.py:104` compares tags with `!=`. MicroPython has no `compare_digest`: neither
  micropython-lib's hmac nor any micropython-org code defines one (code search). The fix is a 3-line XOR-accumulate
  compare. Remote timing over Wi-Fi UDP is hard to exploit, but this is the standard practice
  (https://docs.python.org/3.12/library/hmac.html#hmac.compare_digest).
- **Replay after a Core reboot.** On main, `self.last = (-1, None)` lives in RAM (`eyes/wifi.py:66`). After a reboot,
  any datagram captured earlier is accepted again in ascending order: old gestures, old `set` calibration lines. PR #124
  persists the highest seq in `link.seq`, which fixes this (one flash write per non-`put` command).
- **Unauthenticated beacons and replies.** The beacon (`eyes/wifi.py:83-84`) and `ok/err <seq>` replies carry no tag.
  The Mac trusts the beacon's source address (`noggin/wifi.py:48-52`) and accepts any reply from `(ip, 4712)`
  (`noggin/wifi.py:83-95`). A LAN host can beacon as `eyes` and draw the Mac's commands, or spoof acks so lines never
  fall back to USB. Under PR #124 it can also fake the flash outcome. Fix: tag the beacon and every reply with the
  same `tag()` (name, seq or uptime bound in), ~4 lines each side.
- Token storage: plaintext `wifi.json` on the Core and the Mac (umask 077, gitignored). The Mac-side standard would be
  the Keychain. It is not worth it while the same token sits readable on the Core's filesystem over USB.

### 4. Standard secure channels considered

| Option | Runs on the Core? | Runs on the Mac? | Verdict |
|---|---|---|---|
| DTLS (PSK or certs) | Upstream MicroPython has `PROTOCOL_DTLS_CLIENT/SERVER` from v1.25.0 (commit 321b30ca56; ssl.rst L123-181, v1.26.1). The vendor's ssl doc lists only `PROTOCOL_TLS_CLIENT/SERVER` (ssl.rst L16-26, L123-126), and `e7cd27f2` is not an upstream commit (GitHub API 422), so this build is **unverified**. **No TLS-PSK**: "psk" never appears in `extmod/modtls_mbedtls.c` | **No DTLS in CPython `ssl`**; needs a third-party binding | cost too high |
| TLS-PSK over TCP | No (above) | CPython's PSK callbacks arrived in 3.13 (https://docs.python.org/3.13/library/ssl.html); we run 3.12 | not possible |
| mTLS over TCP (self-signed certs, pinned) | Documented: `CERT_REQUIRED` validates the peer, server or client (vendor ssl.rst L24-26); untested on the C3 | stdlib `ssl` | the only standard that fits; costs cert provisioning, TCP connection state in the cooperative loop, mbedTLS RAM on the C3 |
| MQTT (umqtt + mosquitto, TLS) | `umqtt.simple` takes `ssl=` (micropython-lib umqtt/simple.py L29-88) | mosquitto supports `psk_hint`/`psk_file` (https://mosquitto.org/man/mosquitto-conf-5.html), but the Core cannot do PSK | adds a broker for two subscribers; no |
| CoAP + OSCORE (RFC 8613) | microCoAPy has no OSCORE (https://github.com/insighio/microCoAPy); micropython-lib has no CoAP | aiocoap implements OSCORE and EDHOC (https://aiocoap.readthedocs.io/en/latest/stateofoscore.html) | we would hand-roll OSCORE on the Core: worse than now |
| ESP-NOW | yes (radio note) | **no**: a Mac cannot speak it without a bridge board | no |
| Matter | no official MicroPython SDK; uMatter is an experimental C-module proof of concept for C5/C6 (https://github.com/mateuszsury/uMatter) | — | no |

No LAN IoT command-channel standard runs on both ends here except mTLS over TCP. Our scheme is the integrity half of
what DTLS and OSCORE do: a MAC with replay protection. **Keep it, apply #2 and #3.** Revisit mTLS if confidentiality
is ever wanted.

## 5. The noggin service socket (noggin/service.py)

- `noggin/service.py:246` does one `conn.recv(65536)`. A stream socket may return part of a message, and a
  `UserPromptSubmit` Trigger carries the full prompt, "Pasted content ... arrives expanded in place"
  (https://code.claude.com/docs/en/hooks.md, "UserPromptSubmit input"). A long prompt or a big paste is truncated,
  fails JSON and is dropped. Fix: read to EOF (`conn.makefile("rb").read()` under the existing timeout). This is
  stdlib, a few characters.
- The socket file is `srwxr-xr-x` on this Mac (default umask), so only Cansin can connect. Keep it.
- Alternatives: Claude Code `type: "http"` hooks would delete `hook.sh` and `nc`
  (https://code.claude.com/docs/en/hooks.md, "HTTP hook fields"). But the service would then listen on localhost TCP,
  which any local process or a browser page can reach. The Unix socket is safer. launchd's `Sockets` key
  (`man launchd.plist`) gives socket activation, which we do not need with `KeepAlive`. **Keep, fix the read.**

## 6. Hooks installer, plist, settings (noggin/install_hooks.py, Makefile)

- `install_hooks.py:39` does `json.dump(cfg, open(path, "w"))`. That truncates `~/.claude/settings.json` before
  writing, so a crash, a disk-full or a concurrent Claude Code write loses the user's settings. Standard: write a temp
  file in the same directory, then `os.replace` (https://docs.python.org/3.12/library/os.html#os.replace). The same
  applies to `calibration.json` (`service.py:198`), though that one is in git.
- Alternative standard: ship the hooks as a Claude Code plugin. "Define plugin hooks in `hooks/hooks.json` ... When a
  plugin is enabled, its hooks merge with your user and project hooks" (https://code.claude.com/docs/en/hooks.md,
  "Hook locations"). `claude plugin install --scope user` still writes `enabledPlugins` to a settings file, but
  Claude Code writes it, not our script. There is no CLI that edits hooks; `/hooks` is read-only.
- Plist: `sed 's|__REPO__|…|'` (`Makefile` `start`) breaks on a path containing `|` or `&`. `plistlib` (already used
  by `make check`) could write it. Low value. **Keep.** `launchctl bootstrap/bootout` is the current API. **Keep.**

## 7-11. The model (model/)

- **STL I/O (switch).** `model/fits.py:32` parses binary or ASCII STL with `struct`, and `model/beams.py:48`
  integrates signed tetrahedra by hand. trimesh 5.2.0 is already locked: `load_stl` reads binary and falls back to
  ASCII (trimesh/exchange/stl.py L23-52), and `mesh.volume` / `mass_properties` are on the mesh (trimesh/base.py).
  The reports restamp.
- **Circle fit (switch).** `model/fits.py:40-86` builds the Kasa normal equations by hand and solves them with
  pure-Python Gaussian elimination. Normal equations square the condition number. `numpy.linalg.lstsq` on the
  `[x, y, 1]` design matrix is the same fit, done stably
  (https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html). scikit-image's `CircleModel`
  (skimage 0.26 measure/fit.py L455) would add a large dependency for three lines. No.
- **Collision (prototype first).** `model/engine/meshes.py:104-200` does KD-tree pruning,
  `trimesh.triangles.closest_point`, a hand-written Möller-Trumbore ray-parity `inside()` (L131) and pseudo-normals
  (L150). This exists because trimesh's own proximity needs `rtree`: on this venv, `Trimesh.contains`,
  `proximity.signed_distance` and `proximity.closest_point` all raise `ModuleNotFoundError: rtree`. `CollisionManager`
  needs python-fcl (`trimesh.collision.fcl is None` here) and offers `min_distance_*` and `ContactData.depth`
  (trimesh/collision.py L83-92, L186-196, L467-621). Adding `rtree` would let `signed_distance` and `contains`
  replace `to_surface` / `inside` / `pseudo_normal`. Risk: runtime, and the "0 mm designed contact vs penetration"
  semantics. Prototype on the current reports and switch if the numbers agree to 0.01 mm.
  **Superseded (#139):** the MuJoCo switch (#146) replaces this collision code with convex decomposition, so the
  prototype was dropped. Its one finished run, on noggin-eyes (287 judged pairs), matched our judge to 1e-15 mm with
  no penetration flips, but `signed_distance` took 663 s against our 9 s.
- **Rotation (switch, trivial).** `model/engine/linkage.py:18` is Rodrigues about an axis through a point.
  `trimesh.transformations.rotation_matrix(angle, direction, point)` has the same contract (in radians).
- **Keep:** the four-bar solver (`linkage.py:30-82`) is the closed-form circle intersection; a numeric solver (sympy,
  pinocchio) adds nothing for planar loops. The report stamps (`model/engine/run.py:49-77`) are sha256 content
  hashing, which is the standard; DVC would be a workflow, not a fix. The voxel cable union (`cables.py:166-212`) is
  low value to replace (trimesh voxel marching cubes needs scikit-image; a manifold3d union would change the
  conservative-by-design result). CadQuery STEP/STL, Blender `bpy`, scipy `ConvexHull` and ffmpeg are already
  libraries.
- Minor: `eyes/build_trace.py:49` range-fetches a zip member and raw-inflates it without checking the bytes. Pinning a
  sha256 of the fetched range is the standard integrity check. Low.

## 9. The Core program (eyes/)

- **PWM (switch, with a hardware check).** `eyes/eyes.py:74-75` drives servos with `duty(int(angle*102/180+25))`,
  10-bit at 50 Hz: 102 counts over 180°, so **~1.76° per step**. Calibration decimals and slow eases (900-1200 ms
  lid droops) are quantised to that. `duty_ns()` sets the pulse width directly
  (https://docs.micropython.org/en/latest/esp32/quickref.html, PWM). The LEDC hardware gives at least 13 bits even
  at 5 kHz, and more at lower frequencies (ESP-IDF LEDC, ESP32-C3:
  https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/api-reference/peripherals/ledc.html). The same 0.49-2.48 ms
  mapping keeps the calibration, but rounding moves every position slightly, so the lid stops must be rechecked on
  the Mech.
- **Keep:** quadratic ease-out (`eyes.py:123-137`) is two lines. Calibration as JSON is stdlib. `asyncio` is documented
  on the build, but the cooperative poll loop (`boot.py`) is simpler. mpremote is the standard host tool;
  `eyes/interrupt.py` exists only because the stock app ignores mpremote's Ctrl-C (build-notes).

## 12. Wi-Fi flashing (#108, PR #124)

- Standard options, and why none fits:
  - The vendor **removes** `esp32.set_boot`, `get_next_update` and `mark_app_valid_cancel_rollback`, and `webrepl`
    (index.rst L193-215, "to prevent unauthorized firmware manipulation", L217-222). Upstream ESP32_GENERIC_C3 has a
    single `factory` app partition with no OTA (partitions-4MiBplus.csv, v1.26.1). Firmware OTA is also against
    ADR 0002 and "never flash firmware".
  - `mip` on the device needs `requests`, network access and the HTTPS index (micropython-lib mip/__init__.py L6-25).
    Pointing it at a LAN HTTP server would be unauthenticated code download, worse than ours.
  - mpremote's only transports are serial and `rfc2217://` (mpremote.rst L94-105); there is no WebREPL transport.
- PR #124's design is sound: HMAC-tagged `put` chunks, a `commit <file> <sha256>` whose hash travels in an
  authenticated line (end-to-end integrity), `.bak` plus a 10 s probation in `boot.py`, and USB as recovery. **Keep it
  custom.** It depends on #3, though: an unauthenticated reply can fake the flash outcome.

## 13. Discovery

- MicroPython's ESP32 port runs an mDNS responder that advertises `network.hostname()` as an A record only
  (`MICROPY_HW_ENABLE_MDNS_RESPONDER`, mpconfigport.h L356-361, v1.26.1); there is no `mdns_service_add`, so no
  DNS-SD. The vendor's doc says "Broadcasting via mDNS. (If enabled)" (network.rst L169-193). The Mac resolves
  `.local` natively (`scutil --dns` shows `domain: local, options: mdns`).
- mDNS answers "where", not "is it alive". The noggin service's Wi-Fi-or-USB choice runs on beacon freshness
  (`noggin/wifi.py:59-60`), so replacing the beacon would need a probe loop instead. **Keep the beacon and tag it
  (#3).** Optionally set `network.hostname(name)` so `eyes.local` works for humans (one line, after a REPL check).

## Decisions for Cansin

1. **Link security level.** Keep integrity-only HMAC over UDP (recommended, with #2 and #3), or move to mTLS over TCP
   with pinned self-signed certs (the only standard that runs on both ends; confidentiality, at the cost of cert
   provisioning and C3 RAM).
2. **Hooks.** Atomic merge into `settings.json` (small, recommended now), or ship noggin's hooks as a Claude Code
   plugin. Either touches `~/.claude` and needs your go.
3. **New model dependency.** Allow `rtree` (or python-fcl) so trimesh replaces our collision geometry, after a
   prototype shows matching numbers.
4. **PWM `duty_ns`.** Finer servo steps, at the cost of a hands-on recheck of the lid stops.
5. **CI pins.** Pin skills `ref`s and action SHAs: deliberate bumps instead of following HEAD.

## Open checks (one 30 s REPL session when serial is free)

`import hmac` (expected to fail until installed); `import mip, requests`; `hasattr(ssl, "PROTOCOL_DTLS_CLIENT")`;
`esp32.Partition.find(esp32.Partition.TYPE_APP)`; `network.hostname()`; `os.statvfs("/")`, and the filesystem type
(LittleFS wear-levels the `link.seq` writes). Which upstream release `e7cd27f2` is built from is unverified: it is not
an upstream commit, and the build date falls between v1.25.0 (2025-04-15) and v1.26.0 (2025-08-09).
