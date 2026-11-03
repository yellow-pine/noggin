"""The next Mech's Torso (#685), its head variant's board carrier (#686, Back alone since #712) and Stage 1's test stand
(#720) as CadQuery parts, every size from model/base.py, each drawn where it sits at rest in the head's frame
(model/neck.py)."""

import math

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
WINDOW, POST = 8.0, 4.0  # its windows' width and the posts' between them
# the rack's Bones (head, waist) as (semi-width, height): the shelf's and the rails' taller than its 3 mm, carved flat
# on top where the boards stand (#708)
RACK_BONE, RAIL_BONE, POST_BONE = ((3.0, 3.6), (2.4, 3.4)), ((1.5, 3.6), (1.2, 3.4)), ((1.5, 1.5), (1.1, 1.1))


def _box(x, y, z, r=0.0, edges="|Z"):
    """A box (envelopes.box), its `edges` filleted r when r."""
    out = box(x, y, z)
    return out.edges(edges).fillet(r) if r else out


@bone.carved
def torso(mechanical=False):
    """The Torso (printed upright): its floor (the foot; the neck mount stands on it), its walls round it, and the pack's
    cradle on the floor behind the neck mount. As Bones (#708), carved from it (#809): its upright corners round and a
    row of lancet windows through each wall, a post between each two under a rim along the top, each window's head
    pointed so it prints without support."""
    (x0, x1), (y0, y1), (z0, z1) = nb.TORSO
    floor = nk.MOUNT_Z[0]
    out = _box((x0, x1), (y0, y1), (z0, z1), 0.0 if mechanical else CORNER)
    out = out.cut(_box((x0 + WALL, x1 - WALL), (y0 + WALL, y1 - WALL), (floor, z1 + 1)))
    if not mechanical:
        for axis, (lo, hi), across in (("x", (x0, x1), (y0, y1)), ("y", (y0, y1), (x0, x1))):
            for c in _windows(lo + CORNER, hi - CORNER):
                for wall in (across[0] + WALL / 2, across[1] - WALL / 2):  # each wall's middle
                    out = out.cut(_lancet(axis, c, wall, floor + 1.5, z1 - nb.TRAY_T))
    w, d = nb.PACK[0] / 2 + 0.5, nb.PACK[1] / 2 + 0.5
    ring = _box((-w - WALL, w + WALL), (nb.PACK_Y - d - WALL, nb.PACK_Y + d + WALL), (floor, floor + RIM))
    return out.union(ring.cut(box((-w, w), (nb.PACK_Y - d, nb.PACK_Y + d), (floor, floor + RIM))))


def _windows(lo, hi):
    """The windows' middles along a wall from lo to hi, WINDOW wide with a post POST wide between each two."""
    n = int((hi - lo + POST) // (WINDOW + POST))
    start = (lo + hi) / 2 - (n - 1) * (WINDOW + POST) / 2
    return [start + i * (WINDOW + POST) for i in range(n)]


def _lancet(axis, c, wall, z0, z1):
    """A window through the wall whose middle is on the plane (y or x) `wall`, centred at c along `axis`, its sill on
    z0, its sides upright and its head pointed at 50 deg up to z1."""
    peak = WINDOW / 2 * math.tan(math.radians(50))
    outline = [
        (c - WINDOW / 2, z0),
        (c + WINDOW / 2, z0),
        (c + WINDOW / 2, z1 - peak),
        (c, z1),
        (c - WINDOW / 2, z1 - peak),
    ]
    plane = "XZ" if axis == "x" else "YZ"
    origin = (0, wall, 0) if axis == "x" else (wall, 0, 0)
    return cq.Workplane(plane, origin=origin).polyline(outline).close().extrude(WALL, both=True)


@bone.carved
def rack(mechanical=False):
    """Back's board rack (#708): a flange screwed under the gimbal frame's plate at its back edge, a post up behind the
    plate at each end of the row, from each a rail forward over the gimbal, and the shelf the boards stand on over the
    eyes, between the rails. As Bones, carved from it (#809): the posts struts, the rails Bones, the shelf a Bone across
    under the boards' fronts and one under their backs."""
    t, (y, under) = nb.TRAY_T, (nb.RACK_Y, gm.PLATE_Z[0])
    w, top = nb.width() / 2 + t, nb.BACK_Z - nb.BOARD_H / 2  # the posts and rails outboard of the row; its bottom
    out = box((-w, w), (y - 8, y + t), (under - 3, under))
    if mechanical:
        out = out.union(box((-w, w), (nb.BACK_Y, nb.BACK_Y + nb.BOARD_D), (top - t, top)))
        for s in (-1, 1):
            xs = sorted(s * c for c in (w - t, w))
            out = out.union(box(xs, (y, y + t), (under - 3, top))).union(box(xs, (nb.BACK_Y, y + t), (top - t, top)))
        return out
    x, back, (hw, _) = w - t / 2, y + t / 2, RACK_BONE[0]  # inside the mechanical posts and rails (carved, #809)
    front, rear = nb.BACK_Y + hw, nb.BACK_Y + nb.BOARD_D - hw
    z = top - t  # flat-ended Bones, each ending inside the next: no heads, a light mesh
    for s in (-1, 1):
        out = out.union(bone.bone((s * x, back, z), (s * x, front, z), *RAIL_BONE, heads=False))
    for y_ in (front, rear):  # the shelf: a Bone across under the boards' fronts and one under their backs
        out = out.union(bone.bone((-x, y_, z), (x, y_, z), *RACK_BONE, heads=False))
    (r, _), (waist, _) = POST_BONE
    for s in (-1, 1):  # from inside the flange up into the rail: two cones, waisted (a round loft this thin and long
        # tessellates to ~44k faces)
        lo, hi = under - 1.5, top - t / 2
        mid = (lo + hi) / 2
        for z0, z1, r0, r1 in ((lo, mid, r, waist), (mid, hi, waist, r)):
            cone = cq.Solid.makeCone(r0, r1, z1 - z0, cq.Vector(s * x, back, z0))
            out = out.union(cq.Workplane().add(cone))
    return out


@bone.carved
def stand(mechanical=False):
    """Stage 1's test stand (printed upside down, on its top): an open box under the gimbal frame's plate, from the desk
    to the plate's underside, its top's holes under the head mount's (nk.HEAD_SCREWS), the eyes Core against its back
    face; as Bones (#704) its upright edges round."""
    x, top, r = gm.EYE["L"][0] + gm.LID_X["upright"][1], gm.PLATE_Z[0], 0.0 if mechanical else ROUND / 3
    y = gm.PLATE_Y
    out = _box((-x, x), y, (nb.STAND_Z, top), r)
    out = out.cut(
        _box((-x + WALL, x - WALL), (y[0] + WALL, y[1] - WALL), (nb.STAND_Z, top - nb.TRAY_T), r and r - WALL)
    )
    for sx, sy in nk.HEAD_SCREWS:
        out = out.cut(cyl("z", (sx, sy, 0), 1.7, (top - nb.TRAY_T, top)))
    return out
