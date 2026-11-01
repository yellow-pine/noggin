"""Seam: `python -m model.convex_parts` (CI's cold convex cache), on a box with CoACD stubbed (no decomposition here)."""

import trimesh

from model import convex_parts, mjcf


def test_a_part_is_stale_until_its_pieces_are_cut(tmp_path, monkeypatch):
    monkeypatch.setattr(mjcf, "CONVEX", str(tmp_path / "convex"))
    box = trimesh.creation.box((10, 10, 10))
    box.export(tmp_path / "box.stl")
    meshes = {"box": (str(tmp_path / "box.stl"), None)}
    assert convex_parts.stale(meshes) == ["box"]
    assert not (tmp_path / "convex").exists()  # asking cuts nothing
    monkeypatch.setattr(mjcf.coacd, "run_coacd", lambda mesh, **_: [(box.vertices, box.faces)])
    mjcf.convex(*meshes["box"])
    assert convex_parts.stale(meshes) == []
    box.apply_scale(2).export(tmp_path / "box.stl")
    assert convex_parts.stale(meshes) == ["box"]


def test_parts_holds_every_documents_meshes():
    meshes = convex_parts.parts()
    assert {"upper lid", "servo", "base plate"} <= set(meshes)
    assert meshes["servo"][1]  # its leads clipped, as model/mjcf.py's spec() cuts it
