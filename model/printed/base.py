"""The next Mech's base and its Base candidates' board carriers (#642) as CadQuery parts, every size from model/base.py,
each drawn where it sits at rest in the head's frame (model/neck.py)."""

from model import base as nb
from model import neck as nk
from model.envelopes import box
from model.printed.gimbal import cyl

WALL, RIM = 2.0, 6.0  # the pack cradle's walls and their height
PACK = (28.4, 51.2)  # the pack's footprint (model/envelopes.py battery), 0.5 mm clear each side in its cradle


def plate():
    """The base plate (printed flat): the shirt's floor under the neck mount's foot, and the pack's cradle behind it."""
    (x0, x1), (y0, y1), (z0, z1) = nb.PLATE
    out = box((x0, x1), (y0, y1), (z0, z1))
    w, d = PACK[0] / 2 + 0.5, PACK[1] + 1
    ring = box((-w - WALL, w + WALL), (nb.PACK_Y - 0.5 - WALL, nb.PACK_Y + d + WALL), (z1, z1 + RIM))
    return out.union(ring.cut(box((-w, w), (nb.PACK_Y - 0.5, nb.PACK_Y + d), (z1, z1 + RIM))))


def tray():
    """(a)'s board tray (printed on its back): a flange screwed under the gimbal frame's plate and a plate hanging from
    it, the boards on its back face."""
    w, (y, z) = nb.ROW_W / 2 + 3, nb.TRAY
    top = nk.FLANGE_Z[1]  # the gimbal frame's underside
    flange = box((-w, w), (y - 8, y + nb.TRAY_T), (top - 3, top))
    return flange.union(box((-w, w), (y, y + nb.TRAY_T), (z - nb.BOARD_H / 2 - 3, top)))


def tower():
    """(b)'s board tower (printed upright): a rod on the pan axis, standing on the neck mount's column in the pan shank's
    place, up to the shelf over the lids."""
    w, y = nb.ROW_W / 2 + 3, nk.AXIS[0]
    rod = cyl("z", (0, y, 0), nb.TOWER_R, (nk.DISC_Z[0], nb.SHELF_Z))
    return rod.union(box((-w, w), (y - nb.BOARD_D / 2, y + nb.BOARD_D / 2), (nb.SHELF_Z, nb.SHELF_Z + nb.TRAY_T)))
