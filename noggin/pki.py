"""Unused: the Link is signed UDP and MQTT was rejected (docs/adr/0005, update 2026-11-01); kept until a Core holds TLS.
The local CA #157 planned for the Link: keys and certificates for ca, broker, mac, eyes and neck, EC P-256, by the
openssl CLI.

`python -m noggin.pki [--rotate]` fills ~/.noggin/pki (mode 700, files 600). The Cores would get DER copies over USB
(a setup wizard step, removed with the MQTT rejection). Certificates are valid from the moment they are made, and the
Core's mbedTLS checks the dates (CONFIG_MBEDTLS_HAVE_TIME_DATE, MicroPython ports/esp32/boards/sdkconfig.base), so a
Core must set its clock (NTP) before its first handshake: it boots at 2000-01-01."""

import ipaddress
import os
import socket
import subprocess
import sys
from pathlib import Path

from noggin.core import CORES

PKI = Path.home() / ".noggin" / "pki"
CNF = Path(__file__).with_name("pki.cnf")
DAYS = "3650"


def _openssl(*args, cwd):
    r = subprocess.run(["openssl", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"openssl {args[0]}: {r.stderr.strip()}")
    return r.stdout


def _issue(d, name, profile, *extra):
    signer = ["-CA", "ca.crt", "-CAkey", "ca.key"] if profile != "ca" else []
    _openssl(
        "req", "-x509", "-config", str(CNF), "-extensions", profile,
        "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-noenc", "-keyout", f"{name}.key",
        "-subj", f"/CN={name}", "-days", DAYS, *signer, *extra, "-out", f"{name}.crt", cwd=d,
    )  # fmt: skip


def _san(hosts):
    return "subjectAltName=" + ",".join(f"IP:{h}" if _is_ip(h) else f"DNS:{h}" for h in hosts)


def _is_ip(h):
    try:
        ipaddress.ip_address(h)
        return True
    except ValueError:
        return False


def _have(d, name):
    return (d / f"{name}.key").exists() and (d / f"{name}.crt").exists()


def _names(d, hosts):
    checks = [a for h in hosts for a in ("-checkip" if _is_ip(h) else "-checkhost", h)]
    r = subprocess.run(
        ["openssl", "x509", "-in", "broker.crt", "-noout", *checks], cwd=d, capture_output=True, text=True
    )
    return r.stdout.count(" does match") == len(hosts)  # the exit code on a mismatch differs between OpenSSL 3 and 4


def ensure(d: Path, hosts, rotate=False):
    """Make whatever is missing; keep what is there (the Cores hold copies), unless rotate."""
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)  # before any key is written; mkdir's mode is cut by the umask
    new_ca = rotate or not _have(d, "ca")
    if new_ca:
        _issue(d, "ca", "ca")
    if new_ca or not _have(d, "broker") or not _names(d, hosts):  # a new LAN IP (DHCP) needs a new broker certificate
        _issue(d, "broker", "server", "-addext", _san(hosts))
    for name in ("mac", *CORES):
        if new_ca or not _have(d, name):
            _issue(d, name, "client")
    # the Cores take DER: no PEM parsing on the C3, and smaller files
    _openssl("x509", "-in", "ca.crt", "-outform", "DER", "-out", "ca.crt.der", cwd=d)
    for core in CORES:
        _openssl("x509", "-in", f"{core}.crt", "-outform", "DER", "-out", f"{core}.crt.der", cwd=d)
        _openssl("pkey", "-in", f"{core}.key", "-outform", "DER", "-out", f"{core}.key.der", cwd=d)
    for f in d.iterdir():
        os.chmod(f, 0o600)


def hosts():
    """The names the broker answers to: the LAN IP and hostname (the Cores), loopback (the noggin service)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("192.0.2.1", 9))  # sends nothing: only picks the interface of the default route
        ip = s.getsockname()[0]
    return [ip, socket.gethostname(), "127.0.0.1", "localhost"]


if __name__ == "__main__":
    if not _openssl("version", cwd=None).startswith("OpenSSL"):  # macOS's /usr/bin/openssl is LibreSSL: no req -CA
        sys.exit("noggin/pki.py needs OpenSSL 3 or later on PATH (brew install openssl)")
    ensure(PKI, hosts(), rotate="--rotate" in sys.argv[1:])
    print(PKI)
