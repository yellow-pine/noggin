# The 9 g clutch servo as data and a model. Plain Python: imports on the Core too.
# Published figures: docs/research/2026-10-31-electrical.md section 1 and Clutch ("<=" and ">=" bounds taken as values).
SPEC = {  # volts -> stall and rated torque kgf.cm, stall A, no-load (running) A, standby A, s per 60 deg
    6.0: {
        "stall_kgfcm": 1.2,
        "rated_kgfcm": 0.4,
        "stall_a": 0.650,
        "running_a": 0.060,
        "standby_a": 0.008,
        "s_per_60": 0.12,
    },
    4.8: {
        "stall_kgfcm": 1.0,
        "rated_kgfcm": 0.32,
        "stall_a": 0.550,
        "running_a": 0.050,
        "standby_a": 0.008,
        "s_per_60": 0.14,
    },
}
STALL_KGFCM = SPEC[6.0]["stall_kgfcm"]
STANDBY_A = SPEC[6.0]["standby_a"]
# kg.m^2, the motor's inertia through the gears at the horn (inferred: a micro motor's rotor through ~1:300)
ARMATURE = 1e-4

# Standard tilt servo: manufacturer stall figures, not a continuous torque rating.
# docs/research/2026-11-04-standard-tilt-servo.md records the interpolation and design margin.
STANDARD_SPEC = {
    4.8: {"stall_kgfcm": 9.4, "s_per_60": 0.19},
    6.0: {"stall_kgfcm": 11.0, "s_per_60": 0.15},
}


def profile(axis, volts=5.0):
    """The installed servo's electrical/mechanical limits at its supply voltage.

    Between published voltages interpolation is inferred. The standard servo's
    continuous design limit is one third of stall, inferred, never a vendor rating.
    """
    standard = axis in ("tilt", "pan")
    specs = STANDARD_SPEC if standard else SPEC
    (v0, s0), (v1, s1) = sorted(specs.items())
    if not v0 <= volts <= v1:
        raise ValueError("servo voltage outside the modelled specification")
    values = {key: s0[key] + (s1[key] - s0[key]) * (volts - v0) / (v1 - v0) for key in s0}
    return {
        **values,
        **(
            {"rated_kgfcm": values["stall_kgfcm"] / 3, "stall_a": 1.4, "running_a": 0.170, "standby_a": 0.010}
            if standard
            else {}
        ),
        "volts": volts,
        "min_v": v0,
        "lead_mm": 160 if standard else 250,
        "mass_g": 55 if standard else 16,
        "travel_deg": 159
        if standard
        else 180,  # calibrated pulse endpoints remain an inference, not a universal 180° claim
        "armature": ARMATURE * (55 / 16 if standard else 1),
        "rated_source": "inferred: one third of stall" if standard else "published",
    }


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
