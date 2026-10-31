"""The mating check (#67, run by `make sim`): every screw, pin and shaft joint of the model lines up with real features
in both parts, and every servo sits in its mount. A joint names a round feature (hole, pin, spline, bore) in each of
its parts; each is measured on the part's own mesh by a circle fit near its declared centre (model/fits.py) and carried
to the document by the part's placement; the joint passes when the axes are within COAXIAL_MM of each other. A servo
passes when it touches the mount its tab screws go into and enters no part (the horn on its spline excepted: the
envelope's spline is simplified). Results go in the report as "mating" (model/test_report.py fails a mismatch). A joint
no source settles is listed in INFERRED with its reason: it warns (run.warnings) instead of failing.

FEATURES is what our parts declare, by mesh stem: each printed part's features() (model/printed FEATURES) and the
hardware envelopes' (model/envelopes.py FEATURES), {feature: (centre, axis, r, half[, band])} in the part's own frame:
centre on the axis, `half` the slab along it that holds the feature's wall, `band` the radial window of the fit (x r)."""

import numpy as np

from model import envelopes, fits, printed
from model import geometry as g
from model.engine import stages

COAXIAL_MM = 0.2
SEAT_MM = 0.1  # the servo's flange touches its mount: the sweep's contact resolution (run.CLEARANCE_MM)
FEATURES = {**printed.FEATURES, **envelopes.FEATURES}


def _servo(label, mount, near, far, bar=None, bar_hole="horn hole"):
    """A servo's tab screws, its horn on the spline and the horn pin through the bar(s)."""
    s, h = f"{label} servo:1", f"{label} horn:1"
    out = [
        (f"{label} servo / {mount.split(':')[0]} near tab screw", [(s, "near tab hole"), (mount, near)]),
        (f"{label} servo / {far[0].split(':')[0]} far tab screw", [(s, "far tab hole"), far]),
        (f"{label} horn on the {label} servo spline", [(s, "spline"), (h, "bore")]),
    ]
    if bar:
        out.append((f"{label} horn pin", [(h, "pin hole"), *[(b, bar_hole) for b in bar]]))
    return out


def _eyes(s):
    lid, eye, br = f"{s} lid", f"{s} eye", f"{s} servo bracket:1"
    bar, crank, upper, lower = (f"{s} {n}:1" for n in ("lid bar", "lid crank", "upper lid", "lower lid"))
    main = "eye bracket:1"
    return [
        *_servo(lid, br, "lid near", (br, "lid far"), [bar, crank]),
        (f"{s} lid bar / {s} lower lid pin", [(bar, "lid hole"), (lower, "pin")]),
        (f"{s} lid crank / {s} upper lid pin", [(crank, "lid hole"), (upper, "pin")]),
        *[
            (f"{s} {which} lid {ear} on the bracket pin", [(lid_part, f"{ear} ear"), (main, f"{s} {ear} lid pin")])
            for which, lid_part in (("upper", upper), ("lower", lower))
            for ear in ("outer", "inner")
        ],
        *_servo(eye, br, "eye near", (br, "eye far"), [f"{s} eyeball bar:1"]),
        (
            f"{s} eyeball bar / {s} eyeball screw",
            [(f"{s} eyeball bar:1", "eyeball hole"), (f"{s} eyeball:1", "screw hole")],
        ),
        (f"{s} eyeball pivot in the fork", [(f"{s} eyeball:1", "pivot"), (main, f"{s} fork")]),
        *[
            (f"{s} servo bracket {k} on the eye bracket", [(br, f"foot {k}"), (main, f"{s} foot {k}")])
            for k in ("outer", "inner", "stem")
        ],
    ]


JOINTS = [
    *_eyes("L"),
    *_eyes("R"),
    *_servo("jaw", "jaw servo mount:1", "near tab hole", ("jaw servo mount:1", "far tab hole"), ["jaw bar:1"]),
    ("jaw bar / bottom jaw lug", [("jaw bar:1", "jaw hole"), ("bottom jaw:1", "lug")]),
    *[(f"{s} jaw hinge", [("bottom jaw:1", f"{s} hinge"), ("top jaw:1", f"{s} pin")]) for s in "LR"],
    *[
        (
            f"jaw servo mount {s} foot on the rail",
            [("jaw servo mount:1", f"foot {s}"), ("eye bracket:1", f"rail {s}")],
        )
        for s in "LR"
    ],
    *_servo("tilt", "pan turntable:1", "tilt near", ("pan turntable:1", "tilt far"), ["tilt bar:1"]),
    ("tilt bar / tilt arm lever", [("tilt bar:1", "lever hole"), ("tilt arm:1", "lever")]),
    ("tilt pivot", [("tilt arm:1", "pivot"), ("upright:1", "tilt pivot")]),
    *_servo(
        "pan", "pan servo lead mount:1", "tab hole", ("pan servo tail mount:1", "tab hole"), ["pan bar:1"]
    ),  # mounts swapped
    ("pan bar / upright lever", [("pan bar:1", "lever hole"), ("upright:1", "lever")]),
    ("upright on the pan turntable", [("upright:1", "pan turntable screw"), ("pan turntable:1", "upright screw")]),
    ("pan pivot", [("pan turntable:1", "pan pivot"), ("base plate:1", "pan pivot")]),
    *[
        (
            f"pan servo {m} mount {k} foot on the base",
            [(f"pan servo {m} mount:1", f"foot {k}"), ("base plate:1", f"{end} foot {k}")],
        )
        for m, end in (("lead", "near"), ("tail", "far"))  # geometry.MOUNT_SWAP_Y
        for k in ("outer", "inner")
    ],
]
# joint: why no source settles it (listed in the report, warns instead of failing)
INFERRED = {
    "jaw horn pin": "the jaw bar's horn end (13 mm crank from its jaw end on the jaw lug's outer face, STL) runs"
    " under the horn arm (seat 11.52 past the tab plane, STEP): 0.58 mm across, no source places either otherwise;"
    " the horn's seat on the real spline needs the calliper",
}
# The part each servo's near tab screw goes into: the servo must touch it.
MOUNTS = {feats[0][0]: feats[1][0] for name, feats in JOINTS if name.endswith(" near tab screw")}


def feature(part, name):
    """(world centre, world axis, fitted r) of a part's feature, or None when its mesh has no such feature."""
    centre, axis, r, half, *band = FEATURES[stages.stem(part.file)][name]
    try:
        fit = fits.fit_circle(part.file, centre, axis, half, r, *band or [fits.HOLE])
    except ValueError:
        return None
    m = part.matrix
    return m[:3, :3] @ fit["centre"] + m[:3, 3], m[:3, "xyz".index(axis)], fit["r"]


def _off(c, a, p):
    """Distance of point p from the axis through c along unit a."""
    v = np.subtract(p, c)
    return float(np.linalg.norm(v - (v @ a) * a))


def check(stage, placed):
    """[{joint, kind, parts, mm, ok[, missing][, inferred]}] for every joint whose parts the document has, then every
    servo's seat and lead exit; `placed` is the document's parts at neutral (meshes.Placed)."""
    from model.engine import meshes  # the engine's mesh judge

    def overlap(a, b):
        return meshes.judge(placed[a], placed[b])[1] if meshes.bbox_gap(placed[a], placed[b]) < SEAT_MM else 0.0

    out = []
    for name, feats in JOINTS:
        if not all(p in stage.parts for p, _ in feats):
            continue
        parts = [p for p, _ in feats]
        row = {"joint": name, "kind": "coaxial", "parts": parts}
        found = [(p, feature(stage.parts[p], f)) for p, f in feats]
        missing = [p for p, f in found if f is None]
        if missing:
            row.update(mm=None, ok=False, missing=missing[0])
        else:
            (c0, a0, _), *rest = (f for _, f in found)
            mm = max(max(_off(c0, a0, c), _off(c, a, c0)) for c, a, _ in rest)
            row.update(mm=round(mm, 3), ok=mm <= COAXIAL_MM)
            # parts joined face to face must not enter each other (the simplified STEP spline excepted)
            deep = [] if "spline" in name else [(overlap(a, b), a, b) for a in parts for b in parts if a < b]
            depth, a, b = max(deep, default=(0.0, None, None))
            if row["ok"] and depth > 0:
                row.update(kind="overlap", parts=[a, b], mm=round(depth, 3), ok=False)
        if name in INFERRED:
            row["inferred"] = INFERRED[name]
        out.append(row)
    for servo, mount in MOUNTS.items():
        if servo not in placed or mount not in placed:
            continue
        horn, name = servo.replace(" servo", " horn"), servo.split(":")[0]
        deepest = max(((overlap(servo, o), o) for o in placed if o not in (servo, horn)), default=(0.0, None))
        if deepest[0] > 0:
            out.append(
                {
                    "joint": f"{name} in its mount",
                    "kind": "overlap",
                    "parts": [servo, deepest[1]],
                    "mm": round(deepest[0], 3),
                    "ok": False,
                }
            )
        else:
            gap = meshes.distance(placed[servo], placed[mount])
            out.append(
                {
                    "joint": f"{name} in its mount",
                    "kind": "seat",
                    "parts": [servo, mount],
                    "mm": round(gap, 3),
                    "ok": gap < SEAT_MM,
                }
            )
        # the lead leaves the case end face (SERVO_STEP x 22.8) straight out to its Port: through no part
        m = stage.parts[servo].matrix
        lead = np.array([(x, *g.SERVO_STEP["lead"][1:]) for x in np.linspace(23.0, g.SERVO_STEP["lead"][0], 6)])
        pts = lead @ m[:3, :3].T + m[:3, 3]
        # clipped meshes (the servos, the battery) are open: ray parity cannot test them
        solid = (
            o for o, p in placed.items() if not stage.parts[o].clip and meshes.bbox_gap(placed[servo], p) < SEAT_MM
        )
        hit = next((o for o in solid if meshes.inside(pts, placed[o]).any()), None)
        out.append(
            {
                "joint": f"{name} lead exit",
                "kind": "lead",
                "parts": [servo, hit] if hit else [servo],
                "mm": None,
                "ok": hit is None,
            }
        )
    return out
