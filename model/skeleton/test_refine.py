"""Refining the source representation changes neither anatomy nor its restorable authored history."""

import numpy as np
import pytest
import trimesh

from model.skeleton import refine


def test_conforming_refinement_retains_original_geometry_vertices_and_authored_keys():
    basis = np.array(((0, 0, 0), (13, 0, 0), (6, 0.06, 0), (5, 1, 2)), float)
    faces = np.array(((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)))
    warp = basis * (1.1, 0.9, 1.0) + (2, -3, 5)
    sculpt = warp.copy()
    sculpt[3, 2] += 0.3
    keys = {"basis": basis, "warp": warp, "sculpt": sculpt}
    result, triangles, lineage = refine.mesh(keys, faces, max_edge=1.0)
    assert len(result["basis"]) > 4
    assert np.array_equal(lineage["original_faces"], faces)
    assert len(lineage["parent_faces"]) == len(triangles)
    for kind, original in keys.items():
        assert np.array_equal(result[kind][:4], original)
        before, after = (
            trimesh.Trimesh(v, f, process=False) for v, f in ((original, faces), (result[kind], triangles))
        )
        assert after.is_watertight and after.is_winding_consistent and after.body_count == 1
        assert after.area == pytest.approx(before.area, rel=1e-12)
        assert after.volume == pytest.approx(before.volume, rel=1e-12)
        for i in range(4, len(result[kind])):
            parent = lineage["vertex_parent_face"][i]
            barycentric = lineage["vertex_barycentric"][i]
            assert barycentric.sum() == pytest.approx(1, abs=1e-12)
            assert barycentric.min() >= -1e-12
            assert result[kind][i] == pytest.approx(barycentric @ original[faces[parent]], abs=1e-11)
    assert trimesh.Trimesh(result["basis"], triangles, process=False).volume == pytest.approx(0.26, abs=1e-12)
    repeated, repeated_faces, repeated_lineage = refine.mesh(keys, faces, max_edge=1.0)
    assert np.array_equal(result["basis"], repeated["basis"])
    assert np.array_equal(triangles, repeated_faces)
    assert np.array_equal(lineage["vertex_barycentric"], repeated_lineage["vertex_barycentric"])
