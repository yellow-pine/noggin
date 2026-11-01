"""The Mech stand-in (#222): the Core's real program, boot.py and the files `make mpy` compiles, as .mpy the way
flash-usb puts them on the Core, run by the Core's MicroPython (mech/build/micropython, `make mech/build/micropython`)
with mech/core's machine, network and socket in place of the ESP32's. A folder is its filesystem; its stdin and stdout
are its USB serial, relayed to a pty while the cable is in."""

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

from noggin.service import FLASH_FILES

REPO = Path(__file__).resolve().parent.parent
MICROPYTHON = REPO / "mech" / "build" / "micropython"
RESET = 128 + signal.SIGTERM  # mech/core/machine.py's reset, as the shell reports it: boot again


def mpy(src, dst):
    """src compiled for the Core (pyproject [tool.noggin]), as `make mpy` does."""
    subprocess.run([Path(sys.executable).parent / "mpy-cross", "-o", dst, src], check=True)


class Mech:
    def __init__(self, root, token, beacon_port, command_port, networks=("home",), air=None, cable=False):
        """networks: the known ones in its wifi.json (synthetic passwords); air: the ones in range, {ssid: RSSI}."""
        self.root = root
        root.mkdir()
        for f in FLASH_FILES:
            mpy(REPO / "eyes" / f.replace(".mpy", ".py"), root / f)
        shutil.copy(REPO / "eyes" / "boot.py", root)
        shutil.copytree(MICROPYTHON.parent / "lib", root / "lib")  # micropython-lib's hmac, mip's on the Core
        nets = [{"ssid": ssid, "password": "pw"} for ssid in networks]
        (root / "wifi.json").write_text(json.dumps({"networks": nets, "token": token}))
        self.move({"home": -50} if air is None else air)
        self.env = {
            **os.environ,
            "MICROPYPATH": f"lib:{REPO / 'mech' / 'core'}",
            "MECH_BEACON_PORT": str(beacon_port),
            "MECH_COMMAND_PORT": str(command_port),
        }
        self.log = root.parent / "core.log"  # its USB output and stderr: tracebacks, mech/core's notes
        self.master = self.tty = None
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
        self.tty = None

    def _usb(self, proc):
        """The Core's output to the log and, cable in, to the pty; what the service writes to the pty, to the Core."""
        out = proc.stdout.fileno()  # pyright: ignore[reportOptionalMemberAccess]
        with open(self.log, "ab", buffering=0) as log:
            while True:
                if self.tty is None and self.master is not None:
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
                    proc.stdin.write(os.read(self.master, 4096))  # pyright: ignore[reportOptionalMemberAccess]
                    proc.stdin.flush()  # pyright: ignore[reportOptionalMemberAccess]
