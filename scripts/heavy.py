"""Run a heavy command (MuJoCo, CoACD, Blender) only while no other one runs on this machine (#246): several at once
took the Mac to ~30 GB. The lock is flock(2) on a file in /tmp (macOS and Linux, every worktree), held by
the command itself after exec and released by the kernel when it exits or is killed, so a dead holder never leaves a
stale lock. Usage: python3 scripts/heavy.py <command> [args...]; NOGGIN_HEAVY_LOCK moves the lock file (tests)."""

import fcntl
import os
import sys

path = os.environ.get("NOGGIN_HEAVY_LOCK", "/tmp/noggin-heavy.lock")
fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o666)
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    holder = os.pread(fd, 32, 0).decode().strip()
    print(
        f"heavy.py: another heavy target runs on this machine; waiting for pid {holder} ({path})",
        file=sys.stderr,
        flush=True,
    )
    fcntl.flock(fd, fcntl.LOCK_EX)
os.ftruncate(fd, 0)
os.pwrite(fd, str(os.getpid()).encode(), 0)  # exec keeps the pid: the waiter's message names the command
os.set_inheritable(fd, True)
os.execvp(sys.argv[1], sys.argv[1:])
