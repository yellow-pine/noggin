"""Public mesh-fitting seam: a vertebra's main passage, even when a plan projection hides it."""

import cadquery as cq
import numpy as np
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


def test_a_shared_bust_warp_preserves_each_bones_authored_sculpt():
    points = np.array([(x, y, z) for x in (-10, 10) for y in (-10, 10) for z in (-10, 10)], float)
    shift = np.array((2, -3, 5))
    arrays = {"bone_basis": points, "bone_warp": points + 1, "bone_sculpt": points + 1.25}
    scene = {
        "bones": [{"name": "public bone", "key": "bone", "matrix": np.eye(4).tolist()}],
        "landmarks": {str(i): {"source": p.tolist(), "target": (p + shift).tolist()} for i, p in enumerate(points)},
    }
    result, report = fit.warp(arrays, scene)
    assert result["bone_warp"] == pytest.approx(points + shift)
    assert result["bone_sculpt"] == pytest.approx(points + shift + 0.25)
    assert report["min_jacobian"] == pytest.approx(1)
    assert report["landmark_error_mm"] < 1e-8


def test_a_target_inside_the_donor_skull_still_registers_its_outer_cortex():
    outer = trimesh.creation.icosphere(subdivisions=3, radius=10)
    inner = trimesh.creation.icosphere(subdivisions=3, radius=8)
    inner.invert()
    skull = trimesh.util.concatenate((outer, inner))
    # The envelope is smaller than the donor skull: nearest-surface correspondence would select the inner wall.
    points = fit.outer_cortex(skull, np.array(((7, 0, 0), (-7, 0, 0))), np.zeros(3))
    assert points == pytest.approx(np.array(((10, 0, 0), (-10, 0, 0))), abs=0.03)


def test_regional_fits_keep_a_shared_bone_joint_continuous_in_the_common_frame():
    head = np.array(((-1, -1, 20), (1, -1, 20), (0, 1, 20), (0, 0, 30)), float)
    body = head * (1, 1, -1)
    scene = {"bones": [], "landmarks": {}, "warp_blend": {"normal": [0, 0, 1], "low": -10, "high": 10}}
    arrays = {}
    for name, points in (
        ("head", np.array(((0, 0, 0), (0, 0, 10)), float)),
        ("body", np.array(((0, 0, -10), (0, 0, 0)), float)),
    ):
        scene["bones"].append({"name": name, "key": name, "matrix": np.eye(4).tolist()})
        for kind in ("basis", "warp", "sculpt"):
            arrays[f"{name}_{kind}"] = points
    for region, points, shift in (("head", head, np.array((2, 0, 0))), ("body", body, np.zeros(3))):
        for i, p in enumerate(points):
            scene["landmarks"][f"{region}{i}"] = {
                "source": p.tolist(),
                "target": (p + shift).tolist(),
                "region": region,
            }
    result, report = fit.warp(arrays, scene)
    assert result["head_warp"] == pytest.approx(np.array(((1, 0, 0), (2, 0, 10))))
    assert result["body_warp"] == pytest.approx(np.array(((0, 0, -10), (1, 0, 0))))
    assert report["min_jacobian"] == pytest.approx(1)
