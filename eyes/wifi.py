# noggin Core-side Wi-Fi Link (docs/adr/0005): join the home Wi-Fi, beacon on UDP 4711,
# serve command lines on UDP 4712. Cooperative: poll(now_ms) from the boot.py loop, never blocks.
# Importable on CPython for tests (network and socket are stubbed there).
import json

try:
    import network, socket
except ImportError:  # CPython: tests set these
    network = socket = None

BEACON_PORT, COMMAND_PORT = 4711, 4712
BEACON_MS, JOIN_MS = 2000, 10000


def start(handle_line):
    """The Link from wifi.json and core.json on the Core, or None without wifi.json (USB only)."""
    try:
        with open("wifi.json") as f:
            cfg = json.load(f)
    except OSError:
        return None
    if not cfg.get("token"):                 # no shared secret: refuse to serve the LAN
        return None
    try:
        with open("core.json") as f:
            name = json.load(f)["name"]          # shortcut: "ports" ignored, the eye pins are fixed until the neck Core exists
    except (OSError, KeyError, ValueError):
        name = "eyes"
    return Wifi(handle_line, name, cfg)


class Wifi:
    def __init__(self, handle_line, name, cfg):
        self.handle_line, self.name, self.cfg = handle_line, name, cfg
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.join_at = None
        self.beacon = self.cmd = None
        self.next_beacon = 0
        self.last = (-1, None)                       # (highest seq, its reply): a retried seq is acked again, an older one dropped

    def poll(self, now_ms):
        if not self.wlan.isconnected():
            if self.join_at is None or now_ms - self.join_at >= JOIN_MS:
                self.wlan.connect(self.cfg["ssid"], self.cfg["password"])
                self.join_at = now_ms
            return
        if self.beacon is None:
            self.beacon = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.beacon.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.cmd.bind(("0.0.0.0", COMMAND_PORT))
            self.cmd.setblocking(False)
        if now_ms >= self.next_beacon:
            msg = "noggin %s %s %d" % (self.name, self.wlan.ifconfig()[0], now_ms // 1000)
            self.beacon.sendto(msg.encode(), ("255.255.255.255", BEACON_PORT))
            self.next_beacon = now_ms + BEACON_MS
        while True:
            try:
                data, addr = self.cmd.recvfrom(256)
            except OSError:                          # EAGAIN: nothing waiting
                return
            self.serve(data, addr)

    def serve(self, data, addr):
        """Datagram `<token> <seq> <command line>` -> reply `ok <seq>` or `err <seq> <reason>`. seq must not go
        backwards (replays are dropped); the highest seq is re-acked without running again."""
        try:
            parts = data.decode().split(" ", 2)
        except (UnicodeError, ValueError):       # junk on the LAN must never stop the loop
            return
        if len(parts) < 3 or parts[0] != self.cfg["token"] or not parts[1].isdigit():
            return
        seq, line = int(parts[1]), parts[2]
        if seq < self.last[0]:
            return
        if seq > self.last[0]:
            try:
                self.handle_line(line)
                reply = "ok %d" % seq
            except Exception as e:
                reply = "err %d %s" % (seq, type(e).__name__)
            self.last = (seq, reply)
        self.cmd.sendto(self.last[1].encode(), addr)
