"""Seam: the eye gimbal inside the private Morty reference (#967), as model/review places him: the gimbal frame and every
eye drive part (servos, horns, bars, links, yokes, cores, the bail), with each eye servo at either end of its range, at
least a Shell's wall and its clearance inside his outer surface, in both Skeleton styles. The caps and lids are the
eyes' own surfaces, seen through his eye openings, so they are left out. Local only: it reads the reference through
Blender (review.MORTY); CI has neither, and nothing of the reference leaves the run."""

import functools
import os
import shutil

import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

from model import geometry as g
from model import gimbal as gm
from model import review, skeleton, skin, stages

MARGIN = skin.WALL + gm.LID_CLEAR_MM  # a Shell's wall, and its least room to a part it does not sit on
VISIBLE = ("eyeball cap", "upper lid", "lower lid")  # seen through his eye openings, not hidden behind his Skin
HORNS = ("yaw horn", "pitch horn", "L lid horn", "R lid horn")  # the eyes Core's; the head's move the Skin with them
EXPORT = """
import bpy, numpy as np
with bpy.data.libraries.load({blend!r}) as (src, dst):
    dst.collections = ["Morty reference"]
bpy.context.scene.collection.children.link(dst.collections[0])
bpy.context.view_layer.update()
dg, out = bpy.context.evaluated_depsgraph_get(), {{}}
for i, o in enumerate(o for o in dst.collections[0].all_objects if o.type == "MESH"):
    me = o.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    out[f"v{{i}}"] = np.array([o.matrix_world @ v.co for v in me.vertices])
    out[f"f{{i}}"] = np.array([t.vertices[:] for t in me.loop_triangles])
np.savez({out!r}, **out)
print("review: done")
"""


def _parts(stage):
    """The eyes Sub-assembly's parts in `stage` but the caps and lids."""
    return [n for n in stages.eyes_sub().parts if n in stage.parts and not any(v in n for v in VISIBLE)]


@pytest.fixture(scope="module")
def outside(tmp_path_factory):
    """(points) -> mm each lies outside Morty's outer surface (negative: inside), at rest, in the documents' world."""
    if not os.path.isfile(review.MORTY) or not shutil.which(skeleton.BLENDER):
        pytest.skip("no local Morty reference (review.MORTY) or no Blender")
    import vtk  # here: cadquery's OCP brings it; only this local check casts rays
    from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray

    path = str(tmp_path_factory.mktemp("morty") / "reference.npz")
    # no review.SLOT here: the model tests run under that same heavy lock (just test), which a second flock would wait on
    review._blender(["--python-expr", EXPORT.format(blend=review.MORTY, out=path)])
    with np.load(path) as z:
        meshes = [trimesh.Trimesh(z[f"v{i}"], z[f"f{i}"], process=False) for i in range(len(z.files) // 2)]
    os.remove(path)  # the reference stays where it is
    mesh = trimesh.util.concatenate(meshes).apply_transform(review.placed())
    mesh.merge_vertices()
    data, pts, cells = vtk.vtkPolyData(), vtk.vtkPoints(), vtk.vtkCellArray()
    pts.SetData(numpy_to_vtk(mesh.vertices.astype(float), deep=True))
    tri = np.c_[np.full(len(mesh.faces), 3), mesh.faces].astype(np.int64).ravel()
    cells.SetCells(len(mesh.faces), numpy_to_vtkIdTypeArray(tri, deep=True))
    data.SetPoints(pts)
    data.SetPolys(cells)
    tree = vtk.vtkOBBTree()
    tree.SetDataSet(data)
    tree.BuildLocator()
    rays = np.random.default_rng(0).normal(size=(48, 3))
    rays *= 2000.0 / np.linalg.norm(rays, axis=1)[:, None]
    hits = vtk.vtkPoints()

    def seen(p):
        """Whether 3 of the rays from p leave without meeting him: outside a surface about half do; in a void (under
        his hair, where his meshes overlap) none."""
        free = 0
        for r in rays:
            tree.IntersectWithLine(p, p + r, hits, None)
            free += hits.GetNumberOfPoints() == 0
            if free == 3:
                return True
        return False

    # his outer surface: the faces seen from just outside them
    outer = [i for i, p in enumerate(mesh.triangles_center + 0.3 * mesh.face_normals) if seen(p)]
    surface, faces = trimesh.sample.sample_surface_even(mesh.submesh([outer], append=True), 600000, seed=0)
    normals, near = mesh.face_normals[outer][faces], cKDTree(surface)

    def mm(points):
        d, i = near.query(points)
        return np.where(np.einsum("ij,ij->i", points - surface[i], normals[i]) > 0, d, -d)

    return mm


@functools.cache
def _cloud(stem):
    """Points on the part's mesh (just ours): its vertices and its surface every 1 mm."""
    mesh = trimesh.load(stages.stl(stem), force="mesh")
    return np.vstack([mesh.vertices, trimesh.sample.sample_surface_even(mesh, int(mesh.area), seed=0)[0]])


def _poses(stage):
    yield "rest", {n: p.matrix for n, p in stage.parts.items()}
    for horn in HORNS:
        for deg in stage.horns[horn].limits:
            yield f"{horn} {deg:.0f}", stages.pose(stage, horn, deg).parts


@pytest.mark.model
@pytest.mark.parametrize("doc", list(g.MECH))
def test_the_eye_gimbal_hides_inside_mortys_reference(doc, outside):
    """#967: at rest and with each eye servo at either end, every point of the eye gimbal's frame and drives lies
    MARGIN inside Morty's outer surface; a part that comes nearer or pokes through is listed with its worst mm."""
    stage, near = stages.STAGES[doc], {}
    for pose, mats in _poses(stage):
        for n in _parts(stage):
            worst = float(outside(trimesh.transform_points(_cloud(stages.stem(stage.parts[n].file)), mats[n])).max())
            if worst > -MARGIN and worst > near.get(n, (-np.inf,))[0]:
                near[n] = (round(worst, 2), pose)
    assert near == {}
