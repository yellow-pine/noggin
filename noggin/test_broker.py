"""The real Mosquitto under our generated config, with throwaway certificates; clients are paho-mqtt, the Eclipse
reference client (https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html)."""

import queue
import socket
import subprocess
import threading
import time

import paho.mqtt.client as mqtt
import pytest
from paho.mqtt.enums import CallbackAPIVersion

from noggin.broker import Broker

CORES = ("eyes", "neck")


def openssl(*args, cwd):
    subprocess.run(["openssl", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture(scope="module")
def pki(tmp_path_factory):
    """A one-day CA and the broker, mac, eyes and neck certificates, each named by its CN, as #157 lays them out."""
    d = tmp_path_factory.mktemp("pki")
    key = ["-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes"]
    openssl("req", "-x509", *key, "-keyout", "ca.key", "-out", "ca.crt", "-subj", "/CN=noggin-ca", "-days", "1", cwd=d)
    (d / "san.ext").write_text("subjectAltName=DNS:localhost,IP:127.0.0.1\n")
    for name in ("broker", "mac", *CORES):
        openssl("req", *key, "-keyout", f"{name}.key", "-out", f"{name}.csr", "-subj", f"/CN={name}", cwd=d)
        ext = ["-extfile", "san.ext"] if name == "broker" else []
        openssl("x509", "-req", "-in", f"{name}.csr", "-CA", "ca.crt", "-CAkey", "ca.key", "-CAcreateserial",
                "-out", f"{name}.crt", "-days", "1", *ext, cwd=d)  # fmt: skip
    return d


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def listening(port):
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
        return True
    except OSError:
        return False


def wait_for(pred, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def broker(pki):
    b = Broker(CORES, pki, port=free_port())
    b.start()
    assert wait_for(lambda: listening(b.port))
    yield b
    b.stop()


class Client:
    """A connected MQTT v5 client with a certificate (`name`) or without one; `got` queues (topic, payload)."""

    def __init__(self, pki, port, name=None):
        self.got, self.subscribed = queue.Queue(), threading.Event()
        self.c = mqtt.Client(CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
        cert, key = (str(pki / f"{name}.crt"), str(pki / f"{name}.key")) if name else (None, None)
        self.c.tls_set(ca_certs=str(pki / "ca.crt"), certfile=cert, keyfile=key)
        self.c.on_message = lambda c, u, m: self.got.put((m.topic, m.payload.decode()))
        self.c.on_subscribe = lambda *a: self.subscribed.set()
        self.c.connect("localhost", port)
        self.c.loop_start()
        if not wait_for(self.c.is_connected, 3.0):
            self.close()
            raise ConnectionError(f"{name} not connected")

    def subscribe(self, *topics):
        self.subscribed.clear()
        self.c.subscribe([(t, 1) for t in topics])
        assert self.subscribed.wait(3.0)

    def publish(self, topic, payload):
        self.c.publish(topic, payload, qos=1).wait_for_publish(3.0)

    def next(self):
        return self.got.get(timeout=3.0)

    def close(self):
        self.c.loop_stop()
        self.c.disconnect()


def test_a_core_reads_its_commands_and_flash_and_writes_its_status(pki, broker):
    mac, eyes = Client(pki, broker.port, "mac"), Client(pki, broker.port, "eyes")
    mac.subscribe("noggin/#")
    eyes.subscribe("noggin/eyes/cmd", "noggin/eyes/flash/#")
    mac.publish("noggin/eyes/cmd", "rest")
    mac.publish("noggin/eyes/flash/eyes.py", "chunk")
    assert eyes.next() == ("noggin/eyes/cmd", "rest")
    assert eyes.next() == ("noggin/eyes/flash/eyes.py", "chunk")
    eyes.publish("noggin/eyes/status", "online")
    seen = [mac.next() for _ in range(3)]  # the Mac reads all of noggin/#: its own two, then the status
    assert seen[-1] == ("noggin/eyes/status", "online")
    mac.close()
    eyes.close()


def test_a_core_cannot_reach_another_cores_topics_or_write_commands(pki, broker):
    mac, eyes = Client(pki, broker.port, "mac"), Client(pki, broker.port, "eyes")
    mac.subscribe("noggin/#")
    eyes.subscribe("noggin/neck/cmd", "noggin/neck/flash/#", "noggin/eyes/cmd")
    mac.publish("noggin/neck/cmd", "rest")
    mac.publish("noggin/neck/flash/eyes.py", "chunk")
    mac.publish("noggin/eyes/cmd", "wink 1")
    assert eyes.next() == ("noggin/eyes/cmd", "wink 1")  # one connection keeps order: neck's two never came
    for _ in range(3):
        mac.next()  # the Mac reads all three
    eyes.publish("noggin/neck/status", "spoofed")
    eyes.publish("noggin/eyes/cmd", "forged")
    eyes.publish("noggin/eyes/status", "online")
    assert mac.next() == ("noggin/eyes/status", "online")
    assert eyes.got.empty()  # its forged cmd was dropped, so it never came back to its own subscription
    mac.close()
    eyes.close()


def test_a_client_without_a_certificate_is_refused(pki, broker):
    with pytest.raises((ConnectionError, OSError)):
        Client(pki, broker.port).close()


def test_mosquitto_is_restarted_when_it_exits(pki, broker):
    first = broker.proc
    first.kill()
    first.wait()
    assert wait_for(lambda: (broker.poll(), broker.proc is not first)[1])
    assert wait_for(lambda: listening(broker.port))
    assert Client(pki, broker.port, "neck").c.is_connected()


def test_without_the_pki_it_is_skipped_with_a_log_line(tmp_path, capsys):
    b = Broker(CORES, tmp_path, port=free_port())
    b.start()
    assert b.proc is None
    assert "broker skipped: no ca.crt, broker.crt, broker.key in" in capsys.readouterr().out
