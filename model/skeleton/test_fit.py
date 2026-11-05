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
    arrays["bone_faces"] = np.array(((0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5)))
    scene = {
        "bones": [{"name": "public bone", "key": "bone", "group": "Skull", "matrix": np.eye(4).tolist()}],
        "landmarks": {str(i): {"source": p.tolist(), "target": (p + shift).tolist()} for i, p in enumerate(points)},
        "anatomical_regions": {"skull": {"scale": 1.0, "matrix": np.eye(4).tolist()}},
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
    scene["anatomical_regions"] = {
        "skull": {"scale": 1.0, "matrix": np.eye(4).tolist()},
        "upper_chest": {"scale": 1.0, "matrix": np.eye(4).tolist()},
    }
    arrays = {}
    for name, points in (
        ("head", np.array(((0, 0, 0), (0, 0, 10), (1, 0, 0), (0, 1, 0)), float)),
        ("body", np.array(((0, 0, -10), (0, 0, 0), (1, 0, 0), (0, 1, 0)), float)),
    ):
        scene["bones"].append(
            {"name": name, "key": name, "group": "Skull" if name == "head" else "Ribcage", "matrix": np.eye(4).tolist()}
        )
        arrays[name + "_faces"] = np.array(((0, 1, 2), (0, 2, 3), (0, 3, 1), (1, 3, 2)))
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
    assert result["head_warp"] == pytest.approx(np.array(((1, 0, 0), (2, 0, 10), (2, 0, 0), (1, 1, 0))))
    assert result["body_warp"] == pytest.approx(np.array(((0, 0, -10), (1, 0, 0), (2, 0, 0), (1, 1, 0))))
    assert report["min_jacobian"] == pytest.approx(1)


def test_declared_uniform_regional_resize_does_not_consume_local_shape_budget():
    # The regional size is explicit, never estimated separately from each fitted Bone.
    gradients = np.array([np.diag((1.5, 2.0, 2.5))])
    report = fit.check_stretch(gradients, 2.0)
    assert report["minimum"] == pytest.approx(0.75)
    assert report["maximum"] == pytest.approx(1.25)


def test_preserved_volume_cannot_hide_excessive_local_squash_and_stretch():
    with pytest.raises(ValueError, match="local stretch"):
        fit.check_stretch(np.array([np.diag((0.5, 1.0, 2.0))]), 1.0)


def test_final_sculpt_surface_changes_count_against_the_same_regional_budget():
    basis = np.array(((0, 0, 0), (1, 0, 0), (0, 1, 0)), float)
    final = basis.copy()
    final[1, 0] = 1.3
    with pytest.raises(ValueError, match="surface stretch"):
        fit.check_surface_stretch(basis, final, np.array(((0, 1, 2),)), 1.0)


def test_surface_budget_accepts_rigid_placement_after_declared_regional_resize():
    basis = np.array(((0, 0, 0), (1, 0, 0), (0, 1, 0)), float)
    final = basis @ np.array(((0, 1, 0), (-1, 0, 0), (0, 0, 1))) * 2 + (4, 5, 6)
    report = fit.check_surface_stretch(basis, final, np.array(((0, 1, 2),)), 2.0)
    assert report["minimum"] == pytest.approx(1)
    assert report["maximum"] == pytest.approx(1)


def test_a_region_cannot_hide_an_inherited_anisotropic_baseline():
    matrix = np.diag((0.5, 1.0, 2.0, 1.0)).tolist()
    scene = {
        "bones": [{"group": "C1", "matrix": matrix}],
        "anatomical_regions": {"cervicals": {"scale": 1.0, "matrix": matrix}},
    }
    with pytest.raises(ValueError, match="uniform"):
        fit.warp({}, scene)


def test_cervical_bones_cannot_be_independently_reposed():
    scene = {
        "bones": [{"group": "C1", "matrix": np.diag((2.0, 2.0, 2.0, 1.0)).tolist()}],
        "anatomical_regions": {"cervicals": {"scale": 1.0, "matrix": np.eye(4).tolist()}},
    }
    with pytest.raises(ValueError, match="share"):
        fit.warp({}, scene)


def test_original_cervical_joint_is_preserved_by_one_declared_region_frame():
    arrays, bones = {}, []
    for name, group, points in (
        ("upper", "C1", np.array(((0, 0, 0), (0, 0, 10), (1, 0, 0), (0, 1, 0)), float)),
        ("lower", "C2", np.array(((0, 0, -10), (0, 0, 0), (1, 0, 0), (0, 1, 0)), float)),
    ):
        for kind in ("basis", "warp", "sculpt"):
            arrays[name + "_" + kind] = points.copy()
        arrays[name + "_faces"] = np.array(((0, 1, 2), (0, 2, 3), (0, 3, 1), (1, 3, 2)))
        bones.append({"name": name, "group": group, "key": name, "matrix": np.eye(4).tolist()})
    matrix = np.eye(4)
    matrix[:3, :3] *= 0.8
    matrix[:3, 3] = (4, 5, 6)
    scene = {"bones": bones, "landmarks": {}}
    result, report = fit.regional_seed(arrays, scene, {"cervicals": {"scale": 0.8, "matrix": matrix.tolist()}})
    assert result["upper_sculpt"][0] == pytest.approx(result["lower_sculpt"][1])
    assert scene["bones"][0]["matrix"] == scene["bones"][1]["matrix"]
    assert report["regional_stretch"]["upper"]["field"]["minimum"] == pytest.approx(1)


def test_constrained_affine_meets_exact_anchors_without_spending_region_budget():
    source = np.array(((-2, 0, 0), (2, 0, 0), (0, 4, 0)), float)
    target = source * 1.1 + (4, 5, 6)
    matrix, report = fit.constrained_affine(source, target)
    assert source @ matrix[:3, :3].T + matrix[:3, 3] == pytest.approx(target, abs=1e-6)
    assert report["anchor_error_mm"] < 1e-6
    assert report["stretch"]["minimum"] >= 0.75
    assert report["stretch"]["maximum"] <= 1.25


def test_declared_regional_size_and_rigid_pitch_keep_bilateral_functional_anchors_exact():
    source = np.array(((20, 0, 0), (-20, 0, 0)), float)
    target = np.array(((25, 10, 30), (-25, 10, 30)), float)
    matrix, report = fit.regional_pose(source, target, uniform_size=1.1, pitch_deg=30)
    assert source @ matrix[:3, :3].T + matrix[:3, 3] == pytest.approx(target, abs=1e-10)
    mapped = np.array((0, 0, 10)) @ matrix[:3, :3].T + matrix[:3, 3]
    assert mapped == pytest.approx((0, 4.5, 30 + 11 * np.sqrt(3) / 2), abs=1e-10)
    assert report["declared_uniform_size"] == 1.1
    assert report["measured_initial_local_lengths"] == pytest.approx((1.25 / 1.1, 1, 1))
    declared = np.asarray(report["declared_uniform_frame"])
    assert np.linalg.svd(declared[:3, :3], compute_uv=False) == pytest.approx(np.full(3, 1.1))


def test_affine_anchor_incompatibility_is_not_reported_as_global_shape_impossibility():
    source = np.array(((0, 0, 0), (1, 0, 0), (0, 1, 0)), float)
    target = np.array(((0, 0, 0), (3, 0, 0), (0, 0.5, 0)), float)
    with pytest.raises(ValueError, match="affine.*scale"):
        fit.constrained_affine(source, target)


def test_coarse_head_constraint_keeps_a_real_diagonal_groove():
    cage = {
        "radial_first_exits": {
            "210": {
                "origin_world_x_mm": 0,
                "origin_world_y_mm": 0,
                "radius_mm_by_angle_deg": {
                    str(i * 45): r for i, r in enumerate((100, 100, 100, 100, 100, 47, 92.5, 47))
                },
            }
        }
    }
    q = np.array(((-65 / np.sqrt(2), -65 / np.sqrt(2), 210), (0, -65, 210)))
    margins = fit.coarse_head_margin(q, cage, 4.2)
    assert margins[0] < -20
    assert margins[1] > 0


def test_floor_extended_skin_removes_false_z0_base_cut_penalty_without_altering_sidewalls():
    from model.skeleton.envelope import Envelope

    box = trimesh.creation.box(bounds=((-50, -50, 0), (50, 50, 100)))
    raw_env = Envelope(box.vertices, box.faces)
    ext_v, ext_f = fit.floor_extended_skin(box.vertices, box.faces, extension_mm=200.0)
    ext_env = Envelope(ext_v, ext_f)
    # A point at z=1 mm near the center of the chest is only 1 mm from the artificial z=0 cut,
    # but 49 mm inside the actual ±50 mm sidewalls.
    probe = np.array(((0.0, 0.0, 1.0), (0.0, 0.0, 50.0)))
    assert raw_env.distance(probe)[0] == pytest.approx(1.0, abs=1e-5)
    assert ext_env.distance(probe)[0] == pytest.approx(50.0, abs=1e-5)
    assert ext_env.distance(probe)[1] == pytest.approx(50.0, abs=1e-5)


def test_joint_witnesses_extract_and_evaluate_opposing_articular_patches():
    b0 = trimesh.creation.box(bounds=((10, -10, 100), (25, 10, 110)))
    b1 = trimesh.creation.box(bounds=((10, -10, 88.5), (25, 10, 98.5)))
    arrays = {
        "b0_basis": np.asarray(b0.vertices, float),
        "b0_faces": np.asarray(b0.faces, np.int32),
        "b1_basis": np.asarray(b1.vertices, float),
        "b1_faces": np.asarray(b1.faces, np.int32),
    }
    scene = {
        "bones": [
            {"name": "occipital bone", "key": "b0", "group": "Skull", "matrix": np.eye(4).tolist()},
            {"name": "C1", "key": "b1", "group": "C1", "matrix": np.eye(4).tolist()},
        ]
    }
    witnesses = fit.joint_witnesses(arrays, scene)
    assert "C0 L" in witnesses["joints"]
    c0 = witnesses["joints"]["C0 L"]
    assert c0["native_gap_mm"]["min"] == pytest.approx(1.5, abs=1e-5)
    evaluated = fit.evaluate_joint_witnesses(
        witnesses,
        {"occipital bone": arrays["b0_basis"] + (0, 0, 5), "C1": arrays["b1_basis"] + (0, 0, 5)},
        {"occipital bone": arrays["b0_faces"], "C1": arrays["b1_faces"]},
    )
    assert evaluated["C0 L"]["deformed_gap_mm"]["min"] == pytest.approx(1.5, abs=1e-5)
