"""The next Mech's Torso (#685), its head variant's board carrier (#686, Back alone since #712) and Stage 1's test stand
(#720) as CadQuery parts, every size from model/base.py, each drawn where it sits at rest in the head's frame
(model/neck.py)."""

from model import base as nb
from model import gimbal as gm
from model import neck as nk
from model.envelopes import box
from model.printed.gimbal import cyl

WALL, RIM = 2.0, 6.0  # the Torso's and the pack cradle's walls; the cradle's height, 0.5 mm clear round the pack
ROUND = 12.0  # as Bones (#704): the Torso's corners round in plan, the cradle's and the rack's by a third of it


def _box(x, y, z, r=0.0, edges="|Z"):
    """A box (envelopes.box), its `edges` filleted r when r."""
    out = box(x, y, z)
    return out.edges(edges).fillet(r) if r else out


def torso(plain=False):
    """The Torso (printed upright): its floor (the foot; the neck mount stands on it), its walls round it, and the pack's
    cradle on the floor behind the neck mount. As Bones (#704) round in plan, its walls' thickness kept."""
    (x0, x1), (y0, y1), (z0, z1) = nb.TORSO
    floor, r = nk.MOUNT_Z[0], 0.0 if plain else ROUND
    out = _box((x0, x1), (y0, y1), (z0, z1), r)
    out = out.cut(_box((x0 + WALL, x1 - WALL), (y0 + WALL, y1 - WALL), (floor, z1 + 1), r and r - WALL))
    w, d = nb.PACK[0] / 2 + 0.5, nb.PACK[1] / 2 + 0.5
    ring = _box((-w - WALL, w + WALL), (nb.PACK_Y - d - WALL, nb.PACK_Y + d + WALL), (floor, floor + RIM), r / 3)
    return out.union(ring.cut(box((-w, w), (nb.PACK_Y - d, nb.PACK_Y + d), (floor, floor + RIM))))


def _flange(w, top, r=0.0):
    """The carriers' flange screwed under the gimbal frame's plate at its back edge and their wall rising behind the
    plate's edge to `top`, the wall's top corners and the flange's front ones round `r`."""
    y, under = nb.RACK_Y, gm.PLATE_Z[0]
    flange = _box((-w, w), (y - 8, y + nb.TRAY_T), (under - 3, under), r, "|Z and <Y")
    return flange.union(_box((-w, w), (y, y + nb.TRAY_T), (under - 3, top), r, "|Y and >Z"))


def rack(plain=False):
    """Back's board rack (printed on its back): the flange and the wall up to the row's top, the boards on its back
    face; as Bones (#704) its corners round."""
    # the row no lower than the plate (BACK_Z)
    return _flange(nb.width() / 2 + 3, nb.BACK_Z + nb.BOARD_H / 2, 0.0 if plain else ROUND / 3)


def stand(plain=False):
    """Stage 1's test stand (printed upside down, on its top): an open box under the gimbal frame's plate, from the desk
    to the plate's underside, its top's holes under the head mount's (nk.HEAD_SCREWS), the eyes Core against its back
    face; as Bones (#704) its upright edges round."""
    x, top, r = gm.EYE["L"][0] + gm.LID_X["upright"][1], gm.PLATE_Z[0], 0.0 if plain else ROUND / 3
    y = gm.PLATE_Y
    out = _box((-x, x), y, (nb.STAND_Z, top), r)
    out = out.cut(
        _box((-x + WALL, x - WALL), (y[0] + WALL, y[1] - WALL), (nb.STAND_Z, top - nb.TRAY_T), r and r - WALL)
    )
    for sx, sy in nk.HEAD_SCREWS:
        out = out.cut(cyl("z", (sx, sy, 0), 1.7, (top - nb.TRAY_T, top)))
    return out
