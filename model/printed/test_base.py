"""Seam: the next Mech's Torso and its head variants' board carriers (model/printed/base.py) as model/stages.py places
them at rest with the neck and the gimbal: the Torso holds the neck mount, the pan servo and the pack inside its walls;
each variant's carriers and boards overlap nothing."""

import itertools

import pytest

from model import base, stages
from model import geometry as g
from model.printed.base import WALL
from model.printed.test_gimbal import _overlaps
from model.printed.test_neck import _shape

PLUGGED = {frozenset((f"next Core {n}:1", f"next Shield {n}:1")) for n in (1, 2)}  # each Core in its Shield's header
BASE = ("next torso", "next pack", "next board", "next switch", "next Core", "next Shield")


def _hits(doc):
    """{frozenset(pair)} of the parts overlapping at rest where one is the base's or the boards'."""
    shapes = {n: _shape(p) for n, p in stages.STAGES[doc].parts.items()}
    return {
        frozenset((a, b))
        for a, b in itertools.combinations(shapes, 2)
        if (a.startswith(BASE) or b.startswith(BASE))
        and frozenset((a, b)) not in PLUGGED
        and _overlaps(shapes[a], shapes[b]) > 0.01
    }


@pytest.mark.build
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


@pytest.mark.build
@pytest.mark.parametrize("doc", sorted(g.NEXT))
def test_each_variants_carriers_and_boards_overlap_nothing_at_rest(doc):
    assert _hits(doc) == set()
