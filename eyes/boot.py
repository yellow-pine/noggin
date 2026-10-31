# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
# noggin: replaces the stock boot.py. Reads one command per line on USB serial;
# with wifi.json present, also beacons and serves the same commands over UDP (eyes/wifi.py).
# After a Wi-Fi flash (flash.trial lists the files it swapped in) the new program has 10 s to reach `noggin ready`,
# or their .bak files go back and the Core reboots. This file is the fallback, so it only ever changes over USB.
import os
import select
import sys
import time

import machine


def restore(_timer=None):
    """Put back the .bak of every file the last Wi-Fi flash swapped in, then reboot onto them."""
    with open("flash.trial") as f:
        names = f.read().split()
    for name in names:
        if name + ".bak" in os.listdir():
            try:
                os.remove(name)
            except OSError:
                pass
            os.rename(name + ".bak", name)
    os.remove("flash.trial")
    machine.reset()


trial = "flash.trial" in os.listdir()
if trial:
    guard = machine.Timer(0)
    guard.init(mode=machine.Timer.ONE_SHOT, period=10000, callback=restore)
try:
    import wifi

    from eyes import Eyes

    e = Eyes()
    link = wifi.start(e.handle_line)
    e.handle_line("rest")
except KeyboardInterrupt:  # Ctrl-C from eyes/interrupt.py: USB takes over, nothing is put back
    if trial:
        guard.deinit()
    raise
except Exception:
    if trial:
        restore()
    raise
if trial:
    guard.deinit()
    os.remove("flash.trial")
print("noggin ready")
poll = select.poll()
poll.register(sys.stdin, select.POLLIN)
while True:
    if poll.poll(50):
        line = sys.stdin.readline()
        if line.strip() == "ping":
            print("ok")
        else:
            e.handle_line(line)
    now = time.ticks_ms()
    if link:
        link.poll(now)
    e.tick(now)
