"""Measured Mech geometry as data (mm, degrees). Source: docs/research/2026-10-31-twin.md.
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


def mirror_x(p):
    """Reflect an eyes-frame point about the mech centreline x=29.5 (L side -> R side)."""
    x, y, z = p
    return (2 * CENTRE_X - x, y, z)


# Absolute servo angle limits in degrees from the designer's remote config; neutral is 90.
HORN_LIMITS = {
    "l_lid": (70, 120), "l_eye": (60, 120), "r_lid": (70, 120), "r_eye": (60, 120),
    "tilt": (20, 150), "rotate": (40, 160), "mouth": (0, 180),
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
    "jaw_horn": _pivot((75.9, -48.6, 23.1), X, inferred=True),
    "pan": _pivot((0.0, 0.0, 0.0), Z, "pt"),
    "tilt": _pivot((0.0, -13.0, 33.4), X, "pt"),
    "tilt_horn": _pivot((22.5, 17.6, 18.4), X, "pt", inferred=True),
    "pan_horn": _pivot((-20.5, 38.2, 15.0), Z, "pt", inferred=True),
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

# Standoff tops. Receiver shield pattern is 23 x 24; switch board is a single pair.
STANDOFFS = {
    "eyes_base": {
        "receiver": [(-14.8, -25.6, 51.0), (8.2, -25.6, 51.0), (-14.8, -25.6, 75.0), (8.2, -25.6, 75.0)],
        "switch": [(29.5, -25.6, 51.0), (29.5, -25.6, 75.0)],
    },
    "pt_base": {
        "receiver_1": [(26.0, 40.5, 13.0), (50.0, 40.5, 13.0), (26.0, 63.5, 13.0), (50.0, 63.5, 13.0)],
        "receiver_2": [(26.0, 73.5, 13.0), (50.0, 73.5, 13.0), (26.0, 96.5, 13.0), (50.0, 96.5, 13.0)],
        "switch": [(6.0, 68.5, 13.0), (6.0, 92.5, 13.0)],
    },
}

# Pivot-to-pivot hole spacing of each link.
BARS = {"eyelid_bar": 41.0, "eyelid_crank": 41.0, "tilt_bar": 20.0, "pan_bar": 15.0,
        "connector_bar": 31.4, "eyeball_bar": 27.0}

# Bambu STEP files, local mm (measured in Fusion 2026-10-31). Servo: tab holes along +X on the tab mid-plane,
# shaft at x=16.69 pointing -Z, horn seats on the boss top 10.35 beyond the tab plane. Line-arm horn: hub at
# (0,20,0), bore along Z, arm holes at x=+-14.15. Receiver: PCB bottom y=0, 23 x 24 holes, Core under the PCB.
SERVO_STEP = {"tab_holes": [(-2.55, 5.9, -0.65), (25.25, 5.9, -0.65)], "shaft": (16.69, 5.9, -0.65),
              "horn_seat": 10.35}
HORN_STEP = {"hub": (0.0, 20.0, 0.0), "hole": 14.15}


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
