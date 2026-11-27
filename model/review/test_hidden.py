"""Seam: the eye gimbal inside the private Morty reference (#967), as model/review places him: the gimbal frame and every
eye drive part (servos, horns, bars, links, yokes, cores, the bail), with each eye servo at either end of its range, at
least a Shell's wall and its clearance inside his outer surface, in both Skeleton styles. The caps and lids are the
eyes' own surfaces, seen through his eye openings, so they are left out. One of the review's own checks, as
test_review.py's on the written file: `just review` runs it on the parts it just built (NOGGIN_REVIEW set), and by hand
it is `NOGGIN_REVIEW=1 pytest model/review/test_hidden.py` after `just ours`. It reads the reference through Blender
(review.MORTY), which CI does not have, so it skips there (and is not marked model: the Model shards would only skip
it), and nothing of the reference leaves the run."""

import functools
import os
import shutil

import numpy as np
import pytest
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

from model import geometry as g
from model import gimbal as gm
from model import review, skeleton, skin, stages

MARGIN = skin.WALL + gm.LID_CLEAR_MM  # a Shell's wall, and its least room to a part it does not sit on
VISIBLE = ("eyeball cap", "upper lid", "lower lid")  # seen through his eye openings, not hidden behind his Skin
HORNS = ("yaw horn", "pitch horn", "L lid horn", "R lid horn")  # the eyes Core's; the head's move the Skin with them
PITCH, FAR = 1.0, 6.0  # depth()'s voxel, and how far from his surface it measures, mm
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


def _points(mesh, step):
    """Points on the mesh no farther apart than `step`: each triangle's barycentric grid."""
    tri, out = mesh.triangles, []
    n = np.ceil(np.linalg.norm(tri - np.roll(tri, 1, axis=1), axis=2).max(axis=1) / step).clip(1).astype(int)
    for k in np.unique(n):
        i, j = np.meshgrid(np.arange(k + 1), np.arange(k + 1))
        w = np.stack([i, j, k - i - j], -1)[i + j <= k] / k
        out.append(np.einsum("pw,twc->tpc", w, tri[n == k]).reshape(-1, 3))
    return np.vstack(out)


def depth(mesh):
    """(points) -> mm each lies outside the closed mesh's outer surface (negative: inside; past FAR either way,
    FAR). His sculpt crosses itself (hair, lids, collar), so the room outside is flooded from a corner of his box
    through the PITCH voxels his surface does not cross: a point in a voxel the flood reached, or one his surface
    crosses, is outside, and his outer surface is the part of it beside the flood. The distance is to that surface's
    points, exact to their spacing; the voxels only sort inside from outside and skip the deep points."""
    v = _points(mesh, 0.4 * PITCH)  # within a quarter voxel of every point of the surface: no face-to-face leak
    lo = v.min(axis=0) - 2 * PITCH
    shape = np.floor((v.max(axis=0) + 2 * PITCH - lo) / PITCH).astype(int) + 1

    def cell(p):
        return tuple(np.floor((p - lo) / PITCH).astype(int).T)

    wall = np.zeros(shape, bool)
    wall[cell(v)] = True
    rooms, _ = ndimage.label(~wall)
    room = rooms == rooms[0, 0, 0]
    deep = ndimage.distance_transform_edt(~(wall | room)) * PITCH  # mm inside, to a voxel
    outer = cKDTree(v[ndimage.binary_dilation(room, np.ones((3, 3, 3), bool))[cell(v)]])

    def mm(points):
        inside = ((points > lo) & (points < lo + shape * PITCH)).all(axis=1)
        d = np.zeros(len(points))
        d[inside] = deep[cell(points[inside])]
        near = d < FAR  # the rest lie FAR or more inside
        exact = np.minimum(outer.query(points[near], distance_upper_bound=FAR)[0], FAR)
        d[near] = np.where(d[near] > 0, exact, -exact)
        return -np.minimum(d, FAR)

    return mm


def test_depth_reads_a_ball_through_a_ball_as_one_surface():
    """Two balls crossing, as his sculpt's meshes do: a point inside either is inside, by its distance to the outer
    surface alone (the part of each ball inside the other is not his surface), and a point outside is outside."""
    mesh = trimesh.util.concatenate(
        [trimesh.creation.icosphere(4, 20.0), trimesh.creation.icosphere(4, 20.0).apply_translation((25.0, 0, 0))]
    )
    mm = depth(mesh)
    points = np.array([(0.0, 0, 0), (12.5, 0, 0), (18.0, 0, 0), (0, 18.0, 0), (0, 21.0, 0), (60.0, 0, 0)])
    # the middle of the lens is 7.5 mm inside each ball, and 15.6 mm from where the two meet, the outer surface there
    assert mm(points) == pytest.approx([-FAR, -FAR, -FAR, -2.0, 1.0, FAR], abs=0.15)


@pytest.fixture(scope="module")
def outside(tmp_path_factory):
    """depth() of Morty's reference at rest, in the documents' world."""
    if not (os.environ.get("NOGGIN_REVIEW") and os.path.isfile(review.MORTY) and shutil.which(skeleton.BLENDER)):
        pytest.skip("the review's check (NOGGIN_REVIEW, as just review sets it): needs the Morty reference and Blender")
    path = str(tmp_path_factory.mktemp("morty") / "reference.npz")
    held = review.lock(review.SLOT, wait=True)  # the laptop's one Blender slot, as test_review.py takes it
    try:
        review._blender(["--python-expr", EXPORT.format(blend=review.MORTY, out=path)])
    finally:
        held.close()
    with np.load(path) as z:
        meshes = [trimesh.Trimesh(z[f"v{i}"], z[f"f{i}"], process=False) for i in range(len(z.files) // 2)]
    os.remove(path)  # the reference stays where it is
    return depth(trimesh.util.concatenate(meshes).apply_transform(review.placed()))


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
