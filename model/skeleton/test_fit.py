"""Public mesh-fitting seam: a vertebra's main passage, even when a plan projection hides it."""

import cadquery as cq
import pytest
import trimesh

from model.skeleton import fit


@pytest.fixture
def vertebra():
    """A central oblique neural passage and two smaller lateral foramina, with known centres."""
    body = cq.Workplane("XY").ellipse(25, 18).extrude(12)
    axis = cq.Vector(0, 0.8, 1).normalized()
    body = body.cut(cq.Solid.makeCylinder(5, 40, cq.Vector(0, -8, -10), axis))
    for x in (-17, 17):
        body = body.cut(cq.Solid.makeCylinder(2.5, 12, cq.Vector(x, 0, 0)))
    points, faces = body.val().tessellate(0.05, 0.1)
    return trimesh.Trimesh([p.toTuple() for p in points], faces)


def test_the_central_canal_is_registered_instead_of_a_lateral_hole(vertebra):
    # At the body's halfway plane z=6, its known neural passage is y=0.8*z; lateral holes are x=±17.
    assert fit.canal(vertebra)[:2] == pytest.approx((0, 4.8), abs=0.1)
