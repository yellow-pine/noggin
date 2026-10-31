import json, os, socket, tempfile, threading, time, uuid
from daemon.eyesd import Daemon

class FakeSerial:
    def __init__(self): self.buf = b""
    def write(self, b): self.buf += b
    def close(self): pass

def send(path, text):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect(path); s.sendall(text.encode()); s.close()

def wait_for(pred, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred(): return True
        time.sleep(0.02)
    return False

def test_hook_json_reaches_the_board_and_mute_persists(tmp_path):
    sock = os.path.join(tempfile.gettempdir(), f"n{uuid.uuid4().hex[:6]}.sock")  # AF_UNIX path limit 104 bytes
    state = tmp_path / "mute"
    fake = FakeSerial()
    d = Daemon(sock_path=sock, open_serial=lambda: fake, mute_file=state)
    t = threading.Thread(target=d.run, daemon=True); t.start()
    assert wait_for(lambda: d.ready)
    send(sock, json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "x"}) + "\n")
    assert wait_for(lambda: fake.buf == b"thinking\n")
    send(sock, "off\n")
    assert wait_for(lambda: state.exists())
    send(sock, json.dumps({"hook_event_name": "Stop", "session_id": "x"}) + "\n")
    time.sleep(0.3)
    assert fake.buf == b"thinking\n"            # muted: nothing more
    send(sock, "on\n"); send(sock, "eureka 2\n")   # manual gesture for the wizard
    assert wait_for(lambda: fake.buf.endswith(b"eureka 2\n"))
    d.stop()
