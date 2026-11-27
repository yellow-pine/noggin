"""Run a heavy command (MuJoCo, CoACD, Blender) only while no other one runs on this machine (#246): several at once
took the Mac to ~30 GB. The lock is flock(2) on a file in /tmp (macOS and Linux, every worktree), held by
the command itself after exec and released by the kernel when it exits or is killed, so a dead holder never leaves a
stale lock. The command's whole process tree owns it: whatever takes it again under the command, a nested heavy.py or
`take` in Python, goes straight on (#1026). Usage: python3 scripts/heavy.py <command> [args...]; NOGGIN_HEAVY_LOCK
moves the lock file (tests)."""

import fcntl
import os
import sys
import time

PATH = os.environ.get("NOGGIN_HEAVY_LOCK", "/tmp/noggin-heavy.lock")  # noqa: S108 one path every worktree shares
HOLDER = "NOGGIN_HEAVY_HOLDER"  # the holding command's pid, in its environment: only its own tree inherits it


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def take(path=PATH):
    """The heavy lock at `path`, waited for: an open fd that holds it until it is closed or the process ends. Under
    the command that holds it already, the fd holds nothing and comes back at once."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o666)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        holder = os.pread(fd, 32, 0).decode().strip()
        if holder and holder == os.environ.get(HOLDER) and alive(int(holder)):
            # shortcut: takers under one command run at once (pytest -n under heavy.py), each Blender under its own
            # ceiling; a second lock among them once that is too much memory
            return fd
        mins = int(time.time() - os.fstat(fd).st_mtime) // 60  # the holder wrote its pid when it took the lock
        print(
            f"heavy.py: another heavy recipe runs on this machine ({path}); "
            f"waiting for pid {holder or '?'}, which has held it for {mins} min",
            file=sys.stderr,
            flush=True,
        )
        fcntl.flock(fd, fcntl.LOCK_EX)
    os.ftruncate(fd, 0)
    os.pwrite(fd, str(os.getpid()).encode(), 0)  # exec keeps the pid: the waiter's message names the command
    return fd


if __name__ == "__main__":
    fd = take()
    os.set_inheritable(fd, True)
    os.environ[HOLDER] = os.pread(fd, 32, 0).decode()  # this command, or the one above it that holds the lock
    os.execvp(sys.argv[1], sys.argv[1:])  # noqa: S606 the command it was given, by design
