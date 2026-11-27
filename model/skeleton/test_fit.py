"""Seam: model/skeleton/fit.py's numbers, on shapes small enough to solve in a test: the field lands its landmarks
within the budget and under a skin, refuses a stretch past it, and finds a vertebra's canal."""

import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

from model.skeleton import envelope, fit


def _box():
    return trimesh.creation.box(extents=(40, 40, 40)).subdivide().subdivide().vertices


def test_the_field_lands_its_landmarks_inside_the_budget():
    x = _box()
    pairs = [((20, 20, 20), (26, 24, 20), (1, 1, 1)), ((-20, -20, -20), (-20, -20, -20), (1, 1, 1))]
    _, f, hit = fit.solve(x, np.full(len(x), 1.25), pairs, 1.0)
    assert np.abs(hit - [p[1] for p in pairs]).max() <= fit.TOL_MM
    lo, hi = fit.stretch(f, np.full(len(x), 1.25))
    assert lo.min() >= fit.LOW and hi.max() <= 1.25


def test_the_field_brings_its_region_under_a_skin():
    """A 40 mm box in a 33 mm ball, its corners 1.6 mm out of it: fitted, every vertex RAW under the ball."""
    x, ball = _box(), envelope.Skin(trimesh.creation.icosphere(subdivisions=4, radius=33.0))
    assert ball.depth(x).min() < -1.5
    pairs = [((0, 0, s * 20), (0, 0, s * 20), (1, 1, 1)) for s in (-1, 1)]
    y, f, _ = fit.solve(x, np.full(len(x), 1.25), pairs, 1.0, ball)
    fit.stretch(f, np.full(len(x), 1.25))
    assert ball.depth(y).min() >= fit.RAW


def test_the_field_brings_a_face_under_a_crease_of_the_skin_its_vertices_straddle():
    """Two 30 mm balls crossing leave a waist 20.4 mm round between them; a box's long edges cross it 21.2 mm out,
    between vertices that lie 5 mm and more under the balls. Fitted with its faces, the whole surface is RAW under the skin
    (Morty's hairline and the grooves of his hair cut in between a bone's vertices the same way)."""
    waist = envelope.Skin(
        trimesh.util.concatenate(
            [trimesh.creation.icosphere(subdivisions=4, radius=30.0).apply_translation((s * 22, 0, 0)) for s in (-1, 1)]
        )
    )
    box = trimesh.creation.box(extents=(40, 30, 30)).subdivide().apply_translation((10, 0, 0))
    x, faces = np.array(box.vertices), np.array(box.faces)
    assert waist.depth(x).min() > fit.RAW + fit.AIM and waist.depth(fit.surface(x, faces)).min() < 0
    pairs = [((s * 15 + 10, 0, 0), (s * 15 + 10, 0, 0), (1, 1, 1)) for s in (-1, 1)]
    y, f, _ = fit.solve(x, np.full(len(x), 1.25), pairs, 1.0, waist, faces=faces)
    fit.stretch(f, np.full(len(x), 1.25))
    assert waist.depth(fit.surface(y, faces)).min() >= fit.RAW


def test_a_fill_draws_its_rows_out_to_the_skin_inside_the_budget():
    """A 40 mm box in a 40 mm ball, its bottom's corners pinned, its top filled: the top comes up at least 4 mm, never
    past RAW under the ball, every local length inside the budget (fit.stretch raises otherwise); unfilled, it stays."""
    x, ball = _box(), envelope.Skin(trimesh.creation.icosphere(subdivisions=4, radius=40.0))
    pairs = [((sx * 20, sy * 20, -20), (sx * 20, sy * 20, -20), (1, 1, 1)) for sx in (-1, 1) for sy in (-1, 1)]
    rows, caps = np.flatnonzero(x[:, 2] > 19), np.full(len(x), 1.25)
    y, f, _ = fit.solve(x, caps, pairs, 1.0, ball, rows)
    fit.stretch(f, caps)
    assert y[rows, 2].max() >= 24.0 and ball.depth(y).min() >= fit.RAW
    still, _, _ = fit.solve(x, caps, pairs, 1.0, ball)
    assert np.abs(still - x).max() < 0.01


def test_a_stretch_past_the_budget_is_refused():
    with pytest.raises(ValueError, match="local stretch"):
        fit.stretch(np.array([np.diag((1.3, 1.0, 1.0))]), np.array((1.25,)))


def test_a_vertebras_canal_is_its_plan_views_largest_hole():
    ring = trimesh.creation.annulus(r_min=8, r_max=20, height=10).apply_translation((3, 4, 0))
    assert fit.canal(ring) == pytest.approx((3, 4), abs=0.5)


def test_the_canal_path_runs_from_its_foot_to_the_tilt_axis():
    assert fit.canal_y(-146.0) == pytest.approx(91.6) and fit.canal_y(-48.7) == pytest.approx(76.6)


def test_the_neck_keeps_its_canals_on_the_path_and_its_spines_under_the_skin():
    """Seven rings, their spines longer down the neck as C1 to C7's are, the lowest two past the skin's back (a box's
    wall at y 123) before the fit: fitted, every canal on the cervical path, C1's round the pan axis, every vertex RAW
    under the skin and over the path's foot, within the budget, each spine still a spine."""
    ring = trimesh.creation.annulus(r_min=8, r_max=14, height=12).subdivide()
    basis, faces = {}, {}
    for i, n in enumerate(fit.NECK):
        spine = trimesh.creation.box(extents=(6, 6 + 3 * i, 6)).subdivide().subdivide()
        one = trimesh.util.concatenate([ring, spine.apply_translation((0, 17 + 1.5 * i, 0))])
        basis[n], faces[n] = one.vertices + (0, 0, -14.0 * i), one.faces
    skin = envelope.Skin(trimesh.creation.box(bounds=((-60, 20, -190), (60, 123, 0))))
    out, report = fit.vertebrae(basis, faces, skin)
    for n in fit.NECK:
        y = out[n]
        z = (y[:, 2].min() + y[:, 2].max()) / 2
        mid = fit.canal(trimesh.Trimesh(y, faces[n], process=False))
        assert mid == pytest.approx((0, fit.PAN[1] if n == "atlas" else fit.canal_y(z)), abs=1.0)
        assert skin.depth(y).min() >= fit.RAW and y[:, 2].min() >= -146.5
    assert out["c7"][:, 1].max() > fit.canal_y(out["c7"][:, 2].mean()) + 25
    assert fit.LOW <= report["stretch"][0] and report["stretch"][1] <= 1.25 and report["skin_mm"] >= fit.RAW


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
        fit.gate(v, v * (3, 1, 1), faces, one, [np.zeros(3)])
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


def test_the_field_keeps_its_rows_clear_of_what_moves_by_them():
    """A 40 mm box in a 40 mm ball, its bottom's corners pinned, its top filled toward the ball, a plate of points
    2 mm over the top: the top's rows stop CLEAR_MM under the plate, where unhindered they rise 4 mm and more."""
    x, ball = _box(), envelope.Skin(trimesh.creation.icosphere(subdivisions=4, radius=40.0))
    pairs = [((sx * 20, sy * 20, -20), (sx * 20, sy * 20, -20), (1, 1, 1)) for sx in (-1, 1) for sy in (-1, 1)]
    rows, caps = np.flatnonzero(x[:, 2] > 19), np.full(len(x), 1.25)
    plate = np.c_[np.mgrid[-30:30.1:1, -30:30.1:1].reshape(2, -1).T, np.full(61 * 61, 22.0)]
    y, _, _ = fit.solve(x, caps, pairs, 1.0, ball, rows, clear=(rows, cKDTree(plate)))
    assert y[rows, 2].max() <= 22.0 - fit.CLEAR_MM


def test_the_head_sees_the_neck_turn_back_as_it_tilts_and_pans():
    """A point on the tilt axis stays as the head tilts; one 10 mm behind it sinks 10 mm as the head tilts 90 deg
    face down; one 10 mm beside the pan axis swings behind it as the head pans 90 deg."""
    on, behind = np.array(fit.TILT), np.array(fit.TILT) + (0, 10, 0)
    assert fit.seen(np.array([on, behind]), 90, 0) == pytest.approx(np.array([on, on - (0, 0, 10)]))
    beside = np.array(fit.PAN) + (10, 0, 0)
    assert fit.seen(beside[None], 0, 90) == pytest.approx((np.array(fit.PAN) - (0, 10, 0))[None])
