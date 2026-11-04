"""The Mech's shared data (mm, degrees): the bought hardware's vendor STEP frames, the Cores' servos, the Themes, the
Colour groups and materials of the printed parts, and the Mech's documents. The
physical Mech runs on CHANNELS (the noggin service, the eye program). Pure Python, no imports."""

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
# The servos by the names the remote config and calibration use, and their Mech labels (Stage 1's horns, model/stages.py
# eyes_sub). Core 1 drives the eye gimbal (docs/build/wiring.md servo ports, #896): a lid servo per eye, one yaw and
# one pitch servo for both eyes; Core 2 tilt/mouth/pan.
CHANNELS = {"core1": {1: "l_lid", 2: "yaw", 3: "r_lid", 4: "pitch"}, "core2": {1: "tilt", 2: "mouth", 3: "pan"}}
SERVO_LABEL = {
    "l_lid": "L lid",
    "yaw": "yaw",
    "r_lid": "R lid",
    "pitch": "pitch",
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


# Themes (#805, #819, docs/adr/0022): the Mech's look on four axes, a Shape and a Palette per category (the
# Skeleton: the PETG parts, the Skin: the PLA Shells). The Palettes of a category share its Colour groups, so any paints
# any Shape; each prints each group in one filament, at most 4 a Palette: (line, name, code, hex), the hex its slicer's
# filaments_color_codes.json (the picks' research: ADR 0022)
_BLACK = ("PETG Basic", "Black", "30105", "#000000")
THEMES = {
    "Skeleton shape": ("realistic", "mechanical"),  # drawn as Bones, or in boxes and cylinders (MECHANICAL)
    "Skeleton palette": {
        "anatomical": {
            "Bones": ("PETG Basic", "Dark Beige", "30403", "#DBC8B6"),
            "Joints": ("PETG Matte", "White", "35100", "#FFFFFF"),
            "Linkages": ("PETG Matte", "Pink", "35700", "#FABBCB"),  # Cansin, 2026-11-03: not red, nor dark brown
            "Mounts": _BLACK,
        },
        "robot": {
            "Bones": ("PETG Matte", "Gray", "35102", "#7F7E83"),
            "Joints": _BLACK,
            "Linkages": ("PETG Basic", "Gray", "30107", "#7F7E83"),
            "Mounts": _BLACK,
        },
        "black": dict.fromkeys(("Bones", "Joints", "Linkages", "Mounts"), _BLACK),
    },
    "Skin shape": (SKINLESS := "none", "morty", "bart", "cansin"),  # none: the Skeleton bare, the stills' look (#876)
    # face: face, ears, nose, lids (Bart's spikes); hair: hair, brows; eye whites: and teeth; accessories: Cansin's
    # sunglasses, in a colour of its own Palette's in the others
    "Skin palette": {
        "morty": {
            "face": ("PLA Basic", "Beige", "10201", "#F7E6DE"),
            "hair": (brown := ("PLA Basic", "Cocoa Brown", "10802", "#6F5034")),
            "pupils": brown,  # jagged
            "clothes": ("PLA Matte", "Lemon Yellow", "11400", "#F7D959"),  # shirt and collar
            "eye whites": ("PLA Basic", "Jade White", "10100", "#FFFFFF"),
            "accessories": brown,
        },
        "bart": {
            "face": (yellow := ("PLA Basic", "Sunflower Yellow", "10402", "#FEC600")),
            "hair": yellow,  # the spikes
            "pupils": (charcoal := ("PLA Matte", "Charcoal", "11101", "#000000")),  # dots
            "clothes": ("PLA Matte", "Scarlet Red", "11200", "#DE4343"),  # shirt and collar
            "eye whites": ("PLA Matte", "Ivory White", "11100", "#FFFFFF"),
            "accessories": charcoal,
        },
        "default": {  # #813: PLA Pure, all four owned
            "face": ("PLA Pure", "Milky Pink", "17200", "#F7CED7"),
            "hair": (black := ("PLA Pure", "Absolute Black", "17101", "#000000")),
            "pupils": black,
            "clothes": (white := ("PLA Pure", "Pure White", "17100", "#FFFFFF")),  # jacket and tee, one Shell
            "eye whites": white,
            "accessories": ("PLA Pure", "Apricot", "17300", "#FFB673"),  # the sunglasses
        },
    },
}
# Presets (#819): a named Theme, its value on each axis in THEMES' order; the first the default, which the README, the
# site's first visit and the default pictures show. A Skin shape without its own Shells yet (SKINS) wears Morty's.
PRESETS = {
    name: dict(zip(THEMES, axes, strict=True))
    for name, axes in {
        "Default build": ("mechanical", "black", SKINLESS, "default"),  # no Skin, the default Skin palette (#889)
        "Morty": ("realistic", "anatomical", "morty", "morty"),
        "Bart": ("realistic", "anatomical", "bart", "bart"),
    }.items()
}
THEME = next(iter(PRESETS.values()))
# a document's name in each Skeleton shape: its name as Bones, the first's, then this (-mechanical)
SKELETON_SUFFIX = {v: f"-{v}" if i else "" for i, v in enumerate(THEMES["Skeleton shape"])}


def slug(preset):
    """A Preset's name in an address and a picture's: "default-build"."""
    return preset.lower().replace("'", "").replace(" ", "-")


def shape(doc):
    """A document's Skeleton shape: the one its name, less its Skin's (undressed), ends in (-mechanical), else the
    first."""
    doc = undressed(doc)
    return next((v for v, s in SKELETON_SUFFIX.items() if s and doc.endswith(s)), THEMES["Skeleton shape"][0])


def theme(doc):
    """A document's Theme: the first Preset in its Skeleton shape (the GLB's colours, which the viewer repaints)."""
    return next(t for t in PRESETS.values() if t["Skeleton shape"] == shape(doc))


def filament(group, theme):
    """The filament a Colour group is printed in under a Theme, its Palette's: (line, name, code, hex)."""
    return next(THEMES[a][v][group] for a, v in theme.items() if a.endswith("palette") and group in THEMES[a][v])


# Each spool variant from its maker's TDS (100% infill, ISO 527 tensile; docs/research/2026-11-02-literature-cams-am.md,
# 2026-10-31-filament.md), in-layer (xy) and across layers (z, #626). PETG for the Mech's skeleton (#51): HF is the
# worst case until the spool's variant is confirmed.
MATERIALS = {
    "PLA Pure": {"density_g_cm3": 1.24, "E_mpa": {"xy": 2481, "z": 2196}, "tensile_mpa": {"xy": 51.5, "z": 30.0}},
    "PETG HF": {"density_g_cm3": 1.28, "E_mpa": {"xy": 1810, "z": 1540}, "tensile_mpa": {"xy": 34.0, "z": 23.0}},
    "PETG Basic": {"density_g_cm3": 1.25, "E_mpa": {"xy": 1460, "z": 1120}, "tensile_mpa": {"xy": 48.0, "z": 39.0}},
}
# Printed parts: each one's Colour group (THEMES) and material (model/mjcf.py mass() reads it)
_SKELETON = {
    "Bones": ("gimbal frame", "cervical carrier", "head mount", "jaw", "test stand"),
    "Joints": ("eyeball core", "yaw yoke", "bail", "nod plate"),
    "Linkages": (
        "tie-bar",
        "push-rod",
        "pitch bar",
        "lid bar",
        "lid link",
        "L upper lid",
        "R upper lid",
        "L lower lid",
        "R lower lid",
        "jaw bar",
    ),
    "Mounts": ("torso", "torso lid", "cranium tray"),  # the realistic skull's black box pedestal (#838)
}
PRINTED = {
    **{name: (group, "PETG HF") for group, names in _SKELETON.items() for name in names},
    "L eyeball cap": ("eye whites", "PLA Pure"),
    "R eyeball cap": ("eye whites", "PLA Pure"),
}
# The Skin shapes drawn so far (model/skin.py, model/printed/skin.py), each its sub-assembly: Morty's (#665) the
# documents' own, the eyeball caps above his too; Cansin's (#813) and Bart's (#807) on the same Seats. Each one's Shells
# by Colour group
SKINS = {"morty": "morty", "cansin": "cansin", "bart": "bart"}
_LIDS = tuple(f"{s} {lid} lid cover" for s in "LR" for lid in ("upper", "lower"))
_SHELLS = {
    "morty": {
        "face": ("face", "mouth cover", *_LIDS),  # the face with his nose and ears
        "hair": ("hair",),
        "pupils": ("L pupil", "R pupil"),  # jagged
        "clothes": ("shirt front", "shirt back"),
    },
    "cansin": {
        "face": ("face", "mouth cover", *_LIDS),  # with the nose and ears
        "hair": ("hair", "L brow", "R brow"),  # the hair tufted on top
        "pupils": ("L pupil", "R pupil"),  # dots, each in a plug that fills the cap's jagged seat
        "eye whites": ("L pupil plug", "R pupil plug", "teeth"),
        "clothes": ("shirt front", "shirt back"),  # the jacket over the tee, its lapels on the front
        "accessories": ("sunglasses",),  # aviators hooked on the tee's neckline
    },
    "bart": {
        "face": ("face", "mouth cover", *_LIDS),  # with the nose and ears
        "hair": ("hair",),  # his crown, the spikes on it
        "pupils": ("L pupil", "R pupil"),  # dots, each in a plug that fills the cap's jagged seat, as Cansin's
        "eye whites": ("L pupil plug", "R pupil plug"),
        "clothes": ("shirt front", "shirt back"),
    },
}
PRINTED |= {
    f"{skin} {name}": (group, "PLA Pure")
    for skin, groups in _SHELLS.items()
    for group, names in groups.items()
    for name in names
}
# Each Skeleton part is drawn in two styles (#704, model/printed): as Bones (realistic) under its own name, mechanical
# under this suffix
MECHANICAL = " mechanical"
PRINTED |= {name + MECHANICAL: v for name, v in PRINTED.items() if v[1].startswith("PETG")}
# The realistic Skeleton's skull (#838; the Skeleton scene, model/skeleton, docs/adr/0025): meshes under their sources' licences (docs/adr/0023), on
# the realistic documents alone (SKULL_SUB): the mechanical Skeleton has none. Its bones as they show bare (SKULL), and
# the skull and mandible carved round every Skin's Shells too (WORN), printed to wear a Skin (Cansin, 2026-11-03): the
# documents, which wear one, carry the worn ones; the pictures' bare look shows the bare ones
SKULL = ("skull", "mandible", "atlas", "axis")
WORN = {"skull": "worn skull", "mandible": "worn mandible"}
BONES = (*SKULL, *WORN.values())
PRINTED |= dict.fromkeys(BONES, ("Bones", "PETG HF"))
SKULL_SUB = "skull"

# The Mech (#51, #629), clean-room (#618's licence check): only our Envelopes of the hardware we own and our own
# parts: the eye gimbal (#630, model/gimbal.py) on the neck and jaw (#641, model/neck.py) on the Torso, one document per
# head variant (#686, model/base.py) with the sub-assemblies that carry its boards, all in the head's frame, the Torso's
# foot on z 0 (base.TORSO, model/test_neck.py).
_HEAD = ((0, -150, 177), X, Z)
MECH = {
    f"mech-{v}": {sub: _HEAD for sub in ("neck", "jaw", "eyes", "cranium", "base", *carriers)}
    for v, carriers in (("back", [SKINS["morty"], SKULL_SUB]),)  # Back alone since Cansin picked it (#712); Morty's
    # Skin on it (#665), the other Skins on DRESSED's
}
# The Mech's Stages (#720), cumulative, for ease of build: 1 the eye block on its test stand with the eyes Core, the
# stand's foot on z 0 (base.STAND_Z, model/test_base.py); 2 adds the Torso with both Cores (#838), the neck and the head
# mount; 3 adds the jaw and the mouth: the whole Mech, the leading head variant's document
_STAND = ((0, -150, 78), X, Z)
STAGES = {
    "stage1": {"eyes": _STAND, "stand": _STAND},
    "stage2": {sub: _HEAD for sub in ("neck", "eyes", "cranium", "base")},
    **dict([next(iter(MECH.items()))]),
}
# each document also in every other Skeleton (#704, #805: theme()), under -<value>: realistic and mechanical, the skull
# the realistic one's alone
MECH |= {
    doc + s: {k: f for k, f in subs.items() if k != SKULL_SUB}
    for doc, subs in MECH.items()
    for s in SKELETON_SUFFIX.values()
    if s
}
STAGES |= {
    doc + s: {k: f for k, f in subs.items() if k != SKULL_SUB}
    for doc, subs in STAGES.items()
    for s in SKELETON_SUFFIX.values()
    if s
}
# Stage 3 in each other Skin shape drawn (#813): each document of MECH under -<shape> after its Skeleton's suffix (the
# viewer's GLB names, site/src/viewer/state.mjs), that Skin's Shells for Morty's; not simulated: Cansin's sit on
# Morty's Seats, which his document's sim holds
DRESSED = {
    f"{doc}-{skin}": {(sub if sub != SKINS["morty"] else SKINS[skin]): f for sub, f in subs.items()}
    for doc, subs in MECH.items()
    for skin in list(SKINS)[1:]
}


def undressed(doc):
    """The document a DRESSED one wears its Skin on (its name less -<shape>), else itself."""
    return next((doc.removesuffix(f"-{s}") for s in list(SKINS)[1:] if doc.endswith(f"-{s}")), doc)


def dressed(doc, skin):
    """The document in the Skin shape `skin`: its DRESSED one where that Skin is drawn on it, else itself."""
    return f"{doc}-{skin}" if f"{doc}-{skin}" in DRESSED else doc


# Physics runs on the mechanical documents alone (#809): each Bone is carved from its mechanical part, so clearance,
# overlap, torque, strength, the sim and its gates measured there hold for realistic too, whose figures are these. The
# sim takes the whole Mech and Stage 1 (its test stand): Stage 2 moves as the whole Mech less parts
SIMULATED = [d for d in STAGES if d.endswith(SKELETON_SUFFIX["mechanical"]) and not d.startswith("stage2")]
