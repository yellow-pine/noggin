# noggin eye program for the Core (ESP32-C3, MicroPython).
# Plays named gestures and background modes (thinking, exercise) on four servos.
# Servos stay powered: released, the lids and eyes fall under gravity (gravity beats the smooth linkages).
# Calibration lives in self.cal: defaults below, overridden live by `set key value`
# lines that the noggin service pushes from eyes/calibration.json.
# Importable on CPython for tests (machine is stubbed there).
import json
import time

from machine import PWM, Pin  # pyright: ignore[reportMissingImports]

try:
    from time import sleep_ms  # pyright: ignore[reportAttributeAccessIssue]
except ImportError:  # CPython

    def sleep_ms(ms):
        time.sleep(ms / 1000)


try:
    import gaze_trace  # real human eye movements (GazeBase): saccade shapes, a scan, a viewing session

    TRACE_BLINKS = set(gaze_trace.THINK_BLINKS)
except ImportError:
    gaze_trace = None


# called between a gesture's steps: wifi.start hooks the Link in, so it is served while a gesture plays (#205)
between_steps = None


def wait(ms):
    """sleep_ms in steps of at most 20 ms, between_steps() after each: beacons and acks go out while a gesture plays."""
    while ms > 0:
        sleep_ms(min(ms, 20))
        ms -= 20
        if between_steps:
            between_steps()


def _s8(v):
    return (v - 256 if v > 127 else v) / 2  # trace bytes: signed int8 half-degrees


# shield port 1..4 -> GPIO 3,2,1,0; core.json "ports" (port -> servo name) picks the GPIO per name, defaults below
PORT_GPIO = {"1": 3, "2": 2, "3": 1, "4": 0}
L_LID, L_EYE, R_LID, R_EYE = 3, 2, 1, 0
NAME = {L_LID: "l_lid", L_EYE: "l_eye", R_LID: "r_lid", R_EYE: "r_eye"}
LIDS, EYES = (L_LID, R_LID), (L_EYE, R_EYE)
EYE_CENTER = 90
LID_OPEN_FULL, LID_CLOSED = 1.0, 0.0
SLEW = 428  # deg/s, the servo's rated slew at 4.8 V (eyes/servo.py, not flashed): no move asks for more
OVER = 0.05  # toon overshoot past a lid level, then settle (docs/research/2026-11-01-toon-eyes.md)
# glide's curves (f 0..1 of the time -> 0..1 of the way) and their steepest slope, for the slew guard
EASE = {
    "": (lambda f: f, 1),
    "in": (lambda f: f * f, 2),  # slow in: a lid falling shut
    "out": (lambda f: 1 - (1 - f) ** 2, 2),  # slow out: a lid reopening
    "io": (lambda f: f * f * (3 - 2 * f), 1.5),  # both: a settle
}


def servo_map():
    """Servo name -> GPIO from core.json, or the defaults without the file."""
    try:
        with open("core.json") as f:
            return {name: PORT_GPIO[port] for port, name in json.load(f)["ports"].items()}
    except (OSError, KeyError, ValueError):
        return {name: pin for pin, name in NAME.items()}


# Fallback values (#213's, 2026-11-01); eyes/calibration.json is the source of truth (retuned since, #255).
# Each servo has exact end angles; everything else derives from them: an eye's straight-ahead is the average
# of its two ends, lid levels are fractions (0 closed .. 1 open) along a lid's closed, rest and open points.
# Lid positions are in one shared frame, the right lid servo's degrees (lo closed, hi open): the lid servos are
# mounted mirror-image, so the same numbers fit both lids and the Core writes 180 - a to the MIRRORED servo.
# The lid bars make equal servo steps unequal lid steps, so each lid has a third point, where it sits at
# lid_rest, and the map is straight from closed to rest and from rest to open.
# Lid ends sit inside the mechanical stops: the clutch servos slip (and decalibrate) when stalled.
MIRRORED = (L_LID,)


def mirror(pin, a):
    """Shared lid frame <-> servo degrees (the same map both ways)."""
    return 180 - a if pin in MIRRORED else a


DEFAULT_CAL = {
    "l_lid_lo": 44,
    "l_lid_rest": 67.8,
    "l_lid_hi": 129,
    "r_lid_lo": 44,
    "r_lid_rest": 67.8,
    "r_lid_hi": 129,
    "l_eye_lo": 58,
    "l_eye_hi": 118,
    "r_eye_lo": 58,
    "r_eye_hi": 118,
    "lid_rest": 0.28,
    "lid_think": 0.16,
    "lid_closed": 0.10,
    "lid_open": 0.95,
    "think_trace": 0,  # 1: replay the GazeBase recording while thinking instead of synthetic drift
}


def _pulse_ns(angle):
    return int((angle * 102 / 180 + 25) * 20_000_000 / 1023)  # stock bbl.servos 10-bit duty at 50 Hz, unquantised


class Eyes:
    def __init__(self):
        self.cal = dict(DEFAULT_CAL)
        self.gpio = servo_map()
        self.pwm = {}
        self.pos = {}
        self.mode = "rest"
        self.next_drift = 0
        self.next_blink = 0
        self.think_side = 1
        self.think_start = None
        self.trace_i = -1
        self.until = 0
        self.rand = 12345

    # --- calibration ------------------------------------------------------
    def range(self, pin):
        """The servo's (low, high) degrees."""
        lo, hi = mirror(pin, self.cal[NAME[pin] + "_lo"]), mirror(pin, self.cal[NAME[pin] + "_hi"])
        return min(lo, hi), max(lo, hi)

    def _lid_shared(self, pin, f):
        """A lid level (0 closed .. 1 open) in the shared frame: straight closed..rest, then rest..open."""
        name, r = NAME[pin], self.cal["lid_rest"]
        lo, rest, hi = self.cal[name + "_lo"], self.cal[name + "_rest"], self.cal[name + "_hi"]
        f = min(1.0, max(0.0, f))
        if f < r:
            return lo + (rest - lo) * f / r
        return rest + (hi - rest) * (f - r) / (1 - r) if r < 1 else rest

    def _lid_angle(self, pin, f):
        return mirror(pin, self._lid_shared(pin, f))

    def _eye_angle(self, pin, angle):
        """Gesture angles are written around EYE_CENTER; the eye's real centre is the average of its ends."""
        lo, hi = self.range(pin)
        return (lo + hi) / 2 + (angle - EYE_CENTER)

    # --- servo primitives -------------------------------------------------
    def set(self, targets):
        """targets are keyed by the default pin; the servo map says which GPIO (if any) carries that name here."""
        for pin, angle in targets.items():
            gpio = self.gpio.get(NAME[pin])
            if gpio is None:  # a servo this Core does not carry (neck Core): skipped
                continue
            lo, hi = self.range(pin)
            angle = min(hi, max(lo, angle))
            if gpio not in self.pwm:
                self.pwm[gpio] = PWM(Pin(gpio), freq=50)
            self.pwm[gpio].duty_ns(_pulse_ns(angle))
            self.pos[pin] = angle

    def glide(self, ms, targets, step=20, ease=""):
        """Move along an EASE curve over ms, in more steps when the servo could not keep up at SLEW."""
        start = {
            p: self.pos.get(
                p, self._eye_angle(p, EYE_CENTER) if p in EYES else self._lid_angle(p, self.cal["lid_rest"])
            )
            for p in targets
        }
        curve, peak = EASE[ease]
        span = max(abs(targets[p] - start[p]) for p in targets)
        n = max(1, ms // step, int(peak * span * 1000 / (SLEW * step)) + 1)
        for i in range(1, n + 1):
            f = curve(i / n)
            self.set({p: start[p] + (targets[p] - start[p]) * f for p in targets})
            wait(step)

    def release(self):
        for p in self.pwm.values():
            p.deinit()
        self.pwm.clear()

    def lids(self, f, ms=0, ease="", pins=LIDS, over=0.0):
        """Lids to level f; with `over`, ease out to f + over first, then settle back in 100 ms."""
        if over:
            self.lids(f + over, ms, "out", pins)
            ms, ease = 100, "io"
        t = {p: self._lid_angle(p, f) for p in pins}
        self.glide(ms, t, ease=ease) if ms else self.set(t)

    def eyes(self, angle, ms=0):
        t = {p: self._eye_angle(p, angle) for p in EYES}
        self.glide(ms, t) if ms else self.set(t)

    def _side(self):
        self.rand = (self.rand * 1103515245 + 12345) & 0x7FFFFFFF
        return 1 if self.rand & 1 else -1

    # Toon timing (#258, docs/research/2026-11-01-toon-eyes.md): anticipation, slow in and slow out, holds, overshoot
    # and settle. Saccades keep real human shapes (docs/research/2026-10-31-natural-eye-motion.md).
    def blink(self, level=None, hold=80, shut=None):
        """A tiny lift, ease-in close, hold shut, ease-out reopen a little past the level, settle. From lid_rest:
        40 + 160 + 80 + 240 + 100 ms."""
        level = self.cal["lid_rest"] if level is None else level
        over = min(OVER, self.cal["lid_open"] - level)  # never past lid_open, by the open stop
        self.lids(level + over, 40)
        self.lids(self.cal["lid_closed"] if shut is None else shut, 160, "in")
        wait(hold)
        self.lids(level, 240, over=over)

    def saccade(self, angle):
        """Move the eyes along a real saccade's velocity profile (GazeBase, nearest amplitude), undershoot
        and correction included. Without a trace: ~93% step, pause, corrective step."""
        cur = self.pos.get(L_EYE, self._eye_angle(L_EYE, EYE_CENTER)) - self._eye_angle(L_EYE, 0)
        d = angle - cur
        if gaze_trace is None or abs(d) < 2:
            self.eyes(cur + d * 0.93)
            wait(120)
            self.eyes(angle)
            wait(60)
            return
        prof = gaze_trace.SACCADE[min(gaze_trace.SACCADE, key=lambda a: abs(a - abs(d)))]
        jump = max(prof[k] - (prof[k - 1] if k else 0) for k in range(len(prof)))
        dt = max(10, int(jump * abs(d) * 1000 / SLEW) + 1)  # a big saccade's samples spaced out to the slew
        for f in prof:
            self.eyes(cur + d * f)
            wait(dt)
        self.eyes(angle)

    def replay(self, samples, blinks=()):
        """Play a 25 Hz gaze clip around centre, each sample's move capped at what the servo slews in a sample."""
        lim = SLEW / gaze_trace.HZ  # pyright: ignore[reportOptionalMemberAccess]
        for i in range(len(samples)):
            cur = self.pos.get(L_EYE, self._eye_angle(L_EYE, EYE_CENTER)) - self._eye_angle(L_EYE, 0)
            self.eyes(cur + max(-lim, min(lim, EYE_CENTER + _s8(samples[i]) - cur)))
            if i in blinks:
                self.blink(level=self.cal["lid_think"])
            wait(1000 // gaze_trace.HZ)  # pyright: ignore[reportOptionalMemberAccess]

    def rest_pose(self):
        self.lids(self.cal["lid_rest"], 200)
        self.eyes(EYE_CENTER, 200)

    # --- gestures ----------------------------------------------------------
    def eureka(self, i):
        """Surprise, a toon take: lids squash, pop wide, eyes dart aside, a moving hold, back to centre, double blink,
        lids ease to rest past it and settle."""
        side = self._side()
        amp, hold = {1: (12, 300), 2: (22, 550), 3: (25, 800)}[i]
        wide = self.cal["lid_open"] - 0.15  # the moving hold's end, out of the open stop's margin (test_stall.py)
        self.lids(self.cal["lid_think"], 100, "io")  # anticipation
        wait(60)
        self.lids(self.cal["lid_open"])  # AU5: the take, as a step at the servo's full slew
        self.saccade(EYE_CENTER + side * amp)
        self.lids(wide, hold, "io")  # a moving hold: the stare relaxes a little
        if i == 3:
            self.saccade(EYE_CENTER - side * amp)
            wait(500)  # double-take
        self.saccade(EYE_CENTER)
        self.blink(level=wide)
        if i >= 2:
            wait(200)
            self.blink(level=wide)
        self.lids(self.cal["lid_rest"], 300, over=-0.04)

    def attention(self, i):
        """Needs you: half lids, two slow pursuit sweeps (~40 deg/s), centre, lids open past rest, settle, one blink."""
        self.lids(self.cal["lid_think"], 200, "io")
        if gaze_trace is not None:  # a real person scanning left-right (HSS task)
            self.replay(gaze_trace.SCAN)
        else:
            self.eyes(EYE_CENTER - 25, 600)
            for _ in range(2):
                self.eyes(EYE_CENTER + 25, 1250)
                self.eyes(EYE_CENTER - 25, 1250)
        self.saccade(EYE_CENTER)
        self.lids(self.cal["lid_rest"], 240, over=OVER)
        wait(200)
        self.blink()

    def bored(self, i):
        """Drowsy: lids droop, lazy real gaze drift, slow heavy blinks (lids falling shut, slow in), one long closure,
        settle. No overshoot: heavy lids."""
        droop = 0.35 * self.cal["lid_rest"] / 0.28
        self.lids(droop, 500, "io")
        if gaze_trace is not None:  # the calmest 6 s of a real viewing session, with heavy blinks on top
            calm, n = gaze_trace.CALM, len(gaze_trace.CALM)
            for k, (blink_at, hold) in enumerate(((n // 4, 500), (n // 2, 500), (3 * n // 4, 1500))):
                start = 0 if k == 0 else [n // 4, n // 2][k - 1]
                for j in range(start, blink_at):
                    self.eyes(EYE_CENTER + _s8(calm[j]))
                    wait(1000 // gaze_trace.HZ)
                self.lids(self.cal["lid_closed"], 200 if hold < 1500 else 250, "in")
                wait(hold)
                self.lids(droop if hold < 1500 else self.cal["lid_rest"], 900 if hold < 1500 else 1200, "out")
        else:
            self.eyes(EYE_CENTER - 6, 800)
            for _ in range(2):
                self.lids(self.cal["lid_closed"], 200, "in")
                wait(500)
                self.lids(droop, 900, "out")
                wait(700)
            self.lids(self.cal["lid_closed"], 250, "in")
            wait(1500)  # the stall-time rule (test_stall.py) caps closures at 2 s, ramps included
            self.lids(self.cal["lid_rest"], 1200, "out")
        self.saccade(EYE_CENTER)

    def wince(self, i):
        """A flinch (no anticipation): both lids snap shut, eyes twitch (small real saccades), hold the squeeze, reopen
        fast past rest, hold, settle."""
        self.lids(self.cal["lid_closed"])
        for a in (4, -4, 3):
            self.saccade(EYE_CENTER + a)
        self.saccade(EYE_CENTER)
        wait(150)
        self.lids(self.cal["lid_rest"] + 0.1, 200, "out")
        wait(150)
        self.lids(self.cal["lid_rest"], 300, "io")

    def wink(self, i):
        """Toon wink: eyes glance toward that side, the lid lifts a touch, closes over 200 ms (slow in) as the other
        lid squints 20%, holds 350 ms, both reopen past rest and settle.
        1 = mech's left lid (viewer's right), 2 = mech's right lid (viewer's left), 3 = random."""
        pin = {1: L_LID, 2: R_LID}.get(i, L_LID if self._side() > 0 else R_LID)
        other, rest = R_LID if pin == L_LID else L_LID, self.cal["lid_rest"]
        self.saccade(EYE_CENTER + (8 if pin == L_LID else -8))
        self.lids(rest + OVER, 40, pins=(pin,))  # anticipation
        shut = {pin: self._lid_angle(pin, self.cal["lid_closed"]), other: self._lid_angle(other, 0.8 * rest)}
        self.glide(200, shut, ease="in")
        wait(350)
        self.lids(rest, 240, over=OVER)
        wait(150)
        self.saccade(EYE_CENTER)

    GESTURES = {"eureka": eureka, "attention": attention, "bored": bored, "wince": wince, "wink": wink}

    # --- commands ----------------------------------------------------------
    def handle_line(self, line):
        parts = line.strip().split()
        if not parts:
            return
        cmd, args = parts[0], parts[1:]
        if cmd in ("thinking", "rest"):
            self.mode = cmd
            if cmd == "rest":
                self.rest_pose()
            else:  # a small look the other way first (anticipation), then a gaze-evoked blink with the saccade aside
                self.think_side = self._side()
                self.eyes(EYE_CENTER - self.think_side * 4, 80)
                self.lids(self.cal["lid_closed"])
                self.saccade(EYE_CENTER + self.think_side * 18)
                self.lids(self.cal["lid_think"], 240, over=OVER)
                self.next_drift = 0
                self.next_blink = 0
                self.think_start = None
                self.trace_i = -1
        elif cmd == "release":  # unpower (e.g. muted overnight); next command re-powers
            self.release()
        elif cmd == "set" and len(args) == 2 and args[0] in self.cal:
            self.cal[args[0]] = type(DEFAULT_CAL[args[0]])(float(args[1]))
        elif cmd == "pose" and len(args) in (2, 4):  # pose lids <0-1> | eyes <angle> | both; holds
            for key, val in zip(args[::2], args[1::2]):
                if key == "lids":
                    self.lids(float(val), 150)
                elif key == "eyes":
                    self.eyes(float(val), 150)
        elif cmd == "exercise" and len(args) == 1:  # run-in: smooth mid-range cycling, never near a stop
            self.mode = "exercise"
            self.until = None
            self.minutes = float(args[0])
            self.next_drift = 0
        elif cmd in self.GESTURES and len(args) == 1 and args[0] in ("1", "2", "3"):
            self.GESTURES[cmd](self, int(args[0]))
            if self.mode == "thinking":
                self.lids(self.cal["lid_think"], 200, "io")

    def tick(self, now_ms):
        """Call often. Drives the background modes."""
        if self.mode == "exercise":
            if self.until is None:
                self.until = now_ms + int(self.minutes * 60000)
            if now_ms >= self.until:
                self.handle_line("rest")
                return
            if now_ms < self.next_drift:
                return
            self.rand = (self.rand * 1103515245 + 12345) & 0x7FFFFFFF
            f = 0.15 + 0.70 * (self.rand % 1000) / 1000
            self.lids(f, 600)
            lo, hi = self.range(L_EYE)
            self.eyes(lo + (hi - lo) * (0.30 + 0.40 * (self.rand % 997) / 997), 600)  # 30%-70% of the eye range
            self.next_drift = now_ms + 1500
            return
        if self.mode != "thinking":
            return
        if gaze_trace is not None and self.cal["think_trace"]:  # replay the recording, looping
            if self.think_start is None:
                self.think_start = now_ms
            i = ((now_ms - self.think_start) * gaze_trace.HZ // 1000) % len(gaze_trace.THINK)
            if i != self.trace_i:
                self.trace_i = i
                self.eyes(EYE_CENTER + _s8(gaze_trace.THINK[i]))
                if i in TRACE_BLINKS:
                    self.blink(level=self.cal["lid_think"])
            return
        if now_ms >= self.next_blink:  # sparse blinks while thinking: one per 5-8 s
            self.rand = (self.rand * 1103515245 + 12345) & 0x7FFFFFFF
            if self.next_blink:  # spontaneous: one in four stops a little short of shut
                partial = 0.04 if (self.rand >> 8) % 4 == 0 else 0
                self.blink(level=self.cal["lid_think"], shut=self.cal["lid_closed"] + partial)
            self.next_blink = now_ms + 5000 + self.rand % 3000
        if now_ms < self.next_drift:
            return
        self.rand = (self.rand * 1103515245 + 12345) & 0x7FFFFFFF
        shift = (self.rand % 7) - 3  # micro-saccades of a few degrees around the averted gaze
        self.saccade(EYE_CENTER + self.think_side * 18 + shift * 2)
        self.next_drift = now_ms + 400 + self.rand % 500  # fixations 0.4-0.9 s
