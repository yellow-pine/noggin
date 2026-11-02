"""Seam: model/printed/bone.py, a Bone between two joints on the print bed: flat on the bed with no overhang past 45
deg, thick at its joints and waisted mid-span."""

import cadquery as cq
import pytest

from model.printed import bone

A, B = (0.0, 0.0, -5.0), (30.0, 10.0, -5.0)


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
