"""Drop the Core to its REPL so mpremote can talk to it. The stock RC app (and our eye program)
ignore mpremote's quick Ctrl-C; a couple of Ctrl-Cs with a pause do the job.
Usage: python eyes/interrupt.py [reset]   (reset: then soft-reset with Ctrl-D so the program on the Core starts)"""

import glob
import sys
import time

import serial

ports = sorted(glob.glob("/dev/cu.usbmodem*"))
if not ports:
    sys.exit("no Core on USB")
for _attempt in range(15):  # the noggin service may still be letting go of the Link
    try:
        s = serial.Serial(ports[0], 115200, timeout=0.5, exclusive=True)
        break
    except (serial.SerialException, OSError):
        time.sleep(0.2)
else:
    sys.exit("Link busy: is the noggin service still running? (make stop)")
with s:
    for _ in range(3):
        s.write(b"\x03")
        time.sleep(0.4)
    time.sleep(0.6)
    s.write(b"\x02")
    time.sleep(0.3)  # friendly REPL
    print("Core at REPL on", ports[0], "" if b">>>" in s.read(500) else "(no prompt seen)")
    if "reset" in sys.argv[1:]:
        s.write(b"\x04")
        time.sleep(1.0)  # Ctrl-D: soft reset, boot.py runs
        print("Core reset:", s.read(200).decode(errors="replace").strip() or "(no output yet)")
