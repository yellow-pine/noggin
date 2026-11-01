"""Our pan servo mounts, the tail mount and the lead mount (its arch lets the servo lead out): independent parametric designs (never traced from the designer's meshes)
in the PT frame (Z up, pan axis Z through the origin). One XZ profile 5 deep along Y: a z 3..6 foot screwed to the base
through r 1.35 holes at x -32.5 and -8.5, a tower to the z 15 top (chamfered 3 at the top corners) with the pan servo's
r 1.1 tab hole down from it at x -20.5. The lead mount arches over the base (x -25.5..-15.5 up to z 8). Measured
numbers: docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

from model import fits

PROFILE = [(-35.5, 3), (-5.5, 3), (-5.5, 6), (-11.5, 6), (-11.5, 12), (-14.5, 15), (-26.5, 15), (-29.5, 12), (-29.5, 6)]
PROFILE += [(-35.5, 6)]
DEPTH = 5.0
TOP, TAB_X, TAB_R, TAB_BOTTOM = 15.0, -20.5, 1.1, 5.0
FEET_X, FOOT_R, FOOT_TOP = (-32.5, -8.5), 1.35, 6.0
ARCH = {"x": (-25.5, -15.5), "top": 8.0}


TAIL, LEAD = ((27.0, 32.0), 29.55, 29.5), ((54.9, 59.9), 57.35, 57.4)  # (y span, tab hole y, feet y)


def tail():
    return mount(*TAIL)


def lead():
    out = mount(*LEAD)
    (x0, x1), y0 = ARCH["x"], 54.9
    arch = cq.Workplane("XY").box(x1 - x0, DEPTH, ARCH["top"] - 3, centered=False).translate((x0, y0, 3))
    return out.cut(arch)


def mount(y, tab_y, feet_y):
    out = cq.Workplane("XZ", origin=(0, y[1], 0)).polyline(PROFILE).close().extrude(y[1] - y[0])
    out = out.cut(cq.Workplane("XY", origin=(TAB_X, tab_y, TAB_BOTTOM)).circle(TAB_R).extrude(TOP - TAB_BOTTOM))
    feet = cq.Workplane("XY", origin=(0, feet_y, 3)).pushPoints([(x, 0) for x in FEET_X]).circle(FOOT_R)
    return out.cut(feet.extrude(FOOT_TOP - 3))


def features(which):
    """{feature: (centre, axis, r, half[, band])} the mating check fits on our mesh (model/mating.py)."""
    _, tab_y, feet_y = which
    z, half = fits.slab(TAB_BOTTOM, TOP)
    foot_z, foot_half = fits.slab(3.0, FOOT_TOP)  # the foot from the z 3 profile floor
    feet = {f"foot {k}": ((x, feet_y, foot_z), "z", FOOT_R, foot_half) for k, x in zip(("outer", "inner"), FEET_X)}
    return {"tab hole": ((TAB_X, tab_y, z), "z", TAB_R, half), **feet}
