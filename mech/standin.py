"""The Mech stand-in (#222): the Core's real program, boot.py and the files `make mpy` compiles, as .mpy the way
flash-usb puts them on the Core, run by the Core's MicroPython (mech/build/micropython, `make mech/build/micropython`)
with mech/core's machine, network and socket in place of the ESP32's. A folder is its filesystem; its stdin and stdout
are its USB serial, copied to and from a pty while the cable is in."""

import json
import os
import pty
import select
import shutil
import signal
import subprocess
import sys
import threading
import tty
from pathlib import Path

from noggin.core import MODULES, STAMP, stamp
from noggin.wifi import BEACON_PORT, COMMAND_PORT

REPO = Path(__file__).resolve().parent.parent
MICROPYTHON = REPO / "mech" / "build" / "micropython"
RESET = 128 + signal.SIGTERM  # mech/core/machine.py's reset, as the shell reports it: boot again


def mpy(src, dst, *opts):
    """src compiled for the Core (pyproject [tool.noggin]), as `make mpy` does."""
    subprocess.run([Path(sys.executable).parent / "mpy-cross", *opts, "-o", dst, src], check=True)


def program(dst, folder="eyes"):
    """The files `make mpy` builds, into dst, stamp.mpy too; folder: the source folder named in their bytecode, so two
    builds of the same program differ."""
    for m in MODULES:
        mpy(REPO / "eyes" / f"{m}.py", dst / f"{m}.mpy", "-s", f"{folder}/{m}.py")
    (dst / f"{STAMP}.py").write_text(stamp())
    mpy(dst / f"{STAMP}.py", dst / f"{STAMP}.mpy", "-s", f"{folder}/{STAMP}.py")
    (dst / f"{STAMP}.py").unlink()  # on the Core a .py would shadow its .mpy


class Mech:
    def __init__(self, root, token, beacon_port, command_port, networks=("home",), air=None, cable=False):
        """networks: the known ones in its wifi.json (synthetic passwords); air: the ones in range, {ssid: RSSI}."""
        self.root = root
        root.mkdir()
        program(root)
        shutil.copy(REPO / "eyes" / "boot.py", root)
        shutil.copytree(MICROPYTHON.parent / "lib", root / "lib")  # micropython-lib's hmac, mip's on the Core
        nets = [{"ssid": ssid, "password": "pw"} for ssid in networks]
        (root / "wifi.json").write_text(json.dumps({"networks": nets, "token": token}))
        self.move({"home": -50} if air is None else air)
        self.env = {
            **os.environ,
            "MICROPYPATH": f"lib:{REPO / 'mech' / 'core'}",
            "MECH_PORTS": f"{BEACON_PORT}:{beacon_port} {COMMAND_PORT}:{command_port}",  # mech/core/socket.py
        }
        self.log = root.parent / "core.log"  # its USB output and stderr: tracebacks, mech/core's notes
        self.cable, self.master, self.tty = cable, None, None
        if cable:
            self.master, self.slave = pty.openpty()
            tty.setraw(self.slave)  # no echo of the Core's output back into it before the service opens the port
            self.tty = os.ttyname(self.slave)
        self.power_on()

    def move(self, air):
        """The networks in range now, {ssid: RSSI}, swapped in whole (the Core reads it on every poll)."""
        (self.root / "air.new").write_text(json.dumps(air))
        os.replace(self.root / "air.new", self.root / "air.json")

    def power_on(self):
        """Boot, and boot again after every machine.reset, until power_off."""
        with open(self.log, "ab") as err:
            self.proc = subprocess.Popen(
                ["sh", "-c", f'while :; do "$0" boot.py; [ $? = {RESET} ] || exit; done', MICROPYTHON],
                cwd=self.root,
                env=self.env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=err,
                start_new_session=True,
            )
        threading.Thread(target=self._usb, args=(self.proc,), daemon=True).start()

    def power_off(self):
        os.killpg(self.proc.pid, signal.SIGKILL)
        self.proc.wait()

    def pull(self):
        """The cable out: the service's port goes dead; the Core runs on, its output unread."""
        self.cable = False

    def _usb(self, proc):
        """The Core's output to the log and, cable in, to the pty; what the service writes to the pty, to the Core."""
        assert proc.stdout and proc.stdin
        out, into = proc.stdout.fileno(), proc.stdin
        with open(self.log, "ab", buffering=0) as log:
            while True:
                if not self.cable and self.master is not None:
                    os.close(self.master)
                    os.close(self.slave)
                    self.master = None
                ready, _, _ = select.select([out] + ([self.master] if self.master is not None else []), [], [], 0.1)
                if out in ready:
                    data = os.read(out, 4096)
                    if not data:  # powered off
                        return
                    log.write(data)
                    if self.master is not None:
                        os.write(self.master, data)
                if self.master is not None and self.master in ready:
                    into.write(os.read(self.master, 4096))
                    into.flush()
