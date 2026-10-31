"""Measured Mech geometry as data (mm, degrees). Source: docs/research/2026-10-31-model.md.
Eyes frame: L eye centre at origin, +Y up, -Z front. PT frame: Z up, pan axis through (0,0).
Pure Python, no imports: scripts/fusion_run.py inlines this file into Fusion scripts.
"""

EYE_L = (0.0, 0.0, 0.0)
EYE_R = (59.0, 0.0, 0.0)
CENTRE_X = 29.5


def eyes_to_pt(p):
    x, y, z = p
    return (29.5 - x, z - 28.5, y + 81.5)


def pt_to_eyes(p):
    x, y, z = p
    return (29.5 - x, z - 81.5, y + 28.5)


def pt_to_eyes_standalone(p):
    """PandT base point -> eyes frame for the eyes-only build (no neck): the bracket v2 stem drops through the
    pan bearing recess at the PT origin (builder-confirmed) and the servo brackets' feet rest on the plate top
    (side photo), so plate top z=3 is y=-35.6."""
    x, y, z = p
    return (29.5 - x, z - 38.6, y + 15.5)


def mirror_x(p):
    """Reflect an eyes-frame point about the mech centreline x=29.5 (L side -> R side)."""
    x, y, z = p
    return (2 * CENTRE_X - x, y, z)


# Absolute servo angle limits in degrees from the designer's remote config; neutral is 90.
HORN_LIMITS = {
    "l_lid": (70, 120),
    "l_eye": (70, 110),
    "r_lid": (70, 120),
    "r_eye": (70, 110),  # eye +-20 [I]: the eyeball bar enters the bracket at +-25 in the model (inferred horn pivot)
    # tilt [I]: the config says 20, but at 20..29 the inferred tilt horn and bar sweep into the pan base's front chord
    # (contact from horn -61 deg, 1.05 mm deep at -70): the lower end stops at 30 until the tilt servo shaft is measured.
    "tilt": (30, 150),
    "rotate": (40, 160),
    # mouth [I]: the config says 0..180, but the jaws are modelled closed at neutral and the connector-bar four-bar only
    # has solutions on the opening side (horn -45..0 = jaw -40..0 deg; driven past 0 Fusion flips the jaw): one side only.
    "mouth": (50, 90),
}

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def _pivot(point, axis, frame="eyes", inferred=False):
    p = {"point": point, "axis": axis, "frame": frame}
    if inferred:
        p["inferred"] = True  # servo shaft offset from guides/photos, not the STLs
    return p


# Revolute axes. Points on the axis; "inferred" marks positions still open (+-4 mm).
PIVOTS = {
    "l_lid": _pivot(EYE_L, X),
    "r_lid": _pivot(EYE_R, X),
    "l_eye": _pivot(EYE_L, Y),
    "r_eye": _pivot(EYE_R, Y),
    "l_lid_horn": _pivot((-16.0, -13.5, 40.0), X, inferred=True),
    "r_lid_horn": _pivot((75.0, -13.5, 40.0), X, inferred=True),
    "l_eye_horn": _pivot((2.9, 0.0, 26.9), Y, inferred=True),
    "r_eye_horn": _pivot((56.1, 0.0, 26.9), Y, inferred=True),
    "jaw_hinge": _pivot((CENTRE_X, -49.6, 8.0), X),
    # Jaw horn at the servo's horn seat: tab plane x=75.9 (the mount lug's mid-plane) minus SERVO_STEP horn_seat, shaft -X
    # (body outboard through the lug window), shaft 5.34 below the body centre (z 23.1; 33.6 if the servo is the other way up) [I].
    "jaw_horn": _pivot((65.55, -48.6, 23.1), X, inferred=True),
    "pan": _pivot((0.0, 0.0, 0.0), Z, "pt"),
    "tilt": _pivot((0.0, -13.0, 33.4), X, "pt"),
    # PT horn pivots at the horn seat (tab plane + SERVO_STEP horn_seat), shaft offset 5.34 from the tab-hole midpoint
    # toward the near hole, as the eyes servos: tilt shaft -X on the pan-base tower, pan shaft +Z on the mounts [I].
    "tilt_horn": _pivot((12.15, 14.1, 18.4), X, "pt", inferred=True),
    "pan_horn": _pivot((-20.5, 38.1, 25.35), Z, "pt", inferred=True),
}

SERVO_TAB_SPACING = 27.8  # SG90 mounting tab hole pitch

# Measured servo tab-hole pairs (the two mounting screw holes).
SERVOS = {
    "l_lid": {"tab_holes": [(-5.4, -32.35, 40.0), (-5.4, -4.65, 40.0)], "frame": "eyes"},
    "r_lid": {"tab_holes": [(64.4, -32.35, 40.0), (64.4, -4.65, 40.0)], "frame": "eyes"},
    "l_eye": {"tab_holes": [(-6.0, -9.0, 26.9), (21.8, -9.0, 26.9)], "frame": "eyes"},
    "r_eye": {"tab_holes": [(65.0, -9.0, 26.9), (37.2, -9.0, 26.9)], "frame": "eyes"},
    "tilt": {"tab_holes": [(22.5, -5.04, 18.38), (22.5, 22.54, 18.38)], "frame": "pt"},
    "pan": {"tab_holes": [(-20.5, 29.55, 15.0), (-20.5, 57.35, 15.0)], "frame": "pt"},
    "jaw": {"tab_holes": [(75.9, -48.6, 14.43), (75.9, -48.6, 42.23)], "frame": "eyes"},
}

# Standoff tops. Receiver shield pattern is 23 x 24 [M]. Eyes base: the (29.5, 51/75) pair carries the wire
# keeper and the switch board hangs on the short post at the back edge (build photos 2026-10-31); its top y
# is inferred (+-2 mm).
STANDOFFS = {
    "eyes_base": {
        "receiver": [(-14.8, -25.6, 51.0), (8.2, -25.6, 51.0), (-14.8, -25.6, 75.0), (8.2, -25.6, 75.0)],
        "wire_keeper": [(29.5, -25.6, 51.0), (29.5, -25.6, 75.0)],
        "switch": [(8.24, -30.6, 92.5)],
    },
    "pt_base": {
        "receiver_1": [(26.0, 40.5, 13.0), (50.0, 40.5, 13.0), (26.0, 63.5, 13.0), (50.0, 63.5, 13.0)],
        "receiver_2": [(26.0, 73.5, 13.0), (50.0, 73.5, 13.0), (26.0, 96.5, 13.0), (50.0, 96.5, 13.0)],
        "switch": [(6.0, 68.5, 13.0), (6.0, 92.5, 13.0)],
        "switch_post": [(34.5, 108.5, 7.7)],  # the single back post the eyes-only build hangs the switch on (photo)
        "wire_keeper": [(-7.5, 40.5, 7.7), (7.5, 40.5, 7.7)],
    },
}

# Pivot-to-pivot hole spacing of each link.
BARS = {
    "eyelid_bar": 41.0,
    "eyelid_crank": 41.0,
    "tilt_bar": 20.0,
    "pan_bar": 15.0,
    "connector_bar": 31.4,
    "eyeball_bar": 27.0,
}

# Bambu STEP files, local mm (measured in Fusion 2026-10-31). Servo: tab holes along +X on the tab mid-plane,
# shaft at x=16.69 pointing -Z, horn seats on the boss top 10.35 beyond the tab plane. Horn = the kit's short
# single arm ("half arm1"): hub at (0,20,0), bore along Z, arm along +X with holes every 2 mm; the build pins
# the bars at the second-from-last hole (guide p.15), 12.75 from the hub. Receiver: PCB bottom y=0, 23 x 24
# holes, Core under the PCB.
SERVO_STEP = {
    "tab_holes": [(-2.55, 5.9, -0.65), (25.25, 5.9, -0.65)],
    "shaft": (16.69, 5.9, -0.65),
    "horn_seat": 10.35,
    # where the lead leaves the servo: the STEP's three wires run straight on to x=42, the real lead is flexible, so the
    # mesh is cut there (the tab end) and the cable reach measures from there
    "lead": (27.7, 5.9, 11.0),
}
HORN_STEP = {"hub": (0.0, 20.0, 0.0), "pin": 12.75}
SWITCH_STEP = {"hole": (10.25, 0.0, 0.0)}  # the mounting hole on the PCB bottom; PCB x -7.25..13.25, z +-16
# Receiver STEP Ports: the four servo headers and the XH power socket (top centres); the PWM numbering of the headers is
# inferred. The switch board's two XH sockets are not located: the cable reach takes its mounting hole for both [I].
RECEIVER_STEP = {
    "headers": {
        "PWM1": (4.2, 10.8, 0.4),
        "PWM2": (4.2, 10.8, 4.6),
        "PWM3": (-4.2, 10.8, 0.4),
        "PWM4": (-4.2, 10.8, 4.6),
    },
    "xh_power": (0.0, 9.62, -9.75),
}


def _dist(a, b):
    return sum((p - q) ** 2 for p, q in zip(a, b)) ** 0.5


def _unit(v):
    n = sum(c * c for c in v) ** 0.5
    return tuple(c / n for c in v)


def servo_frame(key):
    """Where SERVOS[key] sits: (origin, tab_x, shaft). origin is the point of the tab mid-plane under the shaft,
    tab_x the unit vector along the tabs from the hole far from the shaft to the near one (the STEP's +X),
    shaft the unit direction the output shaft points. The shaft axis is PIVOTS[key + '_horn'], so the tab
    holes land within the inferred +-4 mm."""
    pivot = PIVOTS[key + "_horn"]
    a, b = sorted(SERVOS[key]["tab_holes"], key=lambda h: _dist(h, pivot["point"]), reverse=True)
    tab_x = _unit([q - p for p, q in zip(a, b)])
    toward_horn = sum((p - q) * c for p, q, c in zip(pivot["point"], a, pivot["axis"]))
    shaft = tuple(c if toward_horn > 0 else -c for c in pivot["axis"])
    along = sum((p - q) * c for p, q, c in zip(a, pivot["point"], shaft))
    origin = tuple(p + along * c for p, c in zip(pivot["point"], shaft))
    return origin, tab_x, shaft


# Lid linkage (L side; mirror_x for R). Lid pins r=1 along X on the lid ears [M]; the bar and crank hang on
# the lid-servo horn pin outside the ears, the straight bar outboard of the crank (guide p.23) [I: x +-3].
LID_PINS = {"inside": (-22.0, 12.0, 0.0), "outside": (-22.0, -12.0, 0.0)}
LID_LINKS = {"eyelid_bar": {"lid": "inside", "x": -29.5}, "eyelid_crank": {"lid": "outside", "x": -25.5}}
EYEBALL_BAR_PINS = [(-10.0, 4.0, 27.0), (-10.0, 4.0, 0.0)]  # eye-horn end, eyeball end [M]

# Pan-tilt linkage. Lever holes fitted on the STLs (model/fits.py) [M]: the tilt bar joins the tilt horn pin to the
# tilt arm's lever (x 3..8 slab, hole along X; the arm STL is at the v1 height, upright v2 raises it 5 mm); the pan bar
# joins the pan horn pin to the upright v2's lever (x -8..-3, hole along Z through its top z=26.8). The research note's
# "pan-bar post at (18,19)" is the pan-base tower corner. Bar mid-planes [I]: the horn is 4.15 thick from its seat
# along the shaft (tilt x 8.0..12.15, pan z 25.35..29.5), the bar rides on the horn's outer face: tilt bar x 10.1..13.1
# (the arm lever, x 3..8, is bridged by the M2.5 screw), pan bar z 29.5..32.5 (the upright lever top is z=26.8). Horn direction at neutral [I]: tilt horn horizontal toward
# +Y with the bar vertical (guide step 15), pan horn forward (-Y) with the bar along X, tangent to the lever (step 14).
# Jaw (eyes frame) [I]: the connector bar rides on the jaw horn's outer face (x 56.4..61.4) against the bottom jaw's pivot lug
# (x 61.5..70.5, hole r 1.1 along X at (y -58.1, z -10.44), M2.5 self-tapping through the bar's larger hole, guide step 8); the
# horn points down (-Y) at neutral, clear of the bracket rail (y > -40.6) the +Y solution would run into.
TILT_ARM_SHIFT_Z = 5.0
PT_LEVER_HOLES = {"tilt": (8.0, 26.5, 33.4 + TILT_ARM_SHIFT_Z), "pan": (-5.5, 25.5, 26.8), "jaw": (58.9, -58.1, -10.44)}
PT_BAR_PLANES = {"tilt": ("x", 11.6), "pan": ("z", 31.0), "jaw": ("x", 58.9)}
PT_HORN_DIR = {"tilt": (0, 1, 0), "pan": (0, -1, 0), "jaw": (0, -1, 0)}
HORN_BAR = {"tilt": "tilt_bar", "pan": "pan_bar", "jaw": "connector_bar"}  # BARS key of each horn's link


def horn_pin(key):
    """(pin, lever) world points in the bar's mid-plane for the tilt, pan or jaw link at neutral: the pin HORN_STEP['pin']
    from the horn pivot and BARS[HORN_BAR[key]] from the lever hole, on the side PT_HORN_DIR says."""
    axis, plane = PT_BAR_PLANES[key]
    i = "xyz".index(axis)
    u, v = [k for k in range(3) if k != i]
    hub, hole = PIVOTS[key + "_horn"]["point"], PT_LEVER_HOLES[key]
    r1, r2 = HORN_STEP["pin"], BARS[HORN_BAR[key]]
    d = _dist((hub[u], hub[v]), (hole[u], hole[v]))
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = (r1 * r1 - a * a) ** 0.5
    eu, ev = (hole[u] - hub[u]) / d, (hole[v] - hub[v]) / d
    want = PT_HORN_DIR[key]
    best = None
    for s in (1, -1):
        pin = [0.0, 0.0, 0.0]
        pin[i], pin[u], pin[v] = plane, hub[u] + a * eu - s * h * ev, hub[v] + a * ev + s * h * eu
        score = sum((p - q) * w for p, q, w in zip(pin, hub, want))
        if best is None or score > best[0]:
            best = (score, tuple(pin))
    lever = list(hole)
    lever[i] = plane
    return best[1], tuple(lever)


# Designer STLs that are in local frames: pivot holes (mm) and the hole axis.
STL_LOCAL = {
    # Circle fits on the STL holes (model/fits.py, 2026-10-31): 41 mm pitch; the crank is the eyelid bar with its
    # horn end stepped up 3 mm, both holes along Z (the earlier Y-axis entry had the crank turned 90 degrees).
    "eyelid bar": {"holes": [(-20.5, 0.0, 1.5), (20.5, 0.0, 1.5)], "hole_axis": Z},
    "eyelid bar crank": {"holes": [(-20.5, 0.0, 4.5), (20.5, 0.0, 1.5)], "hole_axis": Z},
    # Pan-tilt bars: the smaller hole (r 1.1, +x end) takes the M2 horn screw (guide step 12), the larger (r 1.35) the
    # M2.5 lever screw; listed horn end first.
    "tilt bar": {"holes": [(10.0, 0.0, 1.5), (-10.0, 0.0, 1.5)], "hole_axis": Z},
    "PandT bar": {"holes": [(7.5, 0.0, 1.5), (-7.5, 0.0, 1.5)], "hole_axis": Z},
    # Jaws connector bar: a 50 x 15.5 x 5 Z-shaped plate, holes along its thickness (research note); which hole is the
    # larger (jaw) one is inferred: horn end first [I].
    "jaws connector bar": {"holes": [(16.0, -2.5, -6.0), (-13.0, -2.5, 6.0)], "hole_axis": Y},
}

# Eyes base pockets [M]. Battery STEP, local mm: pack floor z=-8.15, pack along +Y from 0, lead fused to the
# pack body beyond y=56 (plug at y 50..55).
BATTERY_POCKET = {"x": (38.0, 74.0), "z": (55.0, 111.0), "floor_y": -35.6}
BATTERY_POCKET_PT = {"x": (-48.0, -24.0), "y": (71.0, 127.0), "floor_z": 3.0}  # PandT base, PT frame [M]
BATTERY_STEP = {"floor_z": -8.15, "lead_y": 56.0, "plug": (3.5, 52.5, 3.5)}


# Printed parts: spool and material per STL stem (model/parts.py gives each library part the spool's appearance and a
# physical material of that density; the engine (model/engine/masses.py) and beams.py take masses from it). Spools are Bambu PLA Pure; the density
# is Bambu Studio's PLA base profile (no PLA Pure figure is published). Colours per the build (grilled 2026-10-31);
# "(colour inferred)" where an STL name does not map cleanly onto a named part.
SPOOLS = {"Milky Pink": "#F7CED7", "Pure White": "#FFFFFF", "Absolute Black": "#000000", "Apricot": "#FFB673"}
MATERIALS = {"PLA Pure": {"density_g_cm3": 1.24}}  # PETG possible later, per part
PRINTED = {
    stem: (spool, "PLA Pure")
    for spool, stems in {
        "Milky Pink": [
            "L servo bracket",
            "R servo bracket",
            "main bracket v2",
            "inside lid",
            "outside lid",
            "eyeball bar",
            "eyelid bar",
            "eyelid bar crank",
            "wire keeper",
        ],
        "Pure White": [
            "L eyeball regular",
            "R eyeball regular",
            "tilt bar",
            "PandT bar",
            "PandT servo mount plain",
            "PandT servo mount cutout",
            "top jaw plain",
            "bottom jaw plain",
            "jaws connector bar",
            "jaws servo mount",
        ],
        "Absolute Black": [
            "regular pupil",
            "PandT base",
            "PandT tilt arm",
            "PandT bearing block",
            "PandT wire holder (colour inferred)",
        ],
        "Apricot": [
            "PandT upright v2",
            "PandT pan base (colour inferred)",
        ],  # the pan base reads beige in the guide photos (p.18)
    }.items()
    for stem in stems
}


# Stage documents (model/stage.py) insert the sub-assembly designs by reference, each at an (origin, x axis, z axis) frame
# in the PT frame (fusion_lib.align takes the same triple). The bracket v2 stem (eyes x 23.5..35.5, z 13..18, bottom
# y=-45.6) is clamped in STEM_IN's part: through the pan recess of the base in the desk build (stage 1,
# pt_to_eyes_standalone), in the tilt arm window on the neck (stages 2 and 3, eyes_to_pt). Depth in the window [I].
EYES_ON_BASE = ((29.5, -15.5, 38.6), (-1, 0, 0), (0, 1, 0))
EYES_ON_STACK = ((29.5, -28.5, 81.5), (-1, 0, 0), (0, 1, 0))
STEM_BOTTOM = (29.5, -45.6, 15.5)  # centre of the stem's bottom face, eyes frame
STAGES = {
    "noggin-stage1": {"noggin-base": ((0, 0, 0), X, Z), "noggin-eyes": EYES_ON_BASE},
    "noggin-stage2": {
        "noggin-base": ((0, 0, 0), X, Z),
        "noggin-stack": ((0, 0, 0), X, Z),
        "noggin-eyes": EYES_ON_STACK,
    },
    "noggin-stage3": {
        "noggin-base": ((0, 0, 0), X, Z),
        "noggin-stack": ((0, 0, 0), X, Z),
        "noggin-eyes": EYES_ON_STACK,
        "noggin-mouth": EYES_ON_STACK,
    },
}
STEM_IN = {"noggin-stage1": "PandT base", "noggin-stage2": "tilt arm", "noggin-stage3": "tilt arm"}


def in_frame(frame, p):
    """A point of a sub-assembly's own frame in the PT frame: origin + x*px + y*py + z*pz with y = z cross x."""
    origin, x, z = frame
    y = (z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0])
    return tuple(o + x[i] * p[0] + y[i] * p[1] + z[i] * p[2] for i, o in enumerate(origin))
