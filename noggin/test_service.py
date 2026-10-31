import json
import os
import socket
import tempfile
import threading
import time
import uuid

from noggin.service import Service


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
