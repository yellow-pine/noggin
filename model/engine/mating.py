"""The mating check (#67, run by `make sim`): every screw, pin and shaft joint of the model lines up with real features
in both parts, and every servo sits in its mount. A joint names a round feature (hole, pin, spline, bore) in each of
its parts; each is measured on the part's own mesh by a circle fit near its declared centre (model/fits.py) and carried
to the document by the part's placement; the joint passes when the axes are within COAXIAL_MM of each other. A servo
passes when it touches the mount its tab screws go into and enters no part (the horn on its spline excepted: the STEP
spline is simplified). Results go in the report as "mating" (model/test_report.py fails a mismatch). A joint no source
settles is listed in INFERRED with its reason: it warns (run.warnings) instead of failing.

FEATURES is the interface a part supplies, by mesh stem: {feature: (centre, axis, r, half[, band])} in the part's own
frame (the designer's STL frame, the STEP's local frame): centre on the axis, `half` the slab along it that holds the
feature's wall, `band` the radial window of the fit (x r). Our printed parts (model/printed) export in the designer's
frame under the same stem, so the same table reads them; once they declare their features exactly they take these
entries' place."""

import os

import numpy as np

from model import fits
from model import geometry as g

COAXIAL_MM = 0.2
SEAT_MM = 0.1  # the servo's flange touches its mount: the sweep's contact resolution (run.CLEARANCE_MM)
HOLE, BORE = (
    (0.6, 1.8),
    (0.8, 1.3),
)  # fit bands: a plain hole; a bore or pin with a wall or counterbore close outside it


def _mirror(features):
    """The R-side features of an L-side table (geometry.mirror_x)."""
    return {k: (g.mirror_x(c), *rest) for k, (c, *rest) in features.items()}


_L_BRACKET = {  # [M] fitted 2026-10-31; tab holes on the lug axes, feet on the main bracket plate (z 18)
    "lid near": ((-5.41, -4.65, 40.0), "x", 1.1, 2.1),
    "lid far": ((-5.41, -32.35, 40.0), "x", 1.1, 2.1),
    "eye near": ((-6.0, -9.0, 26.9), "y", 1.1, 2.6),
    "eye far": ((21.8, -9.0, 26.9), "y", 1.1, 2.6),
    "foot outer": ((-13.42, -7.75, 19.5), "z", 1.35, 1.6),
    "foot inner": ((10.24, -0.5, 19.5), "z", 1.3, 1.6),
}
_L_MAIN = {
    "L foot outer": ((-13.42, -7.75, 15.5), "z", 1.1, 2.6),
    "L foot inner": ((10.24, -0.5, 15.5), "z", 1.1, 2.6),
    "L outer lid pin": ((-22.5, 0.0, 0.0), "x", 1.75, 2.0, BORE),
    "L inner lid pin": ((22.5, 0.0, 0.0), "x", 1.75, 2.0, BORE),
    "L fork": ((0.0, 2.0, 0.0), "y", 1.6, 2.0),
}
_L_EYEBALL = {"screw hole": ((-10.0, 2.0, 0.0), "y", 1.1, 1.0), "pivot": ((0.0, -7.5, 0.0), "y", 1.3, 6.6, BORE)}
_LID = {"outer ear": ((-22.5, 0.0, 0.0), "x", 2.0, 2.0, BORE), "inner ear": ((22.5, 0.0, 0.0), "x", 2.0, 2.0, BORE)}
FEATURES = {
    # STEPs (model/build/steps), local mm (geometry.SERVO_STEP, HORN_STEP; docs/research/2026-10-31-shafts.md)
    "servo": {
        "near tab hole": ((25.25, 5.9, -1.15), "z", 1.1, 1.2),
        "far tab hole": ((-2.55, 5.9, -1.15), "z", 1.1, 1.2),
        "spline": ((16.69, 5.9, -12.9), "z", 2.35, 1.7, (0.8, 1.2)),  # z -11.2..-14.52, clear of the collar r 2.4
    },
    "horn": {"bore": ((0.0, 20.0, 2.975), "z", 2.15, 1.2, BORE), "pin hole": ((12.75, 20.0, 0.8), "z", 0.5, 0.9)},
    # eyes (designer frame; the R lids and eyeball bar are the L STLs moved, so their features are the L ones)
    "L servo bracket": {**_L_BRACKET, "foot stem": ((29.5, -31.6, 19.5), "z", 1.35, 1.6)},
    "R servo bracket": {**_mirror(_L_BRACKET), "foot stem": ((29.5, -21.6, 19.5), "z", 1.35, 1.6)},
    "main bracket v2": {
        **_L_MAIN,
        **{"R" + k[1:]: v for k, v in _mirror(_L_MAIN).items()},
        "L foot stem": ((29.5, -31.6, 15.5), "z", 1.1, 2.6),
        "R foot stem": ((29.5, -21.6, 15.5), "z", 1.1, 2.6),
        "rail L": ((65.92, -35.6, 15.5), "z", 1.1, 2.6),
        "rail R": ((70.92, -35.6, 15.5), "z", 1.1, 2.6),
    },
    "inside lid": {**_LID, "pin": ((-22.0, 12.0, 0.0), "x", 1.0, 3.0)},
    "outside lid": {**_LID, "pin": ((-22.0, -12.0, 0.0), "x", 1.0, 3.0)},
    "eyelid bar": {"horn hole": ((20.5, 0.0, 1.5), "z", 1.1, 1.6), "lid hole": ((-20.5, 0.0, 1.5), "z", 1.35, 1.6)},
    "eyelid bar crank": {
        "horn hole": ((20.5, 0.0, 1.5), "z", 1.1, 1.6),
        "lid hole": ((-20.5, 0.0, 4.5), "z", 1.35, 1.6),
    },
    "eyeball bar": {
        "horn hole": ((-10.0, 4.0, 27.0), "y", 1.05, 2.0),
        "eyeball hole": ((-10.0, 4.0, 0.0), "y", 1.25, 2.0),
    },
    "L eyeball regular": _L_EYEBALL,
    "R eyeball regular": _mirror(_L_EYEBALL),
    # mouth (eyes frame)
    "jaws servo mount": {
        "near tab hole": ((75.92, -48.6, 42.23), "x", 1.1, 2.6),
        "far tab hole": ((75.92, -48.6, 14.43), "x", 1.1, 2.6),
        "foot L": ((65.92, -35.6, 20.5), "z", 1.35, 2.0),
        "foot R": ((70.92, -35.6, 20.5), "z", 1.35, 2.0),
    },
    "jaws connector bar": {
        "horn hole": ((-22.05, -2.5, 6.5), "z", 1.1, 1.6),
        "jaw hole": ((22.05, -2.5, -6.5), "z", 1.35, 1.6),
    },
    "bottom jaw plain": {
        "lug": ((71.92, -58.1, -10.44), "x", 1.1, 1.6),
        "L hinge": ((-8.0, -49.6, 8.0), "x", 2.0, 3.0),
        "R hinge": ((70.0, -49.6, 8.0), "x", 2.0, 3.0),
    },
    "top jaw plain": {"L pin": ((-8.0, -49.6, 8.0), "x", 1.75, 4.0), "R pin": ((68.0, -49.6, 8.0), "x", 1.75, 4.0)},
    # pan-tilt (PT frame; the tilt arm STL at the v1 height, geometry.TILT_ARM_SHIFT_Z)
    "PandT pan base": {
        "tilt near": ((22.5, 22.54, 18.38), "x", 1.1, 2.6),
        "tilt far": ((22.5, -5.04, 18.38), "x", 1.1, 2.6),
        "upright screw": ((0.0, -8.0, 6.0), "z", 1.1, 2.5),
        "pan pivot": ((0.0, 0.0, 8.5), "z", 1.75, 3.0),
    },
    "PandT servo mount plain": {
        "tab hole": ((-20.5, 29.5, 9.0), "z", 1.1, 6.1),
        "foot outer": ((-32.5, 29.5, 4.5), "z", 1.35, 1.5),
        "foot inner": ((-8.5, 29.5, 4.5), "z", 1.35, 1.5),
    },
    "PandT servo mount cutout": {
        "tab hole": ((-20.5, 57.3, 9.0), "z", 1.1, 6.1),
        "foot outer": ((-32.5, 57.4, 4.5), "z", 1.35, 1.5),
        "foot inner": ((-8.5, 57.4, 4.5), "z", 1.35, 1.5),
    },
    "PandT base": {
        "near foot outer": ((-32.5, 29.5, 0.5), "z", 1.1, 2.6),
        "near foot inner": ((-8.5, 29.5, 0.5), "z", 1.1, 2.6),
        "far foot outer": ((-32.5, 57.4, 0.5), "z", 1.1, 2.6),
        "far foot inner": ((-8.5, 57.4, 0.5), "z", 1.1, 2.6),
        "pan pivot": ((0.0, 0.0, 1.5), "z", 1.3, 3.6),
    },
    "PandT upright v2": {
        "pan base screw": ((0.0, -8.0, 10.5), "z", 1.35, 2.0),
        "lever": ((-5.5, 25.5, 24.0), "z", 1.1, 3.0),
        "tilt pivot": ((0.0, -13.0, 33.4), "x", 1.1, 12.0),
    },
    "PandT tilt arm": {"lever": ((8.0, 26.5, 33.4), "x", 1.1, 3.0), "pivot": ((0.0, -13.0, 28.4), "x", 1.35, 13.5)},
    "tilt bar": {"horn hole": ((10.0, 0.0, 1.5), "z", 1.1, 1.6), "lever hole": ((-10.0, 0.0, 1.5), "z", 1.35, 1.6)},
    "PandT bar": {"horn hole": ((7.5, 0.0, 1.5), "z", 1.1, 1.6), "lever hole": ((-7.5, 0.0, 1.5), "z", 1.35, 1.6)},
}


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
    bar, crank, inside, outside = (
        f"{s} {n}:1" for n in ("eyelid bar", "eyelid bar crank", "inside lid", "outside lid")
    )
    main = "main bracket v2:1"
    return [
        *_servo(lid, br, "lid near", (br, "lid far"), [bar, crank]),
        (f"{s} eyelid bar / {s} outside lid pin", [(bar, "lid hole"), (outside, "pin")]),
        (f"{s} eyelid crank / {s} inside lid pin", [(crank, "lid hole"), (inside, "pin")]),
        *[
            (f"{s} {which} lid {ear} on the bracket pin", [(lid_part, f"{ear} ear"), (main, f"{s} {ear} lid pin")])
            for which, lid_part in (("inside", inside), ("outside", outside))
            for ear in ("outer", "inner")
        ],
        *_servo(eye, br, "eye near", (br, "eye far"), [f"{s} eyeball bar:1"]),
        (
            f"{s} eyeball bar / {s} eyeball screw",
            [(f"{s} eyeball bar:1", "eyeball hole"), (f"{s} eyeball:1", "screw hole")],
        ),
        (f"{s} eyeball pivot in the fork", [(f"{s} eyeball:1", "pivot"), (main, f"{s} fork")]),
        *[
            (f"{s} servo bracket {k} on main bracket v2", [(br, f"foot {k}"), (main, f"{s} foot {k}")])
            for k in ("outer", "inner", "stem")
        ],
    ]


JOINTS = [
    *_eyes("L"),
    *_eyes("R"),
    *_servo("jaw", "jaws servo mount:1", "near tab hole", ("jaws servo mount:1", "far tab hole"), ["connector bar:1"]),
    ("connector bar / bottom jaw lug", [("connector bar:1", "jaw hole"), ("bottom jaw:1", "lug")]),
    *[(f"{s} jaw hinge", [("bottom jaw:1", f"{s} hinge"), ("top jaw:1", f"{s} pin")]) for s in "LR"],
    *[
        (
            f"jaws servo mount {s} foot on the rail",
            [("jaws servo mount:1", f"foot {s}"), ("main bracket v2:1", f"rail {s}")],
        )
        for s in "LR"
    ],
    *_servo("tilt", "pan base:1", "tilt near", ("pan base:1", "tilt far"), ["tilt bar:1"]),
    ("tilt bar / tilt arm lever", [("tilt bar:1", "lever hole"), ("tilt arm:1", "lever")]),
    ("tilt pivot", [("tilt arm:1", "pivot"), ("upright v2:1", "tilt pivot")]),
    *_servo(
        "pan", "servo mount cutout:1", "tab hole", ("servo mount plain:1", "tab hole"), ["pan bar:1"]
    ),  # mounts swapped
    ("pan bar / upright lever", [("pan bar:1", "lever hole"), ("upright v2:1", "lever")]),
    ("upright on the pan base", [("upright v2:1", "pan base screw"), ("pan base:1", "upright screw")]),
    ("pan pivot", [("pan base:1", "pan pivot"), ("PandT base:1", "pan pivot")]),
    *[
        (
            f"servo mount {m} {k} foot on the base",
            [(f"servo mount {m}:1", f"foot {k}"), ("PandT base:1", f"{end} foot {k}")],
        )
        for m, end in (("cutout", "near"), ("plain", "far"))  # geometry.MOUNT_SWAP_Y
        for k in ("outer", "inner")
    ],
]
# joint: why no source settles it (listed in the report, warns instead of failing)
INFERRED = {
    "jaw horn pin": "the connector bar's horn end (13 mm crank from its jaw end on the jaw lug's outer face, STL) runs"
    " under the horn arm (seat 11.52 past the tab plane, STEP): 0.58 mm across, no source places either otherwise;"
    " the horn's seat on the real spline needs the calliper",
}
# The part each servo's near tab screw goes into: the servo must touch it.
MOUNTS = {feats[0][0]: feats[1][0] for name, feats in JOINTS if name.endswith(" near tab screw")}


def feature(part, name):
    """(world centre, world axis, fitted r) of a part's feature, or None when its mesh has no such feature."""
    stem = os.path.splitext(os.path.basename(part.file))[0]
    centre, axis, r, half, *band = FEATURES[stem][name]
    try:
        fit = fits.fit_circle(part.file, centre, axis, half, r, *band or [HOLE])
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
    from model.engine import meshes  # the engine's mesh judge; fits stays pure Python

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
