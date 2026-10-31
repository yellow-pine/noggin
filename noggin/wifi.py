"""Wi-Fi Link: learn each Core from its UDP beacon (`noggin <name> <ip> <uptime s>`, trusted only for the
sender's real address) and send it command lines as `<tag> <seq> <line>` datagrams (HMAC of `<name> <seq> <line>` under
the shared token, so the secret never travels), each acked with `ok <seq>` from that Core's address and command port
(retried once, then dropped)."""

import importlib.util
import ipaddress
import socket
import time
from pathlib import Path

ACK_SECONDS = 0.2

_spec = importlib.util.spec_from_file_location("core_wifi", Path(__file__).resolve().parent.parent / "eyes" / "wifi.py")
assert _spec and _spec.loader
_core_wifi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_core_wifi)
tag = _core_wifi.tag  # the Core's own function and ports: both sides always agree
BEACON_PORT, COMMAND_PORT = _core_wifi.BEACON_PORT, _core_wifi.COMMAND_PORT


class Wifi:
    def __init__(self, token, beacon_port=BEACON_PORT, command_port=COMMAND_PORT, stale=6.0):
        self.token, self.command_port, self.stale = token, command_port, stale
        self.cores = {}  # name -> (ip, uptime, seen at)
        self.seq = 0
        self.beacons = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.beacons.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.beacons.bind(("", beacon_port))
        self.beacons.setblocking(False)
        self.port = self.beacons.getsockname()[1]
        self.cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cmd.settimeout(ACK_SECONDS)

    def poll(self, now):
        """Drain beacons; return the names that just came (back) on Wi-Fi."""
        fresh_before = {n for n in self.cores if self.fresh(n, now)}
        while True:
            try:
                data, addr = self.beacons.recvfrom(256)
            except (BlockingIOError, OSError):
                break
            parts = data.decode(errors="replace").split()
            if len(parts) == 4 and parts[0] == "noggin" and parts[1].isalnum() and parts[3].isdigit():
                try:
                    ipaddress.IPv4Address(parts[2])
                except ValueError:
                    continue
                self.cores[parts[1]] = (
                    addr[0],
                    parts[3],
                    now,
                )  # the claimed ip is for humans; the source address is what we trust
        return [n for n in self.cores if self.fresh(n, now) and n not in fresh_before]

    def close(self):
        self.beacons.close()
        self.cmd.close()

    def fresh(self, name, now):
        return name in self.cores and now - self.cores[name][2] < self.stale

    def status(self, name):
        ip, uptime, _ = self.cores[name]
        return f"wifi {ip} uptime {uptime}s"

    def send(self, name, lines):
        """Deliver each line in turn; True when every one was acked."""
        ip = self.cores[name][0]
        for line in lines:
            self.seq = max(
                self.seq + 1, int(time.time() * 1000)
            )  # the Core drops any seq below its highest: survive restarts
            datagram = f"{tag(self.token, f'{name} {self.seq} {line}')} {self.seq} {line}".encode()
            for _attempt in range(2):
                self.cmd.sendto(datagram, (ip, self.command_port))
                if self.acked(self.seq, ip):
                    break
            else:
                return False
        return True

    def acked(self, seq, ip):
        end = time.time() + ACK_SECONDS
        while time.time() < end:
            try:
                data, addr = self.cmd.recvfrom(256)
            except (TimeoutError, OSError):
                return False
            reply = data.decode(errors="replace").split()
            if (
                addr == (ip, self.command_port) and len(reply) >= 2 and reply[1] == str(seq)
            ):  # only the Core we sent to can ack
                return True  # `err <seq> ...` is still delivered: the Core saw it, retrying would not help
        return False
