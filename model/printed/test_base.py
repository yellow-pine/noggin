"""Seam: the Mech's Torso (model/printed/base.py) as model/stages.py places it at rest with the neck and the
gimbal: the Torso holds the neck mount, the pack, the switch board and the power-path board inside its walls, the pan
servo over them (#858); its boards, the cranium tray's and the tray overlap nothing."""

import itertools

import cadquery as cq
import numpy as np
import pytest
import trimesh

from model import base, skin, stages
from model import geometry as g
from model import gimbal as gm
from model import neck as nk
from model.printed import base as printed_base
from model.printed import bone
from model.printed.base import WALL
from model.printed.test_gimbal import _overlaps
from model.printed.test_neck import _shape

PLUGGED = {frozenset((f"Core {n}:1", f"Shield {n}:1")) for n in (1, 2)}  # each Core in its Shield's header
BASE = ("torso", "pack", "switch", "power-path", "test stand")  # and the cranium's (#858)
BASE += ("cranium tray", "Core", "Shield", "hub")


@pytest.mark.model
def test_the_torso_holds_the_neck_mount_the_pack_and_the_power_path_board_inside_its_walls():
    """#685: the shirt is the base. In plan each lies inside the Torso's walls, the pan servo over them (#858), the pack
    lying on its floor; the Torso's bottom is the foot, so nothing hangs below it."""
    (x0, x1), (y0, y1), (z0, z1) = base.TORSO
    parts = stages.neck_sub().parts | stages.base_sub().parts
    foot = printed_base.torso().val().BoundingBox()  # without the Seats the Skin adds (model/skin.py)
    assert (foot.xmin, foot.xmax, foot.ymin, foot.ymax, foot.zmin) == pytest.approx((x0, x1, y0, y1, z0))
    for name in (
        "neck mount:1",
        "pan servo:1",
        "pack:1",
        "switch board:1",
        "power-path board:1",
    ):
        b = _shape(parts[name]).BoundingBox()
        assert x0 + WALL <= b.xmin and b.xmax <= x1 - WALL and y0 + WALL <= b.ymin and b.ymax <= y1 - WALL, name
    lying = [_shape(parts[n]).BoundingBox().zmin for n in ("pack:1", "neck mount:1", "power-path board:1")]
    assert lying[0] == pytest.approx(lying[1]) == pytest.approx(lying[2])  # on the floor the neck mount stands on
    assert _shape(parts["pan servo:1"]).BoundingBox().zmin > z1  # over the lid, on the post (#858)


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


@pytest.fixture(
    params=[pytest.param(d, marks=pytest.mark.bones) if g.SKULL_SUB in g.MECH[d] else d for d in sorted(g.MECH)]
)
def head(request):
    """(the document, the box round the parts its tilt turns at rest), built in setup: CI's 15 s times the test alone."""
    stage = stages.STAGES[request.param]
    rides = [n for n in stage.horns["tilt horn"].loops[0].rockers if n.removesuffix(":1") not in skin.DRAWN]  # Skeleton
    solids = [_shape(stage.parts[n]) for n in rides if n.removesuffix(":1") not in g.BONES]
    for n in (n for n in rides if n.removesuffix(":1") in g.BONES):  # a mesh (#838): its STL's box
        (x0, y0, z0), (x1, y1, z1) = trimesh.load(stage.parts[n].file).apply_transform(stage.parts[n].matrix).bounds
        solids.append(cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0)))
    return request.param, cq.Compound.makeCompound(solids).BoundingBox()


@pytest.mark.model
def test_what_rides_the_head_fits_the_compact_head_its_eyes_in_its_lower_half(head):
    """#708, a hard gate in both Skeletons: the parts the tilt turns, at rest, under the head's shell (#828,
    base.shelled), fit gimbal.HEAD_MM (W x D x H), the eye centres at most base.EYES_UP of the way up them (the sim
    report reads the same off the MJCF: model/candidates.py)."""
    doc, b = head
    eyes = np.array(stages.DOCS[doc]["eyes"][0])
    lo, hi = base.shelled(np.array((b.xmin, b.ymin, b.zmin)) - eyes, np.array((b.xmax, b.ymax, b.zmax)) - eyes)
    assert all(s <= h for s, h in zip(hi - lo, gm.HEAD_MM))
    assert -lo[2] / (hi[2] - lo[2]) <= base.EYES_UP


def test_the_pedestal_as_bones_rounds_its_corners_sinks_its_plaque_and_prints_its_two_parts_as_drawn():
    """#708, #838: as Bones, carved from the mechanical parts, the pedestal's corners round, its plaque sunk in front
    and its lid's border down round the panel: just inside each mechanical corner, in the plaque's middle and on the
    border lies nothing, the panel inside it stands. Both lids have the post's hole and its slot back, and sit inside
    the walls, flush with their top, so they never slide off. The Torso prints upright, the lid flat, no overhang past
    45 deg."""
    (x0, x1), (y0, y1), (z0, z1) = base.TORSO
    torso, plain = printed_base.torso().val(), printed_base.torso(mechanical=True).val()
    lid, flat = printed_base.lid().val(), printed_base.lid(mechanical=True).val()
    for x, y in itertools.product((x0 + 1, x1 - 1), (y0 + 1, y1 - 1)):
        assert not torso.isInside(cq.Vector(x, y, (z0 + z1) / 2))
    (px0, px1), (pz0, pz1) = printed_base.PLAQUE
    assert not torso.isInside(cq.Vector((px0 + px1) / 2, y0 + 0.5, (pz0 + pz1) / 2))
    assert plain.isInside(cq.Vector((px0 + px1) / 2, y0 + 0.5, (pz0 + pz1) / 2))
    assert not lid.isInside(cq.Vector(0, y0 + 5, z1 - 0.5)) and lid.isInside(cq.Vector(30, y0 + 20, z1 - 0.5))
    for look in (lid, flat):
        bb = look.BoundingBox()
        assert x0 + printed_base.WALL < bb.xmin and bb.xmax < x1 - printed_base.WALL and bb.zmax == pytest.approx(z1)
        assert not look.isInside(cq.Vector(0, nk.AXIS[0], z1 - 1)) and not look.isInside(cq.Vector(0, y1 - 1, z1 - 1))
    assert bone.overhang_deg(torso) <= 45 and bone.overhang_deg(lid) <= 45
