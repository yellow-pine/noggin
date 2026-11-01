# The Mech stand-in's time (mech/standin.py): the unix port's, with ticks_ms counted from boot as on the ESP32, where it
# counts from power-on (the beacon's uptime in eyes/wifi.py sums the ticks from 0).
import utime  # the unix port's own, which this file shadows
from utime import *  # noqa: F403

_BOOT = utime.ticks_ms()


def ticks_ms():
    return utime.ticks_diff(utime.ticks_ms(), _BOOT)
