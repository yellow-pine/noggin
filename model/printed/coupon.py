"""The clearance coupon (#624): a Coupon, not a part of the Mech. Printed once in each filament, it shows the clearance
our printer needs before a pivot or a magnet seat relies on one (docs/research/2026-11-02-literature-cams-am.md:
below a critical clearance a printed joint fuses). A plate flat on the bed, a 3 mm pin printed in each hole, the
clearance per side stepping up from the notched corner, and a row of pockets for the shells' 4x2 mm magnet disc
(docs/face-design.md), each at its own fit. How to print and read it: docs/build/tests.md."""

import cadquery as cq

PINS = (0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4)  # clearance per side, mm
POCKETS = (0.05, 0.1, 0.15, 0.2)  # the magnet pockets' clearance per side, mm
PIN_D = 3.0  # the busy pivots' steel shank, an M3 screw's (inferred)
DISC = (4.0, 2.0)  # the magnet disc, diameter x height
PLATE, PROUD, PITCH = 4.0, 4.0, 8.0  # plate thickness, pin above it, spacing
FOOT = 0.4  # each hole's bottom edge chamfered: the first layer's squish would fuse every pin
SLOT = (0.8, 1.5)  # a screwdriver slot in each pin's top, width x depth
NOTCH = 3.0  # the corner by the tightest pin, cut at 45 degrees


def pin(i):
    """Pin i's centre (x, y): from the notched corner up."""
    return 7.0 + PITCH * i, 6.0


def pocket(i):
    """Magnet pocket i's centre (x, y), tightest by the notched end."""
    return 7.0 + PITCH * i, 16.0


def build():
    size = (2 * 7.0 + PITCH * (len(PINS) - 1), 22.0)
    notch = cq.Workplane("XY").polyline([(0, 0), (NOTCH, 0), (0, NOTCH)]).close().extrude(PLATE)
    plate = cq.Workplane("XY").box(*size, PLATE, centered=False).cut(notch)
    pins = []
    for i, c in enumerate(PINS):
        (x, y), r = pin(i), PIN_D / 2 + c
        hole = (
            cq.Workplane("XY").circle(r).extrude(PLATE).union(cq.Workplane().add(cq.Solid.makeCone(r + FOOT, r, FOOT)))
        )
        plate = plate.cut(hole.translate((x, y, 0)))
        slot = cq.Workplane("XY").box(PIN_D, SLOT[0], SLOT[1], centered=(True, True, False))
        top = PLATE + PROUD
        pins.append(
            cq.Workplane("XY")
            .circle(PIN_D / 2)
            .extrude(top)
            .cut(slot.translate((0, 0, top - SLOT[1])))
            .translate((x, y, 0))
        )
    for i, c in enumerate(POCKETS):
        (x, y), (d, h) = pocket(i), DISC
        seat = cq.Workplane("XY").circle(d / 2 + c).extrude(h).translate((0, 0, PLATE - h))
        plate = plate.cut(seat.union(cq.Workplane("XY").circle(0.75).extrude(PLATE)).translate((x, y, 0)))
    return cq.Workplane().add(cq.Compound.makeCompound([plate.val(), *(p.val() for p in pins)]))
