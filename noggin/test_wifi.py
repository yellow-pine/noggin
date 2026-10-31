"""Wi-Fi Link against a fake UDP Core: beacons in, `<tag> <seq> <line>` out, `ok <seq>` back."""

import json
import os
import socket
import tempfile
import threading
import time
import uuid

from noggin.service import Service
from noggin.test_service import FakeSerial, wait_for
from noggin.wifi import tag

TOKEN = "s3cret"


class FakeCore(threading.Thread):
    """Beacons to the service's listen port and acks commands; `drop` says how many datagrams to lose first."""

    def __init__(self, name="eyes", token=TOKEN, drop=0, ack=True, claim_ip="127.0.0.1", stranger=False):
        super().__init__(daemon=True)
        self.name_, self.token, self.drop, self.ack, self.claim_ip = name, token, drop, ack, claim_ip
        self.stranger = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) if stranger else None  # acks from another port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(0.05)
        self.port = self.sock.getsockname()[1]
        self.beacon_to, self.beaconing, self.lines, self.datagrams, self.running = None, True, [], [], True

    def run(self):
        last = 0.0
        while self.running:
            if self.beaconing and self.beacon_to and time.time() - last > 0.1:
                self.sock.sendto(f"noggin {self.name_} {self.claim_ip} 42".encode(), self.beacon_to)
                last = time.time()
            try:
                data, addr = self.sock.recvfrom(1024)
            except TimeoutError:
                continue
            self.datagrams.append(data.decode())
            if self.drop:
                self.drop -= 1
                continue
            t, seq, line = data.decode().split(" ", 2)
            if t != tag(self.token, f"{self.name_} {seq} {line}"):
                continue
            self.lines.append(line)
            if self.stranger:
                self.stranger.sendto(f"ok {seq}".encode(), addr)
            if self.ack:
                self.sock.sendto(f"ok {seq}".encode(), addr)


def start(tmp_path, core, open_serial=lambda: None, stale=6.0, wifi=True):
    sock = os.path.join(tempfile.gettempdir(), f"n{uuid.uuid4().hex[:6]}.sock")
    cal = tmp_path / "calibration.json"
    cal.write_text('{"lid_rest": 0.28}')
    wf = tmp_path / "wifi.json"
    if wifi:
        wf.write_text(json.dumps({"ssid": "x", "password": "y", "token": TOKEN}))
    s = Service(
        sock_path=sock,
        open_serial=open_serial,
        mute_file=tmp_path / "m",
        cal_file=cal,
        wifi_file=wf,
        beacon_port=0,
        command_port=core.port,
        stale=stale,
    )
    threading.Thread(target=s.run, daemon=True).start()
    assert wait_for(lambda: s.ready)
    core.beacon_to = ("127.0.0.1", s.wifi.port)
    core.start()
    return s, sock


def ask(path, text):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(path)
    s.sendall(text.encode())
    s.settimeout(1.0)
    try:
        return s.recv(4096).decode()
    finally:
        s.close()


def test_beacon_puts_the_core_on_wifi_in_status(tmp_path):
    core = FakeCore()
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: "eyes wifi" in ask(sock, "status\n"))
    assert ask(sock, "status\n") == "eyes wifi 127.0.0.1 uptime 42s\nneck offline\nmode follow\n"
    s.stop()
    core.running = False


def test_gesture_reaches_the_eyes_core_with_a_tag_not_the_token(tmp_path):
    core = FakeCore()
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: core.lines == ["set lid_rest 0.28", "rest"])  # calibration + mode on discovery
    ask(sock, "eureka 2\n")
    assert wait_for(lambda: core.lines[-1:] == ["eureka 2"])
    t, seq, line = core.datagrams[-1].split(" ", 2)
    assert t == tag(TOKEN, f"eyes {seq} {line}") and TOKEN not in core.datagrams[-1] and seq.isdigit()
    s.stop()
    core.running = False


def test_ack_from_another_address_does_not_count(tmp_path, capsys):
    core = FakeCore(ack=False, stranger=True)
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: len(core.datagrams) == 2)  # sent twice, given up: the stranger's `ok` is not the Core's
    time.sleep(0.3)
    assert len(core.datagrams) == 2
    assert "no ack, dropped" in capsys.readouterr().out
    s.stop()
    core.running = False


def test_beacon_claiming_another_ip_is_reached_at_its_real_source_address(tmp_path):
    core = FakeCore(claim_ip="10.9.9.9")
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: core.lines == ["set lid_rest 0.28", "rest"])  # delivered to 127.0.0.1, not 10.9.9.9
    assert "eyes wifi 127.0.0.1" in ask(sock, "status\n")
    s.stop()
    core.running = False


def test_malformed_beacons_are_ignored(tmp_path):
    core = FakeCore(claim_ip="not-an-ip")
    core.name_ = "eyes;rm"
    s, sock = start(tmp_path, core)
    time.sleep(0.3)
    assert "eyes offline" in ask(sock, "status\n") and core.lines == []
    s.stop()
    core.running = False


def test_lost_datagram_is_resent_once_with_the_same_seq(tmp_path):
    core = FakeCore(drop=1)
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: core.lines == ["set lid_rest 0.28", "rest"])
    assert core.datagrams[0].split()[:2] == core.datagrams[1].split()[:2]  # the retry repeats the seq
    assert len(core.datagrams) == 3
    s.stop()
    core.running = False


def test_unacked_command_is_dropped_and_the_next_one_still_goes(tmp_path, capsys):
    core = FakeCore(ack=False)
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: len(core.datagrams) == 2)  # calibration line sent twice, then given up
    time.sleep(0.3)
    assert len(core.datagrams) == 2
    core.ack = True
    ask(sock, "eureka 2\n")
    assert wait_for(lambda: core.lines[-1:] == ["eureka 2"])
    assert "no ack, dropped" in capsys.readouterr().out
    s.stop()
    core.running = False


def test_stale_beacon_falls_back_to_usb_and_returns_to_wifi(tmp_path):
    core, fake = FakeCore(), FakeSerial()
    fake.port = "/dev/cu.usbmodem1"
    s, sock = start(tmp_path, core, open_serial=lambda: fake, stale=0.5)
    assert wait_for(lambda: core.lines[-1:] == ["rest"])
    core.beaconing = False
    assert wait_for(
        lambda: ask(sock, "status\n") == "eyes usb /dev/cu.usbmodem1 uptime n/a\nneck offline\nmode follow\n"
    )
    ask(sock, "eureka 2\n")
    assert wait_for(lambda: fake.buf.endswith(b"eureka 2\n")) and "eureka 2" not in core.lines
    core.beaconing = True
    assert wait_for(lambda: "eyes wifi" in ask(sock, "status\n"))
    ask(sock, "wince 2\n")
    assert wait_for(lambda: core.lines[-1:] == ["wince 2"]) and b"wince" not in fake.buf
    s.stop()
    core.running = False


def test_offline_core_makes_commands_silent_no_ops(tmp_path):
    core = FakeCore()
    core.beaconing = False
    s, sock = start(tmp_path, core, wifi=False)  # no wifi.json either
    ask(sock, "eureka 2\n")
    time.sleep(0.2)
    assert ask(sock, "status\n") == "eyes offline\nneck offline\nmode follow\n" and core.datagrams == []
    s.stop()
    core.running = False


def test_neck_core_is_seen_but_receives_nothing(tmp_path):
    core = FakeCore(name="neck")
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: ask(sock, "status\n") == "eyes offline\nneck wifi 127.0.0.1 uptime 42s\nmode follow\n")
    ask(sock, "eureka 2\n")
    time.sleep(0.2)
    assert core.datagrams == []
    s.stop()
    core.running = False


def test_seq_is_milliseconds_since_the_epoch_and_strictly_increases(tmp_path):
    core = FakeCore()
    s, sock = start(tmp_path, core)
    before = int(time.time() * 1000)
    assert wait_for(lambda: len(core.lines) == 2)
    seqs = [int(d.split()[1]) for d in core.datagrams]
    assert before <= seqs[0] < seqs[1] <= int(time.time() * 1000) + 1
    s.stop()
    core.running = False
