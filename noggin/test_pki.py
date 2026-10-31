"""The Link's local CA, always in a temp dir (never the real ~/.noggin/pki). Checked with the openssl CLI itself."""

import os
import socket
import stat
import subprocess
import sys
from pathlib import Path

from noggin import pki

ROOT = Path(__file__).resolve().parent.parent
HOSTS = ["192.168.1.5", "mac.local"]


def openssl(*args, cwd):
    return subprocess.run(["openssl", *args], cwd=cwd, capture_output=True, text=True)


def test_the_ca_signs_the_broker_as_a_server_and_each_client_as_a_client(tmp_path):
    pki.ensure(tmp_path, HOSTS)
    assert openssl("verify", "-CAfile", "ca.crt", "-purpose", "sslserver", "broker.crt", cwd=tmp_path).returncode == 0
    for name in ("mac", "eyes", "neck"):
        assert (
            openssl("verify", "-CAfile", "ca.crt", "-purpose", "sslclient", f"{name}.crt", cwd=tmp_path).returncode == 0
        )
        assert openssl("verify", "-CAfile", "ca.crt", "-purpose", "sslserver", f"{name}.crt", cwd=tmp_path).returncode
        subject = openssl(
            "x509", "-in", f"{name}.crt", "-noout", "-subject", "-nameopt", "RFC2253", cwd=tmp_path
        ).stdout
        assert subject.strip() == f"subject=CN={name}"  # the broker's use_identity_as_username reads this


def test_the_broker_certificate_names_the_macs_lan_ip_and_hostname(tmp_path):
    pki.ensure(tmp_path, HOSTS)
    check = ["x509", "-in", "broker.crt", "-noout", "-checkip", "192.168.1.5", "-checkhost", "mac.local"]
    assert "NOT" not in openssl(*check, cwd=tmp_path).stdout
    assert (
        "does NOT match" in openssl("x509", "-in", "broker.crt", "-noout", "-checkip", "10.0.0.9", cwd=tmp_path).stdout
    )


def test_only_the_owner_can_reach_the_keys(tmp_path):
    d = tmp_path / "pki"
    pki.ensure(d, HOSTS)
    assert stat.S_IMODE(d.stat().st_mode) == 0o700
    assert {stat.S_IMODE(f.stat().st_mode) for f in d.iterdir()} == {0o600}


def test_each_core_gets_its_key_its_certificate_and_the_ca_in_der(tmp_path):
    pki.ensure(tmp_path, HOSTS)

    def same(kind, pem, der, *show):
        a = openssl(kind, "-in", pem, *show, cwd=tmp_path).stdout
        assert a and a == openssl(kind, "-in", der, "-inform", "DER", *show, cwd=tmp_path).stdout

    same("x509", "ca.crt", "ca.crt.der", "-noout", "-fingerprint")
    for core in ("eyes", "neck"):
        same("x509", f"{core}.crt", f"{core}.crt.der", "-noout", "-fingerprint")
        same("pkey", f"{core}.key", f"{core}.key.der", "-pubout")


def contents(d):
    return {f.name: f.read_bytes() for f in d.iterdir()}


def test_running_again_keeps_every_key_and_certificate(tmp_path):
    pki.ensure(tmp_path, HOSTS)
    first = contents(tmp_path)
    pki.ensure(tmp_path, HOSTS)
    assert contents(tmp_path) == first


def test_rotate_replaces_everything(tmp_path):
    pki.ensure(tmp_path, HOSTS)
    first = contents(tmp_path)
    pki.ensure(tmp_path, HOSTS, rotate=True)
    after = contents(tmp_path)
    assert after.keys() == first.keys() and all(after[f] != first[f] for f in first)


def test_a_new_lan_ip_reissues_only_the_broker(tmp_path):
    pki.ensure(tmp_path, HOSTS)
    first = contents(tmp_path)
    pki.ensure(tmp_path, ["192.168.1.77", "mac.local"])
    after = contents(tmp_path)
    assert {f for f in first if after[f] != first[f]} == {"broker.key", "broker.crt"}
    assert "NOT" not in openssl("x509", "-in", "broker.crt", "-noout", "-checkip", "192.168.1.77", cwd=tmp_path).stdout


def test_the_command_writes_under_home_and_names_this_mac(tmp_path):
    env = {**os.environ, "HOME": str(tmp_path)}  # never the real ~/.noggin
    subprocess.run([sys.executable, "-m", "noggin.pki"], cwd=ROOT, env=env, check=True, capture_output=True)
    d = tmp_path / ".noggin" / "pki"
    assert openssl("verify", "-CAfile", "ca.crt", "eyes.crt", cwd=d).returncode == 0
    names = openssl(
        "x509", "-in", "broker.crt", "-noout", "-checkhost", socket.gethostname(), "-checkip", "127.0.0.1", cwd=d
    )
    assert names.stdout.count(" does match") == 2


def test_git_ignores_keys_and_certificates_wherever_they_land():
    paths = ["eyes.key", "noggin/mac.key", "eyes/eyes.key.der", "ca.crt", "x/ca.crt.der", "broker.pem"]
    assert all(subprocess.run(["git", "check-ignore", "-q", p], cwd=ROOT).returncode == 0 for p in paths)
