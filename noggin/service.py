"""noggin service: owns the Link to the Core and a Unix socket for Triggers and the CLI. Socket lines are either Trigger
JSON from a Claude Code hook (forwarded to the Director) or plain commands: `on` / `off` (Mute, persisted as a file)
/ `<gesture> <1-3>` / `thinking` / `rest` / `exercise <min>` (passed to the Core) / `pose ...` (passed on and held,
dropping hook Triggers, until `follow`; re-sent, after a `rest`, on every `set`, `reload`, `on` and Link reconnect while
unmuted) / `set <key> <value>` (saved to the calibration file and sent) / `reload` (resend the file) / `demo [once |
<gesture> [level]]` (play gestures on a loop, dropping hook Triggers) / `follow` (back to the hooks from demo or
pose; the mode after any restart) / `flash` (the eye program to the eyes Core over Wi-Fi, answered with the outcome;
`make flash`). The whole calibration file is pushed whenever the Link connects. Run as `python -m noggin.service`.
noggin/broker.py (Mosquitto) can ride along as `broker`, but nothing starts it: the Link is signed UDP
(docs/adr/0005, update 2026-11-01)."""

import glob
import json
import os
import signal
import socket
import sys
import time
from pathlib import Path

from noggin.wifi import BEACON_PORT, COMMAND_PORT, STALE, Wifi
from reactions.director import Director

SOCK = os.path.expanduser("~/.noggin.sock")  # AF_UNIX paths max 104 bytes: keep it short
MUTE_FILE = Path(os.path.expanduser("~/.noggin.mute"))
CAL_FILE = Path(__file__).resolve().parent.parent / "eyes" / "calibration.json"
WIFI_FILE = CAL_FILE.with_name("wifi.json")  # the wizard writes it here and copies it to the Core
PORT_GLOB = "/dev/cu.usbmodem*"
CORES = ("eyes", "neck")
USB_CORE = "eyes"  # shortcut: the one USB Link is assumed to be the eyes Core, until a second port is told apart
GESTURES = ("eureka", "attention", "bored", "wince", "wink")
DEMO_LINES = {"thinking", "rest"} | {f"{g} {n}" for g in GESTURES for n in "123"}
SEQUENCE = ["eureka 1", "eureka 2", "eureka 3", "attention 2", "bored 2", "wince 2", "wink 3", "thinking", "rest"]
HOLD = {"thinking": 8.0}  # a background mode, not a gesture: the demo holds it this long
FLASH_FILES = ("eyes.mpy", "gaze_trace.mpy", "wifi.mpy")  # eyes/build (make mpy); boot.py goes over USB alone, as .py
READ_CAP = 1 << 20  # bytes per connection; a Trigger with a long paste fits, a runaway writer is cut off
READ_SECONDS = 0.5  # the whole connection, so a stalled writer can't hold up the Director's tick
MANUAL = {"thinking", "rest", "release", "eureka", "attention", "bored", "wince", "wink", "exercise"}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def read_all(conn):
    """A connection's bytes up to EOF; raises TimeoutError past READ_SECONDS, ValueError past READ_CAP."""
    end, data = time.monotonic() + READ_SECONDS, b""
    while True:
        conn.settimeout(max(end - time.monotonic(), 0.001))
        chunk = conn.recv(65536)
        if not chunk:
            return data
        data += chunk
        if len(data) > READ_CAP:
            raise ValueError(f"over {READ_CAP} bytes")


def _replay():
    """eyes/replay.py: the eye program on the Mac."""
    if str(CAL_FILE.parent) not in sys.path:
        sys.path.append(str(CAL_FILE.parent))
    import replay

    return replay


def gesture_seconds(line, cal):
    """How long the Core plays `line`, from the eye program's own clock (eyes/replay.py)."""
    if line in HOLD:
        return HOLD[line]
    return _replay().play([line], cal)[1] / 1000


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


class Service:
    def __init__(
        self,
        sock_path=SOCK,
        open_serial=open_link,
        mute_file=MUTE_FILE,
        cal_file=CAL_FILE,
        wifi_file=WIFI_FILE,
        beacon_port=BEACON_PORT,
        command_port=COMMAND_PORT,
        stale=STALE,
        duration=gesture_seconds,
        pause=5.0,
        broker=None,
    ):
        self.sock_path, self.open_serial, self.mute_file, self.cal_file = sock_path, open_serial, mute_file, cal_file
        self.director = Director()
        self.director.muted = self.mute_file.exists()
        self.link, self.last_probe, self.ready, self.running = None, 0.0, False, True
        self.live = {}  # name -> uptime, of each Core whose beacon was fresh at the last loop
        self.mode = "follow"  # or the demo command playing, or the pose held; never persisted, so a restart follows
        self.duration, self.pause, self.demo, self.step, self.next_step = duration, pause, [], 0, 0.0
        token = json.loads(wifi_file.read_text())["token"] if wifi_file.exists() else ""
        self.wifi = Wifi(token, beacon_port, command_port, stale)
        self.broker = broker

    def status(self, now):
        return "".join(f"{name} {self.link_status(name, now)}\n" for name in CORES) + f"mode {self.mode}\n"

    def link_status(self, name, now):
        if self.wifi.fresh(name, now):
            return self.wifi.status(name)
        if name == USB_CORE and self.link is not None:
            return f"usb {getattr(self.link, 'port', '')} uptime n/a"  # the USB Link carries no beacon, so no uptime
        return "offline"

    def stop(self):
        self.running = False

    def calibration(self):
        """The calibration file in the shared lid frame (a file from before #213 is converted; `set` saves it so)."""
        return _replay().shared_frame(json.loads(self.cal_file.read_text())) if self.cal_file.exists() else {}

    def cal_lines(self):
        return [f"set {k} {v}" for k, v in self.calibration().items()]

    def read_core(self):
        """Log whatever the Core prints (ready banner, unknown commands, tracebacks after a brownout)."""
        try:
            n = self.link.in_waiting  # pyright: ignore[reportOptionalMemberAccess]
            if n:
                for line in self.link.read(n).decode(errors="replace").splitlines():  # pyright: ignore[reportOptionalMemberAccess]
                    if line.strip():
                        log("Core:", line.strip())
        except Exception as e:
            self.drop_link(e)

    def drop_link(self, e):
        log("Link lost:", e)
        try:
            self.link.close()  # pyright: ignore[reportOptionalMemberAccess]
        except Exception:
            pass
        self.link = None

    def send(self, lines, core="eyes"):
        """Wi-Fi while the Core's beacon is fresh; whatever Wi-Fi did not deliver goes over the USB Link
        (USB_CORE only), else is dropped with a log line."""
        if not lines:
            return
        if self.wifi.fresh(core, time.time()):
            try:
                undelivered = self.wifi.send(core, lines)
            except OSError as e:  # unroutable address, socket trouble
                log("wifi error", core, repr(e))
                # shortcut: lines acked before the error repeat over USB; errors hit the first sendto
                undelivered = lines
            if not undelivered:
                return log("sent", core, lines)
            log("no ack over wifi", core, undelivered)
            lines = undelivered
        if core != USB_CORE or self.link is None:
            return log("no Link, dropped", core, lines)
        try:
            self.link.write(("\n".join(lines) + "\n").encode())
            log("sent", lines)
        except Exception as e:  # pyserial raises SerialException(IOError)
            self.drop_link(e)

    def flash(self):
        """The eye program, compiled into build/ beside calibration.json, to the eyes Core over Wi-Fi; the outcome.
        Waits up to one stale window for a beacon: the service may have just started, or the Core be mid-gesture."""
        end = time.time() + self.wifi.stale
        while not self.wifi.fresh("eyes", time.time()) and time.time() < end:
            self.wifi.poll(time.time())
            time.sleep(0.05)
        if not self.wifi.fresh("eyes", time.time()):
            msg = f"flash failed: no beacon from eyes in {self.wifi.stale} s (switched off? USB=1 make flash)"
        else:
            try:
                build = self.cal_file.parent / "build"
                msg = self.wifi.flash("eyes", {f: (build / f).read_bytes() for f in FLASH_FILES})
            except (RuntimeError, OSError) as e:
                msg = f"flash failed: {e}"
            self.live.pop("eyes", None)  # rebooted inside the window, uptime maybe not lower: the loop recalibrates it
        log(msg)
        return msg + "\n"

    def start_demo(self, text):
        line = text.removeprefix("demo").strip()
        if line in ("", "once"):
            lines = SEQUENCE
        else:
            line = line if line in DEMO_LINES else f"{line} 2"  # no level: the normal one
            if line not in DEMO_LINES:
                return log("unknown demo", repr(text))
            lines = [line]
        self.mode, self.demo, self.step, self.next_step = text, lines, 0, 0.0
        log(text)

    def held(self):
        """In pose mode, unmuted: `rest` (ends a thinking drift on the Core) then the held pose; else nothing."""
        return ["rest", self.mode] if self.mode.startswith("pose") and not self.director.muted else []

    def catch_up(self):
        """Calibrate the Core, then bring it to the mode: the held pose, else the Director's."""
        self.send(self.cal_lines() + (self.held() or [self.director.mode()]))

    def follow(self):
        self.mode = "follow"
        log("following")
        self.send([self.director.mode()])

    def play_demo(self, now):
        if now < self.next_step:
            return
        if self.mode == "demo once" and self.step == len(self.demo):
            return self.follow()
        line = self.demo[self.step % len(self.demo)]
        self.step += 1
        self.send([line])
        self.next_step = now + self.duration(line, self.calibration()) + self.pause

    def command(self, text, now):
        if text.split()[0] == "demo":
            return self.start_demo(text)
        if text == "follow":
            return self.follow()
        if text.split()[0] == "pose" and len(text.split()) in (3, 5):  # the Core's own arity, so a typo never holds
            self.mode = text
            log(text)
            return self.send(["rest", text])
        if text == "off":
            self.mute_file.touch()
            log("muted")
            return self.send(self.director.mute() + ["release"])  # muted: unpower, let it slump
        if text == "on":
            self.director.muted = False
            self.mute_file.unlink(missing_ok=True)
            log("unmuted")
            return self.send(self.held())
        if text == "reload":
            return self.send(self.cal_lines() + self.held())
        if text.startswith("set "):
            parts = text.split()
            cal = self.calibration()
            if len(parts) != 3 or parts[1] not in cal:
                return log("unknown calibration key", repr(text))
            cal[parts[1]] = float(parts[2]) if "." in parts[2] else int(parts[2])
            self.cal_file.write_text(json.dumps(cal, indent=1) + "\n")
            return self.send([text] + self.held())  # a held pose re-applied: lid levels follow the limits
        if text.startswith("{"):
            try:
                event = json.loads(text)
            except ValueError:
                return log("bad json")
            if self.mode != "follow":
                return log(self.mode, "dropped", event.get("hook_event_name"))
            return self.send(self.director.handle(event, now))
        if text.split()[0] in MANUAL:
            return self.send([text])
        log("ignored", repr(text))

    def run(self):
        try:
            os.unlink(self.sock_path)
        except FileNotFoundError:
            pass
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(self.sock_path)
        srv.listen(8)
        srv.settimeout(0.2)
        log("listening on", self.sock_path, "muted" if self.director.muted else "")
        self.ready = True
        if self.broker:
            self.broker.start()
        while self.running:
            now = time.time()
            if self.broker:
                self.broker.poll()
            if self.link is None and now - self.last_probe > 2.0:
                self.link, self.last_probe = self.open_serial(), now
                if self.link is not None:
                    self.catch_up()
            self.wifi.poll(now)
            live = self.wifi.live(now)
            for name in self.live.keys() - live.keys():
                log(name, "beacon stale for", self.wifi.stale, "s")
            for name in (live.keys() - self.live.keys()) | {n for n in live if live[n] < self.live.get(n, 0)}:
                log(name, "beacon back:", self.wifi.status(name))  # new, or rebooted inside the stale window
                if name == "eyes":  # a Core (back) on Wi-Fi
                    self.catch_up()
            self.live = live
            if self.mode == "follow":
                self.send(self.director.tick(now))
            elif self.mode.startswith("demo"):
                self.play_demo(now)
            if self.link is not None:
                self.read_core()
            try:
                conn, _ = srv.accept()
            except TimeoutError:
                continue
            with conn:
                try:
                    data = read_all(conn).decode()
                except (OSError, ValueError) as e:  # timeout or a writer gone mid-line; bad UTF-8 is a ValueError
                    log("dropped connection:", e)
                    data = ""
                for line in data.splitlines():
                    try:
                        if line.strip() == "status":
                            conn.sendall(self.status(now).encode())
                        elif line.strip() == "flash":
                            conn.sendall(self.flash().encode())
                        elif line.strip():
                            self.command(line.strip(), now)
                    except OSError as e:  # the client hung up before its answer (nc -w): never take the service down
                        log("client gone:", e)
        srv.close()
        self.wifi.close()
        if self.broker:
            self.broker.stop()


if __name__ == "__main__":
    service = Service()
    signal.signal(signal.SIGTERM, lambda *_: service.stop())  # `make stop` (launchd's SIGTERM)
    service.run()
