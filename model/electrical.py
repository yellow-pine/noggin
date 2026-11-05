"""The Mech's supply as a SPICE netlist (ngspice through spicelib), figures from the datasheets
(docs/research/2026-10-31-electrical.md), the pack by its charge (docs/research/2026-11-02-literature-electrical.md).
Run: .venv/bin/python -m model.electrical. worst_case() is merged into the report of each document with both Cores
(model/report.py). It reads only CHANNELS and the lead lengths."""

import importlib.util
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

from scipy.optimize import brentq
from spicelib import RawRead
from spicelib.simulators.ngspice_simulator import NGspiceSimulator

from model.geometry import CHANNELS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(ROOT, "eyes", name + ".py")
    )  # by path: model/ has its own `eyes`
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


servo = _load("servo")

# The servo lead length: the vendor publishes none (docs/research/2026-10-31-electrical.md 1), so 250 mm, inferred: the
# typical 9 g micro servo figure (docs/research/2026-11-01-best-guesses.md); the
# XH2.54 leads are 100 mm (pan-tilt guide p.8 hardware list). The Y
# lead (guide p.10) joins the halves of one 100 mm XH lead to the battery box's cut lead: each branch from the switch
# board is taken as 100 [I] (the battery box lead's length is not published), wired in 22 AWG with the neck harness.
# Standard neck servos use 10 mm of stock 26 AWG splice plus a 150 mm 22 AWG extension (160 mm total).
SERVO_LEAD_MM, XH_LEAD_MM = 250, 100
STANDARD_STOCK_MM, STANDARD_EXT_MM = 10, 150
# The Mech's power path (#858, docs/research/2026-11-03-usb-c-power.md 7): the pack on the power-path board's
# battery FET (BQ25886; its on-resistance not read, 20 mohm [I]), the switch board after the board's output, then the
# neck cable's output pair (22 AWG, 0.0535 ohm/m, out and back; 250 mm inferred run; #902 research) to
# the Y lead into the Shields, across which the bulk capacitor sits (470 uF: open at DC, so worst_case() is unmoved by
# it; it rides the start edges and the board's switchover).
BATFET_OHM, NECK_CABLE_MM, NECK_OHM_PER_MM, BULK_F = 0.020, 250, 2 * 0.0535e-3, 470e-6
# Head-local 5 V step-down regulator for the crown standard pan servo (#978): Pololu D36V28F5 (item 5267, APM81815
# synchronous buck, 5 V / 3.2 A, 17.8 x 12.7 x 3.6 mm, 1.5 g) fed from the switched neck VBAT/GND; 4.9 V worst-case
# 2 %-low regulation target, 0.5 V dropout [I], and 0.85 lower-bound efficiency at 2S input.
PAN_BUCK_V, PAN_BUCK_DROPOUT_V, PAN_BUCK_EFF = 4.9, 0.5, 0.85


CAP_A = 3.0  # shield max and pack continuous discharge are both 3 A; one pack feeds both shields (pan-tilt guide p.10)
# The pack, 2S 14500: 7.4 V nominal (taken as its resting voltage), over-discharge cutoff 5.8 V (its datasheet, in the
# research note), which its protector compares with the cells' loaded voltage. Its cells and their resistance are not
# published: pack_ohm(), pack_ocv(). The protection board's MOSFETs, 40 mohm [I].
PACK_V = {"nominal": 7.4, "cutoff": 5.8}
PROTECTOR_OHM = 0.040
# The protector's over-discharge delay is not published [I]: a typical protector's shortest factory setting, 20 ms less
# its 20 % tolerance (TI BQ2970 datasheet, https://www.ti.com/lit/ds/symlink/bq2970.pdf; 96, 125 and 144 ms the others).
CUTOFF_DELAY_MS = 20 * 0.8
# The switch board (3 A; its spec table, in the research note): contact resistance not published [I]: 50 mohm for the
# switch and its two XH matings.
SWITCH_OHM = 0.050
# Lead wire gauge not published [I]: 26 AWG copper, 0.134 ohm/m (https://en.wikipedia.org/wiki/American_wire_gauge),
# out and back.
OHM_PER_MM = 2 * 0.134e-3
SHIELD_STANDBY_A = 0.060  # the shield datasheet
# The shield's "universal 5V servo" rail and the Core's 3.3 V from VBAT (3.7-12.6 V), per their datasheets; regulator
# types not published [I]: linear (output current drawn from the input, the worse case for the pack), dropout 0.5 V on
# the servo rail, 0.4 V on the Core (3.7 V VBAT minimum less 3.3 V).
SERVO_RAIL_V, SERVO_DROPOUT_V = 5.0, 0.5
CORE_V, CORE_DROPOUT_V = 3.3, 0.4
STALL_A = servo.SPEC[6.0]["stall_a"]  # the higher of the published stall currents
SERVO_MIN_V = min(servo.SPEC)  # operating voltage 4.8-6 V
# Both Cores stay on the Wi-Fi as stations (ADR 0005), no power save: ESP32-C3 datasheet Table 5-7 (chip peak at 3.3 V,
# docs/research/2026-10-31-shafts.md), transmit up to 335 mA (802.11b at 21 dBm) for a beacon or an ack burst.
WIFI_TX_A = 0.335
# ESP-IDF's default ESP32-C3 brownout level, ESP_BROWNOUT_DET_LVL_SEL_7 "2.51V"
# (https://github.com/espressif/esp-idf/blob/v5.4/components/esp_system/port/soc/esp32c3/Kconfig.system); MicroPython's
# sdkconfig.base keeps it; the Core firmware's own sdkconfig is not published [I].
BROWNOUT_V = 2.51


def pack_ohm(soc):
    """The pack's series resistance at a state of charge (0-1), all a 20-200 ms servo start sees: per cell Chen &
    Rincon-Mora 2006 eq. 3 (https://doi.org/10.1109/TEC.2006.874229), fit to an 850 mAh polymer cell, not our 14500s
    [I]; flat over 20-100 %, rising steeply below (docs/research/2026-11-02-literature-electrical.md 1)."""
    return 2 * (0.1562 * math.exp(-24.37 * soc) + 0.0745) + PROTECTOR_OHM


def pack_ocv(soc):
    """The pack's resting (open-circuit) voltage at a state of charge: per cell Chen & Rincon-Mora 2006 eq. 2, the same
    polymer cell [I]."""
    return 2 * (-1.031 * math.exp(-35 * soc) + 3.685 + 0.2156 * soc - 0.1178 * soc**2 + 0.3201 * soc**3)


def cells_v(soc, amps):
    """The cells' voltage under a current, what the protector compares with the cutoff: the MOSFETs it switches sit
    after it [I]."""
    return pack_ocv(soc) - amps * (pack_ohm(soc) - PROTECTOR_OHM)


def cuts(soc, amps, ms):
    """Whether the protector cuts the pack: its cells held under the cutoff by a current for longer than its delay, a
    loaded-voltage event that comes before the resting voltage reaches the cutoff."""
    return cells_v(soc, amps) < PACK_V["cutoff"] and ms >= CUTOFF_DELAY_MS


def operating_point(netlist):
    """{node: volts} at the netlist's DC operating point (ngspice in batch mode)."""
    with tempfile.TemporaryDirectory() as tmp:
        cir = Path(tmp) / "op.cir"
        cir.write_text(f"{netlist}\n.op\n.end\n")
        if NGspiceSimulator.run(cir, stdout=subprocess.DEVNULL) != 0:
            raise RuntimeError(cir.with_suffix(".log").read_text())
        # ngspice before 44 writes no "Command:" line for spicelib to detect it by (spicelib raw/plot_data.py); CI's
        # base image, Ubuntu 24.04, ships 42 (https://packages.ubuntu.com/noble/ngspice); the 26.04 runners 45
        raw = RawRead(cir.with_suffix(".raw"), dialect="ngspice", verbose=False)
        return {n[2:-1]: float(raw.get_wave(n)[0]) for n in raw.get_trace_names() if n.lower().startswith("v(")}


def lead_ohm(name, motor):
    """Round-trip resistance of a servo's power lead: 10 mm stock 26 AWG + 150 mm 22 AWG for standard servos."""
    if name in ("tilt", "pan"):
        return STANDARD_STOCK_MM * OHM_PER_MM + STANDARD_EXT_MM * NECK_OHM_PER_MM
    return motor["lead_mm"] * OHM_PER_MM


def mech(soc):
    """The Mech's wiring at its worst (#858), on a pack at a state of charge, unplugged: pack, its lead, the
    power-path board's battery FET, the switch board, the neck cable's output pair up the post, the bulk capacitor
    across its end, the Pololu D36V28F5 5 V buck feeding the crown standard pan servo, and the Y lead's branch from
    there to each shield; per shield its standby, the 5 V servo rail and every shield-fed servo at stall on its lead,
    and the Core's 3.3 V in a transmit burst. A linear regulator is a behavioural source in series, dropping what is
    above its output or at least its dropout; the synchronous buck draws power-conserving input current."""
    lines = [
        "* noggin supply",
        f"Vpack cells 0 {pack_ocv(soc)}",
        f"Rpack cells pack {pack_ohm(soc)}",
        f"Rpack_lead pack bat {XH_LEAD_MM * NECK_OHM_PER_MM}",
        f"Rbatfet bat switch_in {BATFET_OHM}",
        f"Rswitch switch_in post {SWITCH_OHM}",
        f"Rneck post switch_out {NECK_CABLE_MM * NECK_OHM_PER_MM}",
        f"Cbulk switch_out 0 {BULK_F}",
    ]
    pan = servo.profile("pan", SERVO_RAIL_V)
    lines += [
        f"Bpan_in switch_out 0 i=V(pan_rail)*{pan['stall_a']}/({PAN_BUCK_EFF}*V(switch_out))",
        f"Bpan_rail pan_rail 0 v=min(V(switch_out)-{PAN_BUCK_DROPOUT_V}, {PAN_BUCK_V})",
        f"Rpan pan_rail pan {lead_ohm('pan', pan)}",
        f"Ipan pan 0 {pan['stall_a']}",
    ]
    for core, ports in CHANNELS.items():
        vbat, rail = f"{core}_vbat", f"{core}_rail"
        lines += [
            f"Ry_{core} switch_out {vbat} {XH_LEAD_MM * NECK_OHM_PER_MM}",
            f"Ishield_{core} {vbat} 0 {SHIELD_STANDBY_A}",
            f"Brail_{core} {vbat} {rail} v=max(V({vbat})-{SERVO_RAIL_V}, {SERVO_DROPOUT_V})",
        ]
        for name in ports.values():
            if name == "pan":
                continue
            motor = servo.profile(name, SERVO_RAIL_V)
            lines += [f"R{name} {rail} {name} {lead_ohm(name, motor)}", f"I{name} {name} 0 {motor['stall_a']}"]
        lines += [
            f"Bcore_{core} {vbat} {core} v=max(V({vbat})-{CORE_V}, {CORE_DROPOUT_V})",
            f"Iwifi_{core} {core} 0 {WIFI_TX_A}",
        ]
    return "\n".join(lines)


def worst_case():
    """Every servo at stall and both Cores bursting, DC (no bulk capacitance rides the bursts out, and it outlasts the
    protector's delay), on a nominal pack and at the charge where it cuts the pack: the pack's charge, resting voltage,
    resistance and loaded cells, the voltage at each servo and each Core's 3.3 V, the current from the pack and into
    each shield."""

    def solve(soc):
        v = operating_point(mech(soc))
        a = (v["cells"] - v["pack"]) / pack_ohm(soc)
        return v, a

    def at(soc):
        v, a = solve(soc)
        return {
            "soc": round(soc, 4),
            "pack_v": round(pack_ocv(soc), 3),
            "pack_ohm": round(pack_ohm(soc), 3),
            "cells_v": round(cells_v(soc, a), 3),
            "pack_a": round(a, 3),
            "shield_a": {
                core: round((v["switch_out"] - v[f"{core}_vbat"]) / (XH_LEAD_MM * NECK_OHM_PER_MM), 3)
                for core in CHANNELS
            },
            "servo_v": {name: round(v[name], 3) for ports in CHANNELS.values() for name in ports.values()},
            "core_v": {core: round(v[core], 3) for core in CHANNELS},
        }

    nominal = at(brentq(lambda s: pack_ocv(s) - PACK_V["nominal"], 0, 1))
    cutoff = at(brentq(lambda s: cells_v(s, solve(s)[1]) - PACK_V["cutoff"], 0, 1))
    return {
        "cap_a": CAP_A,
        "servo_min_v": SERVO_MIN_V,
        "servos": {name: servo.profile(name, SERVO_RAIL_V) for ports in CHANNELS.values() for name in ports.values()},
        "brownout_v": BROWNOUT_V,
        "cutoff_delay_ms": CUTOFF_DELAY_MS,
        "nominal": nominal,
        "cutoff": cutoff,
    }


if __name__ == "__main__":
    print(json.dumps(worst_case(), indent=1))
