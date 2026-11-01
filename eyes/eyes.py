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


def servo_map():
    """Servo name -> GPIO from core.json, or the defaults without the file."""
    try:
        with open("core.json") as f:
            return {name: PORT_GPIO[port] for port, name in json.load(f)["ports"].items()}
    except (OSError, KeyError, ValueError):
        return {name: pin for pin, name in NAME.items()}


# Known-good values for this Mech (2026-11-01, #213); eyes/calibration.json is the source of truth.
# Each servo has exact end angles; everything else derives from them: an eye's straight-ahead is the average
# of its two ends, lid levels are fractions (0 closed .. 1 open) along a lid's closed, rest and open points.
# Lid positions are in one shared frame, the right lid servo's degrees (lo closed, hi open): the lid servos are
# mounted mirror-image, so the same numbers fit both lids and the Core writes 180 - a to the MIRRORED servo.
# The linkage makes equal servo steps unequal lid steps, so each lid has a third point, where it sits at
# lid_rest, and the map is straight from closed to rest and from rest to open.
# Lid ends sit inside the mechanical stops: the clutch servos slip (and decalibrate) when stalled.
MIRRORED = (L_LID,)
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
        lo, hi = self.cal[NAME[pin] + "_lo"], self.cal[NAME[pin] + "_hi"]
        return (180 - hi, 180 - lo) if pin in MIRRORED else (lo, hi)

    def _lid_pos(self, pin, f):
        """A lid level (0 closed .. 1 open) in the shared frame: straight closed..rest, then rest..open."""
        name, r = NAME[pin], self.cal["lid_rest"]
        lo, rest, hi = self.cal[name + "_lo"], self.cal[name + "_rest"], self.cal[name + "_hi"]
        f = min(1.0, max(0.0, f))
        if f < r:
            return lo + (rest - lo) * f / r
        return rest + (hi - rest) * (f - r) / (1 - r) if r < 1 else rest

    def _lid_angle(self, pin, f):
        a = self._lid_pos(pin, f)
        return 180 - a if pin in MIRRORED else a

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

    def glide(self, ms, targets, step=20, ease=False):
        """Linear move, or ease-out (fast first, asymptotic) like an eyelid reopening."""
        start = {
            p: self.pos.get(
                p, self._eye_angle(p, EYE_CENTER) if p in EYES else self._lid_angle(p, self.cal["lid_rest"])
            )
            for p in targets
        }
        n = max(1, ms // step)
        for i in range(1, n + 1):
            f = i / n
            if ease:
                f = 1 - (1 - f) ** 2
            self.set({p: start[p] + (targets[p] - start[p]) * f for p in targets})
            wait(step)

    def release(self):
        for p in self.pwm.values():
            p.deinit()
        self.pwm.clear()

    def lids(self, f, ms=0, ease=False):
        t = {p: self._lid_angle(p, f) for p in LIDS}
        self.glide(ms, t, ease=ease) if ms else self.set(t)

    def lid(self, pin, f, ms=0, ease=False):
        t = {pin: self._lid_angle(pin, f)}
        self.glide(ms, t, ease=ease) if ms else self.set(t)

    def eyes(self, angle, ms=0):
        t = {p: self._eye_angle(p, angle) for p in EYES}
        self.glide(ms, t) if ms else self.set(t)

    def _side(self):
        self.rand = (self.rand * 1103515245 + 12345) & 0x7FFFFFFF
        return 1 if self.rand & 1 else -1

    # Kinematics from docs/research/2026-10-31-natural-eye-motion.md. The 9 g servos slew ~60 deg
    # per 100 ms, about the speed of a real blink close or a 20 deg saccade, so closes and saccades
    # are commanded as steps; only openings and returns are glided.
    def blink(self, level=None, hold=55, open_ms=300):
        """Close as a step, hold, reopen with ease-out (real blinks close ~3x faster than they open)."""
        self.lids(self.cal["lid_closed"])
        wait(80 + hold)
        self.lids(self.cal["lid_rest"] if level is None else level, open_ms, ease=True)

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
        for f in prof:
            self.eyes(cur + d * f)
            wait(10)
        self.eyes(angle)

    def replay(self, samples, blinks=()):
        """Play a 25 Hz gaze clip around centre."""
        for i in range(len(samples)):
            self.eyes(EYE_CENTER + _s8(samples[i]))
            if i in blinks:
                self.blink(level=self.cal["lid_think"])
            wait(1000 // gaze_trace.HZ)  # pyright: ignore[reportOptionalMemberAccess]

    def rest_pose(self):
        self.lids(self.cal["lid_rest"], 200)
        self.eyes(EYE_CENTER, 200)

    # --- gestures ----------------------------------------------------------
    def eureka(self, i):
        """Surprise: lids wide, eyes dart aside, hold, back to centre, double blink, lids ease to rest."""
        side = self._side()
        amp, hold = {1: (12, 300), 2: (22, 550), 3: (25, 800)}[i]
        self.lids(self.cal["lid_open"])  # AU5: widen, as a step
        self.saccade(EYE_CENTER + side * amp)
        wait(hold)
        if i == 3:
            self.saccade(EYE_CENTER - side * amp)
            wait(500)  # double-take
        self.saccade(EYE_CENTER)
        self.blink(level=self.cal["lid_open"], open_ms=250)
        if i >= 2:
            wait(200)
            self.blink(level=self.cal["lid_open"], open_ms=250)
        self.lids(self.cal["lid_rest"], 300, ease=True)

    def attention(self, i):
        """Needs you: half lids, two slow pursuit sweeps (~40 deg/s), centre, lids open, one blink."""
        self.lids(self.cal["lid_think"], 200)
        if gaze_trace is not None:  # a real person scanning left-right (HSS task)
            self.replay(gaze_trace.SCAN)
        else:
            self.eyes(EYE_CENTER - 25, 600)
            for _ in range(2):
                self.eyes(EYE_CENTER + 25, 1250)
                self.eyes(EYE_CENTER - 25, 1250)
        self.saccade(EYE_CENTER)
        self.lids(self.cal["lid_rest"], 300, ease=True)
        wait(200)
        self.blink()

    def bored(self, i):
        """Drowsy: lids droop, lazy real gaze drift, slow heavy blinks, one long closure, settle."""
        droop = 0.35 * self.cal["lid_rest"] / 0.28
        self.lids(droop, 500)
        if gaze_trace is not None:  # the calmest 6 s of a real viewing session, with heavy blinks on top
            calm, n = gaze_trace.CALM, len(gaze_trace.CALM)
            for k, (blink_at, hold) in enumerate(((n // 4, 500), (n // 2, 500), (3 * n // 4, 1800))):
                start = 0 if k == 0 else [n // 4, n // 2][k - 1]
                for j in range(start, blink_at):
                    self.eyes(EYE_CENTER + _s8(calm[j]))
                    wait(1000 // gaze_trace.HZ)
                self.lids(self.cal["lid_closed"], 200 if hold < 1800 else 250)
                wait(hold)
                self.lids(droop if hold < 1800 else self.cal["lid_rest"], 900 if hold < 1800 else 1200, ease=True)
        else:
            self.eyes(EYE_CENTER - 6, 800)
            for _ in range(2):
                self.lids(self.cal["lid_closed"], 200)
                wait(500)
                self.lids(droop, 900, ease=True)
                wait(700)
            self.lids(self.cal["lid_closed"], 250)
            wait(1800)  # the stall-time rule (test_stall.py) caps closures at 2 s
            self.lids(self.cal["lid_rest"], 1200, ease=True)
        self.saccade(EYE_CENTER)

    def wince(self, i):
        """Both lids snap shut, eyes twitch (small real saccades), hold, reopen fast to ~80%, settle."""
        self.lids(self.cal["lid_closed"])
        for a in (4, -4, 3):
            self.saccade(EYE_CENTER + a)
        self.saccade(EYE_CENTER)
        wait(150)
        self.lids(self.cal["lid_rest"] + 0.1, 200, ease=True)
        wait(150)
        self.lids(self.cal["lid_rest"], 300, ease=True)

    def wink(self, i):
        """Slow wink: one lid closes over 400 ms, holds, reopens over 600 ms; eyes glance toward that side.
        1 = mech's left lid (viewer's right), 2 = mech's right lid (viewer's left), 3 = random."""
        pin = {1: L_LID, 2: R_LID}.get(i, L_LID if self._side() > 0 else R_LID)
        self.saccade(EYE_CENTER + (8 if pin == L_LID else -8))
        self.lid(pin, 0.03, 400, ease=True)
        wait(500)  # slow, so it can go nearer the stop than a blink
        self.lid(pin, self.cal["lid_rest"], 600, ease=True)
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
            else:  # gaze-evoked blink with the saccade aside
                self.think_side = self._side()
                self.lids(self.cal["lid_closed"])
                self.saccade(EYE_CENTER + self.think_side * 18)
                self.lids(self.cal["lid_think"], 250, ease=True)
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
                self.lids(self.cal["lid_think"], 200)

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
            if self.next_blink:
                self.blink(level=self.cal["lid_think"])
            self.next_blink = now_ms + 5000 + self.rand % 3000
        if now_ms < self.next_drift:
            return
        self.rand = (self.rand * 1103515245 + 12345) & 0x7FFFFFFF
        shift = (self.rand % 7) - 3  # micro-saccades of a few degrees around the averted gaze
        self.saccade(EYE_CENTER + self.think_side * 18 + shift * 2)
        self.next_drift = now_ms + 400 + self.rand % 500  # fixations 0.4-0.9 s
