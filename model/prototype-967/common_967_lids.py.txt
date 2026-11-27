"""Shared: the sculpt in the head (eyes sub-assembly) frame, from the Blender export (regions) or the raw STL."""
import os, sys
import numpy as np, trimesh
sys.path.insert(0, os.getcwd())
from model import review, stages, gimbal as gm
from model.review import test_hidden as th

NPZ = "/tmp/967-lids/reference-head.npz"
STL = os.path.join(os.path.dirname(review.MORTY), "morty-fixed.stl")

def head_frame():
    eyes = stages.align(*stages.DOCS[review.DOC]["eyes"])
    return np.linalg.inv(eyes) @ review.placed()

def meshes(raw=False):
    if raw or not os.path.isfile(NPZ):
        m = trimesh.load(STL, force="mesh", process=False)
        m.apply_transform(head_frame())
        return [("raw", m)]
    z = np.load(NPZ)
    return [(str(z[f"r{i}"]), trimesh.Trimesh(z[f"v{i}"], z[f"f{i}"], process=False)) for i in range(len(z.files) // 3)]

def unit(a, phi, s=1):
    """Direction about an eye centre: `a` deg along the lids' axis (positive outward; s 1 for L, -1 for R), `phi` deg
    about that axis from forward toward up (the lid's own angle)."""
    a, phi = np.radians(a), np.radians(phi)
    return np.stack([s * np.sin(a), -np.cos(a) * np.cos(phi), np.cos(a) * np.sin(phi)], -1)


def points_normals(mesh, step):
    """th._points with each point's triangle normal."""
    tri, out, nor = mesh.triangles, [], []
    fn = mesh.face_normals
    n = np.ceil(np.linalg.norm(tri - np.roll(tri, 1, axis=1), axis=2).max(axis=1) / step).clip(1).astype(int)
    for k in np.unique(n):
        i, j = np.meshgrid(np.arange(k + 1), np.arange(k + 1))
        w = np.stack([i, j, k - i - j], -1)[i + j <= k] / k
        p = np.einsum("pw,twc->tpc", w, tri[n == k])
        out.append(p.reshape(-1, 3))
        nor.append(np.repeat(fn[n == k], p.shape[1], axis=0))
    return np.vstack(out), np.vstack(nor)


def outer_depth(mesh, pitch=1.0, far=8.0):
    """As test_hidden.depth (mm outside the outer surface, negative inside, capped at `far`), but a surface inside the
    sculpt (never reached by the flood) is inside, and a point in a voxel the outer surface crosses takes its side
    from the nearest outer point's normal, so the reading is exact to the points' spacing on both sides."""
    from scipy import ndimage
    from scipy.spatial import cKDTree
    v, nrm = points_normals(mesh, 0.4 * pitch)
    lo = v.min(axis=0) - 2 * pitch
    shape = np.floor((v.max(axis=0) + 2 * pitch - lo) / pitch).astype(int) + 1
    cell = lambda p: tuple(np.floor((p - lo) / pitch).astype(int).T)
    wall = np.zeros(shape, bool)
    wall[cell(v)] = True
    rooms, _ = ndimage.label(~wall)
    room = rooms == rooms[0, 0, 0]
    near_room = ndimage.binary_dilation(room, np.ones((3, 3, 3), bool))
    keep = near_room[cell(v)]
    outer, onrm = cKDTree(v[keep]), nrm[keep]
    edge = wall & near_room  # the outer surface's own voxels

    def mm(points):
        inside_box = ((points > lo) & (points < lo + shape * pitch)).all(axis=1)
        out = np.full(len(points), far)
        idx = np.flatnonzero(inside_box)
        cc = cell(points[idx])
        dist, j = outer.query(points[idx], distance_upper_bound=far)
        dist = np.minimum(dist, far)
        j = j.clip(0, len(onrm) - 1)
        side = np.einsum("ij,ij->i", points[idx] - outer.data[j], onrm[j]) > 0
        sign = np.where(room[cc], 1.0, np.where(edge[cc], np.where(side, 1.0, -1.0), -1.0))
        out[idx] = sign * dist
        return out

    mm.outer = outer
    return mm
