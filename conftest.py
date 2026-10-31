"""Stub MicroPython's `machine` so the eye program (eyes/eyes.py) imports on CPython and records every servo write."""
import sys, types, importlib, pathlib

class _Pin:
    def __init__(self, n): self.n = n

class _PWM:
    log = []          # (pin, duty) in order; duty 0 == released
    def __init__(self, pin, freq=50): self.pin = pin.n
    def duty(self, d): _PWM.log.append((self.pin, d))
    def deinit(self): _PWM.log.append((self.pin, 0))

machine = types.ModuleType("machine"); machine.Pin, machine.PWM = _Pin, _PWM
sys.modules["machine"] = machine
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "eyes"))

import pytest

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
