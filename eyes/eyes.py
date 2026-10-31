# noggin eye program for the CyberBrick Core (ESP32-C3, MicroPython).
# Plays named gestures and background modes (thinking, exercise) on four servos.
# Servos stay powered: released, the lids and eyes fall under gravity (gravity beats the smooth linkages).
# Calibration lives in self.cal: defaults below, overridden live by `set key value`
# lines that the Daemon pushes from eyes/calibration.json.
# Importable on CPython for tests (machine is stubbed there).
import time
from machine import Pin, PWM

try:
    from time import sleep_ms
except ImportError:  # CPython
    def sleep_ms(ms): time.sleep(ms / 1000)

# shield port 1..4 -> GPIO 3,2,1,0
L_LID, L_EYE, R_LID, R_EYE = 3, 2, 1, 0
NAME = {L_LID: "l_lid", L_EYE: "l_eye", R_LID: "r_lid", R_EYE: "r_eye"}
LIDS, EYES = (L_LID, R_LID), (L_EYE, R_EYE)
EYE_CENTER = 90
LID_OPEN_FULL, LID_CLOSED = 1.0, 0.0

# Known-good values for this Mech (2026-10-31); eyes/calibration.json is the source of truth.
# Each servo has exact end angles for its side; everything else derives from them: an eye's
# straight-ahead is the average of its two ends, lid levels are fractions between a lid's ends.
# Lid ends sit inside the mechanical stops: the clutch servos slip (and decalibrate) when stalled.
# The lid servos are mirror-mounted, hence the per-lid flip (1: open is the low end).
DEFAULT_CAL = {
    "l_lid_lo": 51, "l_lid_hi": 144, "r_lid_lo": 51, "r_lid_hi": 129,
    "l_eye_lo": 58, "l_eye_hi": 118, "r_eye_lo": 58, "r_eye_hi": 118,
    "l_lid_flip": 1, "r_lid_flip": 0,
    "lid_rest": 0.28, "lid_think": 0.16, "lid_closed": 0.10, "lid_open": 0.95,
}


def _duty(angle):
    return int(angle * 102 / 180 + 25)  # 10-bit duty at 50 Hz, stock bbl.servos formula


class Eyes:
    def __init__(self):
        self.cal = dict(DEFAULT_CAL)
        self.pwm = {}
        self.pos = {}
        self.mode = "rest"
        self.next_drift = 0
        self.until = 0
        self.rand = 12345

    # --- calibration ------------------------------------------------------
    def range(self, pin):
        return self.cal[NAME[pin] + "_lo"], self.cal[NAME[pin] + "_hi"]

    def _lid_angle(self, pin, f):
        lo, hi = self.range(pin)
        f = min(1.0, max(0.0, f))
        if self.cal[NAME[pin] + "_flip"]:
            f = 1 - f
        return lo + (hi - lo) * f

    def _eye_angle(self, pin, angle):
        """Gesture angles are written around EYE_CENTER; the eye's real centre is the average of its ends."""
        lo, hi = self.range(pin)
        return (lo + hi) / 2 + (angle - EYE_CENTER)

    # --- servo primitives -------------------------------------------------
    def set(self, targets):
        for pin, angle in targets.items():
            lo, hi = self.range(pin)
            angle = min(hi, max(lo, angle))
            if pin not in self.pwm:
                self.pwm[pin] = PWM(Pin(pin), freq=50)
            self.pwm[pin].duty(_duty(angle))
            self.pos[pin] = angle

    def glide(self, ms, targets, step=20):
        start = {p: self.pos.get(p, self._eye_angle(p, EYE_CENTER) if p in EYES else self._lid_angle(p, self.cal["lid_rest"])) for p in targets}
        n = max(1, ms // step)
        for i in range(1, n + 1):
            self.set({p: start[p] + (targets[p] - start[p]) * i / n for p in targets})
            sleep_ms(step)

    def release(self):
        for p in self.pwm.values():
            p.deinit()
        self.pwm.clear()

    def lids(self, f, ms=0):
        t = {p: self._lid_angle(p, f) for p in LIDS}
        self.glide(ms, t) if ms else self.set(t)

    def eyes(self, angle, ms=0):
        t = {p: self._eye_angle(p, angle) for p in EYES}
        self.glide(ms, t) if ms else self.set(t)

    def blink(self, hold=90):
        # glide, never snap: a snap into the closed end slams the stop and slips the clutch
        self.lids(self.cal["lid_closed"], 80); sleep_ms(hold); self.lids(self.cal["lid_rest"], 80); sleep_ms(120)

    def rest_pose(self):
        self.lids(self.cal["lid_rest"], 200); self.eyes(EYE_CENTER, 200)

    # --- gestures ----------------------------------------------------------
    def eureka(self, i):
        self.lids(self.cal["lid_open"], 60)
        if i == 1:
            self.eyes(105, 150); sleep_ms(300); self.eyes(EYE_CENTER, 200); self.blink()
            return
        self.eyes(118); sleep_ms(600 if i == 2 else 900)
        if i == 3:
            self.eyes(62, 150); sleep_ms(500)  # double-take
        self.eyes(EYE_CENTER, 250); self.blink(); self.blink()
        self.lids(self.cal["lid_think"], 150); self.lids(self.cal["lid_rest"], 250)

    def attention(self, i):
        self.lids(self.cal["lid_think"], 200)
        for _ in range(2):
            self.eyes(65, 600); self.eyes(115, 600)
        self.eyes(EYE_CENTER, 400); sleep_ms(300)
        self.lids(self.cal["lid_rest"], 300)

    def bored(self, i):
        self.lids(self.cal["lid_think"], 600); self.eyes(80, 800)
        for _ in range(2):
            self.lids(self.cal["lid_closed"], 300); sleep_ms(250); self.lids(self.cal["lid_think"], 400); sleep_ms(600)
        self.rest_pose()

    def wince(self, i):
        self.lids(self.cal["lid_closed"], 80)
        for _ in range(3):
            self.eyes(84); sleep_ms(60); self.eyes(96); sleep_ms(60)
        self.eyes(EYE_CENTER); sleep_ms(400)
        self.lids(self.cal["lid_rest"], 700)

    GESTURES = {"eureka": eureka, "attention": attention, "bored": bored, "wince": wince}

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
            else:
                self.lids(self.cal["lid_think"], 300); self.next_drift = 0
        elif cmd == "release":                          # unpower (e.g. muted overnight); next command re-powers
            self.release()
        elif cmd == "set" and len(args) == 2 and args[0] in self.cal:
            self.cal[args[0]] = type(DEFAULT_CAL[args[0]])(float(args[1]))
        elif cmd == "pose" and len(args) in (2, 4):      # pose lids <0-1> | eyes <angle> | both; holds
            for key, val in zip(args[::2], args[1::2]):
                if key == "lids": self.lids(float(val), 150)
                elif key == "eyes": self.eyes(float(val), 150)
        elif cmd == "exercise" and len(args) == 1:       # run-in: smooth mid-range cycling, never near a stop
            self.mode = "exercise"; self.until = None; self.minutes = float(args[0]); self.next_drift = 0
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
                self.handle_line("rest"); return
            if now_ms < self.next_drift:
                return
            self.rand = (self.rand * 1103515245 + 12345) & 0x7FFFFFFF
            f = 0.15 + 0.70 * (self.rand % 1000) / 1000
            self.lids(f, 600)
            lo, hi = self.range(L_EYE)
            self.eyes(lo + (hi - lo) * (0.30 + 0.40 * (self.rand % 997) / 997), 600)   # 30%-70% of the eye range
            self.next_drift = now_ms + 1500
            return
        if self.mode != "thinking" or now_ms < self.next_drift:
            return
        self.rand = (self.rand * 1103515245 + 12345) & 0x7FFFFFFF
        if self.rand % 4 == 0:            # occasional blink
            self.blink(); self.lids(self.cal["lid_think"])
        else:
            self.eyes(70 + self.rand % 41, 500)
        self.next_drift = now_ms + 3000 + self.rand % 3000
