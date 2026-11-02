"""`just live-check` (#29): both Cores on the Mech, each flashed over USB and over Wi-Fi, then probed on Wi-Fi with the
cable in, with the cable out and after the Mech was off, the results appended to docs/build/live-check.md. You plug,
unplug and switch when asked; the rest runs itself through just and the noggin CLI, and reads noggin.log for the acks.
Run from the checkout the noggin service runs from (`just start`)."""

import subprocess
import time
from datetime import date
from pathlib import Path

from noggin.core import CORES
from noggin.wifi import STALE

REPO = Path(__file__).resolve().parent.parent
PAGE = REPO / "docs" / "build" / "live-check.md"
CLI = "noggin/noggin"
PROBE = "wink 3"  # short, and both Cores play it (each its own servos)
BACK = 90  # s for a beacon after a flash over USB or a power-on: the Core boots, joins the Wi-Fi, beacons every 2 s
ACKS = 7  # s for the probe's acks: up to 3 s of tries per Core, one Core after the other (ADR 0005)


def links(status):
    """`noggin status` as {name: its Link}, for each Core and the noggin service ("0.3.0 abc1234")."""
    out = {}
    for line in status.splitlines():
        name, _, rest = line.partition(" ")
        if name in CORES:
            out[name] = rest
        elif line.startswith("noggin service "):
            out["service"] = line.removeprefix("noggin service ")
    return out


def run(sh, ask, log, clock=time.monotonic, wait=time.sleep):
    """The live check: [(step, core, "ok" or "FAIL", detail)]. sh(cmd) -> (exit code, output), run in the repo;
    ask(prompt) returns once you did what it says; log is noggin.log."""
    rows = []

    def row(step, core, ok, detail):
        rows.append((step, core, "ok" if ok else "FAIL", detail))
        print(*rows[-1], sep="  |  ", flush=True)

    def status():
        return links(sh(f"{CLI} status")[1])

    def on_wifi(s, core):
        return s.get(core, "").startswith("wifi ") and s[core].endswith(f" program {s.get('service')}")

    def until(done, seconds):
        start = clock()
        while not done(s := status()) and clock() - start < seconds:
            wait(1)
        return s, round(clock() - start)

    def probe(step, link=lambda s, core: s.get(core)):
        """Both Cores' Links (as link words them) and an ack for the probe gesture, each over Wi-Fi."""
        seen = log.stat().st_size
        sh(f"{CLI} {PROBE}")
        wait(ACKS)
        with log.open() as f:
            f.seek(seen)
            new = f.read().splitlines()
        s = status()
        for core in CORES:
            acked = any(f"sent {core} ['{PROBE}']" in line for line in new)
            said = [line.split(" ", 1)[1] for line in new if f" {core} " in line] or ["nothing logged"]
            row(
                step, core, acked and on_wifi(s, core), f"{link(s, core)}; " + (f"{PROBE} acked" if acked else said[-1])
            )

    if sh(f"{CLI} status")[0]:
        raise SystemExit("the noggin service is not running: just start")
    for core in CORES:
        ask(f"Plug the {core} Core's cable into the Mac, every other cable out. Mech on. Return when done: ")
        print(f"flashing {core} over USB ...", flush=True)
        code, out = sh("just flash-usb")  # stops the noggin service for the cable
        sh("just start")
        s, took = until(lambda s, core=core: on_wifi(s, core), BACK)
        ok = on_wifi(s, core)
        detail = s[core] if ok else f"{s.get(core)} {took} s after the flash"
        row("USB flash", core, ok and not code, (out.strip().splitlines() or ["no output"])[-1] if code else detail)
    for core in CORES:
        print(f"flashing {core} over Wi-Fi ...", flush=True)
        code, out = sh(f"{CLI} flash {core}")
        row("Wi-Fi flash", core, code == 0, out.strip())
    probe("Wi-Fi, cable in")
    ask("Unplug every cable from the Mech. Return when done: ")
    probe("Wi-Fi, cable out")
    ask(f"Switch the Mech off. Return when done, then wait (up to {STALE + 10:.0f} s): ")
    s, took = until(lambda s: all(s.get(c) == "offline" for c in CORES), STALE + 10)
    for core in CORES:
        row("Mech off", core, s.get(core) == "offline", f"{s.get(core)} after {took} s")
    ask(f"Switch the Mech on. Return when done, then wait (up to {BACK} s): ")
    _, took = until(lambda s: all(on_wifi(s, c) for c in CORES), BACK)
    probe(
        "Mech back on",
        lambda s, core: (
            f"back in {took} s: {s[core]}" if on_wifi(s, core) else f"{s.get(core)} {took} s after the switch"
        ),
    )
    return rows


def write(rows, page, heading):
    """The rows as a table under a new `## heading` at the end of page."""
    cell = lambda text: str(text).replace("|", "\\|")  # noqa: E731
    table = "".join(f"| {' | '.join(map(cell, r))} |\n" for r in rows)
    with page.open("a") as f:
        f.write(f"\n## {heading}\n\n| Step | Core | Result | Detail |\n| --- | --- | --- | --- |\n{table}")


def sh(cmd):
    p = subprocess.run(cmd.split(), cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


if __name__ == "__main__":
    rows = run(sh, lambda prompt: input(prompt), REPO / "noggin.log")
    write(rows, PAGE, f"{date.today()}, noggin service {links(sh(f'{CLI} status')[1]).get('service')}")
    failed = sum(r[2] == "FAIL" for r in rows)
    print(f"{len(rows) - failed} ok, {failed} failed: written to {PAGE.relative_to(REPO)}")
    raise SystemExit(1 if failed else 0)
