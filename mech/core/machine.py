# The Mech stand-in's machine (mech/standin.py): what the Core program uses of the ESP32's, on the unix port.
import _thread
import os
import time

import micropython


class Pin:
    def __init__(self, n):
        self.n = n


class PWM:  # shortcut: the servos' pulses go nowhere, record them once a scenario checks the eyes' moves
    def __init__(self, pin, freq=50):
        pass

    def duty_ns(self, ns):
        pass

    def deinit(self):
        pass


class Timer:
    ONE_SHOT = 0

    def __init__(self, n):
        self.armed = False

    def init(self, mode, period, callback):
        self.armed = True
        _thread.start_new_thread(self._fire, (period, callback))

    def _fire(self, period, callback):
        time.sleep_ms(period)
        if self.armed:  # as on the ESP32, the callback runs on the main thread, between bytecodes
            micropython.schedule(callback, self)

    def deinit(self):
        self.armed = False


def reset():
    """A hard reset from any thread: SystemExit from a scheduled callback is only printed (docs/research
    2026-11-01-micropython-unix.md). SIGTERM ends the process; mech/standin.py boots it again."""
    os.system("kill -TERM $PPID")
    while True:
        time.sleep_ms(1000)
