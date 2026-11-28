"""Seam: `python -m model.convex_parts` (CI's cold convex cache), on a box with CoACD stubbed (no decomposition here);
and the cut itself (model/mjcf.py convex), on two boxes a hair into each other and on every part physics runs on
(#1036)."""

import numpy as np
import pytest
import trimesh

from model import convex_parts, mjcf

# How far a corner of a part's pieces may stand outside its mesh, the gates' own tolerance (model/test_mjcf.py
# PENETRATION_MM). A piece is the convex hull of its corners: with every corner on the mesh it bridges the mesh's
# hollows, as far as CoACD's threshold lets it (mjcf.COACD, FINE_MM), and stands proud of it nowhere else. CoACD's own
# snapping moves a corner up to 0.012 mm (the cervical carrier, 129 mm long); rebuilt from voxels, the pieces stood 0.6
# to 0.8 mm out all round
PROUD_MM = 0.05


def proud(mesh, points):
    """mm each point stands outside the mesh, 2 at most: 0 inside it, and within PROUD_MM of its surface."""
    tri = mesh.triangles
    lo, hi = tri.min(axis=1), tri.max(axis=1)

    def off(p, reach):
        """mm from the point to the surface, `reach` at most: by the triangles whose box comes that near it."""
        near = tri[((p >= lo - reach) & (p <= hi + reach)).all(axis=1)]
        if not len(near):
            return reach
        return min(
            reach, np.linalg.norm(trimesh.triangles.closest_point(near, np.tile(p, (len(near), 1))) - p, axis=1).min()
        )

    out = np.zeros(len(points))
    for i, p in enumerate(points):
        if off(p, 2 * PROUD_MM) <= PROUD_MM:
            continue
        # how often the surface wraps the point, by its triangles' solid angles (van Oosterom and Strackee): 0 outside,
        # 1 or more inside, also where the mesh's triangles cross (Bones joined), which a ray's parity reads as outside
        a, b, c = (tri - p).transpose(1, 0, 2)
        la, lb, lc = (np.linalg.norm(x, axis=1) for x in (a, b, c))
        den = la * lb * lc + (a * b).sum(axis=1) * lc + (b * c).sum(axis=1) * la + (c * a).sum(axis=1) * lb
        if np.arctan2(np.einsum("ij,ij->i", a, np.cross(b, c)), den).sum() < np.pi:  # wrapped less than half a turn
            out[i] = off(p, 2.0)
    return out


def corners(pieces):
    return np.unique(np.vstack([trimesh.load(p, force="mesh").vertices for p in pieces]), axis=0)


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


def test_parts_holds_the_meshes_physics_runs_on():
    """#809: the mechanical documents' parts alone; the Bones collide nowhere."""
    meshes = convex_parts.parts()
    assert {"yaw yoke mechanical", "servo", "torso mechanical"} <= set(meshes)
    assert "yaw yoke" not in meshes and "torso" not in meshes
    assert meshes["servo"][1]  # its leads clipped, as model/mjcf.py's spec() cuts it


def test_proud_reads_a_point_outside_the_mesh_and_none_inside_it():
    box = trimesh.creation.box((10, 10, 10))
    points = np.array([(0, 0, 0), (0, 0, 4.98), (0, 0, 5.03), (0, 0, 6), (6, 6, 5), (0, 0, 9)], float)
    assert proud(box, points) == pytest.approx([0, 0, 0, 1, 2**0.5, 2])


def test_a_mesh_whose_triangles_cross_is_cut_as_it_is(tmp_path, monkeypatch):
    """#1036: CoACD took such a mesh (two Bones joined, their triangles 0.01 mm into each other) for no manifold and
    rebuilt it from voxels, each piece 0.55 of a voxel fat all round (0.22 mm on these 40 mm), which read overlaps where
    the exact solids clear."""
    monkeypatch.setattr(mjcf, "CONVEX", str(tmp_path / "convex"))
    boxes = [[(0, -5, -5), (20, 5, 5)], [(19.99, -4, -4), (40, 4, 4)]]
    joined = trimesh.util.concatenate([trimesh.creation.box(bounds=b) for b in boxes])
    joined.export(tmp_path / "joined.stl")
    pieces = mjcf.convex(str(tmp_path / "joined.stl"))
    assert proud(joined, corners(pieces)).max() <= PROUD_MM
    assert sum(trimesh.load(p).volume for p in pieces) == pytest.approx(joined.volume, rel=0.01)


def test_a_seam_one_side_splits_a_hair_from_its_end_is_closed_for_the_cut(tmp_path):
    """#1036: on macOS OCCT meshed the gimbal frame's jaw lugs so, one side of a 2 mm seam split 0.006 mm from its end:
    6 open edges, which CoACD took for no manifold."""
    box = trimesh.creation.box((10, 10, 10))
    a, b, c = box.faces[0]
    hair = box.vertices[a] + (box.vertices[b] - box.vertices[a]) * 6e-4 + box.face_normals[0] * 5e-5
    split = trimesh.Trimesh([*box.vertices, hair], [*box.faces[1:], (a, 8, c), (8, b, c)], process=False)
    split.export(tmp_path / "split.stl")
    assert not trimesh.load(tmp_path / "split.stl", force="mesh").is_watertight
    assert mjcf._mesh(str(tmp_path / "split.stl"), None).is_volume


@pytest.mark.model
@pytest.mark.parametrize("part", sorted(convex_parts.parts()))
def test_the_mesh_the_cut_takes_is_closed(part):
    """#1036: CoACD cuts a mesh as it is (mjcf.COACD), so each is a closed solid."""
    assert mjcf._mesh(*convex_parts.parts()[part]).is_volume


@pytest.mark.model
@pytest.mark.parametrize("part", sorted(convex_parts.parts()))
def test_no_corner_of_a_parts_pieces_stands_proud_of_its_mesh(part):
    """#1036: fat pieces tripped the sim's clearance gates on pairs whose exact solids clear (#975, #1029, #1034)."""
    file, clip = convex_parts.parts()[part]
    assert proud(mjcf._mesh(file, clip), corners(mjcf.convex(file, clip))).max() <= PROUD_MM
