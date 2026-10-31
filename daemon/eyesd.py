"""noggin Daemon: owns the Link to the Core and a Unix socket for Triggers and the CLI.
Socket lines are either Trigger JSON from a Claude Code hook (forwarded to the Director) or
plain commands: `on` / `off` (Mute, persisted as a file) / `<gesture> <1-3>` / `thinking` / `rest` /
`pose ...` / `exercise <min>` (passed to the Core) / `set <key> <value>` (saved to the calibration
file and sent) / `reload` (resend the file). The whole file is pushed whenever the Link connects."""
import glob, json, os, socket, sys, time
from pathlib import Path
from reactions.director import Director

SOCK = os.path.expanduser("~/.noggin.sock")      # AF_UNIX paths max 104 bytes: keep it short
MUTE_FILE = Path(os.path.expanduser("~/.noggin.mute"))
CAL_FILE = Path(__file__).resolve().parent.parent / "eyes" / "calibration.json"
PORT_GLOB = "/dev/cu.usbmodem*"
MANUAL = {"thinking", "rest", "eureka", "attention", "bored", "wince", "pose", "exercise"}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def open_link():
    import serial
    for dev in sorted(glob.glob(PORT_GLOB)):
        try:
            ser = serial.Serial(dev, 115200, timeout=0.2, exclusive=True)
            time.sleep(0.3)
            ser.reset_input_buffer()
            log("Core on", dev)
            return ser
        except (serial.SerialException, OSError) as e:
            log("skip", dev, e)
    return None


class Daemon:
    def __init__(self, sock_path=SOCK, open_serial=open_link, mute_file=MUTE_FILE, cal_file=CAL_FILE):
        self.sock_path, self.open_serial, self.mute_file, self.cal_file = sock_path, open_serial, mute_file, cal_file
        self.director = Director()
        self.director.muted = self.mute_file.exists()
        self.link, self.last_probe, self.ready, self.running = None, 0.0, False, True

    def stop(self):
        self.running = False

    def calibration(self):
        return json.loads(self.cal_file.read_text()) if self.cal_file.exists() else {}

    def cal_lines(self):
        return [f"set {k} {v}" for k, v in self.calibration().items()]

    def send(self, lines):
        if not lines or self.link is None:
            if lines: log("no Link, dropped", lines)
            return
        try:
            self.link.write(("\n".join(lines) + "\n").encode())
            log("sent", lines)
        except Exception as e:  # pyserial raises SerialException(IOError)
            log("Link lost:", e)
            try: self.link.close()
            except Exception: pass
            self.link = None

    def command(self, text, now):
        if text == "off":
            self.mute_file.touch(); log("muted")
            return self.send(self.director.mute())
        if text == "on":
            self.director.muted = False; self.mute_file.unlink(missing_ok=True); log("unmuted")
            return
        if text == "reload":
            return self.send(self.cal_lines())
        if text.startswith("set "):
            parts = text.split()
            cal = self.calibration()
            if len(parts) != 3 or parts[1] not in cal:
                return log("unknown calibration key", repr(text))
            cal[parts[1]] = float(parts[2]) if "." in parts[2] else int(parts[2])
            self.cal_file.write_text(json.dumps(cal, indent=1) + "\n")
            return self.send([text])
        if text.startswith("{"):
            try: event = json.loads(text)
            except ValueError: return log("bad json")
            return self.send(self.director.handle(event, now))
        if text.split()[0] in MANUAL:
            return self.send([text])
        log("ignored", repr(text))

    def run(self):
        try: os.unlink(self.sock_path)
        except FileNotFoundError: pass
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(self.sock_path); srv.listen(8); srv.settimeout(0.2)
        log("listening on", self.sock_path, "muted" if self.director.muted else "")
        self.ready = True
        while self.running:
            now = time.time()
            if self.link is None and now - self.last_probe > 2.0:
                self.link, self.last_probe = self.open_serial(), now
                if self.link is not None:
                    self.send(self.cal_lines() + [self.director.mode()])   # calibrate, then catch up the mode
            self.send(self.director.tick(now))
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            with conn:
                conn.settimeout(0.5)
                try: data = conn.recv(65536).decode()
                except (socket.timeout, UnicodeDecodeError): data = ""
            for line in data.splitlines():
                if line.strip():
                    self.command(line.strip(), now)
        srv.close()


if __name__ == "__main__":
    Daemon().run()
