# The Mech stand-in's network (mech/standin.py): one station that hears the networks in air.json, {ssid: RSSI}, beside
# boot.py; the test rewrites it to move the Mech. Joins are logged on stderr, the stand-in's log.
import json
import sys

STA_IF = 0


def air():
    with open("air.json") as f:
        return json.load(f)


class WLAN:
    PM_NONE = 0

    def __init__(self, iface):
        self.ssid = None

    def active(self, on):
        pass

    def config(self, **kw):
        pass

    def scan(self):
        return [(ssid.encode(), b"", 1, rssi, 3, False) for ssid, rssi in air().items()]

    def connect(self, ssid, password):  # shortcut: any password joins, model a wrong one when a scenario needs it
        if ssid in air():
            self.ssid = ssid
            print("network: joined", ssid, file=sys.stderr)

    def disconnect(self):
        self.ssid = None

    def isconnected(self):
        return self.ssid in air()

    def ifconfig(self):
        return ("127.0.0.1", "255.0.0.0", "127.0.0.1", "127.0.0.1")
