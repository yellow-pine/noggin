"""The next Mech's neck and jaw (#641) as CadQuery parts, every size from model/neck.py (its frame and its design), each
drawn where it sits at rest. Turning bores take the busy pivots' M3 shanks (model/gimbal.py PIN_R); the part a shank
is fixed in has a tapping hole instead. A tie slot through a tab clamps each end of a flexing span."""

from model import gimbal as gm
from model import neck as nk
from model.envelopes import box
from model.printed.gimbal import collar, cyl, link

TAP_R = 1.25  # an M3 shank's tapping hole: the part it is fixed in (inferred)
COLUMN_R = 10.0  # the neck mount's column: its top is the yoke's thrust face, inside the pan bar's sweep
NECK_R = 5.0  # the column's top, in the pan bar's layer: the bar swings to 6.8 mm of the axis at pan 45 (#642)
POCKET = ((0.5, 10.0), (27.0, 41.0))  # (x, y) through the yoke's floor: the tilt horn and bar swing into it at tilt -20
Y, Z = nk.AXIS
FLOOR_D = 35.0  # the yoke's floor, back from the pan axis under the tilt servo


def _servo(label):
    face, shaft, tab, _ = nk.drives()[label]
    return gm.servo_matrix(face, shaft, tab)


def tie(x, y, z):
    """A clamp tab centred at (x, y, z) with a slot along x for a zip tie."""
    return box((x - 3, x + 3), (y - 3, y + 3), (z - 2, z + 2)).cut(
        box((x - 3, x + 3), (y - 2, y + 2), (z - 0.75, z + 0.75))
    )


def mount():
    """The neck mount (static, printed upright): a foot for the base, a column whose top the yoke turns on (the pan
    shank's tapping hole down its axis; narrowed where the pan bar swings past), the pan servo's collar and the pan span's lower clamp in front."""
    foot = box((-14, 42), (Y - 22, Y + 16), nk.MOUNT_Z)
    out = foot.union(cyl("z", (0, Y, 0), COLUMN_R, (nk.MOUNT_Z[1], nk.PAN_Z[0] - 1)))  # 1 mm under the bar
    out = out.union(cyl("z", (0, Y, 0), NECK_R, (nk.PAN_Z[0] - 1, nk.DISC_Z[0])))
    r, (z0, _) = nk.PAN_SPAN
    out = out.union(box((-3, 3), (Y - r - 3, Y - COLUMN_R + 1), (z0 - 2, z0 + 2))).cut(
        box((-3, 3), (Y - r - 2, Y - r + 2), (z0 - 0.75, z0 + 0.75))
    )
    out = out.union(collar(_servo("pan"), nk.MOUNT_Z[1]))
    return out.cut(cyl("z", (0, Y, 0), TAP_R, (nk.MOUNT_Z[1], nk.DISC_Z[0])))


def yoke():
    """The pan yoke (printed upright): a disc on the column (the pan shank's bore) and a floor back under the tilt
    servo (the pan lever's pin; a pocket through it where the tilt horn and bar swing), the cheeks up to the tilt axis (the tilt shanks' tapping holes), the tilt servo's
    collar, the pan span's upper clamp in front and the tilt span's clamp on a post outside the R cheek."""
    out = cyl("z", (0, Y, 0), nk.DISC_R, nk.DISC_Z).union(box((nk.LOOP_X[0], 38), (Y, Y + FLOOR_D), nk.DISC_Z))
    r, (_, z1) = nk.PAN_SPAN
    out = out.union(box((-3, 3), (Y - r - 3, Y - nk.DISC_R + 1), nk.DISC_Z)).cut(
        box((-3, 3), (Y - r - 2, Y - r + 2), (z1 - 0.75, z1 + 0.75))
    )
    for s in (-1, 1):
        xs = sorted(s * c for c in nk.CHEEK_X)
        out = out.union(box(xs, (Y - nk.BOSS_R, Y + nk.BOSS_R), (nk.DISC_Z[1], Z)))
        out = out.union(cyl("x", (0, Y, Z), nk.BOSS_R, xs)).cut(cyl("x", (0, Y, Z), TAP_R, xs))
    rho, _ = nk.TILT_SPAN
    cy, cz = Y + rho * 0.7071, Z - rho * 0.7071  # the clamp 45 deg up behind the axis
    out = out.union(box(nk.LOOP_X, (cy - 2, cy + 2), (nk.DISC_Z[1], cz - 2))).union(tie(sum(nk.LOOP_X) / 2, cy, cz))
    out = out.union(collar(_servo("tilt"), nk.DISC_Z[1]))
    out = out.cut(cyl("z", (0, Y, 0), gm.PIN_R, nk.DISC_Z)).cut(box(*POCKET, nk.DISC_Z))
    return out.cut(cyl("z", (0, Y + nk.PAN_LEVER, 0), TAP_R, nk.DISC_Z))


def head_mount():
    """The head mount (printed on its side, its bores along Z): a flange screwed under the gimbal frame's plate, the
    tilt lugs outside the cheeks (the tilt shanks turn in them), the tilt lever behind, the jaw's lugs (its shanks'
    tapping holes), the mouth servo's collar, and the tilt span's head clamp below the R lug."""
    f0 = nk.FLANGE_Z[0]
    out = box((nk.LOOP_X[0], 45), (-27, Y + nk.TILT_LEVER + 3), nk.FLANGE_Z)
    for x, y in nk.HEAD_SCREWS:
        out = out.cut(cyl("z", (x, y, 0), 1.7, nk.FLANGE_Z))
    rho, _ = nk.TILT_SPAN
    jy, jz = nk.JAW
    for s in (-1, 1):
        xs = sorted(s * c for c in nk.LUG_X)
        out = out.union(box(xs, (Y - nk.BOSS_R, Y + nk.BOSS_R), (Z, f0))).union(cyl("x", (0, Y, Z), nk.BOSS_R, xs))
        out = out.cut(cyl("x", (0, Y, Z), gm.PIN_R, xs))
        js = sorted(s * c for c in (nk.LUG_X[0] + 1, nk.JAW_X[0]))
        out = out.union(box(js, (jy - 5, jy + 5), (jz, f0))).union(cyl("x", (0, jy, jz), 5.0, js))
        out = out.cut(cyl("x", (0, jy, jz), TAP_R, js))
    out = out.union(box((-nk.LUG_X[1], -nk.LUG_X[0]), (Y - 3, Y + 3), (Z - rho - 2, Z)))
    out = out.union(tie(sum(nk.LOOP_X) / 2, Y, Z - rho))
    ly = Y + nk.TILT_LEVER
    out = out.union(box((-1.5, 1.5), (ly - 3, ly + 3), (Z, f0))).union(cyl("x", (0, ly, Z), 3.0, (-1.5, 1.5)))
    out = out.cut(cyl("x", (0, ly, Z), TAP_R, (-1.5, 1.5)))
    return out.union(collar(_servo("mouth"), f0))


def jaw():
    """The jaw (printed on its side): a boss outside each lug (the jaw shanks turn in them), an arm forward from each to
    the chin bar, and the pin for the jaw bar on the L arm."""
    jy, jz = nk.JAW
    x0, x1 = nk.JAW_X
    out = box((-x1, x1), (nk.CHIN_Y, nk.CHIN_Y + 4), (jz - 2, jz + 2))
    for s in (-1, 1):
        xs = sorted((s * x0, s * x1))
        out = out.union(box(xs, (nk.CHIN_Y, jy), (jz - 2, jz + 2))).union(cyl("x", (0, jy, jz), 4.0, xs))
        out = out.cut(cyl("x", (0, jy, jz), gm.PIN_R, xs))
    return out.cut(cyl("x", (0, jy - nk.JAW_LEVER, jz), TAP_R, (x0, x1)))


def pan_bar():
    """The pan bar, flat under the yoke's floor: the yoke's lever pin to the pan horn's."""
    y = Y + nk.PAN_LEVER
    out = box((0, nk.PAN_BAR), (y - 3, y + 3), nk.PAN_Z)
    for x in (0, nk.PAN_BAR):
        out = out.union(cyl("z", (x, y, 0), 3.0, nk.PAN_Z)).cut(cyl("z", (x, y, 0), gm.PIN_R, nk.PAN_Z))
    return out


def tilt_bar():
    y = Y + nk.TILT_LEVER
    return link((y, Z - nk.TILT_BAR), (y, Z), nk.TILT_BAR_X)


def jaw_bar():
    y = nk.JAW[0] - nk.JAW_LEVER
    return link((y, nk.JAW_HORN_Z), (y, nk.JAW[1]), nk.JAW_BAR_X)
