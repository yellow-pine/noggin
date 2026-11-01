"""Stub MicroPython's `machine` so the eye program (eyes/eyes.py) imports on CPython and records every servo write; the
site as MkDocs builds it, for test_site.py and web/test_build.py."""

import importlib
import os
import pathlib
import subprocess
import sys
import types

import pytest


class _Pin:
    def __init__(self, n):
        self.n = n


class _PWM:
    log = []  # (pin, pulse ns) in order; 0 == released

    def __init__(self, pin, freq=50):
        self.pin = pin.n

    def duty_ns(self, ns):
        _PWM.log.append((self.pin, ns))

    def deinit(self):
        _PWM.log.append((self.pin, 0))


machine = types.ModuleType("machine")
machine.Pin, machine.PWM = _Pin, _PWM  # pyright: ignore[reportAttributeAccessIssue]
sys.modules["machine"] = machine
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "eyes"))


@pytest.fixture
def eyes(monkeypatch):
    import eyes as mod

    importlib.reload(mod)
    monkeypatch.setattr(mod, "sleep_ms", lambda ms: None)
    _PWM.log.clear()
    return mod.Eyes()


@pytest.fixture
def pwm_log():
    return _PWM.log


@pytest.fixture(scope="session")
def site(tmp_path_factory):
    """The site as `make site` builds it with MkDocs, strictly (no viewer GLBs, pictures or reports)."""
    out = tmp_path_factory.mktemp("site")
    r = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict", "-d", str(out)],
        cwd=pathlib.Path(__file__).resolve().parent,
        capture_output=True,
        text=True,
        env={**os.environ, "NO_MKDOCS_2_WARNING": "1"},  # hush Material's banner about MkDocs 2 (it requires mkdocs<2)
    )
    assert r.returncode == 0, r.stderr[-3000:]
    return out
