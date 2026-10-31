"""Electrical budget of the Mech from datasheet figures (docs/research/2026-10-31-electrical.md), no circuit, and the
leads the cable corridors route. Run: .venv/bin/python -m model.electrical. budget() is merged into the Mech-wide
(noggin-stage3) report and leads() routed by model/engine/cables.py."""

import importlib.util
import json
import os

from model.geometry import CHANNELS, SERVO_LABEL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(ROOT, "eyes", name + ".py")
    )  # by path: model/ has its own `eyes`
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


servo, replay = _load("servo"), _load("replay")

CAP_A = 3.0  # shield max and pack continuous discharge are both 3 A: one pack per shield
PACK = {"mah": 800, "cutoff_v": 5.8}  # the rating is to the cutoff; no derating, no VBAT sense
SHIELD_STANDBY_A = 0.060
# Both Cores stay on the Wi-Fi as stations (ADR 0005), no power save: ESP32-C3 datasheet Table 5-7 (chip peak at 3.3 V,
# docs/research/2026-10-31-shafts.md): receive 84 mA while listening, transmit up to 335 mA (802.11b at 21 dBm) for a
# beacon or an ack burst.
# Added in amps at the pack as if through a linear regulator (the Core's supply path is not published).
WIFI_RX_A, WIFI_TX_A = 0.084, 0.335
# Holding allowance: a held servo is not spinning (no no-load current), only the torque current for the load.
# Worst moving chain is an eyeball plus its bar, ~10 g on a ~3 cm lever = 0.03 kgf.cm; 0.05 leaves margin
# until #20 measures the real gravity torque. 0.05 / 2.03 kgf.cm per A = 25 mA.
GRAVITY_KGFCM = 0.05
HOLD_A = GRAVITY_KGFCM / servo.fit()["kt_kgfcm_per_a"]
RUN_A = servo.current(GRAVITY_KGFCM, 0)  # moving against the load: no-load current plus the torque current
SESSION_PER_HOUR = {"eureka 2": 20, "attention 1": 10}  # Stop (normal Tier) and notification Triggers


def budget():
    cal = json.load(open(os.path.join(ROOT, "eyes", "calibration.json")))
    moving_s = sum(n * replay.play([line], cal)[1] / 1000 for line, n in SESSION_PER_HOUR.items())
    out = {
        "channels": CHANNELS,
        "cap_a": CAP_A,
        "pack": PACK,
        "stall_a": {},
        "draw_a": {},
        "runtime_h": {},
        "session_moving_s_per_hour": moving_s,
        "hold_a_per_servo": HOLD_A,
        "run_a_per_servo": RUN_A,
        "wifi_a": {"rx": WIFI_RX_A, "tx_peak": WIFI_TX_A},
    }
    for core, ch in CHANNELS.items():
        n = len(ch)
        rest = SHIELD_STANDBY_A + n * (servo.STANDBY_A + HOLD_A) + WIFI_RX_A
        demo = SHIELD_STANDBY_A + n * RUN_A + WIFI_RX_A
        session = rest + (demo - rest) * (moving_s / 3600 if core == "core1" else 0)  # core2 has no choreography yet
        out["stall_a"][core] = n * servo.SPEC[6.0]["stall_a"] + SHIELD_STANDBY_A + WIFI_TX_A  # all at once
        out["draw_a"][core] = {"rest": rest, "session": session, "demo": demo}
        out["runtime_h"][core] = {k: PACK["mah"] / 1000 / a for k, a in out["draw_a"][core].items()}
    return out


# The servo lead length is not published (docs/research/2026-10-31-electrical.md 1, -shafts.md): assumed 250 mm; the
# XH2.54 leads are 100 mm (pan-tilt guide p.8 hardware list); a lead must reach with SLACK_MM to spare.
SERVO_LEAD_MM, XH_LEAD_MM, SLACK_MM = 250, 100, 20


def leads():
    """(lead, Port, Port, length mm) for every lead of the Mech: each servo from where its lead leaves the servo to its
    shield header (CHANNELS), each pack's lead to its switch board, each switch board's XH lead to its shield. Port names
    are the Fusion builds' (model/engine/stages.py ports); model/engine/cables.py routes each from its first Port."""
    out = []
    for n in (1, 2):
        for port, name in CHANNELS[f"core{n}"].items():
            out.append(
                (
                    f"{name} servo -> Core {n} PWM{port}",
                    f"{SERVO_LABEL[name]} servo lead",
                    f"Core {n} servo PWM{port}",
                    SERVO_LEAD_MM,
                )
            )
        out.append((f"pack {n} -> switch {n}", f"battery {n} lead", f"switch board {n} hole", XH_LEAD_MM))
        out.append((f"switch {n} -> shield {n}", f"switch board {n} hole", f"Core {n} XH power", XH_LEAD_MM))
    return out


if __name__ == "__main__":
    print(json.dumps(budget(), indent=1))
