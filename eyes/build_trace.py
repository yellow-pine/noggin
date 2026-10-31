"""Bake real human eye movements (GazeBase, Griffith et al. 2021, CC BY 4.0) into eyes/gaze_trace.py.

Subject 1001, session 1, fetched with a byte range from the figshare zip (offsets valid for GazeBase v3,
file id 27039812). 1 kHz gaze in degrees of visual angle; blinks are NaN gaps; `lab` 2 marks saccades.
Outputs, all horizontal only (the Mech's eyes pan):
  THINK   video viewing (VD1), 60 s at 25 Hz, scaled to fill the eye travel, plus blink sample indices
  SCAN    horizontal saccade task (HSS), 4 s at 25 Hz, replayed by the attention gesture
  CALM    the calmest 6 s of the viewing session (lowest gaze variance), replayed by bored
  SACCADE real saccade shapes from the random-saccade task (RAN): progress 0..1 per 10 ms, by amplitude
Usage: .venv/bin/python eyes/build_trace.py"""

import csv
import subprocess
import zipfile
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE.parent / "docs" / "references" / "gazebase"
URL = "https://ndownloader.figshare.com/files/27039812"
RANGE = "19099-7312369"  # Round_1/Subject_1001.zip, raw deflate inside the outer zip
MEMBERS = {
    "VD1": "S1/S1_Video_1/S_1001_S1_VD1.csv",
    "HSS": "S1/S1_Horizontal_Saccades/S_1001_S1_HSS.csv",
    "RAN": "S1/S1_Random_Saccades/S_1001_S1_RAN.csv",
}
HZ, MAX_DEG, MIN_BLINK_MS = 25, 24.0, 50
SACCADE_AMPS = (10, 20, 25)
RATE = 500  # servo.RATE_DEG_S: the 9 g servo's rated slew; the traces must be followable


def clamp_rate(xs, dt_s, rate=RATE):
    """Limit each step to what the servo can slew in dt_s (later samples follow from the clamped position,
    as the real horn would); returns the clamped samples and how many were clamped."""
    out, n = [xs[0]], 0
    for x in xs[1:]:
        lim = rate * dt_s
        d = x - out[-1]
        if abs(d) > lim:
            d, n = (lim if d > 0 else -lim), n + 1
        out.append(out[-1] + d)
    return out, n


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    z = CACHE / "Subject_1001.zip"
    if not z.exists():
        raw = subprocess.run(["curl", "-sL", "-r", RANGE, URL], capture_output=True, check=True).stdout
        z.write_bytes(zlib.decompress(raw, -15))
    zf = zipfile.ZipFile(z)
    for _task, member in MEMBERS.items():
        out = CACHE / Path(member).name
        if not out.exists():
            out.write_bytes(zf.read(member))


def rows(task):
    return list(csv.DictReader((CACHE / Path(MEMBERS[task]).name).open()))


def good(r):
    return r["val"] in ("0", "0.0") and r["x"].lower() != "nan"


def resample(rows, hz=HZ, gain=1.0, max_deg=MAX_DEG, min_blink_ms=MIN_BLINK_MS, start_s=0, dur_s=None):
    """Horizontal gaze at hz, scaled and clamped, last good value held through gaps; blink sample indices."""
    step = 1000 // hz
    t0, t1 = start_s * 1000, None if dur_s is None else (start_s + dur_s) * 1000
    xs, blinks, gap_start = [], [], None
    for r in rows:
        t = int(float(r["n"]))
        if t < t0 or (t1 is not None and t >= t1):
            continue
        bad = not good(r)
        if bad and gap_start is None:
            gap_start = t
        if not bad and gap_start is not None:
            if t - gap_start >= min_blink_ms:
                blinks.append((gap_start - t0) // step)
            gap_start = None
        if (t - t0) % step == 0:
            xs.append(None if bad else float(r["x"]))
    last, out = 0.0, []
    for x in xs:
        if x is not None:
            last = max(-max_deg, min(max_deg, x * gain))
        out.append(last)
    return out, sorted(set(b for b in blinks if b < len(out)))


def fill_gain(rows, frac=0.9):
    """Gain so that the recording's 5th-95th percentile spans frac of the eye travel."""
    xs = sorted(float(r["x"]) for r in rows if good(r))
    span = max(1e-6, xs[int(len(xs) * 0.95)] - xs[int(len(xs) * 0.05)])
    return 2 * MAX_DEG * frac / span


def calmest(xs, hz=HZ, dur_s=6):
    """Start index of the dur_s window with the lowest variance (lazy, drifting gaze)."""
    n = dur_s * hz
    best, best_var = 0, None
    for i in range(0, len(xs) - n, hz):
        w = xs[i : i + n]
        m = sum(w) / n
        var = sum((v - m) ** 2 for v in w) / n
        if best_var is None or var < best_var:
            best, best_var = i, var
    return best


def saccades(rows, amps=SACCADE_AMPS):
    """Real horizontal saccade shapes: for each target amplitude the closest-amplitude saccade (30-120 ms),
    as progress 0..1 sampled every 10 ms from onset to 150 ms (so the post-saccadic correction is included)."""
    runs, cur = [], None
    for i, r in enumerate(rows):
        if r["lab"] == "2" and good(r):
            cur = cur or [i, i]
            cur[1] = i
        elif cur:
            runs.append(cur)
            cur = None
    found = {}
    for a in amps:
        best = None
        for s, e in runs:
            dur = e - s
            if not 30 <= dur <= 120 or e + 150 >= len(rows):
                continue
            x0, x1 = float(rows[s]["x"]), float(rows[e]["x"])
            amp = abs(x1 - x0)
            if amp < 3 or any(not good(rows[k]) for k in range(s, s + 151)):
                continue
            score = abs(amp - a)
            if best is None or score < best[0]:
                best = (score, s, x0, x1 - x0)
        if best:
            _, s, x0, d = best
            prof = [max(0.0, min(1.3, (float(rows[s + k]["x"]) - x0) / d)) for k in range(0, 151, 10)]
            found[a] = tuple(round(p, 2) for p in prof)
    return found


def main():
    fetch()
    vd1, hss, ran = rows("VD1"), rows("HSS"), rows("RAN")
    think, think_blinks = resample(vd1, gain=fill_gain(vd1))
    scan, _ = resample(hss, gain=fill_gain(hss), start_s=5, dur_s=4)
    c0 = calmest(think)
    calm = [v - sum(think[c0 : c0 + 6 * HZ]) / (6 * HZ) for v in think[c0 : c0 + 6 * HZ]]  # centred
    sac = saccades(ran)
    clamped = {}
    (think, clamped["think"]), (scan, clamped["scan"]), (calm, clamped["calm"]) = (
        clamp_rate(x, 1 / HZ) for x in (think, scan, calm)
    )
    for a, prof in sac.items():
        degs, clamped[f"saccade{a}"] = clamp_rate([p * a for p in prof], 0.01)
        sac[a] = tuple(round(d / a, 2) for d in degs)

    def enc(xs):
        return bytes(int(round(v * 2)) & 0xFF for v in xs)  # signed int8 half-degrees

    (HERE / "gaze_trace.py").write_text(
        "# Generated by build_trace.py from GazeBase subject 1001 session 1 (CC BY 4.0). Do not edit.\n"
        f"HZ = {HZ}\n"
        f"THINK = {enc(think)!r}\nTHINK_BLINKS = {tuple(think_blinks)}\n"
        f"SCAN = {enc(scan)!r}\n"
        f"CALM = {enc(calm)!r}\n"
        f"SACCADE = {sac!r}  # amplitude deg -> progress per 10 ms from onset\n"
    )
    print(
        f"think {len(think) / HZ:.0f} s {len(think_blinks)} blinks | scan {len(scan) / HZ:.0f} s | "
        f"calm {len(calm) / HZ:.0f} s "
        f"range {min(calm):.1f}..{max(calm):.1f} | saccades {sorted(sac)} | samples clamped to {RATE} deg/s: {clamped}"
    )


if __name__ == "__main__":
    main()
