"""Electrical budget of the Mech from datasheet figures (docs/research/2026-10-31-electrical.md), no circuit.
Run: .venv/bin/python twin/electrical.py. budget() is merged into the Mech-wide report (the merge and cable
reach come with the top assembly, #17)."""
import importlib.util, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "eyes", name + ".py"))   # by path: twin/ has its own `eyes`
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


servo, replay = _load("servo"), _load("replay")

CHANNELS = {"core1": {1: "l_lid", 2: "l_eye", 3: "r_lid", 4: "r_eye"},   # docs/build-notes.md, servo ports
            "core2": {1: "tilt", 2: "mouth", 3: "pan"}}                   # second Core, designer's config JSON
CAP_A = min(3.0, 3.0)                      # shield max, pack continuous discharge: one pack per shield
PACK = {"mah": 800, "cutoff_v": 5.8}       # the rating is to the cutoff; no derating, no VBAT sense
SHIELD_STANDBY_A = 0.060
# Wi-Fi station idle + a 2 s beacon (eyes/wifi.py): ~100 mA averaged. Assumption, no measurement on the Core yet;
# docs/research/2026-10-31-radio.md records no draw figure. The Core is a Link on every scenario, so it is always on.
WIFI_A = 0.100
# Holding allowance: a held servo is not spinning (no no-load current), only the torque current for the load.
# Worst moving chain is an eyeball plus its bar, ~10 g on a ~3 cm lever = 0.03 kgf.cm; 0.05 leaves margin
# until #20 measures the real gravity torque. 0.05 / 2.03 kgf.cm per A = 25 mA.
GRAVITY_KGFCM = 0.05
HOLD_A = GRAVITY_KGFCM / servo.fit()["kt_kgfcm_per_a"]
RUN_A = servo.current(GRAVITY_KGFCM, 0)    # moving against the load: no-load current plus the torque current
SESSION_PER_HOUR = {"eureka 2": 20, "attention 1": 10}   # Stop (normal Tier) and notification Triggers


def budget():
    cal = json.load(open(os.path.join(ROOT, "eyes", "calibration.json")))
    moving_s = sum(n * replay.play([line], cal)[1] / 1000 for line, n in SESSION_PER_HOUR.items())
    out = {"channels": CHANNELS, "cap_a": CAP_A, "pack": PACK, "stall_a": {}, "draw_a": {}, "runtime_h": {},
           "session_moving_s_per_hour": moving_s, "hold_a_per_servo": HOLD_A, "run_a_per_servo": RUN_A, "wifi_a": WIFI_A}
    for core, ch in CHANNELS.items():
        n = len(ch)
        rest = SHIELD_STANDBY_A + WIFI_A + n * (servo.STANDBY_A + HOLD_A)
        demo = SHIELD_STANDBY_A + WIFI_A + n * RUN_A
        session = rest + (demo - rest) * (moving_s / 3600 if core == "core1" else 0)   # core2 has no choreography yet
        out["stall_a"][core] = n * servo.SPEC[6.0]["stall_a"]
        out["draw_a"][core] = {"rest": rest, "session": session, "demo": demo}
        out["runtime_h"][core] = {k: PACK["mah"] / 1000 / a for k, a in out["draw_a"][core].items()}
    return out


if __name__ == "__main__":
    print(json.dumps(budget(), indent=1))
