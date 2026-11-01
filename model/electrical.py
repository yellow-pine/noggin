"""The Mech's supply as a SPICE circuit (PySpice on ngspice), figures from the datasheets
(docs/research/2026-10-31-electrical.md), and the leads the cable corridors route. Run: .venv/bin/python -m
model.electrical. worst_case() is merged into the Mech-wide (noggin-stage3) report and leads() routed by
model/cables.py. It reads only CHANNELS and the lead lengths."""

import importlib.util
import json
import os
import re
import sys

# PySpice dlopens libngspice by bare name (PySpice/Spice/NgSpice/Shared.py setup_platform, NGSPICE_LIBRARY_PATH
# overrides it: https://pyspice.fabrice-salvaire.fr/releases/v1.5/faq.html); Homebrew's lib is not on macOS's dyld path.
if sys.platform == "darwin":
    os.environ.setdefault("NGSPICE_LIBRARY_PATH", "/opt/homebrew/lib/libngspice.dylib")

from PySpice.Spice.Netlist import Circuit  # noqa: E402  (after the library path)
from PySpice.Spice.NgSpice.Shared import NgSpiceShared  # noqa: E402

from model.geometry import CHANNELS, SERVO_LABEL  # noqa: E402

# ngspice 42 (Ubuntu noble, CI) names its linear solver on stderr ("Using SPARSE 1.3 as Direct Linear Solver"), and
# PySpice 1.5 fails a command on any stderr line but "Warning:" (Shared.py _send_char), then calls send_char, the hook
# it leaves to subclasses: there, every other stderr line still fails the command.
SOLVER_NOTE = re.compile(r"Using .+ as Direct Linear Solver")


def _send_char(self, message, ngspice_id):
    self._error_in_stderr = any(
        not (m.startswith("Warning:") or SOLVER_NOTE.fullmatch(m.strip())) for m in self._stderr
    )
    return 0


NgSpiceShared.send_char = _send_char

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
# board is taken as 100 [I] (the battery box lead's length is not published).
SERVO_LEAD_MM, XH_LEAD_MM = 250, 100


CAP_A = 3.0  # shield max and pack continuous discharge are both 3 A; one pack feeds both shields (pan-tilt guide p.10)
# The pack, 2S 14500: 7.4 V nominal, over-discharge cutoff 5.8 V (its datasheet, in the research note). Its internal
# resistance is not published [I]: two cells at <= 85 mohm each (AC 1 kHz, a 14500 800 mAh cell datasheet,
# https://www.dnkpower.com/wp-content/uploads/2022/08/14500-battery-datasheet.pdf) plus 40 mohm for the protection
# board's MOSFETs.
PACK_V = {"nominal": 7.4, "cutoff": 5.8}
PACK_OHM = 2 * 0.085 + 0.040
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


def operating_point(circuit):
    """{node: volts} at the circuit's DC operating point (ngspice, shared library)."""
    op = circuit.simulator(simulator="ngspice-shared").operating_point()
    return {str(n): float(op[n][0]) for n in op.nodes}


def mech(pack_v):
    """The stock wiring at its worst: pack, its lead, the switch board, the Y lead's branch to each shield; per shield
    its standby, the 5 V servo rail and every servo at stall on its lead, and the Core's 3.3 V in a transmit burst.
    A regulator is a behavioural source in series, dropping what is above its output or at least its dropout."""
    c = Circuit("noggin supply")
    c.V("pack", "cells", c.gnd, pack_v)
    c.R("pack", "cells", "pack", PACK_OHM)
    c.R("pack_lead", "pack", "switch_in", XH_LEAD_MM * OHM_PER_MM)
    c.R("switch", "switch_in", "switch_out", SWITCH_OHM)
    for core, ports in CHANNELS.items():
        vbat, rail = f"{core}_vbat", f"{core}_rail"
        c.R(f"y_{core}", "switch_out", vbat, XH_LEAD_MM * OHM_PER_MM)
        c.I(f"shield_{core}", vbat, c.gnd, SHIELD_STANDBY_A)
        c.B(f"rail_{core}", vbat, rail, v=f"max(V({vbat})-{SERVO_RAIL_V}, {SERVO_DROPOUT_V})")
        for name in ports.values():
            c.R(name, rail, name, SERVO_LEAD_MM * OHM_PER_MM)
            c.I(name, name, c.gnd, STALL_A)
        c.B(f"core_{core}", vbat, core, v=f"max(V({vbat})-{CORE_V}, {CORE_DROPOUT_V})")
        c.I(f"wifi_{core}", core, c.gnd, WIFI_TX_A)
    return c


def worst_case():
    """Every servo at stall and both Cores bursting, DC (no bulk capacitance rides the bursts out), on a nominal and a
    cut-off pack: the voltage at each servo and each Core's 3.3 V, the current from the pack and into each shield."""
    out = {"cap_a": CAP_A, "servo_min_v": SERVO_MIN_V, "brownout_v": BROWNOUT_V}
    for case, pack_v in PACK_V.items():
        v = operating_point(mech(pack_v))
        out[case] = {
            "pack_v": pack_v,
            "pack_a": round((v["cells"] - v["pack"]) / PACK_OHM, 3),
            "shield_a": {
                core: round((v["switch_out"] - v[f"{core}_vbat"]) / (XH_LEAD_MM * OHM_PER_MM), 3) for core in CHANNELS
            },
            "servo_v": {name: round(v[name], 3) for ports in CHANNELS.values() for name in ports.values()},
            "core_v": {core: round(v[core], 3) for core in CHANNELS},
        }
    return out


def leads():
    """(lead, Port, Port, length mm) for every lead of the Mech: each servo from where its lead leaves the servo to its
    shield header (CHANNELS), the pack's lead to the switch board and the Y lead's two branches from the switch board to
    the shields. Port names are model/stages.py's ports; model/cables.py routes each
    from its first Port."""
    out = [("pack 1 -> switch 1", "battery 1 lead", "switch board 1 in", XH_LEAD_MM)]
    for n in (1, 2):
        out.append((f"switch 1 -> shield {n}", "switch board 1 out", f"Core {n} XH power", XH_LEAD_MM))
        for port, name in CHANNELS[f"core{n}"].items():
            out.append(
                (
                    f"{name} servo -> Core {n} PWM{port}",
                    f"{SERVO_LABEL[name]} servo lead",
                    f"Core {n} servo PWM{port}",
                    SERVO_LEAD_MM,
                )
            )
    return out


if __name__ == "__main__":
    print(json.dumps(worst_case(), indent=1))
