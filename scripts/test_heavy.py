"""heavy.py: one heavy command at a time on a machine; the next waits, and a killed holder frees the lock."""

import fcntl
import os
import signal
import subprocess
import sys

import pytest

from scripts import heavy

HEAVY = [sys.executable, heavy.__file__]


def hold(env):
    """A holder that has the lock once it prints 'held', and keeps it until killed."""
    holder = subprocess.Popen(
        [*HEAVY, "sh", "-c", "echo held; exec sleep 30"], env=env, stdout=subprocess.PIPE, text=True
    )
    assert holder.stdout and holder.stdout.readline() == "held\n"
    return holder


def test_a_second_heavy_command_waits_for_the_first(tmp_path):
    env = {**os.environ, "NOGGIN_HEAVY_LOCK": str(tmp_path / "heavy.lock")}
    holder = hold(env)
    second = subprocess.Popen(
        [*HEAVY, "echo", "ran"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    with pytest.raises(subprocess.TimeoutExpired):  # still waiting while the first holds the lock
        second.wait(timeout=1)
    holder.terminate()
    holder.wait()
    out, err = second.communicate(timeout=5)
    assert (second.returncode, out) == (0, "ran\n")
    assert f"waiting for pid {holder.pid}, which has held it for 0 min" in err


def test_a_killed_holder_frees_the_lock(tmp_path):
    env = {**os.environ, "NOGGIN_HEAVY_LOCK": str(tmp_path / "heavy.lock")}
    holder = hold(env)
    os.kill(holder.pid, signal.SIGKILL)  # no cleanup runs, as when a terminal is closed
    holder.wait()
    second = subprocess.run([*HEAVY, "echo", "ran"], env=env, capture_output=True, text=True, timeout=5)
    assert (second.returncode, second.stdout) == (0, "ran\n")


def test_the_command_exit_status_comes_through(tmp_path):
    env = {**os.environ, "NOGGIN_HEAVY_LOCK": str(tmp_path / "heavy.lock")}
    assert subprocess.run([*HEAVY, "sh", "-c", "exit 3"], env=env, timeout=5).returncode == 3


def test_a_command_under_the_holder_takes_the_lock_again_at_once(tmp_path):
    """#1026: heavy.py in a child of heavy.py's command, as `heavy.py uv run just test` nests them, waited forever."""
    env = {**os.environ, "NOGGIN_HEAVY_LOCK": str(tmp_path / "heavy.lock")}
    under = [*HEAVY, "sh", "-c", '"$@" && echo after', "sh", *HEAVY, "echo", "ran"]  # && keeps sh above its child
    nested = subprocess.run(under, env=env, capture_output=True, text=True, timeout=5)
    assert (nested.returncode, nested.stdout, nested.stderr) == (0, "ran\nafter\n", "")


def test_a_holder_that_died_stands_for_no_one(tmp_path):
    """The lock file and the environment still name a command that is gone: whoever holds the lock now is waited for."""
    env = {**os.environ, "NOGGIN_HEAVY_LOCK": str(tmp_path / "heavy.lock")}
    dead = hold(env)
    dead.kill()
    dead.wait()
    with open(tmp_path / "heavy.lock") as now:  # the next holder, before it wrote its own pid
        fcntl.flock(now, fcntl.LOCK_EX)
        orphan = subprocess.Popen(
            [*HEAVY, "echo", "ran"], env={**env, heavy.HOLDER: str(dead.pid)}, stdout=subprocess.PIPE, text=True
        )
        with pytest.raises(subprocess.TimeoutExpired):
            orphan.wait(timeout=1)
    assert orphan.communicate(timeout=5)[0] == "ran\n"
