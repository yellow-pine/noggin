"""The next Mech's Torso (#685) and its head variants' board carriers (#686) as CadQuery parts, every size from
model/base.py, each drawn where it sits at rest in the head's frame (model/neck.py)."""

from model import base as nb
from model import gimbal as gm
from model import neck as nk
from model.envelopes import box
from model.printed.neck import FLOOR_D

WALL, RIM = 2.0, 6.0  # the Torso's and the pack cradle's walls; the cradle's height, 0.5 mm clear round the pack


def torso():
    """The Torso (printed upright): its floor (the foot; the neck mount stands on it), its walls round it, and the pack's
    cradle on the floor behind the neck mount."""
    (x0, x1), (y0, y1), (z0, z1) = nb.TORSO
    floor = nk.MOUNT_Z[0]
    out = box((x0, x1), (y0, y1), (z0, z1)).cut(box((x0 + WALL, x1 - WALL), (y0 + WALL, y1 - WALL), (floor, z1)))
    w, d = nb.PACK[0] / 2 + 0.5, nb.PACK[1] / 2 + 0.5
    ring = box((-w - WALL, w + WALL), (nb.PACK_Y - d - WALL, nb.PACK_Y + d + WALL), (floor, floor + RIM))
    return out.union(ring.cut(box((-w, w), (nb.PACK_Y - d, nb.PACK_Y + d), (floor, floor + RIM))))


def _flange(w, top):
    """The carriers' flange screwed under the gimbal frame's plate at its back edge and their wall rising behind the
    plate's edge to `top`."""
    y, under = nb.RACK_Y, gm.PLATE_Z[0]
    flange = box((-w, w), (y - 8, y), (under - 3, under))
    return flange.union(box((-w, w), (y, y + nb.TRAY_T), (under - 3, top)))


def rack():
    """Back's board rack (printed on its back): the flange and the wall up to the row's top, the boards on its back
    face."""
    return _flange(nb.width() / 2 + 3, nb.BACK_Z + nb.BOARD_H / 2)  # the row no lower than the plate (BACK_Z)


def _shelf(row, y):
    """A crown shelf (printed upright): the flange, the wall up over the eye gimbal and the shelf forward from it under
    the row lying on it, its middle front to back on y."""
    w, z = nb.width(row) / 2 + 3, nb.CROWN_Z
    shelf = box((-w, w), (y - nb.BOARD_H / 2, nb.RACK_Y + nb.TRAY_T), (z, z + nb.TRAY_T))
    return _flange(w, z + nb.TRAY_T).union(shelf)


def crown_shelf():
    return _shelf(nb._ROW, nb.CROWN_Y)


def split_shelf():
    return _shelf(nb.PAIR, nb.SPLIT_Y)


def switch_bracket():
    """Split's switch bracket (printed flat): an arm back from the pan yoke's floor, under its floor's level, the switch
    board lying under it."""
    y, z = nb.SWITCH
    w = nb.width(nb._ROW[2:]) / 2 + 3
    return box((-w, w), (nk.AXIS[0] + FLOOR_D, y + nb.BOARD_H / 2 + 1), (z, z + nb.TRAY_T))
