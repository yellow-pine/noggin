"""The Mech stand-in (mech/standin.py) beside the real noggin service: the Link's live checks on the Mech
(docs/use/noggin-service.md, #177 and #212) as tests. Real time, each on its own ports and folders."""

import json
import os
import re
import socket
import subprocess
import tempfile
import threading
import time
import uuid

import pytest

from mech.standin import MICROPYTHON, Mech, mpy, program
from noggin import service
from noggin.core import COMMIT, VERSION

TOKEN = "00112233445566778899aabbccddeeff"  # synthetic: never eyes/wifi.json


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait(log, text, after=-1, timeout=30.0):
    """Index of the first service log line after `after` that contains text."""
    end = time.time() + timeout
    while time.time() < end:
        for i in range(after + 1, len(log)):
            if text in log[i]:
                return i
        time.sleep(0.05)
    raise AssertionError(f"no {text!r} in {timeout} s:\n" + "\n".join(log))


@pytest.fixture
def start(tmp_path, monkeypatch):
    """start(cable, ...) -> (ask, mech, log): the noggin service on temp files and free ports, a Mech stand-in that
    knows it, `ask(line)` (the CLI's socket line, its answer back) and the service's log lines."""
    log, running = [], []
    monkeypatch.setattr(service, "log", lambda *a: log.append(" ".join(map(str, a))))
    sock = os.path.join(tempfile.gettempdir(), f"m{uuid.uuid4().hex[:6]}.sock")  # AF_UNIX paths max 104 bytes

    def start(cable=False, **mech_kw):
        mac = tmp_path / "mac"
        mac.mkdir()
        (mac / "calibration.json").write_text('{"lid_rest": 0.28}')
        (mac / "wifi.json").write_text(json.dumps({"token": TOKEN}))
        command_port = free_port()
        svc = service.Service(
            sock_path=sock,
            open_serial=service.open_link,
            mute_file=mac / "mute",
            cal_file=mac / "calibration.json",
            wifi_file=mac / "wifi.json",
            beacon_port=0,
            command_port=command_port,
            stale=3.0,
            pause=1.0,
        )
        mech = Mech(tmp_path / "core", TOKEN, svc.wifi.port, command_port, cable=cable, **mech_kw)
        monkeypatch.setattr(service, "PORT_GLOB", mech.tty or str(tmp_path / "no-cable"))
        t = threading.Thread(target=svc.run, daemon=True)
        t.start()
        running.append((svc, t, mech))
        while not svc.ready:
            time.sleep(0.02)

        def ask(line, timeout=90):
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as c:
                c.settimeout(timeout)
                c.connect(sock)
                c.sendall(line.encode() + b"\n")
                c.shutdown(socket.SHUT_WR)
                return c.makefile().read()

        return ask, mech, log

    yield start
    for svc, t, mech in running:
        svc.stop()
        t.join(5)
        mech.power_off()


def test_the_stand_in_runs_the_cores_micropython():
    # the .mpy version and sub-version; the bits above name this build's native arch (x64 on CI), which bytecode skips
    out = subprocess.run([MICROPYTHON, "-c", "import sys; print(sys.implementation._mpy & 0x3FF)"], capture_output=True)
    assert out.stdout.strip() == b"774"  # eyes/test_micropython.py CORE_MPY


def test_cable_pulled_mid_gesture_nothing_is_dropped(start):
    ask, mech, log = start(cable=True)
    wait(log, "Core on " + mech.tty)
    wait(log, "eyes beacon back")
    ask("demo wink 1")
    n = wait(log, "sent eyes ['wink 1']")
    time.sleep(0.5)  # the wink plays about 2 s
    mech.pull()
    for _ in range(2):
        n = wait(log, "sent eyes ['wink 1']", after=n)
    assert not [line for line in log if "dropped" in line or "no ack" in line], log


def test_wifi_flash_lands_and_a_broken_program_rolls_back_to_its_bak_files(start, tmp_path):
    ask, mech, log = start()
    wait(log, "eyes beacon back")
    build = tmp_path / "mac" / "build"  # what `make mpy` writes beside calibration.json
    build.mkdir()
    program(build, "mac")  # the same program built elsewhere: other bytes, so each file swaps in
    assert ask("flash").startswith("flashed eyes: eyes.mpy gaze_trace.mpy wifi.mpy stamp.mpy"), log
    good = (mech.root / "eyes.mpy").read_bytes()
    assert good == (build / "eyes.mpy").read_bytes() and (mech.root / "eyes.mpy.bak").exists()
    assert not (mech.root / "flash.trial").exists()  # reached `noggin ready`: off probation
    (tmp_path / "broken.py").write_text("while True:\n    pass\n")  # hangs: boot.py's 10 s run out
    mpy(tmp_path / "broken.py", build / "eyes.mpy")
    assert "never reached `noggin ready`" in ask("flash"), log
    assert (mech.root / "eyes.mpy").read_bytes() == good
    status = ask("status")
    assert status.startswith("eyes wifi 127.0.0.1 ") and f" program {VERSION} {COMMIT}\n" in status, status  # #357
    assert "warning" not in status


def test_power_off_and_on_the_beacon_goes_stale_comes_back_and_the_calibration_is_resent(start):
    ask, mech, log = start()
    n = wait(log, "sent eyes ['set lid_rest 0.28', 'rest']")
    off = time.time()
    mech.power_off()
    n = wait(log, "eyes beacon stale for 3.0 s", after=n)
    # off past link.seq's ceiling, 10 s of the Mac's seq: a Core back sooner drops the lines inside it (ADR 0005)
    time.sleep(max(0.0, off + 11 - time.time()))
    mech.power_on()
    n = wait(log, f"eyes beacon back: wifi 127.0.0.1 uptime 0s program {VERSION} {COMMIT}", after=n)
    wait(log, "sent eyes ['set lid_rest 0.28', 'rest']", after=n)


def test_moved_to_another_known_network_the_core_joins_it(start):
    ask, mech, log = start(networks=("home", "office"), air={"home": -50, "office": -80})
    n = wait(log, "eyes beacon back")
    assert "joined home" in mech.log.read_text()  # the loudest known network (#195)
    mech.move({"office": -60, "cafe": -30})  # home out of range; cafe is louder but unknown
    n = wait(log, "eyes beacon stale for 3.0 s", after=n)
    n = wait(log, "eyes beacon back", after=n)  # 10 s of the driver's own reconnect, then a scan
    assert re.findall(r"network: joined (\w+)", mech.log.read_text()) == ["home", "office"]
    wait(log, "sent eyes ['set lid_rest 0.28', 'rest']", after=n)
