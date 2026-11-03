"""Seam: the next Mech's Torso and its head variants' board carriers (model/printed/base.py) as model/stages.py places
them at rest with the neck and the gimbal: the Torso holds the neck mount, the pan servo and the pack inside its walls;
each variant's carriers and boards overlap nothing."""

import itertools

import cadquery as cq
import numpy as np
import pytest

from model import base, stages
from model import geometry as g
from model import gimbal as gm
from model.printed import base as printed_base
from model.printed import bone
from model.printed.base import WALL
from model.printed.test_gimbal import _overlaps
from model.printed.test_neck import _shape

PLUGGED = {frozenset((f"next Core {n}:1", f"next Shield {n}:1")) for n in (1, 2)}  # each Core in its Shield's header
BASE = ("next torso", "next pack", "next board", "next switch", "next Core", "next Shield", "next test stand")


@pytest.mark.model
def test_the_torso_holds_the_neck_mount_the_pan_servo_and_the_pack_inside_its_walls():
    """#685: the shirt is the base. In plan each lies inside the Torso's walls, the pack lying on its floor; the Torso's
    bottom is the foot, so nothing hangs below it."""
    (x0, x1), (y0, y1), (z0, _) = base.TORSO
    parts = stages.next_neck().parts | stages.next_base().parts
    foot = _shape(parts["next torso:1"]).BoundingBox()
    assert (foot.xmin, foot.xmax, foot.ymin, foot.ymax, foot.zmin) == pytest.approx((x0, x1, y0, y1, z0))
    for name in ("next neck mount:1", "next pan servo:1", "next pack:1"):
        b = _shape(parts[name]).BoundingBox()
        assert x0 + WALL <= b.xmin and b.xmax <= x1 - WALL and y0 + WALL <= b.ymin and b.ymax <= y1 - WALL, name
    lying = [_shape(parts[n]).BoundingBox().zmin for n in ("next pack:1", "next neck mount:1")]
    assert lying[0] == pytest.approx(lying[1])  # the pack on the floor the neck mount stands on


@pytest.fixture(params=g.SIMULATED)  # the whole Mech and Stage 1's test stand (#720), mechanical (#809)
def placed(request):
    """{part: its solid at rest} in the document, built in setup: CI's 15 s times the test alone."""
    return {n: _shape(p) for n, p in stages.STAGES[request.param].parts.items()}


@pytest.mark.model
def test_each_variants_carriers_and_boards_overlap_nothing_at_rest(placed):
    """No two overlap where one is the base's or the boards'."""
    pairs = [
        (a, b)
        for a, b in itertools.combinations(placed, 2)
        if (a.startswith(BASE) or b.startswith(BASE)) and frozenset((a, b)) not in PLUGGED
    ]
    assert _overlaps(placed, pairs) == []


@pytest.fixture(params=sorted(g.NEXT))
def head(request):
    """(the document, the box round the parts its tilt turns at rest), built in setup: CI's 15 s times the test alone."""
    stage = stages.STAGES[request.param]
    rides = stage.horns["tilt horn"].loops[0].rockers
    return request.param, cq.Compound.makeCompound([_shape(stage.parts[n]) for n in rides]).BoundingBox()


@pytest.mark.model
def test_what_rides_the_head_fits_the_compact_head_its_eyes_in_its_lower_half(head):
    """#708, a hard gate in both Skeletons: the parts the tilt turns, at rest, under the head's shell (#828,
    base.shelled), fit gimbal.HEAD_MM (W x D x H), the eye centres at most base.EYES_UP of the way up them (the sim
    report reads the same off the MJCF: model/candidates.py)."""
    doc, b = head
    eyes = np.array(stages.DOCS[doc]["next-eyes"][0])
    lo, hi = base.shelled(np.array((b.xmin, b.ymin, b.zmin)) - eyes, np.array((b.xmax, b.ymax, b.zmax)) - eyes)
    assert all(s <= h for s, h in zip(hi - lo, gm.HEAD_MM))
    assert -lo[2] / (hi[2] - lo[2]) <= base.EYES_UP


def test_the_torso_and_the_rack_as_bones_open_the_mechanical_ones_walls_and_shelf_and_the_torso_prints_upright():
    """#708: as Bones, carved from the mechanical parts, the Torso's corners round and its walls windowed, each of the
    rack's cradle floors open under the Core (#828): just inside each mechanical corner, half way up a window's middle,
    and in the middle of each mechanical cradle floor lies nothing; each cradle's roof is flat on top, 15 mm across, in
    both looks, where #665's hair seats. The Torso prints upright, no overhang past 45 deg."""
    (x0, x1), (y0, y1), (z0, z1) = base.TORSO
    torso, rack = printed_base.torso().val(), printed_base.rack().val()
    for x, y in itertools.product((x0 + 1, x1 - 1), (y0 + 1, y1 - 1)):
        assert not torso.isInside(cq.Vector(x, y, (z0 + z1) / 2))
    c = printed_base.CORNER
    wx, wy = printed_base._windows(x0 + c, x1 - c)[0], printed_base._windows(y0 + c, y1 - c)[0]  # a window's middle
    for x, y in ((wx, y0 + 1), (wx, y1 - 1), (x0 + 1, wy), (x1 - 1, wy)):
        assert not torso.isInside(cq.Vector(x, y, (z0 + z1) / 2))
    (x, y), floor = base.CHEEK, gm.PLATE_Z[1] + base.TRAY_T / 2
    for s in (-1, 1):
        assert not rack.isInside(cq.Vector(s * x, y, floor))
        for look in (rack, printed_base.rack(mechanical=True).val()):  # a roof flat on top, 15 across (#665's hair)
            assert all(look.isInside(cq.Vector(s * (x + d), y, base.ROOF_Z - 0.5)) for d in (-5.0, 2.5, 10.0))
            assert not look.isInside(cq.Vector(s * x, y, base.ROOF_Z + 0.5))
    assert bone.overhang_deg(torso) <= 45
