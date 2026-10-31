# The 9 g clutch servo as data and a model. Plain Python: imports on the Core too.
# Published figures: docs/research/2026-10-31-electrical.md section 1 ("<=" bounds taken as values).
SPEC = {  # volts -> stall torque kgf.cm, stall A, no-load (running) A, standby A, s per 60 deg
    6.0: {"stall_kgfcm": 1.2, "stall_a": 0.650, "running_a": 0.060, "standby_a": 0.008, "s_per_60": 0.12},
    4.8: {"stall_kgfcm": 1.0, "stall_a": 0.550, "running_a": 0.050, "standby_a": 0.008, "s_per_60": 0.14},
}
STALL_KGFCM = SPEC[6.0]["stall_kgfcm"]
STANDBY_A = SPEC[6.0]["standby_a"]


def rate(volts=6.0):
    """Rated no-load slew, deg/s."""
    return 60 / SPEC[volts]["s_per_60"]


RATE_DEG_S = rate()


def fit(volts=6.0):
    """DC-motor constants from the published figures, referred to the horn (gear ratio folded in).
    V = I*R + KE*w;  T = KT*(I - I0).  R from stall current, KT from stall torque, KE from no-load speed.
    KT/KE in SI is ~0.32, the gearbox loss the bounds imply; the ratio itself is not identifiable."""
    s = SPEC[volts]
    r = volts / s["stall_a"]
    i0 = s["running_a"]
    kt = s["stall_kgfcm"] / (s["stall_a"] - i0)  # kgf.cm per A
    ke = (volts - i0 * r) / rate(volts)  # V per deg/s
    return {"r_ohm": r, "i0_a": i0, "kt_kgfcm_per_a": kt, "ke_v_per_deg_s": ke}


def current(torque_kgfcm, speed_deg_s, volts=6.0):
    """Amps to deliver torque at speed; capped by what the winding can draw against the back-EMF."""
    f = fit(volts)
    demand = f["i0_a"] + torque_kgfcm / f["kt_kgfcm_per_a"]
    cap = (volts - f["ke_v_per_deg_s"] * abs(speed_deg_s)) / f["r_ohm"]
    return min(demand, cap)


class Plant:
    """First-order servo: tracks the command at the rated slew; `holding` once it has arrived."""

    def __init__(self, pos, volts=6.0):
        self.pos, self.rate, self.holding = pos, rate(volts), True

    def step(self, commanded_deg, dt):
        d = commanded_deg - self.pos
        lim = self.rate * dt
        self.pos += max(-lim, min(lim, d))
        self.holding = abs(commanded_deg - self.pos) < 1e-9
        return self.pos
