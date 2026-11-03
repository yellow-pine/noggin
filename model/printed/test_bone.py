"""Seam: model/printed/bone.py, a Bone between two joints on the print bed: flat on the bed with no overhang past 45
deg, thick at its joints and waisted mid-span; and the Skeleton's style switch (model/printed: mechanical or Bones)."""

import cadquery as cq
import pytest

from model import geometry as g
from model import printed
from model.printed import bone

A, B = (0.0, 0.0, -5.0), (30.0, 10.0, -5.0)
CARVED_MM = 0.05  # a print tolerance, past the booleans' own


def test_a_bone_sits_flat_on_the_bed_with_no_overhang():
    b = bone.bone(A, B, head=(4.0, 4.0), waist=(2.0, 3.0)).val()
    assert len(b.Solids()) == 1 and b.BoundingBox().zmin == pytest.approx(A[2], abs=1e-6)
    assert bone.overhang_deg(b) <= 45


def test_a_bone_is_thick_at_its_joints_and_waisted_mid_span():
    """3 mm to the side of the span, just over the bed: inside near each joint, outside at mid-span (waist 2)."""
    b = bone.bone(A, B, head=(4.0, 4.0), waist=(2.0, 3.0)).val()
    side = cq.Vector(-10, 30, 0).normalized() * 3  # square to the span, in the bed
    at = lambda t: cq.Vector(*A) + (cq.Vector(*B) - cq.Vector(*A)) * t + side + cq.Vector(0, 0, 0.2)  # noqa: E731
    assert b.isInside(at(0.0)) and b.isInside(at(1.0)) and not b.isInside(at(0.5))


def test_overhang_reads_a_ceiling_and_skips_the_bed():
    """A box on the bed has none; the same box with a pocket cut up into it from below reads the pocket's ceiling."""
    block = cq.Workplane().box(10, 10, 4, centered=(True, True, False))
    assert bone.overhang_deg(block.val()) == 0
    pocket = block.cut(cq.Workplane().box(4, 4, 2, centered=(True, True, False))).val()
    assert bone.overhang_deg(pocket) == 90


def test_a_round_bone_stands_on_any_axis_elliptical_all_round():
    """Up z with its sections' height along y: an ellipse round the span, (2, 3) at the waist, (3, 4) at the joints, the
    joints' heads domed out near to an ellipsoid's tips, all one loft."""
    b = bone.bone((0, 0, 0), (0, 0, 20), head=(3.0, 4.0), waist=(2.0, 3.0), up=(0, 1, 0), round=True).val()
    assert b.isValid() and len(b.Solids()) == 1
    for x, y in ((1.9, 0), (-1.9, 0), (0, 2.9), (0, -2.9)):
        assert b.isInside(cq.Vector(x, y, 10)) and not b.isInside(cq.Vector(x * 1.1, y * 1.1, 10))
    assert (
        b.isInside(cq.Vector(0, -3.9, 20)) and b.isInside(cq.Vector(0, 0, 22.5)) and b.isInside(cq.Vector(0, 0, -2.5))
    )


@pytest.fixture(scope="module", params=sorted(printed.STYLED))
def styles(request):
    """(Bones, mechanical) of a styled part, built in setup: CI's 15 s times the test alone (#808)."""
    return tuple(printed.PARTS[s]().val() for s in (request.param, request.param + g.MECHANICAL))


def test_a_styled_skeleton_part_builds_mechanical_and_as_bones(styles):
    """#704: one valid solid in each style, the two not the same."""
    for shape in styles:
        assert shape.isValid() and len(shape.Solids()) == 1
    assert styles[0].Volume() != pytest.approx(styles[1].Volume(), rel=1e-3)


def test_a_bone_is_carved_from_its_mechanical_part(styles):
    """#809: the Bones lie inside the mechanical part, so what physics measures on it (clearance, overlap, torque,
    strength) holds for both: every point of their surface within CARVED_MM of it (a boolean misreads the faces they
    share)."""
    bones, mechanical = styles
    surface, _ = bones.tessellate(0.5, 1.0)
    sample = surface[:: len(surface) // 200 + 1]  # some 200 points: OCCT's isInside is slow on a grown part
    assert [p.toTuple() for p in sample if not mechanical.isInside(p, CARVED_MM)] == []


def test_every_skeleton_part_has_both_styles_or_names_the_ticket_drawing_its_bones():
    """The Skeleton: the next Mech's parts in PETG (geometry.PRINTED). Each is STYLED, or UNSTYLED with its reason."""
    skeleton = {k for k, (_, m) in g.PRINTED.items() if k.startswith("next ") and "PETG" in m and g.MECHANICAL not in k}
    assert set(printed.STYLED) | set(printed.UNSTYLED) == skeleton
    assert not set(printed.STYLED) & set(printed.UNSTYLED) and all(printed.UNSTYLED.values())
    assert printed.styled("next bail", mechanical=True) == "next bail mechanical"
    assert printed.styled("next eyeball core", True) == "next eyeball core"


# each Skeleton part's Colour group as Cansin set them (#805; the Torso a Mount since #838)
GROUPS = {
    "Bones": ["gimbal frame", "head mount", "neck mount", "jaw", "test stand", "skull", "mandible", "atlas", "axis"]
    + ["worn skull", "worn mandible"],
    "Joints": ["yaw yoke", "pan yoke", "eyeball core", "bail"],
    "Linkages": ["tie-bar", "push-rod", "pitch bar", "lid bar", "lid link", "pan bar", "tilt bar", "jaw bar"]
    + [f"{s} {lid}" for s in "LR" for lid in ("upper lid", "lower lid")],
    "Mounts": ["torso", "torso lid"],  # the realistic skull's black box pedestal (#838)
}


def test_every_skeleton_part_carries_its_skeleton_colour_group():
    """#805: each Skeleton part, in both styles, carries its Colour group, one every Skeleton Palette prints."""
    skeleton = {k: group for k, (group, m) in g.PRINTED.items() if k.startswith("next ") and "PETG" in m}
    want = {f"next {part}": group for group, parts in GROUPS.items() for part in parts}
    assert {k.removesuffix(g.MECHANICAL): group for k, group in skeleton.items()} == want
    assert all(set(v) == set(GROUPS) for v in g.THEMES["Skeleton palette"].values())
