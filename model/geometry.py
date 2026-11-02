"""The Mech's shared data (mm, degrees): the bought hardware's vendor STEP frames, the Cores' servos, the spools and
materials of the printed parts, and the next Mech's documents. Today's Mech left the model (#720): the physical Mech
still runs on CHANNELS (the noggin service, the eye program). Pure Python, no imports."""

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)

# Vendor STEP files, local mm (measured 2026-10-31, servo and horns re-read with OCP for #62). Servo: tab plate
# z -2.3..0, shaft at x=16.69 pointing -Z; the horn's inner face sits 11.52 beyond the z -0.65 plane (spline tip z -14.52
# on the 2.35 deep bore). Horn = the kit's short single arm ("half arm1"): hub at (0,20,0), 4.15 tall, spline side
# z 4.15, arm (1.6 thick, holes every 2 mm along +X, r 0.5) on the outer face z 0, its pin hole 12.75 from the hub.
SERVO_STEP = {
    "shaft": (16.69, 5.9, -0.65),
    "horn_seat": 11.52,
    # where the lead leaves the servo: the STEP's three wires run straight on to x=42, the real lead is flexible, so the
    # mesh is cut there (the tab end)
    "lead": (27.7, 5.9, 11.0),
}
HORN_STEP = {"hub": (0.0, 20.0, 0.0), "pin": 12.75, "height": 4.15}
# Battery STEP, local mm: pack floor z=-8.15, pack along +Y from 0 (51.2 long, 28.4 wide), lead fused to the pack body
# beyond y=56
BATTERY_STEP = {"floor_z": -8.15, "lead_y": 56.0}
# The servos by the names the remote config and calibration use, and their Mech labels. Core 1 drives the eyes
# (docs/build/wiring.md servo ports), Core 2 tilt/mouth/pan (guide step 10, the designer's config JSON).
CHANNELS = {"core1": {1: "l_lid", 2: "l_eye", 3: "r_lid", 4: "r_eye"}, "core2": {1: "tilt", 2: "mouth", 3: "pan"}}
SERVO_LABEL = {
    "l_lid": "L lid",
    "l_eye": "L eye",
    "r_lid": "R lid",
    "r_eye": "R eye",
    "tilt": "tilt",
    "mouth": "jaw",
    "pan": "pan",
}


def _unit(v):
    n = sum(c * c for c in v) ** 0.5
    return tuple(c / n for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def align_rows(to_origin, to_x=None, to_z=None, from_origin=(0, 0, 0), from_x=(1, 0, 0), from_z=(0, 0, 1)):
    """4x4 rows (mm) taking the local frame (from_*) onto the world frame (to_*); axes default to identity, x is made
    normal to z (stepped links), y = z cross x. model/stages.py wraps it in numpy (stages.align)."""

    def frame(o, x, z):
        z = _unit([float(c) for c in z])
        dot = sum(float(a) * b for a, b in zip(x, z))
        x = _unit([float(a) - dot * b for a, b in zip(x, z)])
        return [float(c) for c in o], x, _cross(z, x), z

    o1, *b1 = frame(from_origin, from_x, from_z)
    o2, *b2 = frame(to_origin, X if to_x is None else to_x, Z if to_z is None else to_z)
    r = [[sum(w[i] * v[j] for w, v in zip(b2, b1)) for j in range(3)] for i in range(3)]
    t = [o2[i] - sum(r[i][j] * o1[j] for j in range(3)) for i in range(3)]
    return [r[0] + [t[0]], r[1] + [t[1]], r[2] + [t[2]], [0.0, 0.0, 0.0, 1.0]]


# Printed parts: spool and material per part (model/mjcf.py mass() reads theirs). The next Mech's Skeleton in black PETG,
# its Shells in PLA Pure (#51, GLOSSARY).
SPOOLS = {"Milky Pink": "#F7CED7", "Pure White": "#FFFFFF", "Absolute Black": "#000000", "Apricot": "#FFB673"}
# Each spool variant from its maker's TDS (100% infill, ISO 527 tensile; docs/research/2026-11-02-literature-cams-am.md,
# 2026-10-31-filament.md), in-layer (xy) and across layers (z, #626). PETG for the next Mech's skeleton (#51): HF is the
# worst case until the spool's variant is confirmed.
MATERIALS = {
    "PLA Pure": {"density_g_cm3": 1.24, "E_mpa": {"xy": 2481, "z": 2196}, "tensile_mpa": {"xy": 51.5, "z": 30.0}},
    "PETG HF": {"density_g_cm3": 1.28, "E_mpa": {"xy": 1810, "z": 1540}, "tensile_mpa": {"xy": 34.0, "z": 23.0}},
    "PETG Basic": {"density_g_cm3": 1.25, "E_mpa": {"xy": 1460, "z": 1120}, "tensile_mpa": {"xy": 48.0, "z": 39.0}},
}
PRINTED = {
    **{
        name: ("Absolute Black", "PETG HF")
        for name in (
            "next eyeball core",
            "next yaw yoke",
            "next tie-bar",
            "next bail",
            "next push-rod",
            "next pitch bar",
            "next lid bar",
            "next lid link",
            "next L upper lid",
            "next R upper lid",
            "next L lower lid",
            "next R lower lid",
            "next gimbal frame",
            "next neck mount",
            "next pan yoke",
            "next head mount",
            "next jaw",
            "next pan bar",
            "next tilt bar",
            "next jaw bar",
            "next torso",
            "next board rack",
            "next test stand",
        )
    },
    "next L eyeball cap": ("Pure White", "PLA Pure"),
    "next R eyeball cap": ("Pure White", "PLA Pure"),
}
# Each Skeleton part is drawn in two styles (#704, model/printed): as Bones under its own name, plain under this suffix
PLAIN = " plain"
PRINTED |= {name + PLAIN: v for name, v in PRINTED.items() if name.startswith("next ") and v[1].startswith("PETG")}

# The next Mech (#51, #629), clean-room (#618's licence check): only our Envelopes of the hardware we own and our own
# parts: the eye gimbal (#630, model/gimbal.py) on the neck and jaw (#641, model/neck.py) on the Torso, one document per
# head variant (#686, model/base.py) with the sub-assemblies that carry its boards, all in the head's frame, the Torso's
# foot on z 0 (base.TORSO, model/test_neck.py).
_HEAD = ((0, -150, 153), X, Z)
NEXT = {
    f"next-mech-{v}": {sub: _HEAD for sub in ("next-neck", "next-jaw", "next-eyes", "next-base", *carriers)}
    for v, carriers in (("back", ["next-back"]),)  # Back alone since Cansin picked it (#712)
}
# The next Mech's Stages (#720), cumulative, for ease of build: 1 the eye block on its test stand with the eyes Core, the
# stand's foot on z 0 (base.STAND_Z, model/test_base.py); 2 adds the Torso, the neck, the head mount and the boards' rack
# with the neck Core; 3 adds the jaw and the mouth: the whole Mech, the leading head variant's document
_STAND = ((0, -150, 107), X, Z)
STAGES = {
    "next-stage1": {"next-eyes": _STAND, "next-stand": _STAND},
    "next-stage2": {sub: _HEAD for sub in ("next-neck", "next-eyes", "next-base", "next-back")},
    **dict([next(iter(NEXT.items()))]),
}
# each document also with its Skeleton plain (#704, PLAIN): the two looks, Bones and plain
NEXT |= {doc + "-plain": subs for doc, subs in NEXT.items()}
STAGES |= {doc + "-plain": subs for doc, subs in STAGES.items()}
