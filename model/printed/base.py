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
    """Back's board rack (#828), on the gimbal frame's plate behind the eyes: at each end a cradle in its cheek, a sleeve
    open at the back and inside, so the Core on edge (base.back_boards) slides in from behind onto its floor, against
    its front stop, its outer wall and under its roof, flat on top (where a Character's hair seats, #665); and a bar
    across the plate between the two. As Bones, carved from it (#809), like the Torso: each floor open under the Core
    between its sides and a row of lancet windows through each wall."""
    t, floor = nb.TRAY_T, gm.PLATE_Z[1]
    (cx, cy), top = nb.CHEEK, nb.ROOF_Z
    inner, outer = cx - 11.8, cx + 11.0  # 1 mm inside the Shield's pins, 0.3 mm outside the Core's USB-C
    front, y0, y1 = cy - 15.0 - t, cy - 15.0, cy + 9.0  # the stop's front; the Shield's front end, 6 short of its back
    # end: the Core overhangs there, inside the Skin's rounded back corner (model/skin.py TOP)
    shut = inner + 6  # the stop and the roof start clear of the bail's upright
    out = box((-inner, inner), (y0 + 2, y0 + 2 + t), (floor, floor + t))  # the bar
    for s in (-1, 1):
        x = lambda a, b: sorted((s * a, s * b))  # noqa: E731
        for xs, ys, zs in (
            ((inner, outer + t), (y0, y1), (floor, floor + t)),  # the floor
            ((shut, outer + t), (front, y0), (floor, top)),  # the stop
            ((outer, outer + t), (front, y1), (floor, top)),  # the wall
            ((shut, outer + t), (front, y1), (top - t, top)),  # the roof
        ):
            out = out.union(box(x(*xs), ys, zs))
        if not mechanical:
            out = out.cut(box(x(inner + 4, outer - 4), (y0 + 4, y1 - 4), (floor, floor + t)))
            for c in _windows(y0, y1):
                out = out.cut(_lancet("y", c, s * (outer + t / 2), floor + t + 3, top - t - 3))
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
