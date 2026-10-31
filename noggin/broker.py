"""Mosquitto, the Link's MQTT broker (#157), as a child of the noggin service, so it needs no launchd job of its own.
Mutual TLS on 8883 with our CA in ~/.noggin/pki: a client without a certificate from it is refused, and the
certificate's CN is the username the access rules name (https://mosquitto.org/man/mosquitto-conf-5.html).
The Mac (CN mac) reads and writes all of noggin/#; each Core reads only its own cmd and flash topics and writes only
its own status. Mosquitto logs to stderr, which is the service's log."""

import shutil
import subprocess
import time
from pathlib import Path

PKI = Path("~/.noggin/pki").expanduser()
PKI_FILES = ("ca.crt", "broker.crt", "broker.key")
SBIN = "/opt/homebrew/sbin:/usr/local/sbin:/usr/sbin"  # Homebrew and apt put mosquitto in sbin; launchd's PATH lacks it
RESTART_SECONDS = 2.0  # so a broker that dies at once (port taken, bad key) doesn't spin the service loop


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def acl(cores):
    rules = ["user mac", "topic readwrite noggin/#"]
    for c in cores:
        rules += ["", f"user {c}", f"topic read noggin/{c}/cmd", f"topic read noggin/{c}/flash/#"]
        rules += [f"topic write noggin/{c}/status"]
    return "\n".join(rules) + "\n"


def conf(pki, port):
    return f"""persistence false
allow_anonymous false
acl_file {pki / "acl"}
log_timestamp_format %H:%M:%S
listener {port}
cafile {pki / "ca.crt"}
certfile {pki / "broker.crt"}
keyfile {pki / "broker.key"}
require_certificate true
use_identity_as_username true
"""


class Broker:
    def __init__(self, cores, pki=PKI, port=8883):
        self.cores, self.pki, self.port = cores, pki, port
        self.proc, self.started = None, 0.0

    def start(self):
        """Write the config beside the certificates and run Mosquitto; skipped, with a log line, without the PKI or
        the binary (a service restart picks up either once it is there)."""
        missing = [f for f in PKI_FILES if not (self.pki / f).exists()]
        exe = shutil.which("mosquitto") or shutil.which("mosquitto", path=SBIN)
        if missing or not exe:
            return log("broker skipped:", f"no {', '.join(missing)} in {self.pki}" if missing else "no mosquitto")
        (self.pki / "acl").write_text(acl(self.cores))
        (self.pki / "mosquitto.conf").write_text(conf(self.pki, self.port))
        self.proc = subprocess.Popen([exe, "-c", str(self.pki / "mosquitto.conf")], stdin=subprocess.DEVNULL)
        self.started = time.monotonic()
        log("broker on", self.port, "pid", self.proc.pid)

    def poll(self):
        """Restart Mosquitto if it exited (at most every RESTART_SECONDS)."""
        if self.proc is None or self.proc.poll() is None or time.monotonic() - self.started < RESTART_SECONDS:
            return
        log("broker exited", self.proc.returncode)
        self.start()

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(5)
        self.proc = None
