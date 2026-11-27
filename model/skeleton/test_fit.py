"""Seam: model/skeleton/fit.py's numbers, on shapes small enough to solve in a test: the field lands its landmarks
within the budget, refuses a stretch past it, and finds a vertebra's canal."""

import numpy as np
import pytest
import trimesh

from model.skeleton import fit


def test_the_field_lands_its_landmarks_inside_the_budget_and_its_box():
    x = trimesh.creation.box(extents=(40, 40, 40)).subdivide().subdivide().vertices
    pairs = [((20, 20, 20), (26, 24, 20), (1, 1, 1)), ((-20, -20, -20), (-20, -20, -20), (1, 1, 1))]
    box = (np.full(3, -30.0), np.array((30.0, 30.0, 25.0)))
    y, f, hit = fit.solve(x, np.full(len(x), 1.25), pairs, 1.0, box, ((2, 25.0, 1),))
    assert np.abs(hit - [p[1] for p in pairs]).max() <= fit.TOL_MM
    lo, hi = fit.stretch(f, np.full(len(x), 1.25))
    assert lo.min() >= fit.LOW and hi.max() <= 1.25
    assert (y.max(0) <= box[1] + 0.5).all() and y[:, 2].max() == pytest.approx(25.0, abs=0.5)


def test_a_stretch_past_the_budget_is_refused():
    with pytest.raises(ValueError, match="local stretch"):
        fit.stretch(np.array([np.diag((1.3, 1.0, 1.0))]), np.array((1.25,)))


def test_a_vertebras_canal_is_its_plan_views_largest_hole():
    ring = trimesh.creation.annulus(r_min=8, r_max=20, height=10).apply_translation((3, 4, 0))
    assert fit.canal(ring) == pytest.approx((3, 4), abs=0.5)


def test_the_canal_path_runs_from_its_foot_to_the_tilt_axis():
    assert fit.canal_y(-146.0) == pytest.approx(91.6) and fit.canal_y(-48.7) == pytest.approx(76.6)


def test_the_neck_keeps_its_canals_on_the_path_and_its_spines_in_front_of_the_skins_back():
    """Seven rings, their spines longer down the neck as C1 to C7's are, the lowest three past the Skin's neck back
    before the fit: fitted, every canal on the cervical path, C1's round the pan axis, every vertex ROOM in front of
    the back and over the path's foot, within the budget, each spine still a spine."""
    ring = trimesh.creation.annulus(r_min=8, r_max=14, height=12).subdivide()
    basis, faces = {}, {}
    for i, n in enumerate(fit.NECK):
        spine = trimesh.creation.box(extents=(6, 6 + 3 * i, 6)).subdivide().subdivide()
        one = trimesh.util.concatenate([ring, spine.apply_translation((0, 17 + 1.5 * i, 0))])
        basis[n], faces[n] = one.vertices + (0, 0, -14.0 * i), one.faces
    out, report = fit.vertebrae(basis, faces)
    for n in fit.NECK:
        y = out[n]
        z = (y[:, 2].min() + y[:, 2].max()) / 2
        mid = fit.canal(trimesh.Trimesh(y, faces[n], process=False))
        assert mid == pytest.approx((0, fit.PAN[1] if n == "atlas" else fit.canal_y(z)), abs=1.0)
        assert (fit.back(y) - y[:, 1]).min() >= fit.ROOM and y[:, 2].min() >= -146.5
    assert out["c7"][:, 1].max() > fit.canal_y(out["c7"][:, 2].mean()) + 25
    assert fit.LOW <= report["stretch"][0] and report["stretch"][1] <= 1.25 and report["skin_back_mm"] >= fit.ROOM


def test_a_triangles_shear_is_its_greatest_over_its_least_length_factor():
    """A right triangle pulled to twice its width has sheared by 2; one only turned, moved and grown has not."""
    tri, faces = np.array(((0, 0, 0), (1, 0, 0), (0, 1, 0)), float), np.array(((0, 1, 2),))
    assert fit.shear(tri, tri * (2, 1, 1), faces) == pytest.approx([2.0])
    turned = trimesh.transform_points(tri * 3, trimesh.transformations.rotation_matrix(0.7, (1, 2, 3), (4, 5, 6)))
    assert fit.shear(tri, turned, faces) == pytest.approx([1.0])


def _sheet():
    """A flat 20 mm sheet of 2.5 mm triangles round the origin, and one far off it."""
    g = np.mgrid[-10:10.1:2.5, -10:10.1:2.5].reshape(2, -1).T
    v = np.vstack([np.c_[g, np.zeros(len(g))], [(200, 0, 0), (202, 0, 0), (200, 2, 0)]])
    n = 9
    quads = [
        (i * n + j, i * n + j + 1, (i + 1) * n + j + 1, (i + 1) * n + j) for i in range(n - 1) for j in range(n - 1)
    ]
    faces = [t for a, b, c, d in quads for t in ((a, b, c), (a, c, d))] + [(81, 82, 83)]
    return v, np.array(faces)


def test_the_eyes_and_nose_gate_passes_a_sound_warp_and_reads_only_its_region():
    v, faces = _sheet()
    w = v * 1.1
    w[81:] = v[81:] * (1, 9, 1)  # the far triangle sheared out of shape: not the gate's
    report = fit.gate(v, w, faces, np.full(len(v), 1.2), [np.zeros(3)])
    assert report == {"triangles": 128, "folded": 0, "shear": 1.0, "least_jacobian": 1.2}


def test_the_eyes_and_nose_gate_refuses_a_fold_a_shear_and_a_collapse():
    v, faces = _sheet()
    one = np.ones(len(v))
    folded = v.copy()
    folded[40] += (4, 0, 0)  # the middle vertex past its neighbour: the triangles between them turn over
    with pytest.raises(ValueError, match="folded"):
        fit.gate(v, folded, faces, one, [np.zeros(3)])
    with pytest.raises(ValueError, match="sheared"):
        fit.gate(v, v * (2, 1, 1), faces, one, [np.zeros(3)])
    with pytest.raises(ValueError, match="Jacobian"):
        fit.gate(v, v, faces, one * (fit.JACOBIAN_MIN - 0.01), [np.zeros(3)])


def test_the_gate_reads_no_shear_off_a_sliver():
    """A triangle slenderer than SOUND shears with the field's bend along it, whatever the Warp: only its fold counts."""
    v = np.array(((0, 0, 0), (30, 0, 0), (15, 0.5, 0)), float)
    w = v.copy()
    w[2, 1] = 2.0
    assert fit.gate(v, w, np.array(((0, 1, 2),)), np.ones(3), [np.array((15.0, 0, 0))])["shear"] == 1.0
    w[2, 1] = -0.5
    with pytest.raises(ValueError, match="folded"):
        fit.gate(v, w, np.array(((0, 1, 2),)), np.ones(3), [np.array((15.0, 0, 0))])
