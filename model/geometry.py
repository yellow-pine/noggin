"""Measured Mech geometry as data (mm, degrees). Source: docs/research/2026-10-31-model.md.
Eyes frame: L eye centre at origin, +Y up, -Z front. PT frame: Z up, pan axis through (0,0).
Pure Python, no imports: model/fusion_run.py inlines this file into Fusion scripts.
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


# Absolute servo angle limits in degrees, neutral 90. Designer: PurpleShark's remote config (PWM min/max, the same in
# every config under docs/references). Model: where the model sweeps instead, each with its reason (re-checked against
# the settled shafts, docs/research/2026-10-31-shafts.md).
DESIGNER_LIMITS = {
    "l_lid": (75, 120),
    "l_eye": (60, 120),
    "r_lid": (70, 120),
    "r_eye": (75, 120),
    "tilt": (20, 150),
    "rotate": (40, 160),
    "mouth": (0, 180),
}
MODEL_LIMITS = {
    "l_lid": ((70, 120), "one range for the mirrored lid pair: the L lid is swept to the R lid's 70"),
    "l_eye": ((68, 112), "+-22: the eyeball bar rides on main bracket v2 and enters it 0.1 mm at +-24, 0.26 at +-28"),
    "r_eye": ((68, 112), "+-22: the eyeball bar rides on main bracket v2 and enters it 0.1 mm at +-24, 0.26 at +-28"),
    "tilt": (
        (30, 150),
        "at 20..27 the tilt horn and bar sweep into the pan base's front chord (0.06 mm clear at -62, 0.38 mm deep at"
        " -66, 1.16 at -70): the lower end stops at 30, which keeps the pan x tilt grid on neutral",
    ),
    "mouth": (
        (15, 90),
        "the jaws are modelled closed at neutral: horn +1..+22 drives the bottom jaw further shut into the top jaw (the"
        " hinge pair, not swept) and past +22 the connector-bar four-bar has no solution; on the opening side the bar"
        " enters the jaw servo past -75 (0.28 mm at -80): horn -75..0 = jaw -58..0 deg",
    ),
}
HORN_LIMITS = {**DESIGNER_LIMITS, **{k: v for k, (v, _) in MODEL_LIMITS.items()}}

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def _pivot(point, axis, frame="eyes", inferred=False):
    p = {"point": point, "axis": axis, "frame": frame}
    if inferred:
        p["inferred"] = True  # a position no source settles
    return p


# Revolute axes. Points on the axis. Horn pivots sit at the horn seat (its inner face) on the servo shaft: shaft 8.56 from
# the near tab hole (SERVO_STEP), flange on the printed lug face, near hole and direction from the guide pictures and the
# loop closing at neutral (docs/research/2026-10-31-shafts.md, one line each below).
PIVOTS = {
    "l_lid": _pivot(EYE_L, X),
    "r_lid": _pivot(EYE_R, X),
    "l_eye": _pivot(EYE_L, Y),
    "r_eye": _pivot(EYE_R, Y),
    # lid: upper hole (guide p.32 photo, hub 10 mm under the upper screw), shaft outboard, tab on the lug's outer face x -7.42
    "l_lid_horn": _pivot((-19.59, -13.21, 40.0), X),
    "r_lid_horn": _pivot((78.59, -13.21, 40.0), X),
    # eye: outboard hole (only it reaches the eyeball bar pin), shaft up, tab under the lug (y -11.5; guide step 6), the
    # case side on the bracket floor z 21.0 (the lug holes fit at z 26.88: the screws take the 0.12)
    "l_eye_horn": _pivot((2.56, -1.63, 27.0), Y),
    "r_eye_horn": _pivot((56.44, -1.63, 27.0), Y),
    "jaw_hinge": _pivot((CENTRE_X, -49.6, 8.0), X),
    # jaw: upper hole, shaft outboard through the mount plate (mouth guide step 3 photo, p.14 CAD), tab inside it (x 73.42)
    "jaw_horn": _pivot((83.29, -48.6, 33.67), X),
    "pan": _pivot((0.0, 0.0, 0.0), Z, "pt"),
    "tilt": _pivot((0.0, -13.0, 33.4), X, "pt"),
    # tilt: lever-end hole, shaft -X (pan-tilt guide p.7 CAD), tab on the tower's outer face x 25 (the horn clears the lever),
    # centred on the tower's holes (27.58 apart against the tabs' 27.8: each screw 0.11 off)
    "tilt_horn": _pivot((15.13, 14.09, 18.38), X, "pt"),
    # pan: pan-base end hole (p.7 CAD; the far end leaves the bar at full stretch), shaft up, tabs on the mount tops z 15
    "pan_horn": _pivot((-20.5, 38.11, 27.17), Z, "pt"),
}

SERVO_TAB_SPACING = 27.8  # SG90 mounting tab hole pitch

# The printed lug's measured hole axes, at the SERVO_STEP tab plane (z -0.65) where the flange rests on the lug face
# (docs/research/2026-10-31-shafts.md); the servo's own tab holes sit within 0.2 of them (model/engine/mating.py).
SERVOS = {
    "l_lid": {"tab_holes": [(-8.07, -32.35, 40.0), (-8.07, -4.65, 40.0)], "frame": "eyes"},
    "r_lid": {"tab_holes": [(67.07, -32.35, 40.0), (67.07, -4.65, 40.0)], "frame": "eyes"},
    "l_eye": {"tab_holes": [(-6.0, -13.15, 26.88), (21.8, -13.15, 26.88)], "frame": "eyes"},
    "r_eye": {"tab_holes": [(65.0, -13.15, 26.88), (37.2, -13.15, 26.88)], "frame": "eyes"},
    "tilt": {"tab_holes": [(26.65, -5.04, 18.38), (26.65, 22.54, 18.38)], "frame": "pt"},
    "pan": {"tab_holes": [(-20.5, 29.45, 15.65), (-20.5, 57.45, 15.65)], "frame": "pt"},  # the mounts swapped
    "jaw": {"tab_holes": [(71.77, -48.6, 14.43), (71.77, -48.6, 42.23)], "frame": "eyes"},
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
        "switch_post": [(34.5, 108.5, 9.0)],  # switch board 1's post in the two-clip holder at the back edge [M]
        "wire_keeper": [(-7.5, 40.5, 7.7), (7.5, 40.5, 7.7)],
    },
}

# Pivot-to-pivot hole spacing of each link.
BARS = {
    "eyelid_bar": 41.0,
    "eyelid_crank": 41.0,
    "tilt_bar": 20.0,
    "pan_bar": 15.0,
    "connector_bar": 44.1,
    "eyeball_bar": 27.0,
}

# Bambu STEP files, local mm (measured in Fusion 2026-10-31, servo and horns re-read with OCP for #62). Servo: tab plate
# z -2.3..0, tab holes along +X, shaft at x=16.69 pointing -Z; the horn's inner face sits 11.52 beyond the z -0.65 plane
# (spline tip z -14.52 on the 2.35 deep bore). Horn = the kit's short single arm ("half arm1"): hub at (0,20,0), 4.15
# tall, spline side z 4.15, arm (1.6 thick, holes every 2 mm along +X) on the outer face z 0; the build pins the bars at
# the second-from-last hole (guide p.15), 12.75 from the hub. Receiver: PCB bottom y=0, 23 x 24 holes, Core under the PCB.
SERVO_STEP = {
    "tab_holes": [(-2.55, 5.9, -0.65), (25.25, 5.9, -0.65)],
    "shaft": (16.69, 5.9, -0.65),
    "horn_seat": 11.52,
    # where the lead leaves the servo: the STEP's three wires run straight on to x=42, the real lead is flexible, so the
    # mesh is cut there (the tab end) and the cable corridor starts there
    "lead": (27.7, 5.9, 11.0),
}
HORN_STEP = {"hub": (0.0, 20.0, 0.0), "pin": 12.75, "height": 4.15}
SWITCH_STEP = {"hole": (10.25, 0.0, 0.0)}  # the mounting hole on the PCB bottom; PCB x -7.25..13.25, z +-16
# The servos by the names the remote config and calibration use, and their Mech labels (Fusion components "<label> servo").
# Core 1 drives the eyes (docs/build-notes.md servo ports), Core 2 tilt/mouth/pan (guide step 10, the designer's config JSON).
CHANNELS = {"core1": {1: "l_lid", 2: "l_eye", 3: "r_lid", 4: "r_eye"}, "core2": {1: "tilt", 2: "mouth", 3: "pan"}}
EYES_SERVOS = tuple(CHANNELS["core1"].values())
SERVO_LABEL = {
    "l_lid": "L lid",
    "l_eye": "L eye",
    "r_lid": "R lid",
    "r_eye": "R eye",
    "tilt": "tilt",
    "mouth": "jaw",
    "pan": "pan",
}

# Receiver STEP Ports: the four servo headers and the XH power socket (top centres); the PWM numbering of the headers is
# inferred. The switch board's two XH sockets are not located: the cable corridors take its mounting hole for both [I].
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


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def align_rows(to_origin, to_x=None, to_z=None, from_origin=(0, 0, 0), from_x=(1, 0, 0), from_z=(0, 0, 1)):
    """4x4 rows (mm) taking the local frame (from_*) onto the world frame (to_*); axes default to identity, x is made
    normal to z (stepped links), y = z cross x. The engine wraps it in numpy (stages.align), the Fusion builds in a
    Matrix3D in cm (fusion_lib.align)."""

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


# Lid linkage (L side; mirror_x for R). Lid pins r=1 along X on the lid ears [M]. Per the build (#48, build photos
# eyes-lid-linkage*.jpg, guide p.21: the top lid is the inside one) the crank joins the inside lid by its stepped end and
# sits outermost on the horn pin under the nut; the straight bar joins the outside lid, between the horn and the crank.
# "x": bar mid-planes at (horn pin, lid pin). The lid ears' outer faces are at x=-24 [M], so both lid ends ride on
# -24..-27; the straight bar is flat, so it stands 0.26 off the horn's outer face (x -23.74, docs/research/2026-10-31-
# shafts.md); the crank's plain end sits on it (-27..-30) and its 3 mm step brings the other end back to the ear.
LID_PINS = {"inside": (-22.0, 12.0, 0.0), "outside": (-22.0, -12.0, 0.0)}
# The lid horn's arm at neutral (both sides): 3.59 deg from +Y toward the lids (-Z), where its pin best fits both lid loops
# with the lids in the STLs' pose and the 41 mm bars: 41.14 to the inside lid's pin, 40.86 to the outside one's
# (docs/research/2026-10-31-shafts.md).
LID_HORN_ARM = (0.0, 0.99804, -0.06262)
LID_LINKS = {
    "eyelid_bar": {"lid": "outside", "x": (-25.5, -25.5)},
    "eyelid_crank": {"lid": "inside", "x": (-28.5, -25.5)},
}
EYEBALL_BAR_PINS = [(-10.0, 4.0, 27.0), (-10.0, 4.0, 0.0)]  # eye-horn end, eyeball end [M]

# Pan-tilt linkage. Lever holes fitted on the STLs (model/fits.py) [M]: the tilt bar joins the tilt horn pin to the
# tilt arm's lever (x 3..8 slab, hole along X; the arm STL is at the v1 height, upright v2 raises it 5 mm); the pan bar
# joins the pan horn pin to the upright v2's lever (x -8..-3, hole along Z through its top z=26.8). The research note's
# "pan-bar post at (18,19)" is the pan-base tower corner. Bar mid-planes (docs/research/2026-10-31-shafts.md): the tilt
# bar fills the 2.98 between the lever face x 8.0 and the horn arm (outer face x 10.98): x 8..11; the pan bar sits on the
# upright lever top z 26.8 under the horn arm (underside z 29.72, pan-tilt guide p.7 CAD): z 26.8..29.8. Horn direction
# at neutral: tilt horn horizontal toward +Y with the bar vertical (guide step 15), pan horn forward (-Y) with the bar
# along X, tangent to the lever (step 14).
# Jaw (eyes frame): the connector bar is cranked 13 mm along its pins (STL_LOCAL): its larger hole on the outer face of the
# bottom jaw's pivot lug (x 70.42..73.42; hole r 1.1 along X at (y -58.1, z -10.44), M2.5 self-tapping, guide step 8),
# its smaller hole under the jaw horn's arm (x 83.42..86.42; the arm's underside is x 85.84: 0.58 overlap no source
# settles); the horn points down (-Y) at neutral (mouth guide p.14 CAD), clear of the bracket rail (y > -40.6).
# PT_BAR_PLANES: (axis, horn-end plane[, lever-end plane when the bar is cranked]).
TILT_ARM_SHIFT_Z = 5.0
PT_LEVER_HOLES = {
    "tilt": (8.0, 26.5, 33.4 + TILT_ARM_SHIFT_Z),
    "pan": (-5.5, 25.5, 26.8),
    "jaw": (71.92, -58.1, -10.44),
}
PT_BAR_PLANES = {"tilt": ("x", 9.5), "pan": ("z", 28.3), "jaw": ("x", 84.92, 71.92)}
PT_HORN_DIR = {"tilt": (0, 1, 0), "pan": (0, -1, 0), "jaw": (0, -1, 0)}
HORN_BAR = {"tilt": "tilt_bar", "pan": "pan_bar", "jaw": "connector_bar"}  # BARS key of each horn's link


def horn_pin(key):
    """(pin, lever) world points in the bar's mid-plane(s) for the tilt, pan or jaw link at neutral: the pin HORN_STEP['pin']
    from the horn pivot and BARS[HORN_BAR[key]] from the lever hole (in the loop plane), on the side PT_HORN_DIR says."""
    axis, plane, *lever_plane = PT_BAR_PLANES[key]
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
    lever[i] = (lever_plane or [plane])[0]
    return best[1], tuple(lever)


# Designer STLs that are in local frames: pivot holes (mm) and the hole axis.
STL_LOCAL = {
    # Circle fits on the STL holes (model/fits.py, 2026-10-31): 41 mm pitch, both holes along Z; horn end first: the
    # smaller hole (r 1.1, +x end) on the horn screw, the larger (r 1.35) takes the lid screw (guide p.23). The crank is
    # the eyelid bar with its lid end (-x) stepped up 3 mm (+z, placed toward the lid ear).
    "eyelid bar": {"holes": [(20.5, 0.0, 1.5), (-20.5, 0.0, 1.5)], "hole_axis": Z},
    "eyelid bar crank": {"holes": [(20.5, 0.0, 1.5), (-20.5, 0.0, 4.5)], "hole_axis": Z},
    # Pan-tilt bars: the smaller hole (r 1.1, +x end) takes the M2 horn screw (guide step 12), the larger (r 1.35) the
    # M2.5 lever screw; listed horn end first.
    "tilt bar": {"holes": [(10.0, 0.0, 1.5), (-10.0, 0.0, 1.5)], "hole_axis": Z},
    "PandT bar": {"holes": [(7.5, 0.0, 1.5), (-7.5, 0.0, 1.5)], "hole_axis": Z},
    # Jaws connector bar: a 3 mm strip cranked 13 mm along its pins (fits.py, docs/research/2026-10-31-shafts.md); horn end
    # first: the smaller hole (r 1.1) on the horn, the larger (r 1.35) on the jaw (mouth guide step 8).
    "jaws connector bar": {"holes": [(-22.05, -2.5, 6.5), (22.05, -2.5, -6.5)], "hole_axis": Z},
}

# Eyes base pockets [M]. Battery STEP, local mm: pack floor z=-8.15, pack along +Y from 0, lead fused to the
# pack body beyond y=56 (plug at y 50..55).
BATTERY_POCKET = {"x": (38.0, 74.0), "z": (55.0, 111.0), "floor_y": -35.6}
BATTERY_POCKET_PT = {"x": (-48.0, -24.0), "y": (71.0, 127.0), "floor_z": 3.0}  # PandT base, PT frame [M]
BATTERY_STEP = {"floor_z": -8.15, "lead_y": 56.0, "plug": (3.5, 52.5, 3.5)}

# Electronics set n on the PandT base (model/electronics.py, model/engine/stages.py), PT frame, oriented as the designer's
# build: the receiver's XH socket to the front and the Core on top (the STEP has the Core under the shield: flipped about
# the PCB mid-plane). Switch board 1 lies in the base's two-clip holder at the back edge, slide switch lever up at the
# back, reachable from behind (Cansin's build, docs/build-photos/eyes-top.jpg; eyes guide p.13, pan-tilt guide p.23):
# PCB bottom on the clip shelves and the post (all top z 9), between the clip walls (x 18 / 51) against the back wall
# (y 126), the slide switch's underside dropping between the shelves [M]. Set 2 (switch board 2 on the standoff at
# (6, 92.5), battery 2 on top of battery 1 in the box) is inferred.
RECEIVER_AXES = ((0, -1, 0), (-1, 0, 0))  # (x, z) of the receiver STEP
CORE_FLIP = ((0, 0, 1), 180, (0, 0.8, 0))  # (axis, deg, about local mm)
SWITCH_AXES = {1: ((0, -1, 0), (-1, 0, 0)), 2: ((-1, 0, 0), (0, 1, 0))}  # (x, z) of the switch STEP per set
BATTERY_STACK_Z = 16.3  # pack height: the second pack's floor sits on the first pack's top [I]


def receiver_at(n):
    pts = STANDOFFS["pt_base"][f"receiver_{n}"]
    return tuple(sum(c) / len(pts) for c in zip(*pts))


def switch_at(n):
    """(point, x, z): switch board n's mounting hole on its post top and its STEP's axes, align's first arguments."""
    point = STANDOFFS["pt_base"]["switch_post"][0] if n == 1 else STANDOFFS["pt_base"]["switch"][1]  # [I] for set 2
    return point, *SWITCH_AXES[n]


def battery_at(n):
    pocket = BATTERY_POCKET_PT
    return (
        sum(pocket["x"]) / 2,
        pocket["y"][0],
        pocket["floor_z"] - BATTERY_STEP["floor_z"] + (n - 1) * BATTERY_STACK_Z,
    )


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


# The pan servo mounts trade places (27.9, the base's foot-hole pitch): the cutout goes to the shaft end, where the servo's
# lead leaves it (Bambu STEP; pan-tilt guide p.16: "the mount with the cutout is at the cable end"); the STL has it at
# the far end, where the lead would run through the plain mount (docs/research/2026-10-31-shafts.md).
MOUNT_SWAP_Y = 27.9
# Sub-assembly parts placed straight from the designer's STLs (the Fusion builds and model/engine/stages.py read these):
# (component, STL stem, shift mm). Eyes: x shift; lids, eyeball bar and pupil are modelled at one eye; the regular eye and
# the "updated main bracket and base" profile (main bracket v2, placed apart). Stack: shift; the designer exported these
# in the assembled PT frame, except the tilt arm, still at the v1 height (upright v2 raised the pivot 5 mm). Mouth: in
# the eyes frame with the jaws closed; plain jaws, the guide's first variant (the teeth jaws are the same build).
EYES_PARTS = [
    ("L servo bracket", "L servo bracket", 0),
    ("R servo bracket", "R servo bracket", 0),
    ("L eyeball", "L eyeball regular", 0),
    ("R eyeball", "R eyeball regular", 0),
    ("L pupil", "regular pupil", -59),
    ("R pupil", "regular pupil", 0),
    ("L inside lid", "inside lid", 0),
    ("L outside lid", "outside lid", 0),
    ("R inside lid", "inside lid", 59),
    ("R outside lid", "outside lid", 59),
    ("L eyeball bar", "eyeball bar", 0),
    ("R eyeball bar", "eyeball bar", 79),
]
STACK_PARTS = [
    ("bearing block", "PandT bearing block", (0, 0, 0)),
    ("pan base", "PandT pan base", (0, 0, 0)),
    ("upright v2", "PandT upright v2", (0, 0, 0)),
    ("tilt arm", "PandT tilt arm", (0, 0, TILT_ARM_SHIFT_Z)),
    ("servo mount plain", "PandT servo mount plain", (0, MOUNT_SWAP_Y, 0)),
    ("servo mount cutout", "PandT servo mount cutout", (0, -MOUNT_SWAP_Y, 0)),
    ("wire holder", "PandT wire holder", (0, 0, 0)),
]
MOUTH_PARTS = [
    ("top jaw", "top jaw plain"),
    ("bottom jaw", "bottom jaw plain"),
    ("jaws servo mount", "jaws servo mount"),
]

# Stage documents (model/stage.py) insert the sub-assembly designs by reference, each at an (origin, x axis, z axis) frame
# in the PT frame (align_rows takes the same triple). The bracket v2 stem (eyes x 23.5..35.5, z 13..18, bottom
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
# Where STEM_BOTTOM lands in the PT frame: through the 5 mm plate at the pan recess, feet on its top (stage 1); in the tilt
# arm window at (0, -13), the eye centres 78.5 above the plate top (stages 2 and 3). Research note; depth [I].
STEM_AT = {"noggin-stage1": (0.0, 0.0, -7.0), "noggin-stage2": (0.0, -13.0, 35.9), "noggin-stage3": (0.0, -13.0, 35.9)}
