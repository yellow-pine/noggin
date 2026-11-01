"""The mating joints (#67): every screw, pin and shaft joint of the model names a round feature (hole, pin, spline,
bore) in each of its parts; each is measured on the part's own mesh by a circle fit near its declared centre
(model/fits.py) and carried to the document by the part's placement. model/mjcf.py puts a site per part on each fitted
axis, and model/test_mjcf.py holds every joint's sites within COAXIAL_MM across every sweep.

FEATURES is what our parts declare, by mesh stem: each printed part's features() (model/printed FEATURES) and the
hardware envelopes' (model/envelopes.py FEATURES), {feature: (centre, axis, r, half[, band])} in the part's own frame:
centre on the axis, `half` the slab along it that holds the feature's wall, `band` the radial window of the fit (x r)."""

from model import envelopes, fits, printed, stages

COAXIAL_MM = 0.2
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


def feature(part, name):
    """(world centre, world axis, fitted r) of a part's feature, or None when its mesh has no such feature."""
    centre, axis, r, half, *band = FEATURES[stages.stem(part.file)][name]
    try:
        fit = fits.fit_circle(part.file, centre, axis, half, r, *band or [fits.HOLE])
    except ValueError:
        return None
    m = part.matrix
    return m[:3, :3] @ fit["centre"] + m[:3, 3], m[:3, "xyz".index(axis)], fit["r"]
