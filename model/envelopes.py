"""Our hardware envelopes (#58): simple CadQuery stand-ins for the Bambu CyberBrick hardware (servo, Horn, Shield,
Core, switch board, battery) so the engine and the renders need no Bambu file. Each is drawn in its STEP file's own
frame, registered in ENVELOPES by its mesh's name, with the features the mating check fits in FEATURES. Interfaces
(mount holes, shaft, connectors) are the STEP's numbers, read once (history: docs/research); bodies are boxes, plates
and circle hulls of the STEP's outer faces; inner detail is dropped."""

import cadquery as cq
import numpy as np
from scipy.spatial import ConvexHull

from model import fits


def box(x, y, z):
    """The box spanning (lo, hi) on each axis."""
    return cq.Workplane("XY").box(x[1] - x[0], y[1] - y[0], z[1] - z[0], centered=False).translate((x[0], y[0], z[0]))


def hull(plane, circles, depth, origin=(0, 0, 0)):
    """The convex hull of (u, v, r) circles on `plane` at `origin`, extruded `depth` along its normal."""
    t = np.linspace(0, 2 * np.pi, 96, endpoint=False)
    pts = np.concatenate([np.c_[u + r * np.cos(t), v + r * np.sin(t)] for u, v, r in circles])
    ring = pts[ConvexHull(pts).vertices]
    return cq.Workplane(plane, origin=origin).polyline([tuple(p) for p in ring]).close().extrude(depth)


# Servo (9g with clutch): case z -6.9..16.3 (r 1 corners), the tab plate z -2.3..0 with its two slotted r 1.0 tab holes,
# the gear top up to z -11.2 (the hull of the r 5.4 boss on the shaft and an r 3.8 boss beside it) and the r 2.35
# spline to its tip at z -14.52. The lead is not drawn (the engine cuts it at x 27.7).
SERVO = {
    "case": ((-0.05, 22.75), (-0.05, 11.85), (-6.9, 16.3)),
    "tabs": ((-4.9, 27.6), (0.0, 11.8), (-2.3, 0.0)),
    "tab_holes": ((-2.55, 5.9), (25.25, 5.9)),
    "tab_r": 1.0,
    "slot_y": (5.3, 6.5),  # open from each hole to the tab's end
    "shaft": (16.69, 5.9),
    "boss": ((16.69, 5.9, 5.4), (11.7, 5.9, 3.8)),
    "boss_z": (-11.2, -6.9),
    "spline_r": 2.35,
    "tip_z": -14.52,
}


def servo():
    s = SERVO
    case = box(*s["case"]).edges("|Z").fillet(1.0)
    tabs = box(*s["tabs"]).edges("|Z").fillet(1.0)
    (hx0, hy), (hx1, _) = s["tab_holes"]
    (x0, x1), _, (z0, z1) = s["tabs"]
    tabs = tabs.cut(
        cq.Workplane("XY", origin=(0, 0, z0)).pushPoints(s["tab_holes"]).circle(s["tab_r"]).extrude(z1 - z0)
    )
    for slot in ((x0 - 1, hx0), (hx1, x1 + 1)):
        tabs = tabs.cut(box(slot, s["slot_y"], (z0, z1)))
    bz0, bz1 = s["boss_z"]
    top = hull("XY", s["boss"], bz1 - bz0, (0, 0, bz0))
    sx, sy = s["shaft"]
    spline = cq.Workplane("XY", origin=(sx, sy, s["tip_z"])).circle(s["spline_r"]).extrude(bz0 - s["tip_z"])
    return case.union(tabs).union(top).union(spline)


# Horn (the kit's short single arm, "half arm1"): the r 3.63 hub on (0, 20), z 0..4.15, with the r 2.14 spline bore
# down to z 1.85 from the spline side (z 4.15), the screw's r 1.0 hole and r 2.45 counterbore from the outer face (z 0);
# the 1.55 thick arm along +X tapering to its r 2.0 tip at x 14.05, with r 0.5 holes every 2 mm out to x 14.75 (the bars
# pin at 12.75, geometry.HORN_STEP).
HORN = {
    "hub": (0.0, 20.0),
    "hub_r": 3.63,
    "height": 4.15,
    "bore": (2.14, 1.85),
    "screw_r": 1.0,
    "counterbore": (2.45, 1.1),
    "arm": ((0.0, 20.0, 2.9), (14.05, 20.0, 2.0)),
    "arm_t": 1.55,
    "holes_x": (4.75, 6.75, 8.75, 10.75, 12.75, 14.75),
    "hole_r": 0.5,
}


def horn():
    h = HORN
    hx, hy = h["hub"]
    out = cq.Workplane("XY", origin=(hx, hy, 0)).circle(h["hub_r"]).extrude(h["height"])
    out = out.union(hull("XY", h["arm"], h["arm_t"]))
    (br, bz), (cr, cz) = h["bore"], h["counterbore"]
    out = out.cut(cq.Workplane("XY", origin=(hx, hy, bz)).circle(br).extrude(h["height"] - bz))
    out = out.cut(cq.Workplane("XY", origin=(hx, hy, 0)).circle(h["screw_r"]).extrude(h["height"]))
    out = out.cut(cq.Workplane("XY", origin=(hx, hy, 0)).circle(cr).extrude(cz))
    holes = cq.Workplane("XY").pushPoints([(x, hy) for x in h["holes_x"]]).circle(h["hole_r"]).extrude(h["arm_t"])
    return out.cut(holes)


def boxes(spans):
    out = box(*spans[0])
    for b in spans[1:]:
        out = out.union(box(*b))
    return out


def plate(outline, y, holes=(), r=0.0):
    """A PCB in the XZ plane: the (x, z) outline from y[0] to y[1], with r holes at (x, z)."""
    out = cq.Workplane("XZ", origin=(0, y[1], 0)).polyline(outline).close().extrude(y[1] - y[0])
    for x, z in holes:
        out = out.cut(cq.Workplane("XZ", origin=(x, y[1], z)).circle(r).extrude(y[1] - y[0]))
    return out


def mirror_x(spans):
    return [*spans, *(((-x1, -x0), y, z) for (x0, x1), y, z in spans)]


# Shield (X11, the STEP's "receiver"): PCB bottom y 0, 29 x 30 (r 3 corners) with r 1.35 mount holes at x +-11.5,
# z +-12; on top the XH power socket at z -15..-7.2, the two servo header bodies and their 0.64 square pins (x +-1.69,
# +-4.23, +-6.77; z 1.23, 3.77) up to y 10.78, the edge parts at x +-(9.5..14.5); under it the Core's two sockets.
SHIELD = {
    "pcb": ((14.5, 15.0, 3.0), (0.0, 1.6)),
    "holes": ((-11.5, -12.0), (-11.5, 12.0), (11.5, -12.0), (11.5, 12.0)),
    "hole_r": 1.35,
    "parts": [
        ((-3.75, 3.75), (1.6, 7.6), (-15.0, -7.2)),  # XH power socket
        *mirror_x(
            [
                ((0.42, 8.04), (1.6, 4.78), (-0.04, 5.04)),  # servo header body
                ((9.45, 14.5), (1.6, 4.65), (1.32, 6.68)),
                ((9.5, 14.5), (1.6, 4.6), (-4.65, -0.35)),
                ((6.0, 8.0), (-4.3, 0.0), (-8.15, 8.15)),  # the Core's socket
            ]
        ),
    ],
    "pins_x": (-6.77, -4.23, -1.69, 1.69, 4.23, 6.77),
    "pins_z": (1.23, 3.77),
    "pin": (0.64, (1.6, 10.78)),
}


def rounded(half_x, half_z, r):
    """(x, z) outline of a rounded rectangle, 8 points per corner."""
    out = []
    for cx, cz, a in ((half_x - r, half_z - r, 0), (r - half_x, half_z - r, 90), (r - half_x, r - half_z, 180)):
        out += [(cx + r * np.cos(np.radians(a + t)), cz + r * np.sin(np.radians(a + t))) for t in np.linspace(0, 90, 8)]
    cx, cz = half_x - r, r - half_z
    out += [(cx + r * np.cos(np.radians(270 + t)), cz + r * np.sin(np.radians(270 + t))) for t in np.linspace(0, 90, 8)]
    return [tuple(map(float, p)) for p in out]


def shield():
    s = SHIELD
    (hx, hz, r), y = s["pcb"]
    out = plate(rounded(hx, hz, r), y, s["holes"], s["hole_r"]).union(boxes(s["parts"]))
    w, (y0, y1) = s["pin"]
    pins = [((x - w / 2, x + w / 2), (y0, y1), (z - w / 2, z + w / 2)) for x in s["pins_x"] for z in s["pins_z"]]
    return out.union(boxes(pins))


# Core: PCB y -7.4..-5.8 (x +-11 between z +-8.5, its pads out to x +-11.6 on the module side, the USB end x +-4.5 to z -12.5, the antenna end x +-7 to z 14.5), the
# module can (x +-9.75, z -2.45..8.05) down to y -9.4, the USB-C socket (x +-4.47, z -13.39..-6.05) to y -10.68, and on
# the Shield side its two header rows (x +-(6..8)) up to y -2.3.
CORE = {
    "pcb": (
        [(-11, -8.5), (-4.5, -8.5), (-4.5, -12.5), (4.5, -12.5), (4.5, -8.5), (11, -8.5), (11, 8.5), (7, 8.5)]
        + [(7, 14.5), (-7, 14.5), (-7, 8.5), (-11, 8.5)],
        (-7.4, -5.8),
    ),
    "parts": [
        ((-11.6, 11.6), (-7.41, -7.3), (-7.25, 7.25)),  # the castellated pads, 0.6 past the PCB's long edges
        ((-9.75, 9.75), (-9.4, -7.4), (-2.45, 8.05)),  # module can
        ((-4.47, 4.47), (-10.68, -7.4), (-13.39, -6.05)),  # USB-C
        *mirror_x([((6.0, 8.0), (-5.8, -2.3), (-7.55, 7.55))]),  # header rows
    ],
}


def core():
    return plate(*CORE["pcb"]).union(boxes(CORE["parts"]))


# Switch board: PCB y 0..1.6, x -7.25..7.25 by z +-16, with the tab out to its r 3 end round the r 1.35 mounting hole
# at (10.25, z 0) (geometry.SWITCH_STEP); on top the two XH sockets at z +-(7.7..15.5), the slide switch and its lever
# up to y 15.16; under it the switch's pins down to y -4.6.
SWITCH = {
    "pcb": (
        [(-7.25, -16), (7.25, -16), (7.25, -3), (10.25, -3), (10.25, 3), (7.25, 3), (7.25, 16), (-7.25, 16)],
        (0, 1.6),
    ),
    "tab": ((10.25, 0.0), 3.0),
    "hole_r": 1.35,
    "parts": [
        ((-4.5, 3.0), (1.6, 7.6), (7.7, 15.5)),  # XH sockets
        ((-4.5, 3.0), (1.6, 7.6), (-15.5, -7.7)),
        ((-7.11, 5.59), (1.6, 8.9), (-3.37, 3.37)),  # slide switch
        ((-3.71, 0.19), (8.6, 15.16), (-1.97, 1.97)),  # its lever
        *[((x, x + 0.8), (-4.6, 0.0), (-1.03, 1.07)) for x in (-5.96, -1.16, 3.64)],  # its pins
    ],
}


def switch():
    s = SWITCH
    outline, y = s["pcb"]
    (tx, tz), tr = s["tab"]
    out = plate(outline, y).union(cq.Workplane("XZ", origin=(tx, y[1], tz)).circle(tr).extrude(y[1] - y[0]))
    out = out.cut(cq.Workplane("XZ", origin=(tx, y[1], tz)).circle(s["hole_r"]).extrude(y[1] - y[0]))
    return out.union(boxes(s["parts"]))


# Battery (14500 7.4 V 800 mAh): two cells side by side, the hull of r 8.15 circles at x +-6.03 (floor z -8.15,
# geometry.BATTERY_STEP), along +Y from 0 to the pack's end at 51.2; the lead beyond is not drawn (the engine cuts it).
BATTERY = {"cells": ((-6.03, 0.0, 8.15), (6.03, 0.0, 8.15)), "length": 51.2}


def battery():
    # the XZ plane's normal is -Y: extrude back to +Y
    return hull("XZ", BATTERY["cells"], -BATTERY["length"])


def servo_features():
    """{feature: (centre, axis, r, half[, band])} the mating check fits on our mesh (model/engine/mating.py)."""
    s, (_, _, (z0, z1)) = SERVO, SERVO["tabs"]
    z, half = fits.slab(z0, z1)
    (far, near), spline = s["tab_holes"], fits.slab(s["tip_z"], s["boss_z"][0])
    return {
        "near tab hole": ((*near, z), "z", s["tab_r"], half),
        "far tab hole": ((*far, z), "z", s["tab_r"], half),
        "spline": ((*s["shaft"], spline[0]), "z", s["spline_r"], spline[1], (0.8, 1.2)),  # clear of the collar r 2.4
    }


def horn_features():
    """{feature: (centre, axis, r, half[, band])} the mating check fits on our mesh (model/engine/mating.py)."""
    h = HORN
    bore_z, bore_half = fits.slab(h["bore"][1], h["height"])
    pin_z, pin_half = fits.slab(0, h["arm_t"])
    return {
        "bore": ((*h["hub"], bore_z), "z", h["bore"][0], bore_half, fits.BORE),
        "pin hole": ((h["holes_x"][4], h["hub"][1], pin_z), "z", h["hole_r"], pin_half),  # the bars pin at 12.75
    }


ENVELOPES = {"servo": servo, "horn": horn, "receiver": shield, "core": core, "switch": switch, "battery": battery}
FEATURES = {"servo": servo_features(), "horn": horn_features()}
