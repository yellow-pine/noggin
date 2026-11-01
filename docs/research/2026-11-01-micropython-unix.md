# The MicroPython 1.23 unix port as the Mech stand-in (2026-11-01, #222)

Question: can the unix port of the Core's MicroPython (pyproject `[tool.noggin]`, 1.23) run the Core's real program
(eyes/boot.py, wifi.py, eyes.py as .mpy) as a CI process, and what must the stand-in stub? Sources: the MicroPython
source at tag v1.23.0 (`MP/` = https://github.com/micropython/micropython/blob/v1.23.0/), built and probed on macOS
(Apple clang) 2026-11-01.

## Build

- `make -C ports/unix submodules`, then `make -C ports/unix`; the binary is `ports/unix/build-standard/micropython`
  (the default variant, `MP/ports/unix/Makefile`). With `MICROPY_PY_FFI=0 MICROPY_PY_BTREE=0 MICROPY_PY_SSL=0` it
  needs no libffi or mbedtls (`MP/ports/unix/Makefile` lines 118-187); `FROZEN_MANIFEST=` freezes nothing, so it
  needs no mpy-cross build either. Clone, submodules and build took about 10 s on 10 cores.
- Newer compilers warn where v1.23.0 compiled clean (Apple clang: `-Wgnu-folding-constant` in py/emitnative.c,
  `-Wunterminated-string-initialization` in extmod/moductypes.c) and the port builds with `-Werror`:
  `CFLAGS_EXTRA=-Wno-error` builds it.
- It reports `sys.implementation._mpy == 774` and version (1, 23, 0), the Core's (`MP/py/persistentcode.h` lines 37-38:
  MPY_VERSION 6, MPY_SUB_VERSION 3), so it loads the .mpy files mpy-cross 1.23 writes for the Core.
- At about 10 s cold, a prebuilt binary would save nothing worth a second source to trust; it is not looked for.
- micropython-lib, pinned as the `lib/micropython-lib` submodule (50ed36f), carries `python-stdlib/hmac/hmac.py`
  (metadata version 3.4.4, the package `mip install hmac` gives the Core): `hmac.new(key, msg, hashlib.sha256)` agrees
  with CPython's; it has no `compare_digest` (eyes/wifi.py falls back to its XOR loop).

## Behaviour that shapes the stubs

- Import order: a non-extensible built-in first, then the filesystem along `sys.path`, then an extensible built-in
  (`MP/py/builtinimport.c` lines 393-411). `machine`, `os`, `select` and `socket` are extensible
  (`MP_REGISTER_EXTENSIBLE_MODULE` in `MP/extmod/modmachine.c` 254, `modos.c` 234, `modselect.c` 674,
  `MP/ports/unix/modsocket.c` 721), so a `machine.py` or `socket.py` on the path wins; the shadowed built-in is still
  reachable as `usocket` (probed). The unix port has no `network`. Its own `machine` has only mem8/16/32, PinBase,
  Signal, idle, soft_reset, time_pulse_us: no PWM, Pin, Timer or reset.
- `sys.path` is `['', '.frozen', '~/.micropython/lib', '/usr/lib/micropython']`, or `MICROPYPATH`'s colon-separated
  entries in place of the last two (`MP/ports/unix/main.c` lines 555-557); the script's own folder comes first.
- The unix `socket` takes and returns raw `sockaddr` bytes, not `(host, port)` tuples: `bind`, `connect` and `sendto`
  call `mp_get_buffer_raise` on the address (`MP/ports/unix/modsocket.c` lines 198, 228, 358), so `bind(("0.0.0.0",
  p))` raises `TypeError: object with buffer protocol required` (probed); `getaddrinfo(host, port)[0][-1]` makes one.
  A non-blocking `recvfrom` with nothing waiting raises `OSError` EAGAIN, as wifi.py expects.
- `_thread` is on (`MP/ports/unix/mpconfigport.mk` line 15) and `micropython.schedule` runs a callback on the main
  thread, but through `mp_call_function_1_protected` (`MP/py/scheduler.c` line 111): an exception it raises, even
  `SystemExit`, is printed and swallowed (probed). So a stub `machine.reset` cannot be `sys.exit` when a Timer
  callback calls it; `os.system` exists, and `kill -TERM $PPID` from it ends the process from any thread.
- `sys.exit(n)` exits with status n (probed: 42) and `SystemExit` is a `BaseException`, outside `except Exception`.
- `time.ticks_ms`, `ticks_diff` and `sleep_ms` exist; `select.poll` registers `sys.stdin`.
