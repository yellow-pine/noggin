"""The shared numerical fitting seam: bend a connected region without moving its functional anchors."""

import numpy as np
import pytest

from model.skeleton import deformation
from model.skeleton.fit import check_surface_stretch


def test_bounded_nonlinear_bend_keeps_joint_anchors_exact():
    points = np.array([(x, y, z) for x in np.linspace(-3, 3, 13) for y in (-0.1, 0.1) for z in (-0.1, 0.1)])
    anchors = np.array(((-3, 0, 0), (3, 0, 0)), float)
    field, report = deformation.solve(
        points,
        np.eye(4),
        1.0,
        anchors,
        np.array(((0, 0, 0),)),
        2.0,
        lambda p: p[:, 1] - 0.3,
        np.array(((0, 0, 0),)),
    )
    moved, gradient = deformation.evaluate(points, field)
    fixed, _ = deformation.evaluate(anchors, field)
    middle, _ = deformation.evaluate(np.zeros((1, 3)), field)
    assert fixed == pytest.approx(anchors, abs=1e-8)
    assert middle[0, 1] >= 0.3 - 1e-6
    assert report["minimum_length"] >= 0.75 - 1e-6
    assert report["maximum_length"] <= 1.25 + 1e-6
    # A second Bone at the same original joint sees the identical assembled field.
    joined, _ = deformation.evaluate(np.repeat(points[:1], 2, axis=0), field)
    assert joined[0] == pytest.approx(joined[1])
    delta = np.array((1e-4, 0, 0))
    forward, _ = deformation.evaluate(points + delta, field)
    backward, _ = deformation.evaluate(points - delta, field)
    assert (forward - backward) / 2e-4 == pytest.approx(gradient[:, :, 0], abs=1e-7)
    assert np.max(np.abs(moved - points)) > 0.1


def test_joint_pinned_global_shape_modes_do_not_require_large_gaussian_coefficients():
    points = np.array([(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float)
    field, report = deformation.solve(
        points,
        np.eye(4),
        1.0,
        np.array(((-2, 0, 0), (2, 0, 0))),
        np.empty((0, 3)),
        2.0,
        lambda p: 0.8 - p[:, 2],
        np.array(((0, 0, 1),)),
    )
    moved, gradient = deformation.evaluate(points, field)
    assert moved[:, 2] == pytest.approx(points[:, 2] * 0.8, abs=1e-6)
    assert gradient[:, 2, 2] == pytest.approx(np.full(len(points), 0.8), abs=1e-6)
    assert report["sampled_feasible"]


def test_final_skinny_source_triangles_obey_the_budget_even_when_the_smooth_derivative_does():
    # A small curved deflection across a long, thin original triangle can stretch its final chord geometry.
    triangle = np.array(((0, 0, 0), (1, 0, 0), (0.5, 0.0001, 0)), float)
    field, report = deformation.solve(
        triangle,
        np.eye(4),
        1.0,
        np.array(((-3, 0, 0), (3, 0, 0))),
        np.array(((0.5, 0, 0),)),
        2.0,
        lambda p: p[:, 1] - 0.001,
        np.array(((0.5, 0, 0),)),
        triangles=triangle[None],
    )
    final, _ = deformation.evaluate(triangle, field)
    proof = check_surface_stretch(triangle, final, np.array(((0, 1, 2),)), 1.0)
    assert proof["minimum"] >= 0.75 - 1e-6
    assert proof["maximum"] <= 1.25 + 1e-6
    assert report["sampled_feasible"]
