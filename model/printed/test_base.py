"""Seam: the next Mech's Torso and its head variants' board carriers (model/printed/base.py) as model/stages.py places
them at rest with the neck and the gimbal: the Torso holds the neck mount, the pan servo and the pack inside its walls;
each variant's carriers and boards overlap nothing."""

import itertools

import cadquery as cq
import pytest

from model import base, stages
from model import geometry as g
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


@pytest.fixture(params=[*sorted(g.NEXT), "next-stage1"])  # and Stage 1's test stand (#720)
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


def test_the_torso_and_the_rack_as_bones_round_their_corners_and_print_as_they_lie():
    """#704: just inside each of the plain Torso's outside corners and the rack's top corners lies nothing; the Torso
    prints upright and the rack on its back (its back face, the boards', on the bed), no overhang past 45 deg."""
    (x0, x1), (y0, y1), (z0, z1) = base.TORSO
    torso, rack = printed_base.torso().val(), printed_base.rack().val()
    for x, y in itertools.product((x0 + 1, x1 - 1), (y0 + 1, y1 - 1)):
        assert not torso.isInside(cq.Vector(x, y, (z0 + z1) / 2))
    r = rack.BoundingBox()
    for x in (r.xmin + 0.5, r.xmax - 0.5):
        assert not rack.isInside(cq.Vector(x, base.RACK_Y + base.TRAY_T / 2, r.zmax - 0.5))
    assert bone.overhang_deg(torso) <= 45
    on_back = rack.rotate(cq.Vector(), cq.Vector(1, 0, 0), -90)  # its back face (+y) turned down (-z)
    assert bone.overhang_deg(on_back) <= 45
