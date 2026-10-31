"""The CyberBrick electronics on the PandT base (PT frame): receiver shield n with its Core plugged in under it on the
base's standoff set n (1 front, 2 back: guide p.19); set 1 adds the one switch board, the pack and the eyes build's cable
holder (pan-tilt guide p.10, p.23: one pack and switch board feed both shields through a Y lead), with Ports on the
connectors. Inlined via `# include: model/electronics.py` after fusion_lib by model/base.py (set 1) and model/stack.py
(set 2)."""


def electronics(root, n, reuse, ports):
    """Insert set n where geometry puts it (receiver_at, switch_at, battery_at, CABLE_HOLDER_AT). Appends (occurrence,
    Port name, world point) to `ports`; the build places the Ports after parts_end."""
    receiver_m = align(receiver_at(n), *RECEIVER_AXES)
    receiver = insert_part(root, "receiver shield", f"receiver shield {n}", receiver_m, reuse=reuse)
    core = insert_part(root, "Core", f"Core {n}", receiver_m, reuse=reuse)  # under the shield, as the STEP has it
    core_pcb = descendant(core, "CORE")
    usb = core_pcb.component.bRepBodies.itemByName("Body3").createForAssemblyContext(core_pcb).boundingBox
    assert usb.maxPoint.z * 10 < receiver_m.translation.z * 10, "Core must sit under the shield"
    for header, p in RECEIVER_STEP["headers"].items():
        servo = CHANNELS[f"core{n}"].get(int(header[3:]))
        label = f"Core {n} servo {header}" + (f" ({SERVO_LABEL[servo]})" if servo else "")
        ports.append((receiver, label, at(receiver_m, p)))
    ports.append((receiver, f"Core {n} XH power", at(receiver_m, RECEIVER_STEP["xh_power"])))
    ports.append(
        (core, f"Core {n} USB-C", tuple((getattr(usb.minPoint, c) + getattr(usb.maxPoint, c)) * 5 for c in "xyz"))
    )
    if n != 1:
        return
    switch_m = align(*switch_at(), SWITCH_STEP["hole"])  # hole on its post top
    switch = insert_part(root, "switch board", "switch board 1", switch_m, reuse=reuse)
    ports.append((switch, "switch board 1 in", at(switch_m, SWITCH_STEP["in"])))
    ports.append((switch, "switch board 1 out", at(switch_m, SWITCH_STEP["out"])))
    battery_m = align(*battery_at())
    battery = insert_part(root, "battery", "battery 1", battery_m, reuse=reuse)
    ports.append((battery, "battery 1 lead", at(battery_m, BATTERY_STEP["plug"])))  # the pack's plug
    insert_part(root, "wire keeper", "cable holder", align(*CABLE_HOLDER_AT, **CABLE_HOLDER_FROM), reuse=reuse)
