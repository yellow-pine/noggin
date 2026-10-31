# pyright: reportAttributeAccessIssue=false
"""boot.py after a Wi-Fi flash: the files listed in flash.trial are on probation until `noggin ready`; a program that
raises before it, or is still not there after 10 s, gets the .bak files back and the Core reboots."""

import runpy
import sys
import types
from pathlib import Path

import pytest

BOOT = str(Path(__file__).resolve().parent / "boot.py")


class Reset(BaseException):  # machine.reset never returns into the program
    pass


class Ready(Exception):
    """Raised by the stubbed select.poll: boot.py printed `noggin ready` and entered its loop."""


@pytest.fixture
def core(tmp_path, monkeypatch):
    """A Core filesystem after a Wi-Fi flash of eyes.py, and stubs for what boot.py imports."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "eyes.py").write_text("new")
    (tmp_path / "eyes.py.bak").write_text("good")
    (tmp_path / "wifi.py").write_text("untouched")
    (tmp_path / "wifi.py.bak").write_text("older, not part of this flash")
    (tmp_path / "flash.trial").write_text("eyes.py\n")
    timers = []

    class Timer:
        ONE_SHOT = 0

        def __init__(self, n):
            self.armed = False
            timers.append(self)

        def init(self, mode, period, callback):
            self.armed, self.period, self.callback = True, period, callback

        def deinit(self):
            self.armed = False

    def reset():
        raise Reset

    machine = types.SimpleNamespace(Timer=Timer, reset=reset, Pin=object, PWM=object)
    poll = types.SimpleNamespace(register=lambda *a: None, poll=lambda ms: (_ for _ in ()).throw(Ready()))
    eyes = types.SimpleNamespace(Eyes=lambda: types.SimpleNamespace(handle_line=lambda line: None))
    for name, mod in {
        "machine": machine,
        "select": types.SimpleNamespace(poll=lambda: poll, POLLIN=1),
        "wifi": types.SimpleNamespace(start=lambda handle_line: None),
        "eyes": eyes,
    }.items():
        monkeypatch.setitem(sys.modules, name, mod)
    return types.SimpleNamespace(path=tmp_path, timers=timers, eyes=eyes)


def files(path):
    return {p.name: p.read_text() for p in path.iterdir()}


def test_a_new_program_that_raises_before_ready_gets_the_bak_files_back(core):
    def broken():
        raise ZeroDivisionError

    core.eyes.Eyes = broken
    with pytest.raises(Reset):
        runpy.run_path(BOOT)
    assert files(core.path) == {
        "eyes.py": "good",
        "wifi.py": "untouched",
        "wifi.py.bak": "older, not part of this flash",
    }


def test_a_new_program_not_ready_in_10_s_gets_the_bak_files_back(core):
    def hangs():
        assert core.timers[0].armed and core.timers[0].period == 10_000
        core.timers[0].callback(core.timers[0])  # the 10 s are up

    core.eyes.Eyes = hangs
    with pytest.raises(Reset):
        runpy.run_path(BOOT)
    assert files(core.path)["eyes.py"] == "good" and "flash.trial" not in files(core.path)


def test_a_new_program_that_reaches_ready_stays_and_keeps_its_bak(core, capsys):
    with pytest.raises(Ready):
        runpy.run_path(BOOT)
    assert "noggin ready" in capsys.readouterr().out
    assert not core.timers[0].armed
    assert files(core.path)["eyes.py"] == "new" and files(core.path)["eyes.py.bak"] == "good"
    assert "flash.trial" not in files(core.path)


def test_without_a_flash_trial_nothing_is_ever_put_back(core):
    (core.path / "flash.trial").unlink()

    def broken():
        raise ZeroDivisionError

    core.eyes.Eyes = broken
    with pytest.raises(ZeroDivisionError):  # to the REPL, as before
        runpy.run_path(BOOT)
    assert files(core.path)["eyes.py"] == "new" and core.timers == []


def test_ctrl_c_on_probation_hands_the_core_to_usb_without_putting_anything_back(core):
    def interrupted():
        raise KeyboardInterrupt  # eyes/interrupt.py, for a USB flash

    core.eyes.Eyes = interrupted
    with pytest.raises(KeyboardInterrupt):
        runpy.run_path(BOOT)
    assert files(core.path)["eyes.py"] == "new" and not core.timers[0].armed
