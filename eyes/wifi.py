# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
# noggin Core-side Wi-Fi Link (docs/adr/0005): join the home Wi-Fi, beacon on UDP 4711,
# serve command lines on UDP 4712, flash the eye program's files. Cooperative: poll(now_ms) from the boot.py loop.
# Importable on CPython for tests (network and socket are stubbed there).
import binascii
import hashlib
import json
import os

try:
    import socket

    import network
except ImportError:  # CPython: tests set these
    network = socket = None
import time

try:
    from time import ticks_diff

    from machine import reset
except ImportError:  # CPython: tests set reset
    reset = None

    def ticks_diff(a, b):
        return a - b


BEACON_PORT, COMMAND_PORT = 4711, 4712
BEACON_MS, JOIN_MS = 2000, 10000


def tag(token, msg):
    """HMAC-SHA256 tag of msg under the shared token, 32 hex chars. Hand-rolled: MicroPython has hashlib, not hmac.
    msg is `<core name> <seq> <line>`, so a datagram for one Core is worthless to another.
    The noggin service imports this very function, so both sides always agree."""
    key = token.encode()
    if len(key) > 64:
        key = hashlib.sha256(key).digest()
    key = key + b"\x00" * (64 - len(key))
    inner = hashlib.sha256(bytes(b ^ 0x36 for b in key) + msg.encode()).digest()
    outer = hashlib.sha256(bytes(b ^ 0x5C for b in key) + inner).digest()
    return "".join(f"{b:02x}" for b in outer)[:32]


def sha256(path):
    """Hex sha256 of a file, None if it is missing."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(512):
                h.update(chunk)
    except OSError:
        return None
    return binascii.hexlify(h.digest()).decode()


def replace(src, dst):
    try:
        os.remove(dst)  # rename over an existing file is not promised on every MicroPython filesystem
    except OSError:
        pass
    os.rename(src, dst)


def flash(line):
    """`put <file> <offset> <base64>` appends a chunk to <file>.new; `commit <file> <sha256>` checks <file>.new against
    the hash and swaps it in, keeping the old file as <file>.bak and listing it in flash.trial, which boot.py reads to
    put the .bak files back if the new program never reaches `noggin ready`. A commit for a file that already has
    the hash is ok without a swap: the Mac's check after the reboot. boot.py itself only changes over USB."""
    cmd, name, arg, *chunk = line.split()
    if name == "boot.py" or "/" in name or not name.endswith(".py"):
        raise ValueError(name)
    new = name + ".new"
    if cmd == "put":
        if arg != "0" and int(arg) != os.stat(new)[6]:  # chunks arrive in order or not at all
            raise ValueError(arg)
        with open(new, "wb" if arg == "0" else "ab") as f:
            f.write(binascii.a2b_base64(chunk[0]))
        return
    if cmd != "commit" or chunk:
        raise ValueError(cmd)
    if sha256(name) == arg:
        return
    if sha256(new) != arg:
        os.remove(new)
        raise ValueError("sha256")
    try:
        with open("flash.trial") as f:
            trial = f.read().split()
    except OSError:
        trial = []
    if name not in trial:  # a file swapped in again before it ever booted keeps the .bak that last booted
        with open("flash.trial", "a") as f:
            f.write(name + "\n")  # listed before the swap: a power cut halfway still boots on probation
        try:
            replace(name, name + ".bak")
        except OSError:  # a file the Core never had
            pass
    replace(new, name)


def start(handle_line):
    """The Link from wifi.json and core.json on the Core, or None without wifi.json (USB only)."""
    try:
        with open("wifi.json") as f:
            cfg = json.load(f)
    except OSError:
        return None
    if not cfg.get("token"):  # no shared secret: refuse to serve the LAN
        return None
    try:
        with open("core.json") as f:
            name = json.load(f)["name"]  # "ports" is read by eyes.py
    except (OSError, KeyError, ValueError):
        name = "eyes"
    return Wifi(handle_line, name, cfg)


class Wifi:
    def __init__(self, handle_line, name, cfg):
        self.handle_line, self.name, self.cfg = handle_line, name, cfg
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.config(pm=self.wlan.PM_NONE)  # power save: the AP holds our datagrams past the ack window
        self.join_at = None
        self.beacon = self.cmd = None
        self.next_beacon = 0
        self.uptime_ms, self.last_ms = 0, 0  # accumulated with ticks_diff: ticks_ms wraps every ~12 days
        self.last = (-1, None)  # (highest seq, its reply): a retried seq is acked again, an older one dropped

    def poll(self, now_ms):
        self.uptime_ms += ticks_diff(now_ms, self.last_ms)
        self.last_ms = now_ms
        if not self.wlan.isconnected():
            if self.join_at is None or ticks_diff(now_ms, self.join_at) >= JOIN_MS:
                self.wlan.connect(self.cfg["ssid"], self.cfg["password"])
                self.join_at = now_ms
            return
        if self.beacon is None:
            self.beacon = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.beacon.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.cmd.bind(("0.0.0.0", COMMAND_PORT))
            self.cmd.setblocking(False)
        if ticks_diff(now_ms, self.next_beacon) >= 0:
            msg = f"noggin {self.name} {self.wlan.ifconfig()[0]} {self.uptime_ms // 1000}"
            self.beacon.sendto(msg.encode(), ("255.255.255.255", BEACON_PORT))
            self.next_beacon = now_ms + BEACON_MS
        while True:
            try:
                data, addr = self.cmd.recvfrom(256)
            except OSError:  # EAGAIN: nothing waiting
                return
            self.serve(data, addr)

    def serve(self, data, addr):
        """Datagram `<tag> <seq> <command line>` -> `ok <seq>` on receipt, then the line runs (and a parser exception
        follows as `err <seq> <reason>`); `put` and `commit` (flash) are answered once they ran, `ok` or `err`, and
        `reboot` resets the Core after its ack. seq must not go backwards (replays are dropped); the highest seq is
        re-acked with its last reply, never run again."""
        try:
            parts = data.decode().split(" ", 2)
        except (UnicodeError, ValueError):  # junk on the LAN must never stop the loop
            return
        if (
            len(parts) < 3
            or not parts[1].isdigit()
            or parts[0] != tag(self.cfg["token"], self.name + " " + parts[1] + " " + parts[2])
        ):
            return  # the secret never travels: each datagram carries its own tag
        seq, line = int(parts[1]), parts[2]
        if seq < self.last[0]:
            return
        if seq == self.last[0]:
            self.cmd.sendto(self.last[1].encode(), addr)
            return
        if line.startswith(("put ", "commit ")):  # quick, and the Mac must know they took: answered once they ran
            try:
                flash(line)
                self.last = (seq, f"ok {seq}")
            except Exception as e:
                self.last = (seq, f"err {seq} {type(e).__name__}")
            self.cmd.sendto(self.last[1].encode(), addr)
            return
        self.last = (seq, f"ok {seq}")
        self.cmd.sendto(self.last[1].encode(), addr)  # ack on receipt: a gesture runs longer than the ack window
        try:
            if line.strip() == "reboot":  # after a flash
                time.sleep(0.2)  # let the ack leave first
                reset()  # pyright: ignore[reportOptionalCall]
            else:
                self.handle_line(line)
        except Exception as e:
            self.last = (seq, f"err {seq} {type(e).__name__}")
            self.cmd.sendto(self.last[1].encode(), addr)
