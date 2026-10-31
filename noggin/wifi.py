"""Wi-Fi Link: learn each Core from its UDP beacon (`noggin <name> <ip> <uptime s>`) and send it
command lines as `<token> <seq> <line>` datagrams, each acked with `ok <seq>` (retried once, then dropped)."""
import socket, time

BEACON_PORT, COMMAND_PORT = 4711, 4712
ACK_SECONDS = 0.2


class Wifi:
    def __init__(self, token, beacon_port=BEACON_PORT, command_port=COMMAND_PORT, stale=6.0):
        self.token, self.command_port, self.stale = token, command_port, stale
        self.cores = {}   # name -> (ip, uptime, seen at)
        self.seq = 0
        self.beacons = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.beacons.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.beacons.bind(("", beacon_port)); self.beacons.setblocking(False)
        self.port = self.beacons.getsockname()[1]
        self.cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); self.cmd.settimeout(ACK_SECONDS)

    def poll(self, now):
        """Drain beacons; return the names that just came (back) on Wi-Fi."""
        fresh_before = {n for n in self.cores if self.fresh(n, now)}
        while True:
            try: data, _ = self.beacons.recvfrom(256)
            except (BlockingIOError, OSError): break
            parts = data.decode(errors="replace").split()
            if len(parts) == 4 and parts[0] == "noggin":
                self.cores[parts[1]] = (parts[2], parts[3], now)
        return [n for n in self.cores if self.fresh(n, now) and n not in fresh_before]

    def close(self):
        self.beacons.close(); self.cmd.close()

    def fresh(self, name, now):
        return name in self.cores and now - self.cores[name][2] < self.stale

    def status(self, name):
        ip, uptime, _ = self.cores[name]
        return f"wifi {ip} uptime {uptime}s"

    def send(self, name, lines):
        """Deliver each line in turn; True when every one was acked."""
        ip = self.cores[name][0]
        for line in lines:
            self.seq = max(self.seq + 1, int(time.time() * 1000))   # the Core drops any seq below its highest: survive restarts
            datagram = f"{self.token} {self.seq} {line}".encode()
            for attempt in range(2):
                self.cmd.sendto(datagram, (ip, self.command_port))
                if self.acked(self.seq):
                    break
            else:
                return False
        return True

    def acked(self, seq):
        end = time.time() + ACK_SECONDS
        while time.time() < end:
            try: reply = self.cmd.recv(256).decode(errors="replace").split()
            except (socket.timeout, OSError): return False
            if len(reply) >= 2 and reply[1] == str(seq):
                return True   # `err <seq> ...` is still delivered: the Core saw it, retrying would not help
        return False
