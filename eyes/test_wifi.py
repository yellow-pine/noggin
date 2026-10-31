# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
"""Core-side Wi-Fi Link (eyes/wifi.py) on the Mac: `network` and `socket` stubbed, like conftest stubs `machine`."""

import base64
import hashlib

import pytest
import wifi as mod

CFG = {"ssid": "home", "password": "pw", "token": "t0k"}


def dg(seq, line, name="eyes"):
    """A command datagram as the noggin service sends it: `<tag> <seq> <line>`, the tag bound to the Core's name."""
    return f"{mod.tag(CFG['token'], f'{name} {seq} {line}')} {seq} {line}".encode()


class FakeWLAN:
    connected = False
    connects = []
    configs = []
    PM_NONE = 0

    def __init__(self, iface):
        pass

    def active(self, on):
        pass

    def config(self, **kw):
        FakeWLAN.configs.append(kw)

    def connect(self, ssid, password):
        FakeWLAN.connects.append((ssid, password))

    def isconnected(self):
        return FakeWLAN.connected

    def ifconfig(self):
        return ("192.168.1.42", "255.255.255.0", "192.168.1.1", "192.168.1.1")


class FakeSocket:
    sent = []  # (payload, addr) in order
    inbox = []  # (payload, addr) to be received, in order

    def __init__(self, *a):
        self.opts = []

    def setsockopt(self, *a):
        self.opts.append(a)

    def bind(self, addr):
        self.bound = addr

    def setblocking(self, b):
        pass

    def sendto(self, data, addr):
        FakeSocket.sent.append((data, addr))

    def recvfrom(self, n):
        if not FakeSocket.inbox:
            raise OSError(11)
        return FakeSocket.inbox.pop(0)

    def close(self):
        pass


@pytest.fixture
def link(monkeypatch):
    fake_net = type("net", (), {"WLAN": FakeWLAN, "STA_IF": 0})
    fake_sock = type(
        "sock", (), {"socket": FakeSocket, "AF_INET": 2, "SOCK_DGRAM": 2, "SOL_SOCKET": 1, "SO_BROADCAST": 6}
    )
    monkeypatch.setattr(mod, "network", fake_net)
    monkeypatch.setattr(mod, "socket", fake_sock)
    FakeWLAN.connected = False
    FakeWLAN.connects.clear()
    FakeWLAN.configs.clear()
    FakeSocket.sent.clear()
    FakeSocket.inbox.clear()
    handled = []
    w = mod.Wifi(handled.append, "eyes", CFG)
    w.handled = handled
    return w


def test_joins_in_the_background_and_retries_until_connected(link):
    link.poll(0)
    assert FakeWLAN.connects == [("home", "pw")]
    link.poll(5_000)  # still joining: no second connect yet
    assert len(FakeWLAN.connects) == 1
    link.poll(15_000)  # retry after the join window
    assert len(FakeWLAN.connects) == 2
    assert FakeSocket.sent == []  # nothing beaconed while off the network


def test_beacons_name_ip_and_uptime_every_2s_once_joined(link):
    link.poll(0)
    FakeWLAN.connected = True
    link.poll(7_000)
    link.poll(8_000)
    link.poll(9_100)
    assert FakeSocket.sent == [
        (b"noggin eyes 192.168.1.42 7", ("255.255.255.255", 4711)),
        (b"noggin eyes 192.168.1.42 9", ("255.255.255.255", 4711)),
    ]


MAC = ("192.168.1.10", 50000)


def joined(link):
    link.poll(0)
    FakeWLAN.connected = True
    link.poll(1_000)
    FakeSocket.sent.clear()
    return link


def test_command_with_the_token_runs_through_the_parser_and_is_acked(link):
    joined(link)
    FakeSocket.inbox.append((dg(7, "eureka 2\n"), MAC))
    link.poll(1_100)
    assert link.handled == ["eureka 2\n"]
    assert FakeSocket.sent == [(b"ok 7", MAC)]


def test_power_save_is_off_so_datagrams_are_not_held_at_the_access_point(link):
    assert {"pm": FakeWLAN.PM_NONE} in FakeWLAN.configs


def test_ack_goes_out_before_the_line_runs(link):
    joined(link)
    sent_when_run = []
    link.handle_line = lambda line: sent_when_run.extend(FakeSocket.sent)  # a gesture blocks for about a second
    FakeSocket.inbox.append((dg(7, "wink 3"), MAC))
    link.poll(1_100)
    assert sent_when_run == [(b"ok 7", MAC)]


def test_wrong_tag_is_ignored(link):
    joined(link)
    FakeSocket.inbox.append((b"nope 7 eureka 2", MAC))
    link.poll(1_100)
    assert link.handled == [] and FakeSocket.sent == []


def test_datagram_tagged_for_another_core_is_ignored(link):
    joined(link)
    FakeSocket.inbox.append((dg(7, "eureka 2", name="neck"), MAC))
    link.poll(1_100)
    assert link.handled == [] and FakeSocket.sent == []


def test_repeated_seq_is_acked_again_but_not_replayed(link):
    joined(link)
    FakeSocket.inbox.append((dg(7, "eureka 2"), MAC))
    link.poll(1_100)
    FakeSocket.inbox.append((dg(7, "eureka 2"), MAC))
    link.poll(1_200)
    assert link.handled == ["eureka 2"]
    assert FakeSocket.sent == [(b"ok 7", MAC), (b"ok 7", MAC)]


def test_parser_error_is_reported_with_the_seq(link):
    joined(link)
    link.handle_line = lambda line: 1 / 0
    FakeSocket.inbox.append((dg(8, "eureka 2"), MAC))
    link.poll(1_100)
    assert FakeSocket.sent == [(b"ok 8", MAC), (b"err 8 ZeroDivisionError", MAC)]
    FakeSocket.inbox.append((dg(8, "eureka 2"), MAC))
    link.poll(1_200)  # a retry of it is answered with what happened, not run again
    assert FakeSocket.sent[-1] == (b"err 8 ZeroDivisionError", MAC)


def test_malformed_datagram_is_ignored(link):
    joined(link)
    FakeSocket.inbox.append((b"deadbeef", MAC))
    FakeSocket.inbox.append((b"deadbeef x rest", MAC))
    link.poll(1_100)
    assert link.handled == [] and FakeSocket.sent == []


def test_start_is_usb_only_without_wifi_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert mod.start(lambda line: None) is None


def test_start_reads_credentials_and_core_name(tmp_path, monkeypatch, link):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "wifi.json").write_text('{"ssid": "home", "password": "pw", "token": "t0k"}')
    (tmp_path / "core.json").write_text('{"name": "neck", "ports": {"1": "tilt", "2": "mouth", "3": "pan"}}')
    w = mod.start(lambda line: None)
    w.poll(0)
    FakeWLAN.connected = True
    w.poll(2_000)
    assert FakeWLAN.connects == [("home", "pw")]
    assert FakeSocket.sent[0][0].startswith(b"noggin neck ")


def test_older_seq_is_dropped_newer_runs(link):
    joined(link)
    FakeSocket.inbox.append((dg(9, "eureka 2"), MAC))
    link.poll(1_100)
    FakeSocket.inbox.append((dg(5, "wink"), MAC))
    link.poll(1_200)  # replayed old datagram
    FakeSocket.inbox.append((dg(12, "wink"), MAC))
    link.poll(1_300)
    assert link.handled == ["eureka 2", "wink"]
    assert FakeSocket.sent == [(b"ok 9", MAC), (b"ok 12", MAC)]


def test_undecodable_datagram_does_not_crash_the_loop(link):
    joined(link)
    FakeSocket.inbox.append((b"\xff\xfe t0k 1 rest", MAC))
    link.poll(1_100)
    assert link.handled == [] and FakeSocket.sent == []


def test_start_refuses_an_empty_token(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "wifi.json").write_text('{"ssid": "s", "password": "p", "token": ""}')
    assert mod.start(lambda line: None) is None


def test_tag_is_keyed_and_message_bound():
    assert mod.tag("t0k", "eyes 1 rest") == mod.tag("t0k", "eyes 1 rest")
    assert mod.tag("t0k", "eyes 1 rest") != mod.tag("other", "eyes 1 rest")
    assert mod.tag("t0k", "eyes 1 rest") != mod.tag("t0k", "eyes 2 rest")
    assert mod.tag("t0k", "eyes 1 rest") != mod.tag("t0k", "neck 1 rest")
    assert len(mod.tag("t0k", "eyes 1 rest")) == 32


def test_uptime_survives_the_ticks_wrap(link, monkeypatch):
    WRAP = 1 << 30  # MicroPython ticks_ms period
    monkeypatch.setattr(mod, "ticks_diff", lambda a, b: ((a - b + WRAP // 2) % WRAP) - WRAP // 2)
    link.poll(0)
    FakeWLAN.connected = True
    link.poll(WRAP // 2 - 1_000)
    link.poll(WRAP - 1_500)  # ... 1.5 s before the wrap
    link.poll(500)  # 2 s later, ticks wrapped
    assert [int(m.split()[-1]) for m, _ in FakeSocket.sent] == [
        (WRAP // 2 - 1_000) // 1000,
        (WRAP - 1_500) // 1000,
        (WRAP + 500) // 1000,
    ]


# --- flashing over the Link: `put` chunks to <file>.new, `commit` swaps it in by its sha256 ---------------------------


def puts(name, data, chunk=120):
    return [f"put {name} {i} {base64.b64encode(data[i : i + chunk]).decode()}" for i in range(0, len(data), chunk)]


def commit(name, data):
    return f"commit {name} {hashlib.sha256(data).hexdigest()}"


def run(link, lines, seq=100):
    """Each line as a datagram from the Mac; the replies in order."""
    FakeSocket.sent.clear()
    for i, line in enumerate(lines):
        FakeSocket.inbox.append((dg(seq + i, line), MAC))
        link.poll(1_100 + i)
    return [m.decode() for m, _ in FakeSocket.sent]


def test_put_and_commit_swap_the_new_file_in_and_keep_the_old_one_as_bak(link, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "eyes.py").write_bytes(b"old program")
    new = bytes(range(256)) * 2  # several chunks, every byte value
    joined(link)
    replies = run(link, [*puts("eyes.py", new), commit("eyes.py", new)])
    assert replies == [f"ok {100 + i}" for i in range(len(replies))] and len(replies) == 6
    assert (tmp_path / "eyes.py").read_bytes() == new
    assert (tmp_path / "eyes.py.bak").read_bytes() == b"old program"
    assert not (tmp_path / "eyes.py.new").exists()
    assert (tmp_path / "flash.trial").read_text().split() == ["eyes.py"]  # boot.py's cue: on probation
    assert link.handled == []  # flash lines never reach the eye program's parser


def test_a_hash_mismatch_swaps_nothing_and_is_reported(link, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "eyes.py").write_bytes(b"old program")
    joined(link)
    replies = run(link, [*puts("eyes.py", b"new program"), commit("eyes.py", b"something else")])
    assert replies == ["ok 100", "err 101 ValueError"]
    assert (tmp_path / "eyes.py").read_bytes() == b"old program"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["eyes.py"]


def test_boot_py_only_changes_over_usb(link, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    joined(link)
    for name in ("boot.py", "../boot.py", "wifi.json"):
        assert run(link, puts(name, b"x")) == ["err 100 ValueError"]
    assert list(tmp_path.iterdir()) == []


def test_a_chunk_out_of_order_is_refused(link, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    joined(link)
    first, _, third = puts("eyes.py", b"a" * 360)
    assert run(link, [first, third]) == ["ok 100", "err 101 ValueError"]
    assert (tmp_path / "eyes.py.new").read_bytes() == b"a" * 120


def test_flashing_again_before_a_reboot_keeps_the_bak_that_last_booted(link, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "eyes.py").write_bytes(b"good")
    joined(link)
    run(link, [*puts("eyes.py", b"first try"), commit("eyes.py", b"first try")], seq=100)
    run(link, [*puts("eyes.py", b"second try"), commit("eyes.py", b"second try")], seq=200)
    assert (tmp_path / "eyes.py").read_bytes() == b"second try"
    assert (tmp_path / "eyes.py.bak").read_bytes() == b"good"
    assert (tmp_path / "flash.trial").read_text().split() == ["eyes.py"]


def test_commit_of_a_file_already_in_place_is_ok_without_a_swap(link, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "eyes.py").write_bytes(b"running")
    joined(link)
    replies = run(link, [commit("eyes.py", b"running"), commit("eyes.py", b"other")])
    assert replies[0] == "ok 100" and replies[1].startswith("err 101 ")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["eyes.py"]  # the Mac's check after the reboot


def test_reboot_is_acked_then_resets_the_core(link, monkeypatch):
    joined(link)
    events = []
    monkeypatch.setattr(mod, "reset", lambda: events.append(list(FakeSocket.sent)))
    assert run(link, ["reboot"]) == ["ok 100"]
    assert events == [[(b"ok 100", MAC)]] and link.handled == []
