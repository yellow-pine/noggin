"""Wi-Fi Link against a fake UDP Core: beacons in, `<token> <seq> <line>` out, `ok <seq>` back."""
import json, os, socket, tempfile, threading, time, uuid
from noggin.service import Service
from noggin.test_service import FakeSerial, wait_for

TOKEN = "s3cret"


class FakeCore(threading.Thread):
    """Beacons to the service's listen port and acks commands; `drop` says how many datagrams to lose first."""
    def __init__(self, name="eyes", token=TOKEN, drop=0, ack=True):
        super().__init__(daemon=True)
        self.name_, self.token, self.drop, self.ack = name, token, drop, ack
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0)); self.sock.settimeout(0.05)
        self.port = self.sock.getsockname()[1]
        self.beacon_to, self.beaconing, self.lines, self.datagrams, self.running = None, True, [], [], True

    def run(self):
        last = 0.0
        while self.running:
            if self.beaconing and self.beacon_to and time.time() - last > 0.1:
                self.sock.sendto(f"noggin {self.name_} 127.0.0.1 42".encode(), self.beacon_to); last = time.time()
            try: data, addr = self.sock.recvfrom(1024)
            except socket.timeout: continue
            self.datagrams.append(data.decode())
            if self.drop: self.drop -= 1; continue
            token, seq, line = data.decode().split(" ", 2)
            if token != self.token: continue
            self.lines.append(line)
            if self.ack: self.sock.sendto(f"ok {seq}".encode(), addr)


def start(tmp_path, core, open_serial=lambda: None, stale=6.0, wifi=True):
    sock = os.path.join(tempfile.gettempdir(), f"n{uuid.uuid4().hex[:6]}.sock")
    cal = tmp_path / "calibration.json"; cal.write_text('{"lid_rest": 0.28}')
    wf = tmp_path / "wifi.json"
    if wifi: wf.write_text(json.dumps({"ssid": "x", "password": "y", "token": TOKEN}))
    s = Service(sock_path=sock, open_serial=open_serial, mute_file=tmp_path / "m", cal_file=cal, wifi_file=wf,
                beacon_port=0, command_port=core.port, stale=stale)
    threading.Thread(target=s.run, daemon=True).start()
    assert wait_for(lambda: s.ready)
    core.beacon_to = ("127.0.0.1", s.wifi.port); core.start()
    return s, sock


def ask(path, text):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect(path); s.sendall(text.encode())
    s.settimeout(1.0)
    try: return s.recv(4096).decode()
    finally: s.close()


def test_beacon_puts_the_core_on_wifi_in_status(tmp_path):
    core = FakeCore()
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: "eyes wifi" in ask(sock, "status\n"))
    assert ask(sock, "status\n") == "eyes wifi 127.0.0.1 uptime 42s\nneck offline\n"
    s.stop(); core.running = False


def test_gesture_reaches_the_eyes_core_with_the_token(tmp_path):
    core = FakeCore()
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: core.lines == ["set lid_rest 0.28", "rest"])   # calibration + mode on discovery
    ask(sock, "eureka 2\n")
    assert wait_for(lambda: core.lines[-1:] == ["eureka 2"])
    token, seq, line = core.datagrams[-1].split(" ", 2)
    assert token == TOKEN and seq.isdigit()
    s.stop(); core.running = False


def test_lost_datagram_is_resent_once_with_the_same_seq(tmp_path):
    core = FakeCore(drop=1)
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: core.lines == ["set lid_rest 0.28", "rest"])
    assert core.datagrams[0].split()[:2] == core.datagrams[1].split()[:2]   # the retry repeats the seq
    assert len(core.datagrams) == 3
    s.stop(); core.running = False


def test_unacked_command_is_dropped_and_the_next_one_still_goes(tmp_path, capsys):
    core = FakeCore(ack=False)
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: len(core.datagrams) == 2)   # calibration line sent twice, then given up
    time.sleep(0.3); assert len(core.datagrams) == 2
    core.ack = True
    ask(sock, "eureka 2\n")
    assert wait_for(lambda: core.lines[-1:] == ["eureka 2"])
    assert "no ack, dropped" in capsys.readouterr().out
    s.stop(); core.running = False


def test_stale_beacon_falls_back_to_usb_and_returns_to_wifi(tmp_path):
    core, fake = FakeCore(), FakeSerial(); fake.port = "/dev/cu.usbmodem1"
    s, sock = start(tmp_path, core, open_serial=lambda: fake, stale=0.5)
    assert wait_for(lambda: core.lines[-1:] == ["rest"])
    core.beaconing = False; time.sleep(0.6)
    assert ask(sock, "status\n") == "eyes usb /dev/cu.usbmodem1\nneck offline\n"
    ask(sock, "eureka 2\n")
    assert wait_for(lambda: fake.buf.endswith(b"eureka 2\n")) and "eureka 2" not in core.lines
    core.beaconing = True
    assert wait_for(lambda: "eyes wifi" in ask(sock, "status\n"))
    ask(sock, "wince 2\n")
    assert wait_for(lambda: core.lines[-1:] == ["wince 2"]) and b"wince" not in fake.buf
    s.stop(); core.running = False


def test_offline_core_makes_commands_silent_no_ops(tmp_path):
    core = FakeCore(); core.beaconing = False
    s, sock = start(tmp_path, core, wifi=False)   # no wifi.json either
    ask(sock, "eureka 2\n"); time.sleep(0.2)
    assert ask(sock, "status\n") == "eyes offline\nneck offline\n" and core.datagrams == []
    s.stop(); core.running = False


def test_neck_core_is_seen_but_receives_nothing(tmp_path):
    core = FakeCore(name="neck")
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: ask(sock, "status\n") == "eyes offline\nneck wifi 127.0.0.1 uptime 42s\n")
    ask(sock, "eureka 2\n"); time.sleep(0.2)
    assert core.datagrams == []
    s.stop(); core.running = False


def test_seq_is_milliseconds_since_the_epoch_and_strictly_increases(tmp_path):
    core = FakeCore()
    s, sock = start(tmp_path, core)
    before = int(time.time() * 1000)
    assert wait_for(lambda: len(core.lines) == 2)
    seqs = [int(d.split()[1]) for d in core.datagrams]
    assert before <= seqs[0] < seqs[1] <= int(time.time() * 1000) + 1
    s.stop(); core.running = False
