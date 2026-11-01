# pyright: reportOptionalMemberAccess=false
# noggin Core-side Wi-Fi Link (docs/adr/0005): join the known Wi-Fi heard loudest, beacon on UDP 4711 (with the
# program's version and commit),
# serve command lines on UDP 4712, flash the eye program's files. Cooperative: poll(now_ms) from the boot.py loop and,
# while a gesture plays, from its waits (eyes.between_steps).
# Importable on CPython for tests (network and socket are stubbed there).
import binascii
import hashlib
import hmac  # pyright: ignore[reportMissingImports]  # micropython-lib's on the Core (flash-usb's mip), stdlib on the Mac
import json
import os

try:
    import socket

    import network
except ImportError:  # CPython: tests set these
    network = socket = None
import time

try:  # the program's version and commit: make mpy writes stamp.py into eyes/build beside the program, never into git
    from stamp import COMMIT, VERSION  # pyright: ignore[reportMissingImports]
except ImportError:  # CPython, or a program put on without it: the noggin service ignores its beacon
    VERSION = COMMIT = "unknown"

try:
    from time import ticks_diff

    from machine import reset
except ImportError:  # CPython: tests set reset
    reset = None

    def ticks_diff(ticks1, ticks2):
        return ticks1 - ticks2


BEACON_PORT, COMMAND_PORT = 4711, 4712
BEACON_MS, JOIN_MS = 2000, 10000
SEQ_SAVE_MS = 10000  # link.seq is written at most once per 10 s of the Mac's seq (milliseconds since the epoch)


def tag(token, msg):
    """HMAC-SHA256 of msg under the shared token, truncated to 32 hex chars (RFC 2104 section 5). msg starts with the
    Core's name: `<name> <seq> <line>` for a command, `<name> <body>` for the Core's beacon and replies, so a datagram
    for one Core or one direction is worthless anywhere else. The noggin service imports this very function."""
    return hmac.new(token.encode(), msg.encode(), hashlib.sha256).hexdigest()[:32]


def same(a, b):
    """Constant-time compare of two tags (bytes): hmac.compare_digest, else XOR-accumulate (micropython-lib hmac)."""
    if hasattr(hmac, "compare_digest"):
        return hmac.compare_digest(a, b)
    diff = len(a) ^ len(b)
    for i in range(min(len(a), len(b))):  # no zip(strict=) on MicroPython
        diff |= a[i] ^ b[i]
    return diff == 0


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
    the hash is ok without a swap: the Mac's check after the reboot. Only .mpy files: boot.py and .py files change
    over USB alone (import finds a .py before its .mpy)."""
    cmd, name, arg, *chunk = line.split()
    if "/" in name or not name.endswith(".mpy"):
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


def networks(cfg):
    """The known networks in wifi.json, [{"ssid", "password"}]; the one-network shape from before #195 still loads."""
    if "networks" in cfg:
        return cfg["networks"]
    return [{"ssid": cfg["ssid"], "password": cfg["password"]}] if "ssid" in cfg else []


def loudest_known(scan, known):
    """The known network heard loudest in a WLAN.scan() ((ssid, bssid, channel, RSSI, security, hidden) tuples, ssid
    as bytes), or None when none is in range."""
    by_ssid = {n["ssid"].encode(): n for n in known}
    heard = [(rssi, ssid) for ssid, _, _, rssi, *_ in scan if ssid in by_ssid]
    return by_ssid[max(heard)[1]] if heard else None


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
    link = Wifi(handle_line, name, cfg)
    import eyes  # the program boot.py runs: its gestures' waits serve the Link (#205); boot.py only changes over USB

    eyes.between_steps = lambda: link.poll(time.ticks_ms(), True)  # pyright: ignore[reportAttributeAccessIssue]
    return link


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
        try:  # link.seq: no seq at or below it runs again, even across a reboot or a power cut
            with open("link.seq") as f:
                self.saved = int(f.read())
        except (OSError, ValueError):
            self.saved = -1
        self.last = (self.saved, None)  # (highest seq, its reply): a retried seq is acked again, an older one dropped
        self.queue = []  # (seq, line, addr) acked, not run yet

    def poll(self, now_ms, playing=False):
        """playing: called from a gesture's waits (eyes.between_steps). Then no scan (it blocks a second or two), and
        the lines received are acked but wait for the gesture to end, in order, as when the loop stopped for it."""
        self.uptime_ms += ticks_diff(now_ms, self.last_ms)
        self.last_ms = now_ms
        if not self.wlan.isconnected():
            if not playing and (self.join_at is None or ticks_diff(now_ms, self.join_at) >= JOIN_MS):
                self.join_at = now_ms
                try:  # the driver retries the last network on its own, and it cannot scan while it joins
                    self.wlan.disconnect()
                except OSError:  # nothing to leave
                    pass
                try:
                    # shortcut: the scan blocks the loop a second or two each JOIN_MS off the network,
                    # scan less often if the eyes stutter there
                    net = loudest_known(self.wlan.scan(), networks(self.cfg))
                    if net:
                        self.wlan.connect(net["ssid"], net["password"])
                except Exception:  # a radio error or a full heap must never stop boot.py's loop: next window
                    pass
            return
        self.join_at = now_ms  # a drop gets the driver's own reconnect for JOIN_MS before a scan
        if self.beacon is None:
            self.beacon = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.beacon.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # a soft reboot keeps the old socket bound on the ESP32: without this the program dies with EADDRINUSE
            self.cmd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.cmd.bind(("0.0.0.0", COMMAND_PORT))
            self.cmd.setblocking(False)
        if ticks_diff(now_ms, self.next_beacon) >= 0:
            msg = f"noggin {self.name} {self.wlan.ifconfig()[0]} {self.uptime_ms // 1000} {VERSION} {COMMIT}"
            self.beacon.sendto(self.signed(msg), ("255.255.255.255", BEACON_PORT))
            self.next_beacon = now_ms + BEACON_MS
        while True:
            try:
                data, addr = self.cmd.recvfrom(256)
            except OSError:  # EAGAIN: nothing waiting
                break
            self.serve(data, addr)
        # shortcut: a line acked just before the Wi-Fi drops waits until it is back (its err reply needs the socket),
        # run it offline if that bites
        while self.queue and not playing:  # a line's gesture polls here again (playing): what it receives queues
            self.run_line(*self.queue.pop(0))

    def serve(self, data, addr):
        """Datagram `<tag> <seq> <command line>` -> `ok <seq>` on receipt, then poll runs the line (a parser exception
        follows as `err <seq> <reason>`); `put` and `commit` (flash) are answered once they ran, `ok` or `err`, and
        `reboot` resets the Core after its ack. seq must not go backwards (replays are dropped, and link.seq keeps a
        ceiling at or above every seq seen, across a reboot or a power cut); the highest seq is re-acked with its last
        reply, never run again. Every reply is tagged too (signed)."""
        try:
            parts = data.decode().split(" ", 2)
        except (UnicodeError, ValueError):  # junk on the LAN must never stop the loop
            return
        if (
            len(parts) < 3
            or not parts[1].isdigit()
            or not same(parts[0].encode(), tag(self.cfg["token"], self.name + " " + parts[1] + " " + parts[2]).encode())
        ):
            return  # the secret never travels: each datagram carries its own tag
        seq, line = int(parts[1]), parts[2]
        if seq < self.last[0]:
            return
        if seq == self.last[0]:
            if self.last[1]:  # None: seen before a reboot, nothing to ack again
                self.cmd.sendto(self.signed(self.last[1]), addr)
            return
        reboot = line.strip() == "reboot"
        if reboot or seq > self.saved:  # saved before it acts, a commit too: no seq that ran is above link.seq
            self.saved = seq if reboot else seq + SEQ_SAVE_MS  # a ceiling, so lines inside it need no write
            with open("link.seq", "w") as f:  # the reboot's exact seq lets the Mac's next line run at once
                f.write(str(self.saved))
        if line.startswith("put ") or line.startswith(
            "commit "
        ):  # quick, and the Mac must know they took: answered once they ran
            try:
                flash(line)
                self.reply(seq, f"ok {seq}", addr)
            except Exception as e:
                self.reply(seq, f"err {seq} {type(e).__name__}", addr)
            return
        self.reply(seq, f"ok {seq}", addr)  # ack on receipt: a gesture runs longer than the ack window
        self.queue.append((seq, line, addr))  # run by poll, after the gesture playing now (if any)

    def run_line(self, seq, line, addr):
        try:
            if line.strip() == "reboot":  # after a flash
                time.sleep(0.2)  # let the ack leave first
                reset()  # pyright: ignore[reportOptionalCall]
            else:
                self.handle_line(line)
        except Exception as e:
            self.reply(seq, f"err {seq} {type(e).__name__}", addr)

    def reply(self, seq, body, addr):
        if seq >= self.last[0]:  # a queued line's err never lowers it below a newer seq already acked
            self.last = (seq, body)
        self.cmd.sendto(self.signed(body), addr)

    def signed(self, body):
        """`<tag> <body>`: the Mac takes no beacon or reply without it, so no LAN host can pose as this Core."""
        return f"{tag(self.cfg['token'], self.name + ' ' + body)} {body}".encode()
