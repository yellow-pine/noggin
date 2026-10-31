"""One CyberBrick electronics set on the PandT base (PT frame): receiver shield n with its Core on the base's standoff set n
(receiver 1 front, 2 back: guide p.19), its switch board and its battery, with Ports on the connectors. Inlined via
`# include: model/electronics.py` after fusion_lib by model/base.py (set 1) and model/stack.py (set 2)."""

import math

import adsk.core
import adsk.fusion


def electronics(root, n, reuse, ports):
    """Insert set n where geometry puts it (receiver_at, CORE_FLIP, switch_at, battery_at). Appends (occurrence, Port
    name, world point) to `ports`; the build places the Ports after parts_end."""
    axis, deg, about = CORE_FLIP
    flip = adsk.core.Matrix3D.create()
    flip.setToRotation(math.radians(deg), vector(axis), point(about))
    receiver_m = align(receiver_at(n), *RECEIVER_AXES)
    receiver = insert_part(root, "receiver shield", f"receiver shield {n}", receiver_m, reuse=reuse)
    core = insert_part(
        root, "Core", f"Core {n} (flipped onto the shield top, per photo)", matmul(receiver_m, flip), reuse=reuse
    )
    core_pcb = descendant(core, "CORE")
    usb = core_pcb.component.bRepBodies.itemByName("Body3").createForAssemblyContext(core_pcb).boundingBox
    assert usb.minPoint.z * 10 > receiver_m.translation.z * 10, "Core must sit above the shield"
    for header, p in RECEIVER_STEP["headers"].items():
        servo = CHANNELS[f"core{n}"].get(int(header[3:]))
        label = f"Core {n} servo {header}" + (f" ({SERVO_LABEL[servo]})" if servo else "")
        ports.append((receiver, label, at(receiver_m, p)))
    ports.append((receiver, f"Core {n} XH power", at(receiver_m, RECEIVER_STEP["xh_power"])))
    ports.append(
        (core, f"Core {n} USB-C", tuple((getattr(usb.minPoint, c) + getattr(usb.maxPoint, c)) * 5 for c in "xyz"))
    )
    insert_part(
        root,
        "switch board",
        f"switch board {n}" + (" (inferred)" if n == 2 else ""),
        align(switch_at(n), *SWITCH_AXES, SWITCH_STEP["hole"]),
        reuse=reuse,
    )  # hole on the standoff top
    battery_pos = battery_at(n)
    battery = insert_part(
        root, "battery", "battery 1" if n == 1 else "battery 2 (inferred)", align(battery_pos, X, Z), reuse=reuse
    )
    ports.append(
        (battery, f"battery {n} lead", add(battery_pos, BATTERY_STEP["plug"]))
    )  # the pack's plug; wiring is out of scope
