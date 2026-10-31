# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
# noggin: replaces the stock boot.py. Reads one command per line on USB serial;
# with wifi.json present, also beacons and serves the same commands over UDP (eyes/wifi.py).
import select
import sys
import time

import wifi

from eyes import Eyes

e = Eyes()
poll = select.poll()
poll.register(sys.stdin, select.POLLIN)
link = wifi.start(e.handle_line)
e.handle_line("rest")
print("noggin ready")
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
