"""Wi-Fi Link: learn each Core from its UDP beacon (`<tag> noggin <name> <ip> <uptime s>`, taken only when tagged and
sent from the ip it claims) and send it command lines as `<tag> <seq> <line>` datagrams (HMAC of `<name> <seq> <line>`
under the shared token, so the secret never travels), each acked with `<tag> ok <seq>` from that Core's address and
command port (up to four tries a line, each waiting longer; what is never acked goes back to the noggin service, for
USB). Every tag the Core sends is over `<name> <body>`, so no LAN host can pose as a Core or fake its acks.
`flash` sends the eye program the same way, as tagged `put` chunks and `commit` lines (eyes/wifi.py)."""

import base64
import hashlib
import hmac
import importlib.util
import socket
import time
from pathlib import Path

ACK_SECONDS = (0.2, 0.4, 0.8, 1.6)  # one ack window per try: a lost datagram or a busy Core costs a retry
CHUNK = 120  # bytes per `put`: 160 base64 characters keep the datagram inside the Core's 256-byte recvfrom
REBOOT_SECONDS = 40  # the new program's boot and Wi-Fi join, or its 10 s fallback to the .bak files and one more boot

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

    def poll(self, now):
        """Drain beacons; return the names that just came (back) on Wi-Fi."""
        fresh_before = {n for n in self.cores if self.fresh(n, now)}
        while True:
            try:
                data, addr = self.beacons.recvfrom(256)
            except (BlockingIOError, OSError):
                break
            t, _, body = data.decode(errors="replace").partition(" ")
            parts = body.split()
            if (
                len(parts) == 4
                and parts[0] == "noggin"
                and parts[1].isalnum()
                and parts[2] == addr[0]  # a captured beacon replayed from another host is not that Core
                and parts[3].isdigit()
                and self.signed(parts[1], body, t)
            ):
                self.cores[parts[1]] = (addr[0], parts[3], now)
        return [n for n in self.cores if self.fresh(n, now) and n not in fresh_before]

    def signed(self, name, body, t):
        return hmac.compare_digest(t.encode(), tag(self.token, f"{name} {body}").encode())

    def close(self):
        self.beacons.close()
        self.cmd.close()

    def fresh(self, name, now):
        return name in self.cores and now - self.cores[name][2] < self.stale

    def status(self, name):
        ip, uptime, _ = self.cores[name]
        return f"wifi {ip} uptime {uptime}s"

    def send(self, name, lines):
        """Deliver each line in turn, going on past an unacked one; return the lines no try got acked."""
        return [line for line in lines if self.deliver(name, line) is None]

    def deliver(self, name, line):
        """One line, up to four tries; the Core's reply (`ok <seq>`, or `err <seq> <reason>`), None if none came."""
        ip = self.cores[name][0]
        self.seq = max(
            self.seq + 1, int(time.time() * 1000)
        )  # the Core drops any seq below its highest: survive restarts
        datagram = f"{tag(self.token, f'{name} {self.seq} {line}')} {self.seq} {line}".encode()
        for window in ACK_SECONDS:  # every try repeats the seq: the Core re-acks it without running it again
            self.cmd.sendto(datagram, (ip, self.command_port))
            if (reply := self.reply(name, self.seq, ip, window)) is not None:
                return reply
        return None

    def reply(self, name, seq, ip, window):
        end = time.time() + window
        while (left := end - time.time()) > 0:
            self.cmd.settimeout(left)
            try:
                data, addr = self.cmd.recvfrom(256)
            except (TimeoutError, OSError):
                return None
            t, _, reply = data.decode(errors="replace").partition(" ")
            words = reply.split()
            if (  # only the Core we sent to can ack
                addr == (ip, self.command_port)
                and len(words) >= 2
                and words[1] == str(seq)
                and self.signed(name, reply, t)
            ):
                return reply  # `err <seq> ...` is still delivered: the Core saw it, retrying would not help
        return None

    def ok(self, name, line):
        return (self.deliver(name, line) or "").startswith("ok ")

    def flash(self, name, files):
        """Stage files ({name: bytes}) on the Core as `put` chunks, `commit` each by its sha256 (the Core swaps it in,
        keeping a .bak), reboot it and wait for its beacon, then commit again: ok only if the Core runs the new files,
        not the .bak files its boot.py puts back when the new program fails. Raises RuntimeError on a failure."""
        for fname, data in files.items():
            for off in range(0, len(data), CHUNK):
                chunk = base64.b64encode(data[off : off + CHUNK]).decode()
                if not self.ok(name, f"put {fname} {off} {chunk}"):
                    raise RuntimeError(f"{fname} not staged, nothing swapped in")
        commits = [f"commit {fname} {hashlib.sha256(data).hexdigest()}" for fname, data in files.items()]
        for line in commits:
            if not self.ok(name, line):
                raise RuntimeError(f"{line.split()[1]} not swapped in (earlier files were): USB=1 make flash")
        self.send(name, ["reboot"])  # its ack can be lost to the reset: the beacon tells
        since = time.time()
        while time.time() - since < REBOOT_SECONDS:
            self.poll(time.time())
            _, uptime, seen = self.cores[name]
            if seen > since and int(uptime) <= seen - since:  # a beacon from after the reboot
                break
            time.sleep(0.05)
        else:
            raise RuntimeError(f"no beacon in {REBOOT_SECONDS} s since the reboot: check it over USB")
        if not all(self.ok(name, line) for line in commits):
            raise RuntimeError("the new program never reached `noggin ready`: the Core is back on its .bak files")
        return f"flashed {name}: {' '.join(files)}, uptime {uptime}s"
