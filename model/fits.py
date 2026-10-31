"""Pin fits at every pinned joint of a sub-assembly: a circle fitted (least squares) to the designer's STL around the
hole, compared with the fastener. Radial clearance outside CLEARANCE is flagged. Pure Python; `python model/fits.py`
prints the eyes table. Designer STLs: docs/references (local only)."""

import functools
import math
import os
import struct
import sys

CLEARANCE = (0.1, 0.4)  # mm radial, agreed in #20
M2 = 2.0  # M2 screw shank diameter (the bars are screwed to the horn and the eyeball)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EYES_MODELS = os.path.join(REPO, "docs/references/01-eyes/models")
PT_MODELS = os.path.join(REPO, "docs/references/02-pan-tilt/models")
MOUTH_MODELS = os.path.join(REPO, "docs/references/03-mouth/models")
# without the designer's STLs (CI) read ours (model/ours.py), as model/engine/stages.py does
HAVE_REFERENCES = os.path.isdir(EYES_MODELS) and os.path.isfile(os.path.join(REPO, "model/build/steps/horn.stl"))
if not HAVE_REFERENCES:
    EYES_MODELS = PT_MODELS = MOUTH_MODELS = os.path.join(REPO, "model/build/ours")
M2_5 = 2.5  # M2.5 lever and pivot screws (guide: all screws M2.5 unless stated)


def stl(name, folder=EYES_MODELS):
    return os.path.join(folder, name + ".stl")


@functools.cache
def vertices(path):
    d = open(path, "rb").read()
    n = struct.unpack_from("<I", d, 80)[0]
    if 84 + n * 50 == len(d):  # binary
        return {struct.unpack_from("<3f", d, 84 + i * 50 + 12 + 12 * k) for i in range(n) for k in range(3)}
    return {tuple(float(t) for t in l.split()[1:]) for l in d.decode().splitlines() if l.strip().startswith("vertex")}


def fit_circle(path, centre, axis, half, expect_r, within=(0.6, 1.8)):
    """Least-squares circle (Kasa) through the STL vertices within `half` mm of `centre` along `axis` and within
    `within` x expect_r of it radially (a hole's wall vertices sit on its two mouth rings, so `half` spans the part).
    Returns r, the fitted centre, its offset from `centre` and the rms radial residual (large = not round: slot or
    countersink)."""
    i = "xyz".index(axis)
    u, v = [k for k in range(3) if k != i]
    pts = [(p[u] - centre[u], p[v] - centre[v]) for p in vertices(path) if abs(p[i] - centre[i]) <= half]
    pts = [p for p in pts if within[0] * expect_r <= math.hypot(*p) <= within[1] * expect_r]
    if len(pts) < 3:
        raise ValueError(f"{os.path.basename(path)}: no vertices around {centre} {axis}")
    # x^2 + y^2 + a x + b y + c = 0, normal equations solved by elimination
    m = [
        [
            sum(x * x for x, _ in pts),
            sum(x * y for x, y in pts),
            sum(x for x, _ in pts),
            -sum(x * (x * x + y * y) for x, y in pts),
        ],
        [
            sum(x * y for x, y in pts),
            sum(y * y for _, y in pts),
            sum(y for _, y in pts),
            -sum(y * (x * x + y * y) for x, y in pts),
        ],
        [sum(x for x, _ in pts), sum(y for _, y in pts), len(pts), -sum(x * x + y * y for x, y in pts)],
    ]
    for r in range(3):
        p = max(range(r, 3), key=lambda k: abs(m[k][r]))
        m[r], m[p] = m[p], m[r]
        for k in range(3):
            if k != r:
                f = m[k][r] / m[r][r]
                m[k] = [a - f * b for a, b in zip(m[k], m[r])]
    a, b, c = (m[k][3] / m[k][k] for k in range(3))
    x0, y0 = -a / 2, -b / 2
    r = math.sqrt(x0 * x0 + y0 * y0 - c)
    rms = math.sqrt(sum((math.hypot(x - x0, y - y0) - r) ** 2 for x, y in pts) / len(pts))
    c = list(centre)
    c[u], c[v] = centre[u] + x0, centre[v] + y0
    return {
        "r": round(r, 3),
        "centre": tuple(c),
        "offset": round(math.hypot(x0, y0), 3),
        "rms": round(rms, 3),
        "n": len(pts),
    }


def fit_table(joints):
    """joints: (name, hole, pin) with hole = (stl, centre, axis, half) and pin = fastener diameter mm or another
    (stl, centre, axis, half) whose outer wall is fitted the same way (a printed pin)."""
    out = []
    for name, hole, pin, *tag in joints:
        p = pin / 2 if isinstance(pin, float) else fit_circle(*pin, expect_r=1.0)["r"]
        h = fit_circle(*hole, expect_r=p)
        clearance = round(h["r"] - p, 2)
        row = {
            "joint": name,
            "hole_r": h["r"],
            "pin_r": round(p, 3),
            "clearance": clearance,
            "offset": h["offset"],
            "rms": h["rms"],
            "ok": CLEARANCE[0] <= clearance <= CLEARANCE[1],
        }
        if tag:
            row["tag"], row["ok"] = tag[0], True  # self_tapping: the screw cuts its thread, no clearance by design
        out.append(row)
    return out


# Eyes sub-assembly (L side; the R side uses the same STLs mirrored). Hole centres fitted here, not geometry.STL_LOCAL.
# Both bars take the horn screw in their smaller hole (+x end) and the lid in the larger (-x end; guide p.23); the
# crank's lid end is stepped up 3 mm. The crank goes to the inside (top) lid, the straight bar to the outside one (#48).
EYES_JOINTS = [
    ("eyelid bar / horn screw", (stl("eyelid bar"), (20.5, 0, 1.5), "z", 2), M2),
    (
        "eyelid bar / outside lid pin",
        (stl("eyelid bar"), (-20.5, 0, 1.5), "z", 2),
        (stl("outside lid"), (-22, -12, 0), "x", 3),
    ),
    ("eyelid crank / horn screw", (stl("eyelid bar crank"), (20.5, 0, 1.5), "z", 2), M2),
    (
        "eyelid crank / inside lid pin",
        (stl("eyelid bar crank"), (-20.5, 0, 4.5), "z", 2),
        (stl("inside lid"), (-22, 12, 0), "x", 3),
    ),
    ("eyeball bar / horn screw", (stl("eyeball bar"), (-10, 4, 27), "y", 2), M2, "self_tapping"),
    ("eyeball bar / eyeball screw", (stl("eyeball bar"), (-10, 4, 0), "y", 2), M2),
    (
        "inside lid ear / bracket pin",
        (stl("inside lid"), (-22.5, 0, 0), "x", 2),
        (stl("main bracket v2", MOUTH_MODELS), (-22.5, 0, 0), "x", 2),
    ),
    (
        "outside lid ear / bracket pin",
        (stl("outside lid"), (-22.5, 0, 0), "x", 2),
        (stl("main bracket v2", MOUTH_MODELS), (-22.5, 0, 0), "x", 2),
    ),
]
EYES_RECORDED = {  # (hole_r, pin_r, ok) read 2026-10-31; the eyeball bar's horn end (0.05 mm) self-taps by design
    "eyelid bar / horn screw": (1.1, 1.0, True),
    "eyelid bar / outside lid pin": (1.35, 1.0, True),
    "eyelid crank / horn screw": (1.1, 1.0, True),
    "eyelid crank / inside lid pin": (1.35, 1.0, True),
    "eyeball bar / horn screw": (1.05, 1.0, True),
    "eyeball bar / eyeball screw": (1.25, 1.0, True),
    "inside lid ear / bracket pin": (1.998, 1.735, True),
    "outside lid ear / bracket pin": (1.959, 1.735, True),
}

# Stack sub-assembly (pan-tilt): bars pinned to the horns with M2 screws and nuts at the smaller hole (guide step 12), screwed to
# the levers and the tilt pivot with M2.5 (self-tapping into the r 1.1 holes, as the eyeball bar's horn end).
PT_JOINTS = [
    ("tilt bar / horn screw", (stl("tilt bar", PT_MODELS), (10, 0, 1.5), "z", 2), M2),
    ("tilt bar / arm lever screw", (stl("tilt bar", PT_MODELS), (-10, 0, 1.5), "z", 2), M2_5),
    ("tilt arm lever / M2.5", (stl("PandT tilt arm", PT_MODELS), (8, 26.5, 33.4), "x", 3), M2_5, "self_tapping"),
    ("pan bar / horn screw", (stl("PandT bar", PT_MODELS), (7.5, 0, 1.5), "z", 2), M2),
    ("pan bar / upright lever screw", (stl("PandT bar", PT_MODELS), (-7.5, 0, 1.5), "z", 2), M2_5),
    ("upright lever / M2.5", (stl("PandT upright v2", PT_MODELS), (-5.5, 25.5, 26.8), "z", 5), M2_5, "self_tapping"),
    ("tilt arm / pivot screw", (stl("PandT tilt arm", PT_MODELS), (14, -13, 28.4), "x", 1.5), M2_5),
    ("upright / pivot screw", (stl("PandT upright v2", PT_MODELS), (11, -13, 33.4), "x", 1.5), M2_5, "self_tapping"),
]
PT_RECORDED = {  # (hole_r, pin_r, ok) read 2026-10-31
    "tilt bar / horn screw": (1.1, 1.0, True),
    "tilt bar / arm lever screw": (1.35, 1.25, True),
    "tilt arm lever / M2.5": (1.1, 1.25, True),
    "pan bar / horn screw": (1.1, 1.0, True),
    "pan bar / upright lever screw": (1.35, 1.25, True),
    "upright lever / M2.5": (1.1, 1.25, True),
    "tilt arm / pivot screw": (1.35, 1.25, True),
    "upright / pivot screw": (1.1, 1.25, True),
}

# Mouth sub-assembly: the top jaw's pins in the bottom jaw's hinge holes (clipped on, guide step 7) and the connector bar's M2.5
# self-tapped into the jaw's pivot lug (step 8). The bar's own holes are not fitted: at 960 vertices the hole rings tangle
# with the tab-end rounding (rms 0.1-0.16); the research note reads them as r ~1.25.
MOUTH_JOINTS = [
    (
        "L hinge / top jaw pin",
        (stl("bottom jaw plain", MOUTH_MODELS), (-8, -49.6, 8), "x", 3),
        (stl("top jaw plain", MOUTH_MODELS), (-8, -49.6, 8), "x", 4),
    ),
    (
        "R hinge / top jaw pin",
        (stl("bottom jaw plain", MOUTH_MODELS), (70, -49.6, 8), "x", 3),
        (stl("top jaw plain", MOUTH_MODELS), (68, -49.6, 8), "x", 4),
    ),
    (
        "jaw pivot lug / M2.5",
        (stl("bottom jaw plain", MOUTH_MODELS), (66, -58.1, -10.44), "x", 5),
        M2_5,
        "self_tapping",
    ),
]
MOUTH_RECORDED = {  # (hole_r, pin_r, ok) read 2026-10-31; the L pin reads 1.72 (coarser facets than the R pin's 1.75)
    "L hinge / top jaw pin": (2.0, 1.72, True),
    "R hinge / top jaw pin": (2.0, 1.75, True),
    "jaw pivot lug / M2.5": (1.1, 1.25, True),
}


if __name__ == "__main__":
    for row in fit_table(EYES_JOINTS + PT_JOINTS + MOUTH_JOINTS):
        print(
            "%-32s hole r %.3f  pin r %.3f  clearance %5.2f  offset %.2f  rms %.3f  %s"
            % (
                row["joint"],
                row["hole_r"],
                row["pin_r"],
                row["clearance"],
                row["offset"],
                row["rms"],
                row.get("tag") or ("ok" if row["ok"] else "FLAG"),
            )
        )
    sys.exit(0)
