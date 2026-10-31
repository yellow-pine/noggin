"""Core-side Wi-Fi Link (eyes/wifi.py) on the Mac: `network` and `socket` stubbed, like conftest stubs `machine`."""
import pytest
import wifi as mod

CFG = {"ssid": "home", "password": "pw", "token": "t0k"}


def dg(seq, line):
    """A command datagram as the noggin service sends it: `<mac> <seq> <line>`."""
    return f"{mod.mac(CFG['token'], f'{seq} {line}')} {seq} {line}".encode()


class FakeWLAN:
    connected = False
    connects = []
    def __init__(self, iface): pass
    def active(self, on): pass
    def connect(self, ssid, password): FakeWLAN.connects.append((ssid, password))
    def isconnected(self): return FakeWLAN.connected
    def ifconfig(self): return ("192.168.1.42", "255.255.255.0", "192.168.1.1", "192.168.1.1")


class FakeSocket:
    sent = []           # (payload, addr) in order
    inbox = []          # (payload, addr) to be received, in order
    def __init__(self, *a): self.opts = []
    def setsockopt(self, *a): self.opts.append(a)
    def bind(self, addr): self.bound = addr
    def setblocking(self, b): pass
    def sendto(self, data, addr): FakeSocket.sent.append((data, addr))
    def recvfrom(self, n):
        if not FakeSocket.inbox:
            raise OSError(11)
        return FakeSocket.inbox.pop(0)
    def close(self): pass


@pytest.fixture
def link(monkeypatch):
    fake_net = type("net", (), {"WLAN": FakeWLAN, "STA_IF": 0})
    fake_sock = type("sock", (), {"socket": FakeSocket, "AF_INET": 2, "SOCK_DGRAM": 2, "SOL_SOCKET": 1, "SO_BROADCAST": 6})
    monkeypatch.setattr(mod, "network", fake_net); monkeypatch.setattr(mod, "socket", fake_sock)
    FakeWLAN.connected = False; FakeWLAN.connects.clear(); FakeSocket.sent.clear(); FakeSocket.inbox.clear()
    handled = []
    w = mod.Wifi(handled.append, "eyes", CFG)
    w.handled = handled
    return w


def test_joins_in_the_background_and_retries_until_connected(link):
    link.poll(0)
    assert FakeWLAN.connects == [("home", "pw")]
    link.poll(5_000)                                   # still joining: no second connect yet
    assert len(FakeWLAN.connects) == 1
    link.poll(15_000)                                  # retry after the join window
    assert len(FakeWLAN.connects) == 2
    assert FakeSocket.sent == []                       # nothing beaconed while off the network


def test_beacons_name_ip_and_uptime_every_2s_once_joined(link):
    link.poll(0); FakeWLAN.connected = True
    link.poll(7_000); link.poll(8_000); link.poll(9_100)
    assert FakeSocket.sent == [(b"noggin eyes 192.168.1.42 7", ("255.255.255.255", 4711)),
                               (b"noggin eyes 192.168.1.42 9", ("255.255.255.255", 4711))]


MAC = ("192.168.1.10", 50000)

def joined(link):
    link.poll(0); FakeWLAN.connected = True; link.poll(1_000); FakeSocket.sent.clear()
    return link


def test_command_with_the_token_runs_through_the_parser_and_is_acked(link):
    joined(link)
    FakeSocket.inbox.append((dg(7, "eureka 2\n"), MAC))
    link.poll(1_100)
    assert link.handled == ["eureka 2\n"]
    assert FakeSocket.sent == [(b"ok 7", MAC)]


def test_wrong_mac_is_ignored(link):
    joined(link)
    FakeSocket.inbox.append((b"nope 7 eureka 2", MAC))
    link.poll(1_100)
    assert link.handled == [] and FakeSocket.sent == []


def test_repeated_seq_is_acked_again_but_not_replayed(link):
    joined(link)
    FakeSocket.inbox.append((dg(7, "eureka 2"), MAC)); link.poll(1_100)
    FakeSocket.inbox.append((dg(7, "eureka 2"), MAC)); link.poll(1_200)
    assert link.handled == ["eureka 2"]
    assert FakeSocket.sent == [(b"ok 7", MAC), (b"ok 7", MAC)]


def test_parser_error_is_reported_with_the_seq(link):
    joined(link)
    link.handle_line = lambda line: 1 / 0
    FakeSocket.inbox.append((dg(8, "eureka 2"), MAC)); link.poll(1_100)
    assert FakeSocket.sent == [(b"err 8 ZeroDivisionError", MAC)]


def test_malformed_datagram_is_ignored(link):
    joined(link)
    FakeSocket.inbox.append((b"deadbeef", MAC)); FakeSocket.inbox.append((b"deadbeef x rest", MAC)); link.poll(1_100)
    assert link.handled == [] and FakeSocket.sent == []


def test_start_is_usb_only_without_wifi_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert mod.start(lambda line: None) is None


def test_start_reads_credentials_and_core_name(tmp_path, monkeypatch, link):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "wifi.json").write_text('{"ssid": "home", "password": "pw", "token": "t0k"}')
    (tmp_path / "core.json").write_text('{"name": "neck", "ports": {"1": "tilt", "2": "mouth", "3": "pan"}}')
    w = mod.start(lambda line: None)
    w.poll(0); FakeWLAN.connected = True; w.poll(2_000)
    assert FakeWLAN.connects == [("home", "pw")]
    assert FakeSocket.sent[0][0].startswith(b"noggin neck ")


def test_older_seq_is_dropped_newer_runs(link):
    joined(link)
    FakeSocket.inbox.append((dg(9, "eureka 2"), MAC)); link.poll(1_100)
    FakeSocket.inbox.append((dg(5, "wink"), MAC)); link.poll(1_200)       # replayed old datagram
    FakeSocket.inbox.append((dg(12, "wink"), MAC)); link.poll(1_300)
    assert link.handled == ["eureka 2", "wink"]
    assert FakeSocket.sent == [(b"ok 9", MAC), (b"ok 12", MAC)]


def test_undecodable_datagram_does_not_crash_the_loop(link):
    joined(link)
    FakeSocket.inbox.append((b"\xff\xfe t0k 1 rest", MAC)); link.poll(1_100)
    assert link.handled == [] and FakeSocket.sent == []


def test_start_refuses_an_empty_token(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "wifi.json").write_text('{"ssid": "s", "password": "p", "token": ""}')
    assert mod.start(lambda line: None) is None


def test_hmac_is_keyed_and_message_bound():
    assert mod.mac("t0k", "1 rest") == mod.mac("t0k", "1 rest")
    assert mod.mac("t0k", "1 rest") != mod.mac("other", "1 rest")
    assert mod.mac("t0k", "1 rest") != mod.mac("t0k", "2 rest")
    assert len(mod.mac("t0k", "1 rest")) == 32
