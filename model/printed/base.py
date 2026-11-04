"""The Mech's Torso (#685), the cranium tray that carries the Cores in the head (#858), and Stage 1's test stand
(#720) as CadQuery parts, every size from model/base.py, each drawn where it sits at rest in the head's frame
(model/neck.py)."""

import cadquery as cq

from model import base as nb
from model import gimbal as gm
from model import neck as nk
from model.envelopes import box
from model.printed import bone
from model.printed.gimbal import cyl

WALL, RIM = 2.0, 6.0  # the Torso's and the pack cradle's walls; the cradle's height, 0.5 mm clear round the pack
ROUND = 12.0  # as Bones (#704): the test stand's upright edges round by a third of it
CORNER = 4.0  # as Bones: the Torso's upright corners round
# the pedestal's look as Bones (#838): the plaque sunk 1 mm in its front, (x, z), and the lid's panel inside a border
# 1 mm down, BORDER in from its edge
PLAQUE, BORDER = ((-16.0, 16.0), (-156.0, -146.0)), 9.0  # under the shirt's Seats
LEDGE, FIT = 3.0, 0.3  # the ledge inside the walls the lid lies on, flush with their top; its room inside them


def _box(x, y, z, r=0.0, edges="|Z"):
    """A box (envelopes.box), its `edges` filleted r when r."""
    out = box(x, y, z)
    return out.edges(edges).fillet(r) if r else out


@bone.carved
def torso(mechanical=False):
    """The Torso (printed upright), the realistic skull's box pedestal (#838): its floor (the foot; the neck mount stands
    on it), its walls round it, a ledge inside their top for its lid (the pack in and out under it); the pack's cradle
    on the floor behind the neck mount. As Bones (#708), carved
    from it (#809): its upright corners round and a plaque sunk in its front, as the picture Cansin gave."""
    (x0, x1), (y0, y1), (z0, z1) = nb.TORSO
    floor, top = nk.MOUNT_Z[0], z1 - nb.LID_T
    out = _box((x0, x1), (y0, y1), (z0, z1), 0.0 if mechanical else CORNER)
    out = out.cut(_box((x0 + WALL, x1 - WALL), (y0 + WALL, y1 - WALL), (floor, z1 + 1)))
    out = out.union(_ledge(top))
    if not mechanical:
        (px0, px1), (pz0, pz1) = PLAQUE  # sunk 1 mm, its top at 45 deg so it prints upright
        sunk = [(y0 - 1, pz0), (y0 + 1, pz0), (y0 + 1, pz1 - 2), (y0 - 1, pz1)]
        out = out.cut(cq.Workplane("YZ", origin=(px0, 0, 0)).polyline(sunk).close().extrude(px1 - px0))
    w, d = nb.PACK[0] / 2 + 0.5, nb.PACK[1] / 2 + 0.5
    ring = _box((-w - WALL, w + WALL), (nb.PACK_Y - d - WALL, nb.PACK_Y + d + WALL), (floor, floor + RIM))
    return out.union(ring.cut(box((-w, w), (nb.PACK_Y - d, nb.PACK_Y + d), (floor, floor + RIM))))


def _ledge(top):
    """A ledge round inside the walls' top, LEDGE wide, its underside 45 deg (it prints upright): the lid lies on it."""
    (x0, x1), (y0, y1), _ = nb.TORSO
    xi, yi = (x0 + WALL, x1 - WALL), (y0 + WALL, y1 - WALL)
    (cx, cy), (w, d) = ((sum(xi) / 2, sum(yi) / 2)), (xi[1] - xi[0], yi[1] - yi[0])
    under = (
        cq.Workplane("XY", origin=(cx, cy, top - LEDGE))
        .rect(w, d)
        .workplane(offset=LEDGE)
        .rect(w - 2 * LEDGE, d - 2 * LEDGE)
        .loft()
    )
    return box(xi, yi, (top - LEDGE, top)).cut(under)


@bone.carved
def lid(mechanical=False):
    """The Torso's lid (printed flat), inside the walls' top on their ledge, so it lifts out but never slides: the neck
    mount's post up through a hole in its middle, slotted to the back so it slides on over the walls and
    drops in, and a hole over the switch board's lever. As Bones, carved from it: a border 1 mm down round its panel,
    as the picture."""
    (x0, x1), (y0, y1), (_, z1) = nb.TORSO
    y_axis, hole = nk.AXIS[0], nk.POST_R + nb.POST_GAP
    a = WALL + FIT
    out = box((x0 + a, x1 - a), (y0 + a, y1 - a), (z1 - nb.LID_T, z1))
    out = out.cut(cyl("z", (0, y_axis, 0), hole, (z1 - nb.LID_T - 1, z1 + 1)))
    out = out.cut(box((-hole, hole), (y_axis, y1 + 1), (z1 - nb.LID_T - 1, z1 + 1)))
    out = out.cut(cyl("z", (*nb.SWITCH_AT, 0), 6.0, (z1 - nb.LID_T - 1, z1 + 1)))  # a finger down to the switch's lever
    if not mechanical:
        inner = box((x0 + BORDER, x1 - BORDER), (y0 + BORDER, y1 - BORDER), (z1 - 1, z1 + 1))
        out = out.cut(box((x0 + 3, x1 - 3), (y0 + 3, y1 - 3), (z1 - 1, z1 + 1)).cut(inner))
    return out


def tray(mechanical=False):
    """The cranium tray (#858; printed on its plate's top, upside down), hidden in the realistic skull's cranium in every
    Skeleton, so drawn one way (mechanical alike): its plate over the eyes' drives that the Cores lie on, a leg down
    from each back corner behind the bail to its foot on the gimbal frame's plate, and the hub's riser on the plate from
    the R foot forward, a hole in it round the head mount's rear L screw's nut."""
    (x0, x1), (y0, y1) = nb.LEG_X, nb.LEG_Y
    out = box((-x1 - 6, x1 + 6), (nb.CORES_AT[1] - 17, y1), nb.TRAY_Z)
    for s in (-1, 1):
        out = out.union(box(sorted((s * x0, s * x1)), (y0, y1), (gm.PLATE_Z[1], nb.TRAY_Z[0])))
    # the riser as wide as before the legs moved out past the pitch servo (#901)
    riser = box((-24.5, nb.HUB_X[1]), (nb.HUB_Y - nb.HUB_LENGTH, nb.HUB_Y), (gm.PLATE_Z[1], nb.HUB_Z))
    sx, sy = next((x, y) for x, y in nk.HEAD_SCREWS if x < 0 and y > nb.HUB_Y - nb.HUB_LENGTH)
    return out.union(riser.cut(cyl("z", (sx, sy, 0), 3.5, (gm.PLATE_Z[1], nb.HUB_Z))))


@bone.carved
def stand(mechanical=False):
    """Stage 1's test stand (printed upside down, on its top): an open box under the gimbal frame's plate, from the desk
    to the plate's underside round the hanging yaw servo, its top behind that, with the holes under the head mount's
    (nk.HEAD_SCREWS), the eyes Core against its back face; as Bones (#704) its upright edges round."""
    x, top, r = gm.EYE["L"][0] + gm.LID_X["upright"][1], gm.PLATE_Z[0], 0.0 if mechanical else ROUND / 3
    y = (gm.PLATE_Y[0] - 5.0, gm.PLATE_Y[1])  # its front behind the lower lids' sweep, before the yaw servo (#901)
    out = _box((-x, x), y, (nb.STAND_Z, top), r)
    out = out.cut(_box((-x + WALL, x - WALL), (y[0] + WALL, y[1] - WALL), (nb.STAND_Z, top), r and r - WALL))
    out = out.union(box((-x + WALL, x - WALL), (nb.STAND_TOP_Y, y[1] - WALL), (top - nb.TRAY_T, top)))
    for sx, sy in nk.HEAD_SCREWS:
        out = out.cut(cyl("z", (sx, sy, 0), 1.7, (top - nb.TRAY_T, top)))
    return out
