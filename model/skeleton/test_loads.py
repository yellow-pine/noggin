"""Finished Bone load manifest consumed by the mechanical carrier model: actual mesh, head-local units."""

import json

import numpy as np
import pytest
import trimesh

from model.skeleton import loads


def test_a_finished_bones_load_has_its_physical_mass_centroid_and_com_inertia(tmp_path):
    mesh = trimesh.creation.box(extents=(10, 20, 30))
    mesh.apply_translation((4, 5, 6))
    stl, manifest = tmp_path / "calvaria.stl", tmp_path / "loads.json"
    mesh.export(stl)
    loads.write(
        {"calvaria": {"file": str(stl), "carrier": "head", "density_g_cm3": 1.28}},
        "known finished cuboid",
        manifest,
    )
    result = json.loads(manifest.read_text())
    assert result["source"] == "known finished cuboid"
    bone = result["parts"]["calvaria"]
    assert bone["carrier"] == "head"
    assert bone["mass_g"] == pytest.approx(7.68)
    assert bone["com_mm"] == pytest.approx((4, 5, 6))
    assert np.asarray(bone["inertia_g_mm2"]) == pytest.approx(np.diag((832, 640, 320)))
