"""Wi-Fi Link against a fake UDP Core: tagged beacons in, `<tag> <seq> <line>` out, `<tag> ok <seq>` back."""

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

import pytest
import wifi as core_wifi  # eyes/wifi.py: the fake Core flashes with the Core's own code

from noggin.core import CORES
from noggin.service import CAL_FILE, DEMO_LINES, HOLD, Service, gesture_seconds
from noggin.test_service import FakeSerial, wait_for
from noggin.wifi import STALE, add_network, tag

TOKEN = "s3cret"  # noqa: S105 synthetic
FAST = (0.05, 0.1, 0.2, 0.4)  # the real windows, quartered: an unacked line costs 0.75 s, not 3 s


def signed(token, name, body):
    """What a Core sends: `<tag> <body>`, the tag over `<name> <body>`; untagged without a token."""
    return (body if token is None else f"{tag(token, f'{name} {body}')} {body}").encode()


@pytest.fixture
def fast(monkeypatch):
    monkeypatch.setattr("noggin.wifi.ACK_SECONDS", FAST)


class FakeCore(threading.Thread):
    """Beacons to the service's listen port and acks commands; `drop` says how many datagrams to lose first, `busy`
    how long its loop is blocked before it reads the first one. Like the Core, it re-acks its last seq unrun, and
    flashes files in the working directory with the Core's own code; `rollback` makes its reboot put the .bak back.
    `beacon_token` and `ack_token` sign what it sends (None: untagged), as a LAN host posing as the Core would."""

    def __init__(
        self,
        name="eyes",
        token=TOKEN,
        drop=0,
        ack=True,
        claim_ip="127.0.0.1",
        program="0.1.0 abc1234",
        stranger=False,
        busy=0.0,
        rollback=False,
        beacon_token=TOKEN,
        ack_token=TOKEN,
        uptime=42,
    ):
        super().__init__(daemon=True)
        self.name_, self.token, self.drop, self.ack, self.claim_ip = name, token, drop, ack, claim_ip
        self.beacon_token, self.ack_token, self.program = beacon_token, ack_token, program
        self.busy, self.last_seq, self.rollback, self.uptime, self.reply = busy, None, rollback, uptime, ""
        self.stranger = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) if stranger else None  # acks from another port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(0.05)
        self.port = self.sock.getsockname()[1]
        self.beacon_to, self.beaconing, self.lines, self.datagrams, self.running = None, True, [], [], True
        self.times = []  # when each datagram arrived

    def run(self):
        last = 0.0
        while self.running:
            if self.beaconing and self.beacon_to and time.time() - last > 0.1:
                beacon = f"noggin {self.name_} {self.claim_ip} {self.uptime} {self.program}".strip()
                self.sock.sendto(signed(self.beacon_token, self.name_, beacon), self.beacon_to)
                last = time.time()
            try:
                data, addr = self.sock.recvfrom(1024)
            except TimeoutError:
                continue
            time.sleep(self.busy)
            self.busy = 0.0
            self.datagrams.append(data.decode())
            self.times.append(time.time())
            if self.drop:
                self.drop -= 1
                continue
            t, seq, line = data.decode().split(" ", 2)
            if t != tag(self.token, f"{self.name_} {seq} {line}"):
                other = [n for n in CORES if t == tag(self.token, f"{n} {seq} {line}")]
                if other and self.ack:  # the other Core's line: one command port serves both here, so ack it for it
                    self.sock.sendto(signed(self.ack_token, other[0], f"ok {seq}"), addr)
                continue
            if seq != self.last_seq:
                self.lines.append(line)
                self.reply = f"ok {seq}"
                if line.startswith(("put ", "commit ")):
                    try:
                        core_wifi.flash(line)
                    except Exception as e:
                        self.reply = f"err {seq} {type(e).__name__}"
                elif line == "reboot":
                    self.reboot()
            self.last_seq = seq
            if self.stranger:
                self.stranger.sendto(signed(TOKEN, self.name_, f"ok {seq}"), addr)
            if self.ack:
                self.sock.sendto(signed(self.ack_token, self.name_, self.reply), addr)

    def reboot(self):
        """What boot.py does next: a program that fails puts the .bak files back; either way it reaches ready."""
        self.uptime, self.last_seq = 0, None
        if self.rollback:
            for n in open("flash.trial").read().split():
                os.replace(n + ".bak", n)
        os.remove("flash.trial")


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


def ask(path, text, timeout=1.0):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(path)
    s.sendall(text.encode())
    s.shutdown(socket.SHUT_WR)  # EOF, as nc gives: the service reads to it, then answers
    s.settimeout(timeout)
    try:
        return s.recv(4096).decode()
    finally:
        s.close()


@pytest.fixture
def service_at(monkeypatch):
    """The noggin service's own version and commit (noggin/core.py reads them from git)."""
    monkeypatch.setattr("noggin.service.VERSION", "0.10.0")
    monkeypatch.setattr("noggin.service.COMMIT", "def5678")


def test_beacon_puts_the_core_and_its_program_in_status_beside_the_services(tmp_path, service_at):
    core = FakeCore(program="0.10.0 abc1234-dirty")
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: "eyes wifi" in ask(sock, "status\n"))
    assert ask(sock, "status\n") == (
        "eyes wifi 127.0.0.1 uptime 42s program 0.10.0 abc1234-dirty\nneck offline\nnoggin service 0.10.0 def5678\n"
        "mode follow\n"
    )
    s.stop()
    core.running = False


def test_status_warns_when_the_core_runs_an_older_program_than_the_service(tmp_path, service_at):
    core = FakeCore(program="0.9.0 abc1234")  # older by number, not by string: "0.9.0" > "0.10.0"
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: "eyes wifi" in ask(sock, "status\n"))
    assert ask(sock, "status\n").endswith(
        "noggin service 0.10.0 def5678\n"
        "warning: eyes runs program 0.9.0, older than the noggin service's 0.10.0: just flash\nmode follow\n"
    )
    s.stop()
    core.running = False


@pytest.mark.parametrize(
    ("program", "warns"),
    [
        ("0.10.0-3-gabc1234 abc1234", False),  # flashed between releases: three commits past v0.10.0 (docs/adr/0017)
        ("0.9.0-3-gabc1234 abc1234", True),  # past an older release: compared by its base X.Y.Z
        ("0.0.0-untagged abc1234", True),  # flashed from a checkout without tags
    ],
)
def test_a_program_between_releases_is_compared_by_its_release(tmp_path, service_at, program, warns):
    core = FakeCore(program=program)
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: "eyes wifi" in ask(sock, "status\n"))
    status = ask(sock, "status\n")
    assert f"program {program}\n" in status and ("warning: eyes runs program" in status) == warns, status
    s.stop()
    core.running = False


@pytest.mark.parametrize("program", ["", "unknown unknown", "0.1 abc1234", "0.1.0"])
def test_a_beacon_without_the_programs_version_and_commit_is_ignored(tmp_path, program):
    core = FakeCore(program=program)  # "": a Core program from before #357; "unknown": one put on without stamp.mpy
    s, sock = start(tmp_path, core)
    time.sleep(0.3)
    assert "eyes offline" in ask(sock, "status\n") and core.datagrams == []
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


def test_the_neck_core_gets_its_calibration_and_live_pose_after_connecting_or_restarting(tmp_path):
    core = FakeCore(name="neck")
    core.beaconing = False
    s, sock = start(tmp_path, core)
    cal = {"tilt_lo": 80, "tilt_rest": 90, "tilt_hi": 100, "mouth_lo": 100, "mouth_hi": 60}
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps(cal))
    core.beaconing = True
    try:
        assert wait_for(lambda: core.lines == [*(f"set {k} {v}" for k, v in cal.items()), "rest"])
        ask(sock, "pose tilt 95 jaw 0.5\n")
        assert wait_for(lambda: core.lines[-2:] == ["rest", "pose tilt 95 jaw 0.5"])
        ask(sock, "set mouth_hi 70\n")
        assert wait_for(lambda: core.lines[-3:] == ["set mouth_hi 70", "rest", "pose tilt 95 jaw 0.5"])
        assert json.loads(path.read_text())["mouth_hi"] == 70
        cal["mouth_hi"] = 70
        core.uptime = 1
        restored = [*(f"set {k} {v}" for k, v in cal.items()), "rest", "pose tilt 95 jaw 0.5"]
        assert wait_for(lambda: core.lines[-len(restored) :] == restored)
    finally:
        s.stop()
        core.running = False


def test_ack_from_another_address_does_not_count(tmp_path, capsys, fast):
    core = FakeCore(ack=False, stranger=True)
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: len(core.datagrams) == 8)  # 2 lines x 4 tries: the stranger's `ok` is not the Core's
    time.sleep(0.5)
    assert len(core.datagrams) == 8
    assert "no ack over wifi" in capsys.readouterr().out
    s.stop()
    core.running = False


def test_beacon_from_another_address_than_it_claims_is_ignored(tmp_path):
    core = FakeCore(claim_ip="10.9.9.9")  # a genuine beacon, captured and replayed by another host
    s, sock = start(tmp_path, core)
    time.sleep(0.3)
    assert "eyes offline" in ask(sock, "status\n") and core.datagrams == []
    s.stop()
    core.running = False


@pytest.mark.parametrize("beacon_token", [None, "forged"])
def test_untagged_or_forged_beacon_is_ignored(tmp_path, beacon_token):
    core = FakeCore(beacon_token=beacon_token)
    s, sock = start(tmp_path, core)
    time.sleep(0.3)
    assert "eyes offline" in ask(sock, "status\n") and core.datagrams == []
    s.stop()
    core.running = False


@pytest.mark.parametrize("ack_token", [None, "forged"])
def test_untagged_or_forged_ack_does_not_count(tmp_path, capsys, fast, ack_token):
    core = FakeCore(ack_token=ack_token)  # from the Core's own address and port, as a spoofer would send it
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: len(core.datagrams) == 8)  # 2 lines x 4 tries: no ack counted
    time.sleep(0.5)
    assert len(core.datagrams) == 8 and "no ack over wifi" in capsys.readouterr().out
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


def test_lost_datagrams_are_resent_up_to_four_tries_with_the_same_seq(tmp_path):
    core = FakeCore(drop=3)
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: core.lines == ["set lid_rest 0.28", "rest"], timeout=3.0)
    assert len({d.split()[1] for d in core.datagrams[:4]}) == 1  # every retry repeats the seq
    assert len(core.datagrams) == 5
    s.stop()
    core.running = False


def test_a_busy_core_that_acks_late_still_counts(tmp_path, capsys):
    core = FakeCore(busy=0.7)  # thinking mode: a blink and a saccade block the Core's loop, past two 0.2 s windows
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: core.lines == ["set lid_rest 0.28", "rest"])
    assert "no ack over wifi" not in capsys.readouterr().out
    s.stop()
    core.running = False


def test_tries_wait_a_growing_ack_window(tmp_path, fast):
    core = FakeCore(ack=False)
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: len(core.times) >= 4)
    gaps = [b - a for a, b in zip(core.times[:3], core.times[1:4], strict=True)]
    assert all(gap >= window * 0.9 for gap, window in zip(gaps, FAST, strict=False)), gaps
    s.stop()
    core.running = False


def test_a_line_lost_on_every_try_does_not_stop_its_batch(tmp_path, capsys, fast):
    core = FakeCore(drop=4)  # all four tries of the calibration line
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: core.lines == ["rest"])
    assert "no ack over wifi eyes ['set lid_rest 0.28']" in capsys.readouterr().out
    s.stop()
    core.running = False


def test_unacked_command_is_dropped_and_the_next_one_still_goes(tmp_path, capsys, fast):
    core = FakeCore(ack=False)
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: len(core.datagrams) == 8)  # calibration and mode line, 4 tries each, then given up
    time.sleep(0.5)
    assert len(core.datagrams) == 8
    core.ack = True
    ask(sock, "eureka 2\n")
    assert wait_for(lambda: core.lines[-1:] == ["eureka 2"])
    assert "no ack over wifi" in capsys.readouterr().out
    s.stop()
    core.running = False


def test_stale_beacon_falls_back_to_usb_and_returns_to_wifi(tmp_path, capsys):
    core, fake = FakeCore(), FakeSerial()
    fake.port = "/dev/cu.usbmodem1"
    s, sock = start(tmp_path, core, open_serial=lambda: fake, stale=0.5)
    assert wait_for(lambda: core.lines[-1:] == ["rest"])
    core.beaconing = False
    assert wait_for(lambda: ask(sock, "status\n").startswith("eyes usb /dev/cu.usbmodem1 uptime n/a\nneck offline\n"))
    time.sleep(0.3)
    out = capsys.readouterr().out
    assert out.count("eyes beacon back: wifi 127.0.0.1 uptime 42s") == 1  # #196: each way logged once
    assert out.count("eyes beacon stale for 0.5 s") == 1
    ask(sock, "eureka 2\n")
    assert wait_for(lambda: fake.buf.endswith(b"eureka 2\n")) and "eureka 2" not in core.lines
    core.beaconing = True
    assert wait_for(lambda: "eyes wifi" in ask(sock, "status\n"))
    ask(sock, "wince 2\n")
    assert wait_for(lambda: core.lines[-1:] == ["wince 2"]) and b"wince" not in fake.buf
    assert capsys.readouterr().out.count("eyes beacon back") == 1
    s.stop()
    core.running = False


def test_the_beacon_stays_fresh_through_the_longest_gesture():
    """The Core's loop, and so its beacon, stops while it plays a gesture (#196: the eyes went offline in every bored).
    The real Core is slower than the replay: bored replays in 11.6 s, its beacon was gone ~16 s (log, 12:24:41)."""
    cal = json.loads(CAL_FILE.read_text())
    longest = max(gesture_seconds(line, cal) for line in DEMO_LINES - HOLD.keys())
    assert longest > 11  # bored: the window must cover it, not the old 6 s
    assert 1.5 * longest + 2 * core_wifi.BEACON_MS / 1000 <= STALE  # plus a late beacon and a lost one


def test_a_core_that_rebooted_inside_the_window_is_calibrated_again(tmp_path, capsys):
    core = FakeCore()
    s, sock = start(tmp_path, core)
    assert wait_for(lambda: core.lines == ["set lid_rest 0.28", "rest"])
    core.uptime = 1  # a brownout or a quick off and on: the beacon never went stale, its uptime went back
    assert wait_for(lambda: core.lines == ["set lid_rest 0.28", "rest"] * 2)
    assert "eyes beacon back: wifi 127.0.0.1 uptime 1s" in capsys.readouterr().out
    s.stop()
    core.running = False


def beaconing(s, core):
    """A second Core (start() starts one), beaconing to the service."""
    core.beacon_to = ("127.0.0.1", s.wifi.port)
    core.start()
    return core


PACK_CUT = re.compile(r"warning: pack cut at \d{4}-\d\d-\d\d \d\d:\d\d:\d\d \(both Cores restarted\): charge the pack")


def test_both_cores_restarting_together_is_a_pack_cut_in_status(tmp_path, capsys):
    eyes = FakeCore()
    s, sock = start(tmp_path, eyes)
    neck = beaconing(s, FakeCore(name="neck", uptime=600))
    assert wait_for(lambda: "neck wifi" in ask(sock, "status\n") and "eyes wifi" in ask(sock, "status\n"))
    assert not PACK_CUT.search(ask(sock, "status\n"))
    eyes.uptime, neck.uptime = 1, 2  # the pack's protection opened: the whole Mech went dark and came back
    assert wait_for(lambda: PACK_CUT.search(ask(sock, "status\n")))
    assert ask(sock, "status\n").endswith("charge the pack\nmode follow\n")
    assert capsys.readouterr().out.count("pack cut: both Cores restarted, charge the pack") == 1
    s.stop()
    eyes.running = neck.running = False


def test_one_core_restarting_alone_is_no_pack_cut(tmp_path, capsys):
    eyes = FakeCore()
    s, sock = start(tmp_path, eyes)
    neck = beaconing(s, FakeCore(name="neck"))
    assert wait_for(lambda: "neck wifi" in ask(sock, "status\n") and "eyes wifi" in ask(sock, "status\n"))
    eyes.uptime = 1  # its USB cable pulled and put back, say
    assert wait_for(lambda: "eyes beacon back: wifi 127.0.0.1 uptime 1s" in capsys.readouterr().out)
    time.sleep(0.3)  # a few more beacons from both
    assert not PACK_CUT.search(ask(sock, "status\n"))
    s.stop()
    eyes.running = neck.running = False


def test_unacked_wifi_lines_go_over_usb(tmp_path, capsys, fast):
    core, fake = FakeCore(ack=False), FakeSerial()
    s, sock = start(tmp_path, core, open_serial=lambda: fake)
    assert wait_for(lambda: len(core.datagrams) == 8)  # discovery: both lines tried four times on Wi-Fi
    assert wait_for(lambda: fake.buf.count(b"set lid_rest 0.28\nrest\n") == 2)  # at USB connect, then the fallback
    ask(sock, "eureka 2\n")
    assert wait_for(lambda: fake.buf.endswith(b"eureka 2\n"))
    out = capsys.readouterr().out
    assert "no ack over wifi" in out and "no Link, dropped" not in out
    s.stop()
    core.running = False


def test_wifi_socket_error_sends_the_whole_batch_over_usb(tmp_path, capsys):
    core, fake = FakeCore(), FakeSerial()
    s, sock = start(tmp_path, core, open_serial=lambda: fake)
    assert wait_for(lambda: core.lines == ["set lid_rest 0.28", "rest"])

    def unroutable(name, lines):
        raise OSError(65, "No route to host")

    s.wifi.send = unroutable
    ask(sock, "reload\n")
    assert wait_for(lambda: fake.buf.count(b"set lid_rest 0.28\n") == 2)  # at USB connect, then the whole batch
    assert "wifi error" in capsys.readouterr().out
    s.stop()
    core.running = False


def test_offline_core_makes_commands_silent_no_ops(tmp_path):
    core = FakeCore()
    core.beaconing = False
    s, sock = start(tmp_path, core, wifi=False)  # no wifi.json either
    ask(sock, "eureka 2\n")
    time.sleep(0.2)
    assert ask(sock, "status\n").startswith("eyes offline\nneck offline\n") and core.datagrams == []
    s.stop()
    core.running = False


def test_the_neck_core_gets_the_lines_too(tmp_path):
    """#620: the neck Core plays each gesture a frame after the eyes Core (its own program skips the eye servos)."""
    core = FakeCore(name="neck")
    s, sock = start(tmp_path, core)
    assert wait_for(
        lambda: ask(sock, "status\n").startswith("eyes offline\nneck wifi 127.0.0.1 uptime 42s program 0.1.0 abc1234\n")
    )
    ask(sock, "eureka 2\n")
    assert wait_for(lambda: core.lines[-1:] == ["eureka 2"])
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


PROGRAM = {  # what just mpy builds: the program, and its stamp.mpy (version and commit)
    "eyes.mpy": b"M\x06 eye program " * 40,
    "gaze_trace.mpy": bytes(range(256)) * 3,
    "wifi.mpy": b"M\x06 link",
    "stamp.mpy": b"M\x06 stamp",
}


def flashing(tmp_path, monkeypatch, core):
    """The compiled program in build/ beside calibration.json on the Mac (just flash), an older one on the fake Core."""
    (tmp_path / "core").mkdir()
    (tmp_path / "build").mkdir()
    monkeypatch.chdir(tmp_path / "core")
    for name, data in PROGRAM.items():
        (tmp_path / "build" / name).write_bytes(data)
        (tmp_path / "core" / name).write_bytes(b"old " + name.encode())
    (tmp_path / "core" / "boot.py").write_bytes(b"usb only")
    s, sock = start(tmp_path, core)
    assert not core.beaconing or wait_for(lambda: core.lines == ["set lid_rest 0.28", "rest"])
    return s, sock


def test_flash_over_wifi_swaps_the_program_in_reboots_and_recalibrates(tmp_path, monkeypatch):
    core = FakeCore()
    s, sock = flashing(tmp_path, monkeypatch, core)
    reply = ask(sock, "flash\n", timeout=30)
    assert reply.startswith("flashed eyes") and "uptime 0s" in reply, reply
    on_core = {p.name: p.read_bytes() for p in (tmp_path / "core").iterdir()}
    assert on_core == {
        **PROGRAM,
        **{f"{n}.bak": b"old " + n.encode() for n in PROGRAM},
        "boot.py": b"usb only",
    }  # boot.py never travels over Wi-Fi
    assert max(len(d) for d in core.datagrams) <= 256  # the Core reads each datagram into 256 bytes
    assert wait_for(lambda: core.lines[-2:] == ["set lid_rest 0.28", "rest"])  # the rebooted Core, calibrated again
    s.stop()
    core.running = False


def test_flash_says_when_the_core_fell_back_to_the_bak_files(tmp_path, monkeypatch):
    core = FakeCore(rollback=True)
    s, sock = flashing(tmp_path, monkeypatch, core)
    reply = ask(sock, "flash\n", timeout=30)
    assert reply.startswith("flash failed") and ".bak" in reply, reply
    assert (tmp_path / "core" / "eyes.mpy").read_bytes() == b"old eyes.mpy"
    s.stop()
    core.running = False


def test_flash_waits_for_a_beacon_not_seen_yet(tmp_path, monkeypatch):
    core = FakeCore()
    core.beaconing = False  # #196: a noggin service just restarted, or a Core busy with a gesture
    s, sock = flashing(tmp_path, monkeypatch, core)
    threading.Timer(0.5, lambda: setattr(core, "beaconing", True)).start()  # while the service is inside `flash`
    reply = ask(sock, "flash\n", timeout=30)
    assert reply.startswith("flashed eyes"), reply
    s.stop()
    core.running = False


def test_a_reboot_the_service_sent_is_no_pack_cut(tmp_path, monkeypatch):
    eyes = FakeCore()
    s, sock = flashing(tmp_path, monkeypatch, eyes)
    neck = beaconing(s, FakeCore(name="neck"))
    assert wait_for(lambda: "neck wifi" in ask(sock, "status\n"))
    neck.uptime = 1  # the neck restarts by itself while flash reboots the eyes
    assert ask(sock, "flash\n", timeout=30).startswith("flashed eyes")
    time.sleep(0.3)
    assert "neck wifi 127.0.0.1 uptime 1s" in ask(sock, "status\n")
    assert not PACK_CUT.search(ask(sock, "status\n"))
    s.stop()
    eyes.running = neck.running = False


def test_flash_needs_the_core_on_wifi(tmp_path, monkeypatch):
    core = FakeCore()
    core.beaconing = False
    s, sock = start(tmp_path, core, stale=0.5)
    assert ask(sock, "flash\n").startswith("flash failed: no beacon from eyes in 0.5 s")
    assert core.datagrams == []
    s.stop()
    core.running = False


@pytest.mark.parametrize(
    "status, port, path",
    [
        ("eyes wifi 192.168.1.42 uptime 9s", True, "wifi"),
        ("eyes usb /dev/cu.usbmodem1 uptime n/a", True, "usb"),
        ("eyes offline", True, "usb"),
        ("eyes offline", False, "wifi"),  # #196: no Core on USB, so the service is not stopped; it waits for a beacon
    ],
)
def test_just_flash_takes_wifi_while_the_beacon_is_fresh_else_usb(tmp_path, status, port, path):
    """just flash's FLASH_VIA (just flash-usb forces the cable; its commands: noggin/test_core.py)."""
    cli = tmp_path / "noggin"
    cli.write_text(f'#!/bin/sh\n[ "$1" = status ] && echo "{status}"\n')
    cli.chmod(0o755)
    (tmp_path / "cu.usbmodem1").touch()
    ports = str(tmp_path / ("cu.usbmodem*" if port else "cu.none*"))
    just = [Path(sys.executable).with_name("just"), "--set", "NOGGIN", cli, "--set", "PORTS", ports]
    root = Path(__file__).resolve().parent.parent
    out = subprocess.run([*just, "--evaluate", "FLASH_VIA"], cwd=root, capture_output=True, text=True, check=True)
    assert out.stdout == path


def test_add_network_keeps_the_others_and_the_token(tmp_path):
    wf = tmp_path / "wifi.json"
    wf.write_text(json.dumps({"ssid": "home", "password": "pw", "token": TOKEN}))  # the one-network shape before #195
    add_network(wf, "studio", "pw2")
    add_network(wf, "home", "new")  # the same SSID again: its password is updated, not a second entry
    assert json.loads(wf.read_text()) == {
        "networks": [{"ssid": "studio", "password": "pw2"}, {"ssid": "home", "password": "new"}],
        "token": TOKEN,
    }


def test_add_network_to_no_file_makes_a_token(tmp_path):
    wf = tmp_path / "wifi.json"
    add_network(wf, "home", "pw")
    cfg = json.loads(wf.read_text())
    assert cfg["networks"] == [{"ssid": "home", "password": "pw"}]
    assert len(cfg["token"]) == 32 and int(cfg["token"], 16) >= 0  # 128 random bits, hex
