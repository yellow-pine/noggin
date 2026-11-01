# The Mech stand-in's socket (mech/standin.py): the unix port's takes raw sockaddrs where the ESP32's takes (ip, port);
# the Core's broadcast lands on localhost, and the Link's ports (eyes/wifi.py) on the ones the test picked.
import os

import usocket  # the unix port's own, which this file shadows
from usocket import *  # noqa: F403

PORTS = {4711: int(os.getenv("MECH_BEACON_PORT")), 4712: int(os.getenv("MECH_COMMAND_PORT"))}


def _sockaddr(addr):
    if not isinstance(addr, tuple):  # what recvfrom returned
        return addr
    host = "127.0.0.1" if addr[0] == "255.255.255.255" else addr[0]
    return usocket.getaddrinfo(host, PORTS.get(addr[1], addr[1]))[0][-1]


class socket:
    def __init__(self, *a):
        self.s = usocket.socket(*a)

    def setsockopt(self, *a):
        self.s.setsockopt(*a)

    def setblocking(self, flag):
        self.s.setblocking(flag)

    def bind(self, addr):
        self.s.bind(_sockaddr(addr))

    def sendto(self, data, addr):
        return self.s.sendto(data, _sockaddr(addr))

    def recvfrom(self, n):
        return self.s.recvfrom(n)
