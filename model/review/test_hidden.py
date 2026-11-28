"""Seam: the eye gimbal inside Morty's Sculpt (#967), as model/review places it on the Mech's eyes: the gimbal frame
and every eye drive part (servos, horns, bars, links, yokes, cores, the bail), with each eye servo over its range, at
least a Shell's wall and its clearance inside his outer surface, in both Skeleton styles: read on the Sculpt git holds
(model/morty), so every run of the Model's tests holds it. And, as the head pans and tilts and the jaw opens, that far
from each region of his Skin that moves against the gimbal then: the regions are the private reference's painted
meshes, read through Blender (review.MORTY), so that half is one of the review's own checks, as test_review.py's on
the written file (`just review` sets NOGGIN_REVIEW; by hand `NOGGIN_REVIEW=1 pytest model/review/test_hidden.py` after
`just ours`), skips in CI, and nothing of the reference leaves the run. The caps and lids are the eyes' own surfaces,
seen through his eye openings, so they are left out of those; the lids, his skin's moving covers, stand proud of his
outer skin nowhere over their travel."""

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
from model import morty, review, skeleton, skin, stages

MARGIN = skin.WALL + gm.LID_CLEAR_MM  # a Shell's wall, and its least room to a part it does not sit on
VISIBLE = ("eyeball cap", "upper lid", "lower lid")  # seen through his eye openings, not hidden behind his Skin
HORNS = tuple(stages.eyes_sub().horns)  # the eyes'; a document's others move the gimbal against his Skin, or it past
FRAME = "gimbal frame:1"  # what the eye gimbal rides
STEPS = 11  # each servo's range, sampled
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
    out[f"r{{i}}"] = o["reference_region"]
np.savez({out!r}, **out)
print("review: done")
"""


def _parts(stage):
    """The eyes Sub-assembly's parts in `stage` but the caps and lids."""
    return [n for n in stages.eyes_sub().parts if n in stage.parts and not any(v in n for v in VISIBLE)]


def _points(mesh, step):
    """Points on the mesh no farther apart than `step`: each triangle's barycentric grid (trimesh's subdivide_to_size
    gives them too, several times slower on his sculpt)."""
    tri, out = mesh.triangles, []
    n = np.ceil(np.linalg.norm(tri - np.roll(tri, 1, axis=1), axis=2).max(axis=1) / step).clip(1).astype(int)
    for k in np.unique(n):
        i, j = np.meshgrid(np.arange(k + 1), np.arange(k + 1))
        w = np.stack([i, j, k - i - j], -1)[i + j <= k] / k
        out.append(np.einsum("pw,twc->tpc", w, tri[n == k]).reshape(-1, 3))
    return np.vstack(out)


def depth(mesh, part=None):
    """(points) -> mm each lies outside the closed mesh's outer surface (negative: inside; past FAR either way,
    FAR). His sculpt crosses itself (hair, lids, collar), so the room outside is flooded from a corner of his box
    through the PITCH voxels his surface does not cross: his outer surface is the part of it beside the flood, and a
    point in a voxel the flood reached, or one his outer surface crosses, is outside. The distance is to that surface's
    points, exact to their spacing; the voxels only sort inside from outside and skip the deep points. With `part`
    ((points) -> which), the distance is to those of the outer surface's points alone (the head's skin,
    model/review/test_nape.py); inside and outside stay the whole mesh's.
    shortcut: a groove narrower than about two voxels reads as filled, so a point just under its floor reads deeper
    than it is; halve PITCH (eight times the voxels) if a part ever lies under one (his cheeks and temples have none)."""
    v = _points(mesh, 0.4 * PITCH)  # within a quarter voxel of every point of the surface: no face-to-face leak
    lo = v.min(axis=0) - 2 * PITCH
    shape = np.floor((v.max(axis=0) + 2 * PITCH - lo) / PITCH).astype(int) + 1

    def cell(p):
        return tuple(np.floor((p - lo) / PITCH).astype(int).T)

    wall = np.zeros(shape, bool)
    wall[cell(v)] = True
    rooms, _ = ndimage.label(~wall)
    room = rooms == rooms[0, 0, 0]
    wall &= ndimage.binary_dilation(room, np.ones((3, 3, 3), bool))  # a surface inside him (his scalp) is inside
    deep = ndimage.distance_transform_edt(~(wall | room)) * PITCH  # mm inside, to a voxel
    outer = v[wall[cell(v)]]
    outer = cKDTree(outer if part is None else outer[part(outer)])

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
    # a point on the first ball's own surface where it runs through the second, 15 mm under the second's: his scalp
    # under his hair is such a surface, and the cranium tray and its boards stand across it (#1089)
    assert mm(np.array([(20.0, 0, 0), (19.0, 6.2, 0)])) == pytest.approx([-FAR, -FAR])


@pytest.fixture(scope="module")
def sculpt():
    """depth() of Morty's Sculpt as git holds it, placed on the Mech's eyes in the documents' world."""
    mesh = trimesh.load(os.path.join(stages.REPO, morty.SCULPT), process=False)
    return depth(mesh.apply_transform(review.placed()))


@pytest.fixture(scope="module")
def regions(tmp_path_factory):
    """{Motion region: its surface's points every mm} of Morty's reference, at rest in the documents' world."""
    if not (os.environ.get("NOGGIN_REVIEW") and os.path.isfile(review.MORTY) and shutil.which(skeleton.BLENDER)):
        pytest.skip("the review's check (NOGGIN_REVIEW, as just review sets it): needs the Morty reference and Blender")
    path = str(tmp_path_factory.mktemp("morty") / "reference.npz")
    held = review.lock(review.SLOT, wait=True)  # the laptop's one Blender slot, as test_review.py takes it
    try:
        review._blender(["--python-expr", EXPORT.format(blend=review.MORTY, out=path)])
    finally:
        held.close()
    try:
        with np.load(path) as z:
            meshes = [
                (str(z[f"r{i}"]), trimesh.Trimesh(z[f"v{i}"], z[f"f{i}"], process=False))
                for i in range(len(z.files) // 3)
            ]
    finally:
        os.remove(path)  # the reference stays where it is
    regions = {}
    for region, mesh in meshes:
        points = _points(mesh.apply_transform(review.placed()), 1.0)
        regions[region] = np.vstack([*([regions[region]] if region in regions else []), points])
    return regions


@functools.cache
def _cloud(stem):
    """Points on the part's mesh (just ours): its vertices and its surface every 1 mm."""
    mesh = trimesh.load(stages.stl(stem), force="mesh")
    return np.vstack([mesh.vertices, trimesh.sample.sample_surface_even(mesh, int(mesh.area), seed=0)[0]])


def _poses(stage):
    """The document at rest and each eye servo at STEPS points over its range: a yawed yoke's corner comes nearest his
    cheek short of the yaw's end."""
    yield "rest", {n: p.matrix for n, p in stage.parts.items()}
    for horn in HORNS:
        for deg in np.linspace(*stage.horns[horn].limits, STEPS):
            yield f"{horn} {deg:.0f}", stages.pose(stage, horn, deg).parts


@pytest.mark.model
@pytest.mark.parametrize("doc", list(g.MECH))
def test_the_eye_gimbal_hides_inside_mortys_sculpt(doc, sculpt):
    """#967: at rest and with each eye servo over its range, every point of the eye gimbal's frame and drives lies
    MARGIN inside Morty's outer surface; a part that comes nearer or pokes through is listed with its worst mm."""
    outside, stage, near = sculpt, stages.STAGES[doc], {}
    for pose, mats in _poses(stage):
        for n in _parts(stage):
            worst = float(outside(trimesh.transform_points(_cloud(stages.stem(stage.parts[n].file)), mats[n])).max())
            if worst > -MARGIN and worst > near.get(n, (-np.inf,))[0]:
                near[n] = (round(worst, 2), pose)
    assert near == {}


PROUD_MM3 = 0.5  # of a lid outside his outer skin: none (0.01 measured), but what two meshed surfaces misread


@pytest.mark.model
@pytest.mark.parametrize("side", "LR")
def test_no_lid_stands_proud_of_his_skin(side):
    """#967 (the skin keeps its shape): the lids' band's outer face is his eyeball's own surface, so over the lid
    servo's range neither lid has any volume outside his Sculpt's outer skin (the solid his Skin is cut from: its
    brows' pockets are no outside, which depth() takes them for), in an eye opening, where his dome is the skin, or
    past its rim; nor has the cap, 1.3 mm under his eye."""
    import manifold3d as m3

    from model.morty import shells

    whole, eye = shells.outside(), np.array(gm.EYE[side])  # the head's frame at rest is the gimbal's

    def solid(name):
        mesh = trimesh.load(stages.stl(name), force="mesh")
        return m3.Manifold(m3.Mesh(np.asarray(mesh.vertices + eye, np.float32), np.asarray(mesh.faces, np.uint32)))

    parts, proud = {k: solid(f"{side} {k}") for k in ("upper lid", "lower lid", "eyeball cap")}, {}
    for deg in np.linspace(gm.LID_EDGES[0] - gm.LID_REST, 0.0, 5):
        moved = gm.moved(float(deg), 0.0)
        for k, part in parts.items():
            out = (part.transform(moved[f"{side} {k}:1"][:3]) - whole).volume()
            if out > PROUD_MM3:
                proud[k, round(float(deg), 1)] = round(out, 1)
    assert proud == {}


@pytest.mark.parametrize("doc", list(g.MECH))
def test_no_region_of_his_skin_moving_against_the_eye_gimbal_comes_near_it(doc, regions):
    """#967, the head's articulation: over the pan's, the tilt's and the jaw's range, each region of his Skin that then
    moves against the eye gimbal (the fixed shoulders and torso under a turning head, the jaw's as it opens;
    review.CARRIERS) keeps MARGIN from every point of the frame and the drives. A seam that opens between two regions
    is the Skin's own (#850)."""
    stage, near = stages.STAGES[doc], {}
    rest = {n: p.matrix for n, p in stage.parts.items()}
    for horn in (h for h in stage.horns if h not in HORNS):
        for deg in np.linspace(*stage.horns[horn].limits, STEPS):
            mats = stages.pose(stage, horn, deg).parts
            for region, points in regions.items():
                carrier = review.CARRIERS[region]
                move = mats[carrier] @ np.linalg.inv(rest[carrier]) if carrier else np.eye(4)
                if np.allclose(move, mats[FRAME] @ np.linalg.inv(rest[FRAME]), atol=1e-9):
                    continue  # it rides with the gimbal here: the check at rest holds it
                surface = cKDTree(trimesh.transform_points(points, move))
                for n in _parts(stage):
                    cloud = trimesh.transform_points(_cloud(stages.stem(stage.parts[n].file)), mats[n])
                    mm = float(surface.query(cloud, distance_upper_bound=MARGIN)[0].min())
                    if mm < near.get((n, region), (MARGIN,))[0]:
                        near[n, region] = (round(mm, 2), f"{horn} {deg:.0f}")
    assert near == {}
