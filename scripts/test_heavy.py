"""heavy.py: one heavy command at a time on a machine; the next waits, and a killed holder frees the lock."""

import os
import signal
import subprocess
import sys

import pytest

HEAVY = [sys.executable, os.path.join(os.path.dirname(__file__), "heavy.py")]


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
    assert f"waiting for pid {holder.pid}" in err


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
