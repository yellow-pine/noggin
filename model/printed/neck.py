"""The Mech's neck and jaw (#641) as CadQuery parts, every size from model/neck.py (its frame and its design), each
drawn where it sits at rest. Turning bores take the busy pivots' M3 shanks (model/gimbal.py PIN_R); the part a shank
is fixed in has a tapping hole instead. A tie slot through a tab clamps each end of a flexing span."""

import functools
import math

import cadquery as cq
import numpy as np

from model import envelopes
from model import gimbal as gm
from model import neck as nk
from model.envelopes import box, hull
from model.printed import bone
from model.printed.gimbal import cyl, link

TAP_R = 1.25  # an M3 shank's tapping hole: the part it is fixed in (inferred)
BAR_BONE = ((3.0, 2.9), (2.4, 2.6))  # the jaw bar's Bones: their heads the mechanical bar's round ends
# #968: the jaw's ramus Bones, its chain's first spans (condyle to angle), deep fore and aft as the ramus is, to hold the
# mouth servo's stall: (head, waist), each its half-depth fore and aft, then across
RAMUS, RAMUS_SPANS = ((4.2, 2.4), (5.0, 2.2)), 3  # its ends the size that sweeps clear of the frame


def tie(x, y, z):
    """A clamp tab centred at (x, y, z) with a slot along x for a zip tie."""
    return box((x - 3, x + 3), (y - 3, y + 3), (z - 2, z + 2)).cut(
        box((x - 3, x + 3), (y - 2, y + 2), (z - 0.75, z + 0.75))
    )


def strut(a, b, head, waist):
    """A round Bone from a to b, flat at both ends (bone.bone round, heads False)."""
    up = (1, 0, 0) if abs(b[0] - a[0]) < 1e-9 else (0, 0, 1)
    return bone.bone(a, b, head, waist, up=up, round=True, heads=False)


def cervical_carrier():
    """Fixed split lateral load path into the Torso; the centre remains open for the anatomical wire canal."""
    _, y, z = nk.HEAD_AXES["tilt"][0]
    out = box((-20, 20), (56, 72), nk.MOUNT_Z)
    for sign in (-1, 1):
        xs = sorted(sign * x for x in (18.0, 22.4))
        rail = box(sorted(sign * x for x in (14, 18)), (60, 68), (nk.MOUNT_Z[0] + 1, nk.MOUNT_Z[1] + 1))
        points = [(sign * x, *point) for x, point in zip(nk.CERVICAL_X, nk.CERVICAL_PATH)]
        for a, b in zip(points, points[1:]):
            rail = rail.union(strut(a, b, (4, 2), (3, 1.6)))
        rail = rail.union(cyl("x", (0, y, z), 3.5, xs)).cut(cyl("x", (0, y, z), TAP_R, xs))
        out = out.union(rail)
    # A passive bar reacts the low rear moving-case motor (#978) at a pin beside the R rail, the reduction four-bar's
    # fixed arm (nk.TILT_ARMS), inboard of the jaw's sweep: the pin's boss on a strut from the rail at the pin's height.
    _, ay, az = nk.TILT_ANCHOR
    (y0, z0), (y1, z1) = nk.CERVICAL_PATH[3], nk.CERVICAL_PATH[2]
    t = (az - z0) / (z1 - z0)
    rail = (-(nk.CERVICAL_X[3] + t * (nk.CERVICAL_X[2] - nk.CERVICAL_X[3])), y0 + t * (y1 - y0), az)
    boss = (nk.REACTION_TAP_X[1] - 8.0, nk.REACTION_TAP_X[1])
    out = out.union(strut(rail, (boss[0] + 3.0, ay, az), (3.5, 3), (3, 2.5)))
    out = out.union(cyl("x", (0, ay, az), 3.5, boss)).cut(cyl("x", (0, ay, az), TAP_R, boss))
    out = out.union(tie(20.0, 78.5, -65.7))
    for x, fy in nk.CARRIER_FEET:
        out = out.cut(cyl("z", (x, fy, 0), 1.7, nk.MOUNT_Z))
    return out


def nod_plate():
    """Tilting cervical carrier, hollow pan spindle and the two real standard-servo tab cradles."""
    _, y, z = nk.HEAD_AXES["tilt"][0]
    out = hull("XY", [(0, y, 12), (-13.8, y, 3.6), (13.8, y, 3.6)], 5, (0, 0, nk.NOD_Z[0]))
    for sign in (-1, 1):
        xs = sorted(sign * x for x in (13.4, 17.4))
        out = out.union(box(xs, (y - 3.6, y + 3.6), tuple(sorted((z, nk.NOD_Z[0] + 1)))))
        out = out.union(cyl("x", (0, y, z), 3.6, xs))  # bored at the end, after the mast's flat
        for fy in (y - 12, y + 12):
            out = out.union(_flat([(0, fy), (sign * 14, fy)], 5, nk.NOD_Z))
        out = out.union(_flat([(sign * 14, y - 12), (sign * 14, y + 12)], 4, nk.NOD_Z))
    out = out.cut(box((-3, 3), (y - 13.5, y - 9.5), (nk.NOD_Z[0] + 1.75, nk.NOD_Z[0] + 3.25)))
    # The tube is integral with the nod carrier: head weight never reaches either servo spline.
    out = out.union(pan_wire_candidate()["spindle"])
    out = out.cut(cyl("z", (0, y, 0), nk.WIRE_R, (nk.NOD_Z[0], nk.PAN_STUDY_Z[1])))
    # #978: the low rear tilt cradle, the case upright behind the canal: a screw block on each tab's case side, past the
    # case's ends, the lower on a beam down from the plate's crossbar in front of the case, the upper under a header over
    # the case's top that joins the rear mast; the mast, beside the case, from the plate's rear arm to the pan cradle.
    s = envelopes.STANDARD_SERVO
    (cx0, cx1), (_, half), _ = s["case"]
    (tx0, tx1), _, (tz0, tz1) = s["tabs"]
    holes, across = sorted({x for x, _ in s["holes"]}), max(y for _, y in s["holes"])  # its tabs' hole lines
    sx, sy, sz = nk.TILT_SHAFT  # the case's long axis up (nk.TILT_CASE), its shaft along -x
    tabs = (sx - tz1, sx - tz0)
    blocks, width = (tabs[1], tabs[1] + 5.0), (sy - half, sy + half)
    beam = (sy - 23.8, width[0] - 0.3)  # in front of the case
    top = (sz + tx1, sz + tx1 + 6.4)  # over the upper tab's end
    for fz, zs in ((sz + holes[0], (sz + tx0 + 0.4, sz + cx0 - 0.3)), (sz + holes[1], (sz + holes[1] - 3.1, top[1]))):
        out = out.union(box(blocks, (beam[1] - 4.0, width[1]), zs))
        for fy in (sy - across, sy + across):
            out = out.cut(cyl("x", (0, fy, fz), 0.8, blocks))
    mast_x, mast_y = (23.0, 29.0), (125.7, 135.3)
    out = out.union(box((sx + 10.4, 21.5), width, top)).union(box((21.0, mast_x[1]), (mast_y[0], width[1]), top))
    out = out.union(box((-9.2, blocks[1]), beam, (sz + holes[0], nk.NOD_Z[1])))
    # a post up from the crossbar to the upper block, so the header, the mast and it frame the pan cradle's load
    out = out.union(box((-9.2, blocks[1]), (beam[0] + 2.0, beam[1]), (nk.NOD_Z[1], top[1])))
    arm = [(13.8, y + 2.5), (sum(mast_x) / 2, beam[0] + 8.0), (sum(mast_x) / 2, sum(mast_y) / 2)]
    out = out.union(_flat(arm, 6.0, nk.NOD_Z))
    out = out.union(_flat([(-4.6, beam[0] + 4.0), (sum(mast_x) / 2, beam[0] + 4.0)], 8.0, nk.NOD_Z))
    # The pan cradle (#978): a block on each tab's case side past the case's ends, joined by a side bar over the Shields'
    # sweep to the mast.
    _, py, pz = nk.PAN_SHAFT  # the case's long axis forward (nk.PAN_CASE), its shaft down
    lid, bar = (pz - tz0, pz + 27.0), (pz + 19.0, pz + 27.0)  # from the tabs' face; the side bar over the Shields
    out = out.union(box((-half, 10.5), (py - tx1, py - cx1 - 0.3), lid))
    out = out.union(box((-half, 10.5), (py - cx0 + 0.3, py - tx0), lid))
    out = out.union(box((half + 0.3, 20.0), (py - tx1, py - tx0), bar)).union(box((19.0, mast_x[1]), mast_y, bar))
    for fy in (py - h for h in holes):
        for x in (-across, across):
            out = out.cut(cyl("z", (x, fy, 0), 0.8, lid))
    out = out.union(box(mast_x, mast_y, (nk.NOD_Z[0], lid[1])))
    out = out.union(box((12.0, mast_x[1]), mast_y, (top[1] - 1.0, lid[1])))  # wider over the tilt case, under the pan's
    for xs in ((17.7, 26), (-26, -17.7)):
        out = out.cut(cyl("x", (0, y, z), 8.5, xs))
    for xs in ((13.4, 17.4), (-17.4, -13.4)):  # the trunnions' shank bores, which the mast's flat crosses
        out = out.cut(cyl("x", (0, y, z), gm.PIN_R, xs))
    return out


def tilt_lever():
    """Adapter on the supplied round horn, with an outboard standoff clear of the actual case and tabs."""
    x, y, z = nk.TILT_SHAFT
    outer = x + envelopes.STANDARD_HORN["face"]
    span = (outer - 5, outer)  # counterbore leaves a full 2 mm printed floor over the stock retaining screw
    out = cyl("x", (0, y, z), 11.5, span)
    out = out.union(hull("YZ", [(y, z, 7), (*nk.TILT_PIN[1:], 5.5)], span[1] - span[0], (span[0], 0, 0)))
    out = out.union(cyl("x", (0, *nk.TILT_PIN[1:]), 4.5, (span[0], nk.REACTION_TAP_X[1])))
    out = out.cut(cyl("x", (0, y, z), 1.6, span))
    out = out.cut(cyl("x", (0, y, z), 2.8, (outer - 3, outer)))
    for dy, dz in envelopes.STANDARD_HORN["mounts"]:
        out = out.cut(cyl("x", (0, y + dy, z + dz), 1.1, span))
    return out.cut(cyl("x", (0, *nk.TILT_PIN[1:]), TAP_R, nk.REACTION_TAP_X))


def tilt_reaction_bar():
    """The reduction four-bar's straight bar (#978), from its crank's pin to the carrier's anchor."""
    from model.printed.gimbal import lid_mechanical

    pins = [tuple(point[1:]) for point in nk.TILT_BAR_PATH]
    out = lid_mechanical(pins, nk.REACTION_BAR_X)
    for point in (nk.TILT_ANCHOR, nk.TILT_PIN):
        out = out.union(cyl("x", (0, *point[1:]), 3.8, nk.REACTION_BAR_X)).cut(
            cyl("x", (0, *point[1:]), gm.PIN_R, nk.REACTION_BAR_X)
        )
    return out


def head_mount():
    """Bearing-supported rotating head carrier, including its real pan rocker post."""
    return pan_wire_candidate()["head carrier"]


def pan_fixed_cap():
    return pan_wire_candidate()["fixed cap"]


def pan_moving_cap():
    return pan_wire_candidate()["moving cap"]


def pan_lever():
    """Printed adapter on the standard round horn; the bar shares the head post's horizontal pin plane."""
    x, y, _ = nk.PAN_SHAFT
    pin = nk.PAN_PIN[:2]
    mounts = [(x + dx, y + dy, 2.2 if dy < 0 else 3.2) for dx, dy in envelopes.STANDARD_HORN["mounts"]]
    out = hull("XY", [*mounts, (*pin, 4.5)], nk.PAN_LEVER_Z[1] - nk.PAN_LEVER_Z[0], (0, 0, nk.PAN_LEVER_Z[0]))
    out = out.union(cyl("z", (*pin, 0), 4.5, (nk.PAN_LEVER_Z[0], nk.PAN_TAP_Z[1])))
    out = out.cut(cyl("z", (*pin, 0), TAP_R, nk.PAN_TAP_Z))
    out = out.cut(cyl("z", (x, y, 0), 2.8, nk.PAN_LEVER_Z))
    for dx, dy in envelopes.STANDARD_HORN["mounts"]:
        out = out.cut(cyl("z", (x + dx, y + dy, 0), 1.1, nk.PAN_LEVER_Z))
    return out


@functools.cache
def pan_wire_candidate():
    """The retained C0 pan bearing stack: spindle, fixed cap, bearing, head carrier and moving cap (head mount, caps)."""
    y = nk.HEAD_AXES["tilt"][0][1]
    (bore, outside, _), (bottom, top) = nk.PAN_STUDY_BEARING, nk.PAN_STUDY_Z
    bolts = [(7.1 * math.cos(a), y + 7.1 * math.sin(a)) for a in np.radians((0, 120, 240))]
    tube_top = bottom - 6.3
    spindle = cyl("z", (0, y, 0), 6.2, (nk.NOD_Z[1], tube_top))
    flare = cq.Solid.makeCone(6.2, 11.5, 5.3, cq.Vector(0, y, tube_top), cq.Vector(0, 0, 1))
    spindle = spindle.union(cq.Workplane().add(flare)).union(cyl("z", (0, y, 0), 11.5, (bottom - 1, bottom)))
    spindle = spindle.union(cyl("z", (0, y, 0), bore / 2, (bottom, top)))
    spindle = spindle.cut(cyl("z", (0, y, 0), nk.WIRE_R, (nk.NOD_Z[1], top)))
    fixed_cap = cyl("z", (0, y, 0), 11.5, (top, top + 4)).cut(cyl("z", (0, y, 0), nk.WIRE_R, (top, top + 4)))
    for x, fy in bolts:
        spindle = spindle.cut(cyl("z", (x, fy, 0), 0.8, (top - 6.5, top)))
        fixed_cap = fixed_cap.cut(cyl("z", (x, fy, 0), 1.1, (top, top + 4)))
    bearing = cyl("z", (0, y, 0), outside / 2, (bottom, top)).cut(cyl("z", (0, y, 0), bore / 2, (bottom, top)))
    carrier = cyl("z", (0, y, 0), 18.5, (bottom - 2, top)).cut(
        cyl("z", (0, y, 0), 15, (bottom - 2, bottom)).union(cyl("z", (0, y, 0), outside / 2, (bottom, top)))
    )
    moving_cap = cyl("z", (0, y, 0), 18.5, (top, top + 4)).cut(cyl("z", (0, y, 0), 15, (top, top + 4)))
    for a in np.radians((0, 120, 240)):
        x, fy = 20.6 * math.cos(a), y + 20.6 * math.sin(a)
        carrier = carrier.union(cyl("z", (x, fy, 0), 3.2, (bottom - 2, top))).cut(
            cyl("z", (x, fy, 0), 0.8, (top - 6.5, top))
        )
        moving_cap = moving_cap.union(cyl("z", (x, fy, 0), 3.2, (top, top + 4))).cut(
            cyl("z", (x, fy, 0), 1.1, (top, top + 4))
        )
    for x, fy in nk.PAN_STUDY_SCREWS:
        delta = np.array((x, fy - y))
        start = delta / np.linalg.norm(delta) * 19.5 + (0, y)
        feet = gm.PLATE_Z[1]
        carrier = carrier.union(_flat([tuple(start), (x, fy)], 6, (bottom + 1, bottom + 4)))
        carrier = carrier.union(cyl("z", (x, fy, 0), 3.8, (feet, bottom + 4))).cut(
            cyl("z", (x, fy, 0), 1.7, (feet, bottom + 4))
        )
    # The post's lower step joins the rotor below the removable cap, without using cap screws as a beam joint.
    carrier = carrier.union(box((-24.8, -17), (y - 10, y + 10), (bottom + 1, top)))
    carrier = carrier.union(box((-24.8, -18.8), (y - 10, y + 10), (top - 0.5, top + 13)))
    px, py, _ = nk.PAN_ANCHOR
    # The lower column stands behind the crank sweep; its top arm reaches the coupler above the crank plate.
    rear = (px, py + 10)
    carrier = carrier.union(_flat([(-26.3, y), rear], 15, (top + 4, top + 13)))
    carrier = carrier.union(cyl("z", (*rear, 0), 7.5, (top + 4, nk.PAN_TAP_Z[1])))
    arm_z = (nk.PAN_LEVER_Z[1] + 1.5, nk.PAN_TAP_Z[1])
    carrier = carrier.union(hull("XY", [(*rear, 7.5), (px, py, 5.0)], arm_z[1] - arm_z[0], (0, 0, arm_z[0])))
    carrier = carrier.cut(cyl("z", (px, py, 0), TAP_R, nk.PAN_TAP_Z))
    carrier = carrier.cut(box((-24.8, -18.8), (y - 2, y + 2), (top + 6.25, top + 7.75)))
    return {
        "spindle": spindle,
        "fixed cap": fixed_cap,
        "bearing": bearing,
        "head carrier": carrier,
        "moving cap": moving_cap,
    }


def jaw_chains():
    """{side: the jaw's chain of joints}: each measured border 2.5 mm in, its body raised JAW_CHAIN_UP, to the chin."""
    points = {}
    for side, border in nk.MANDIBLE_BORDER.items():
        sign = 1 if side == "L" else -1
        points[side] = [
            (x - sign * 2.5, y, z + (nk.JAW_CHAIN_UP if i >= 4 else 0)) for i, (x, y, z) in enumerate(border)
        ]
        points[side].append(tuple(np.add(nk.MENTON, (0, 0, nk.JAW_CHAIN_UP))))
    return points


@bone.grown
def jaw(mechanical=False):
    """Hidden spatial carrier following the measured mandibular ramus/body, hinged at the actual condyles."""
    from model import skin

    points = jaw_chains()
    out = None
    for chain in points.values():
        for i, (a, b) in enumerate(zip(chain, chain[1:])):
            if i < RAMUS_SPANS:
                link = bone.bone(a, b, *RAMUS, up=(1, 0, 0), round=True, heads=False)
            else:
                link = strut(a, b, (3.2, 2.2), (2.8, 2))
            out = link if out is None else out.union(link)
    jy, jz = nk.JAW
    for sign in (-1, 1):
        xs = sorted(sign * x for x in nk.JAW_X)
        out = out.union(cyl("x", (0, jy, jz), nk.BOSS_R, xs)).cut(cyl("x", (0, jy, jz), gm.PIN_R, xs))
    # The actual ramus, not a vertical extension of the old L, takes the drive pin.
    x = sum(nk.JAW_X) / 2
    pin = (x, *nk.JAW_PIN)
    out = out.union(strut(points["L"][2], pin, (3, 2.2), (2.5, 1.8)))
    pin_r = 4.0 if mechanical else 3.5
    out = out.union(cyl("x", (0, *nk.JAW_PIN), pin_r, nk.JAW_X)).cut(cyl("x", (0, *nk.JAW_PIN), TAP_R, nk.JAW_X))
    # Keep the existing resting mouth Shell on its actual Seat while the hidden anatomical load path changes.
    seat = next(s for s in skin.SEATS if s.shell == "morty mouth cover")
    at = np.subtract(seat.at, np.multiply(seat.normal, seat.pad * 0.75))  # the strut's slanted end stays in the pad
    out = out.union(strut(points["L"][-1], at, (3.2, 2.4), (2.8, 2)))
    return out


def _flat(points, w, zs):
    """Flat bars `w` wide through the (x, y) `points` in turn, from zs[0] to zs[1], round at every joint."""
    out = cyl("z", (*points[0], 0), w / 2, zs)
    for a, b in zip(points, points[1:]):
        side = np.array([a[1] - b[1], b[0] - a[0]]) * w / 2 / math.dist(a, b)
        outline = [tuple(map(float, p)) for p in (a + side, b + side, b - side, a - side)]
        bar = cq.Workplane("XY", origin=(0, 0, zs[0])).polyline(outline).close().extrude(zs[1] - zs[0])
        out = out.union(bar).union(cyl("z", (*b, 0), w / 2, zs))
    return out


def pan_bar():
    """The real horizontal coupler between the standard horn adapter and the bearing-supported head post."""
    out = _flat([tuple(nk.PAN_PIN[:2]), tuple(nk.PAN_ANCHOR[:2])], 7.6, nk.PAN_LINK_Z)
    for point in (nk.PAN_PIN, nk.PAN_ANCHOR):
        out = out.cut(cyl("z", (*point[:2], 0), gm.PIN_R, nk.PAN_LINK_Z))
    return out


@bone.carved
def jaw_bar(mechanical=False):
    """The jaw bar: the jaw's lever pin back to the mouth horn's (#838)."""
    solve = nk.LINKAGES["jaw"]
    _, a, b = solve(0)
    return link(tuple(a[1:]), tuple(b[1:]), nk.JAW_BAR_X, mechanical, BAR_BONE)
