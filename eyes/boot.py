# noggin: replaces Bambu's stock boot.py. Reads one command per line on USB serial.
import select
import sys
import time

from eyes import Eyes

e = Eyes()
poll = select.poll()
poll.register(sys.stdin, select.POLLIN)
e.handle_line("rest")
print("noggin ready")
while True:
    if poll.poll(50):
        line = sys.stdin.readline()
        if line.strip() == "ping":
            print("ok")
        else:
            e.handle_line(line)
    e.tick(time.ticks_ms())
