"""Our eyelid bar and eyelid bar crank: independent parametric designs (never traced from the designer's meshes) in
their own local frame (model/geometry.py STL_LOCAL: holes 41 mm apart along X, both along Z). A 5 wide, 3 thick slot;
the horn screw's r 1.1 hole at +x, the lid screw's r 1.35 at -x. The crank is the same bar with its lid end stepped up
3 mm (+Z, toward the lid ear)."""

import cadquery as cq

from model import fits

PITCH, WIDTH, THICK = 41.0, 5.0, 3.0
HORN_R, LID_R = 1.1, 1.35
STEP = {"x": (-23.0, -12.0), "from_x": -18.0}  # the crank: the lid end's slot, and where the lower bar starts


def build():
    return slot(-PITCH / 2, PITCH / 2, 0).cut(hole(PITCH / 2, 0, HORN_R)).cut(hole(-PITCH / 2, 0, LID_R))


def crank():
    r = WIDTH / 2
    low = slot(STEP["from_x"] + r, PITCH / 2, 0).cut(hole(PITCH / 2, 0, HORN_R))
    return low.union(slot(STEP["x"][0] + r, STEP["x"][1] - r, THICK).cut(hole(-PITCH / 2, THICK, LID_R)))


def slot(x0, x1, z):
    """A stadium of WIDTH between end centres x0 and x1 at y 0, z..z+THICK."""
    return cq.Workplane("XY", origin=((x0 + x1) / 2, 0, z)).slot2D(x1 - x0 + WIDTH, WIDTH).extrude(THICK)


def hole(x, z, r):
    return cq.Workplane("XY", origin=(x, 0, z - 1)).circle(r).extrude(THICK + 2)


def features(crank=False):
    """{feature: (centre, axis, r, half[, band])} the mating check fits on our mesh (model/engine/mating.py)."""
    z, half = fits.slab(0, THICK)
    lid_z = z + THICK if crank else z
    return {"horn hole": ((PITCH / 2, 0, z), "z", HORN_R, half), "lid hole": ((-PITCH / 2, 0, lid_z), "z", LID_R, half)}
