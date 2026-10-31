import json
import os
import socket
import tempfile
import threading
import time
import uuid

from noggin.service import READ_CAP, READ_SECONDS, Service, gesture_seconds


class FakeSerial:
    in_waiting = 0
    port = ""

    def __init__(self):
        self.buf = b""

    def write(self, b):
        self.buf += b

    def read(self, n):
        return b""

    def close(self):
        pass


def send(path, text):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(path)
    s.sendall(text.encode())
    s.close()


def wait_for(pred, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.02)
    return False


def test_hook_json_reaches_the_board_and_mute_persists(tmp_path):
    sock = os.path.join(tempfile.gettempdir(), f"n{uuid.uuid4().hex[:6]}.sock")  # AF_UNIX path limit 104 bytes
    state = tmp_path / "mute"
    fake = FakeSerial()
    cal = tmp_path / "calibration.json"
    cal.write_text('{"lid_rest": 0.28, "l_eye_lo": 58}')
    d = Service(sock_path=sock, open_serial=lambda: fake, mute_file=state, cal_file=cal, beacon_port=0)
    t = threading.Thread(target=d.run, daemon=True)
    t.start()
    assert wait_for(lambda: d.ready)
    send(sock, json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "x"}) + "\n")
    assert wait_for(
        lambda: fake.buf == b"set lid_rest 0.28\nset l_eye_lo 58\nrest\nthinking\n"
    )  # calibration + mode on connect, then the Trigger
    send(sock, "off\n")
    assert wait_for(lambda: state.exists())
    send(sock, json.dumps({"hook_event_name": "Stop", "session_id": "x"}) + "\n")
    time.sleep(0.3)
    assert fake.buf.endswith(b"thinking\nrest\nrelease\n")  # mute rests + unpowers the Core; the Stop is dropped
    send(sock, "on\n")
    send(sock, "eureka 2\n")  # manual gesture for the wizard
    assert wait_for(lambda: fake.buf.endswith(b"eureka 2\n"))
    send(sock, "set lid_rest 0.3\n")  # live tune: Core gets it, file keeps it
    assert wait_for(lambda: fake.buf.endswith(b"set lid_rest 0.3\n"))
    assert json.loads(cal.read_text())["lid_rest"] == 0.3
    send(sock, "set bogus 1\n")
    time.sleep(0.2)
    assert "bogus" not in cal.read_text()
    d.stop()


def test_core_output_is_logged(tmp_path, capsys):
    class ChattySerial(FakeSerial):
        pending = b"noggin ready\r\nTraceback (most recent call last):\r\n"

        @property
        def in_waiting(self):
            return len(self.pending)

        def read(self, n):
            out, self.pending = self.pending[:n], self.pending[n:]
            return out

    sock = os.path.join(tempfile.gettempdir(), f"n{uuid.uuid4().hex[:6]}.sock")
    d = Service(
        sock_path=sock,
        open_serial=lambda: ChattySerial(),
        mute_file=tmp_path / "m",
        cal_file=tmp_path / "c.json",
        beacon_port=0,
    )
    t = threading.Thread(target=d.run, daemon=True)
    t.start()
    assert wait_for(lambda: d.ready)
    time.sleep(0.6)
    d.stop()
    t.join(2)
    out = capsys.readouterr().out
    assert "Core: noggin ready" in out and "Core: Traceback" in out


def start(tmp_path, **kw):
    sock = os.path.join(tempfile.gettempdir(), f"n{uuid.uuid4().hex[:6]}.sock")
    fake = FakeSerial()
    s = Service(
        sock_path=sock,
        open_serial=lambda: fake,
        mute_file=tmp_path / "m",
        cal_file=tmp_path / "c.json",
        beacon_port=0,
        **kw,
    )
    threading.Thread(target=s.run, daemon=True).start()
    assert wait_for(lambda: s.ready)
    return s, sock, fake


def ask(path, text):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(path)
    s.sendall(text.encode())
    s.shutdown(socket.SHUT_WR)  # EOF, as nc gives on its stdin's end: the service reads to it, then answers
    s.settimeout(1.0)
    try:
        return s.recv(4096).decode()
    finally:
        s.close()


def test_a_fresh_service_follows_and_status_says_so(tmp_path):
    s, sock, _ = start(tmp_path)
    assert ask(sock, "status\n").endswith("mode follow\n")
    s.stop()


def test_demo_gesture_repeats_it_until_follow(tmp_path):
    s, sock, fake = start(tmp_path, duration=lambda line, cal: 0.0, pause=0.0)
    ask(sock, "demo bored 2\n")
    assert wait_for(lambda: fake.buf.count(b"bored 2\n") >= 3)
    assert ask(sock, "status\n").endswith("mode demo bored 2\n")
    ask(sock, "follow\n")
    assert wait_for(lambda: fake.buf.endswith(b"rest\n"))  # follow catches the Core up to the Director's mode
    n = fake.buf.count(b"bored 2\n")
    time.sleep(0.5)
    assert fake.buf.count(b"bored 2\n") == n and ask(sock, "status\n").endswith("mode follow\n")
    s.stop()


def test_demo_waits_the_gesture_out_plus_the_pause(tmp_path):
    asked = []
    s, sock, fake = start(tmp_path, duration=lambda line, cal: asked.append(line) or 0.3, pause=0.3)
    ask(sock, "demo wince\n")  # no level: the normal one
    assert wait_for(lambda: b"wince 2\n" in fake.buf)
    time.sleep(0.3)
    assert fake.buf.count(b"wince 2\n") == 1  # still inside 0.3 s gesture + 0.3 s pause
    assert wait_for(lambda: fake.buf.count(b"wince 2\n") == 2) and asked[0] == "wince 2"
    s.stop()


def test_unknown_demo_is_ignored(tmp_path):
    s, sock, fake = start(tmp_path, duration=lambda line, cal: 0.0, pause=0.0)
    ask(sock, "demo bored 7\n")
    time.sleep(0.3)
    assert b"bored" not in fake.buf and ask(sock, "status\n").endswith("mode follow\n")
    s.stop()


SEQUENCE = b"eureka 1\neureka 2\neureka 3\nattention 2\nbored 2\nwince 2\nwink 3\nthinking\nrest\n"


def test_demo_loops_the_whole_sequence(tmp_path):
    s, sock, fake = start(tmp_path, duration=lambda line, cal: 0.0, pause=0.0)
    ask(sock, "demo\n")
    assert wait_for(lambda: SEQUENCE + b"eureka 1\n" in fake.buf, timeout=4)
    ask(sock, "follow\n")
    s.stop()


def test_demo_once_plays_the_sequence_then_follows(tmp_path):
    s, sock, fake = start(tmp_path, duration=lambda line, cal: 0.0, pause=0.0)
    ask(sock, "demo once\n")
    assert ask(sock, "status\n").endswith("mode demo once\n")
    assert wait_for(lambda: ask(sock, "status\n").endswith("mode follow\n"), timeout=4)
    assert fake.buf.endswith(SEQUENCE + b"rest\n")  # then the Director's mode
    time.sleep(0.3)
    assert fake.buf.endswith(SEQUENCE + b"rest\n")
    s.stop()


def test_hooks_are_dropped_and_logged_in_demo(tmp_path, capsys):
    s, sock, fake = start(tmp_path, duration=lambda line, cal: 0.0, pause=60.0)
    ask(sock, "demo wink 3\n")
    assert wait_for(lambda: fake.buf.endswith(b"wink 3\n"))
    send(sock, json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "x"}) + "\n")
    time.sleep(0.3)
    assert fake.buf.endswith(b"wink 3\n") and "dropped UserPromptSubmit" in capsys.readouterr().out
    ask(sock, "follow\n")
    send(sock, json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "x"}) + "\n")
    assert wait_for(lambda: fake.buf.endswith(b"rest\nthinking\n"))  # following again: the Director never saw it
    s.stop()


def test_gesture_seconds_come_from_the_core_programs_clock():
    assert gesture_seconds("thinking", {}) == 8.0  # a mode: held, not played out
    assert 1.5 < gesture_seconds("eureka 2", {}) < 3 < gesture_seconds("bored 2", {})  # replayed: about 2 s and 12 s


def test_a_long_prompt_larger_than_one_read_still_reaches_the_board(tmp_path):
    s, sock, fake = start(tmp_path)
    prompt = {"hook_event_name": "UserPromptSubmit", "session_id": "x", "prompt": "paste " * 50_000}
    send(sock, json.dumps(prompt) + "\n")  # ~300 KB, several reads
    assert wait_for(lambda: fake.buf.endswith(b"rest\nthinking\n"))
    s.stop()


def test_a_connection_over_the_cap_is_dropped_and_the_service_carries_on(tmp_path, capsys):
    s, sock, fake = start(tmp_path)
    prompt = {"hook_event_name": "UserPromptSubmit", "session_id": "x", "prompt": "x" * READ_CAP}
    try:
        send(sock, json.dumps(prompt) + "\n")
    except OSError:  # the service hangs up mid-write
        pass
    assert ask(sock, "status\n").endswith("mode follow\n")
    assert b"thinking" not in fake.buf and "dropped connection: over" in capsys.readouterr().out
    s.stop()


def test_a_stalled_writer_is_dropped_after_the_timeout(tmp_path, capsys):
    s, sock, fake = start(tmp_path)
    c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    c.connect(sock)
    c.sendall(json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "x"}).encode() + b"\n")
    time.sleep(READ_SECONDS + 0.3)  # never sends EOF in time
    c.close()
    assert ask(sock, "status\n").endswith("mode follow\n")
    assert b"thinking" not in fake.buf and "dropped connection: timed out" in capsys.readouterr().out
    s.stop()
