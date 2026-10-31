"""One CyberBrick electronics set on the PandT base (PT frame): receiver shield n with its Core on the base's standoff set n
(receiver 1 front, 2 back: guide p.19), its switch board and its battery, with Ports on the connectors. Inlined via
`# include: model/electronics.py` after fusion_lib by model/base.py (set 1) and model/stack.py (set 2)."""

import math

import adsk.core
import adsk.fusion

# Ports on the receiver STEP: geometry.RECEIVER_STEP. Core 1 drives the eyes (docs/build-notes.md), Core 2
# tilt/mouth/pan (guide step 10, config JSON).
CHANNELS = {
    1: {"PWM1": "L lid", "PWM2": "L eye", "PWM3": "R lid", "PWM4": "R eye"},
    2: {"PWM1": "tilt", "PWM2": "mouth", "PWM3": "pan"},
}
# Our build runs one pack and one switch board per shield (docs/build-notes.md); the base has one battery box and one
# pair of switch standoffs, so set 2 is inferred: switch boards hang one per standoff (as the eyes-only build hangs
# its switch on a single post), battery 2 lies on top of battery 1 in the box.
SWITCH_AT = {1: STANDOFFS["pt_base"]["switch"][0], 2: STANDOFFS["pt_base"]["switch"][1]}  # [I]
BATTERY_STACK_Z = 16.3  # pack height: the second pack's floor sits on the first pack's top [I]


def electronics(root, n, reuse, ports):
    """Insert set n, oriented as the designer's build (XH socket to the front, Core on top: the STEP has the Core under
    the shield, flipped about the PCB mid-plane). Appends (occurrence, Port name, world point) to `ports`; the build
    places the Ports after parts_end."""
    stand = STANDOFFS["pt_base"]
    flip = adsk.core.Matrix3D.create()
    flip.setToRotation(math.pi, vector(Z), point((0, 0.8, 0)))
    receiver_m = align(mean(stand[f"receiver_{n}"]), (0, -1, 0), (-1, 0, 0))
    receiver = insert_part(root, "receiver shield", f"receiver shield {n}", receiver_m, reuse=reuse)
    core = insert_part(
        root, "Core", f"Core {n} (flipped onto the shield top, per photo)", matmul(receiver_m, flip), reuse=reuse
    )
    core_pcb = descendant(core, "CORE")
    usb = core_pcb.component.bRepBodies.itemByName("Body3").createForAssemblyContext(core_pcb).boundingBox
    assert usb.minPoint.z * 10 > receiver_m.translation.z * 10, "Core must sit above the shield"
    for header, p in RECEIVER_STEP["headers"].items():
        w = point(p)
        w.transformBy(receiver_m)
        ports.append(
            (
                receiver,
                f"Core {n} servo {header}" + (f" ({CHANNELS[n][header]})" if header in CHANNELS[n] else ""),
                (w.x * 10, w.y * 10, w.z * 10),
            )
        )
    w = point(RECEIVER_STEP["xh_power"])
    w.transformBy(receiver_m)
    ports.append((receiver, f"Core {n} XH power", (w.x * 10, w.y * 10, w.z * 10)))
    ports.append(
        (core, f"Core {n} USB-C", tuple((getattr(usb.minPoint, c) + getattr(usb.maxPoint, c)) * 5 for c in "xyz"))
    )
    insert_part(
        root,
        "switch board",
        f"switch board {n}" + (" (inferred)" if n == 2 else ""),
        align(SWITCH_AT[n], (-1, 0, 0), Y, SWITCH_STEP["hole"]),
        reuse=reuse,
    )  # hole on the standoff top
    pocket = BATTERY_POCKET_PT
    battery_at = (
        sum(pocket["x"]) / 2,
        pocket["y"][0],
        pocket["floor_z"] - BATTERY_STEP["floor_z"] + (n - 1) * BATTERY_STACK_Z,
    )
    battery = insert_part(
        root, "battery", "battery 1" if n == 1 else "battery 2 (inferred)", align(battery_at, X, Z), reuse=reuse
    )
    ports.append(
        (battery, f"battery {n} lead", add(battery_at, BATTERY_STEP["plug"]))
    )  # the pack's plug; wiring is out of scope
