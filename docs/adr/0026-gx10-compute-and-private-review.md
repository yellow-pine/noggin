# GX10 computes; the Mac authors and reviews

> Decided with Cansin on 2026-11-05, ticket #979. Amends ADR 0025's local-only private-reference boundary.

The trusted GX10 runs heavy Python, CAD, fitting, Blender finishing, rendering and validation. Its isolated native ARM64
container builds the project's pinned Blender from checksum-verified official source and matching dependencies. Python
and Blender share one measured 32 GiB worker limit; a measured cgroup OOM retries the same job once at 64 GiB after a
fresh check retains at least 8 GiB of host headroom. The Mac keeps its existing 3 GB Blender safety limit and remains
the interactive viewer.

Cansin's editable private Morty reference remains authoritative on the Mac. Its full mesh, paint and fit data may travel
over the existing Tailscale SSH connection to GX10-local, private, hash-versioned input directories. One writer owns
each source; jobs read immutable staged inputs and return candidates. Private inputs, caches and reference-containing
results stay outside git, public CI uploads and published artifacts. This trust amendment changes no anatomy, motion,
wall, wiring or print-acceptance requirement.

A detached controller keeps computing through a Mac disconnect. It snapshots completed outputs with the exact source
commit and checksums before releasing the shared checkout lock. Delivery resumes over SSH, checks the saved Blender
file and its requested contents, transfers into a sibling temporary file, preserves the previous review and atomically
publishes the latest requested result. The Mac watcher checks its publication receipt, discards Cansin-authorized
incidental edits to that generated review and preserves the active view. Authored sources remain separate.

## Considered Options

- Keep heavy Blender work on the Mac: the real finishing workload exceeds its 3 GB safety limit.
- Share a writable mounted filesystem: neither machine has a ready mount, and Blender's working set belongs on
  GX10-local storage. Incremental transfers avoid a new host driver or server and preserve explicit source ownership.
- Change Blender versions or emulate x86: the native pinned build preserves the project's actual SDF and rendering
  capabilities without changing its version or requiring emulation.

Required GitHub checks remain required. For changes confined to portable runner, resource and watcher code, focused
tests may run in the native Linux ARM64 tool container; report that architecture explicitly. Those tests do not replace
or claim equivalence to architecture-specific hosted integration checks. Operational commands live in CONTRIBUTING.md.
