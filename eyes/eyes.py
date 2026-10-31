# noggin eye program for the CyberBrick Core (ESP32-C3, MicroPython).
# Plays named gestures and a background "thinking" mode on four servos.
# Importable on CPython for tests (machine is stubbed there).
import time
from machine import Pin, PWM

try:
    from time import sleep_ms
except ImportError:  # CPython
    def sleep_ms(ms): time.sleep(ms / 1000)

# shield port 1..4 -> GPIO 3,2,1,0. Ranges from the designer's remote config.
L_LID, L_EYE, R_LID, R_EYE = 3, 2, 1, 0
RANGE = {L_LID: (45, 150), L_EYE: (60, 120), R_LID: (40, 135), R_EYE: (60, 120)}  # calibrated 2026-10-31
LIDS, EYES = (L_LID, R_LID), (L_EYE, R_EYE)
EYE_CENTER = 90
# Horn offsets differ per eye; added to every eye target so 90 looks straight ahead. Set by calibration.
EYE_TRIM = {L_EYE: -5, R_EYE: -5}
LID_OPEN, LID_HALF, LID_CLOSED = 1.0, 0.5, 0.0
LID_REST = 0.28   # neutral: fully open reads as surprised
LID_THINK = 0.16  # thinking / attention: a notch lower than neutral
# The lid servos are mirror-mounted (designer's config drives PWM1 negative, PWM3 positive):
# "open" is one end of the range for the left lid and the other end for the right. Set by calibration.
LID_FLIP = {L_LID: True, R_LID: False}


def _duty(angle):
    return int(angle * 102 / 180 + 25)  # 10-bit duty at 50 Hz, stock bbl.servos formula


class Eyes:
    def __init__(self):
        self.pwm = {}
        self.pos = {}
        self.mode = "rest"
        self.next_drift = 0
        self.rand = 12345

    # --- servo primitives -------------------------------------------------
    def _lid_angle(self, pin, f):
        lo, hi = RANGE[pin]
        if LID_FLIP[pin]:
            f = 1 - f
        return lo + (hi - lo) * f

    def set(self, targets):
        for pin, angle in targets.items():
            lo, hi = RANGE[pin]
            angle = min(hi, max(lo, angle))
            if pin not in self.pwm:
                self.pwm[pin] = PWM(Pin(pin), freq=50)
            self.pwm[pin].duty(_duty(angle))
            self.pos[pin] = angle

    def glide(self, ms, targets, step=20):
        start = {p: self.pos.get(p, EYE_CENTER + EYE_TRIM[p] if p in EYES else self._lid_angle(p, LID_REST)) for p in targets}
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
        t = {p: angle + EYE_TRIM[p] for p in EYES}
        self.glide(ms, t) if ms else self.set(t)

    def blink(self, hold=90):
        self.lids(LID_CLOSED); sleep_ms(hold); self.lids(LID_REST); sleep_ms(120)

    def rest_pose(self):
        self.lids(LID_REST, 200); self.eyes(EYE_CENTER, 200)

    # --- gestures ----------------------------------------------------------
    def eureka(self, i):
        self.lids(LID_OPEN)
        if i == 1:
            self.eyes(105, 150); sleep_ms(300); self.eyes(EYE_CENTER, 200); self.blink()
            return
        self.eyes(118); sleep_ms(600 if i == 2 else 900)
        if i == 3:
            self.eyes(62, 150); sleep_ms(500)  # double-take
        self.eyes(EYE_CENTER, 250); self.blink(); self.blink()
        self.lids(LID_HALF, 150); self.lids(LID_REST, 250)

    def attention(self, i):
        self.lids(LID_THINK, 200)
        for _ in range(2):
            self.eyes(65, 600); self.eyes(115, 600)
        self.eyes(EYE_CENTER, 400); sleep_ms(300)
        self.lids(LID_REST, 300)

    def bored(self, i):
        self.lids(0.35, 600); self.eyes(80, 800)
        for _ in range(2):
            self.lids(LID_CLOSED, 300); sleep_ms(250); self.lids(0.35, 400); sleep_ms(600)
        self.rest_pose()

    def wince(self, i):
        self.lids(LID_CLOSED)
        for _ in range(3):
            self.eyes(84); sleep_ms(60); self.eyes(96); sleep_ms(60)
        self.eyes(EYE_CENTER); sleep_ms(400)
        self.lids(LID_REST, 700)

    GESTURES = {"eureka": eureka, "attention": attention, "bored": bored, "wince": wince}

    # --- commands ----------------------------------------------------------
    def handle_line(self, line):
        parts = line.strip().split()
        if not parts:
            return
        if parts[0] in ("thinking", "rest"):
            self.mode = parts[0]
            if self.mode == "rest":
                self.rest_pose(); sleep_ms(200); self.release()
            else:
                self.lids(LID_THINK, 300); self.release(); self.next_drift = 0
            return
        if parts[0] in self.GESTURES and len(parts) == 2 and parts[1] in ("1", "2", "3"):
            self.GESTURES[parts[0]](self, int(parts[1]))
            if self.mode == "thinking":
                self.lids(LID_THINK, 200)
            sleep_ms(150); self.release()

    def tick(self, now_ms):
        """Call often. In thinking mode, drift the eyes every 3-6 s, then release."""
        if self.mode != "thinking" or now_ms < self.next_drift:
            return
        self.rand = (self.rand * 1103515245 + 12345) & 0x7FFFFFFF
        self.eyes(70 + self.rand % 41, 500)
        sleep_ms(100); self.release()
        self.next_drift = now_ms + 3000 + self.rand % 3000
