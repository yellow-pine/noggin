"""Seam: the next Mech's eye gimbal parts (model/printed/gimbal.py) as model/stages.py places them at rest: no two
overlap, and each cap's pupil seat turns toward the other eye (the toe-in, #630)."""

import itertools

import cadquery as cq
import pytest

from model import envelopes, stages
from model import gimbal as gm
from model.printed import PARTS, gimbal

# a horn's hub on its servo's spline: the Envelopes overlap there by design, as in today's Stages
ON_SPLINE = {frozenset((f"next {d} servo:1", f"next {d} horn:1")) for d in gm.drives()}


def _overlaps(a, b):
    ba, bb = a.BoundingBox(), b.BoundingBox()
    apart = any(
        getattr(ba, f"{k}max") < getattr(bb, f"{k}min") or getattr(bb, f"{k}max") < getattr(ba, f"{k}min")
        for k in "xyz"
    )
    return 0.0 if apart else a.intersect(b).Volume()


@pytest.mark.build
def test_no_two_parts_overlap_at_rest():
    shapes = {}
    for name, p in stages.next_eyes().parts.items():
        stem = stages.stem(p.file)
        m = cq.Matrix([list(map(float, row)) for row in p.matrix[:3]])
        shapes[name] = (PARTS.get(stem) or envelopes.ENVELOPES[stem])().val().transformGeometry(m)
    hits = [
        f"{a} / {b}: {v:.2f} mm3"
        for a, b in itertools.combinations(shapes, 2)
        if frozenset((a, b)) not in ON_SPLINE and (v := _overlaps(shapes[a], shapes[b])) > 0.01
    ]
    assert hits == []


@pytest.mark.parametrize("side, inward", [("L", -1), ("R", 1)])
def test_the_pupil_seat_sits_toward_the_other_eye(side, inward):
    """Just inside the cap's front, 6.6 mm either side of the gaze: the seat (r 7) is cut on the inward side, the cap
    solid on the outward one."""
    cap = gimbal.cap(side).val()
    y = -gm.CAP_R + 0.9
    assert not cap.isInside(cq.Vector(inward * 6.6, y, 0)) and cap.isInside(cq.Vector(-inward * 6.6, y, 0))
