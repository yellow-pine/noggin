"""Morty's skin as the bones' and the mechanism's limit (#893's directive of 2026-11-27, #874): the sculpt's outer
surface in the head's frame (mm, the eyes' middle at the origin), read as a depth: how far a point lies under it,
negative outside. A bone or a part stays ROOM under it: the printed Skin's wall, grown inward, and its clearance.

Skin(mesh) is the measure: the mesh's surface sampled, the outside flooded in from a corner of a GRID mm grid so that
sheets the mesh holds inside itself (the sculpt's hair has an under side inside his head) are no skin, then each grid
point within BAND of the skin given its exact distance to the nearest sample (deeper ones a voxel-rounded one), read
between grid points linearly. morty() is the sculpt's, built once and kept in model/build."""

import fcntl
import functools
import hashlib
import os

import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

from model import morty as morty_
from model import skin, stages

ROOM = skin.WALL + 0.5  # under Morty's surface: the Skin's wall and its clearance (Cansin, 2026-11-27)
GRID, BAND = 1.0, 16.0  # the grid's pitch; how deep the exact distances reach, mm
DENSITY = 8.0  # surface samples a mm2: about 0.35 mm apart, so a depth is good to 0.2 mm
FLOOR = -200.0  # the sculpt is read down to here in the head's frame: under C7 and the shoulders' tops


class Skin:
    """A closed mesh's outer surface, or one cut open at z `floor` (closed there, read above it)."""

    def __init__(self, mesh, floor=None):
        points, face = trimesh.sample.sample_surface(mesh, int(mesh.area * DENSITY), seed=0)
        normals = mesh.face_normals[face]
        self.lo = np.floor(points.min(0)) - 4 * GRID
        if floor is not None:
            self.lo[2] = floor - 4 * GRID
        shape = np.ceil((points.max(0) + 4 * GRID - self.lo) / GRID).astype(int) + 1
        at = np.round((points - self.lo) / GRID).astype(int)
        seen = (at[:, 2] >= 0) if floor is not None else np.ones(len(at), bool)
        points, normals, at = points[seen], normals[seen], at[seen]
        wall = np.zeros(shape, bool)
        wall[tuple(at.T)] = True
        wall = ndimage.binary_dilation(wall)  # a voxel the surface only clips may hold no sample: no leak through it
        if floor is not None:
            wall[:, :, :5] = True  # the cut, closed
        label, _ = ndimage.label(~wall)
        outside = label == label[0, 0, -1]
        outer = ndimage.binary_dilation(outside, np.ones((3, 3, 3), bool), iterations=2)[tuple(at.T)]
        points, normals, at = points[outer], normals[outer], at[outer]
        surface = np.zeros(shape, bool)
        surface[tuple(at.T)] = True
        far = ndimage.distance_transform_edt(~surface) * GRID
        self.grid = np.where(outside, -far, far).astype(np.float32)
        band = np.argwhere(far < BAND)
        q = band * GRID + self.lo
        near, j = cKDTree(points).query(q, workers=-1)
        sign = np.where(outside[tuple(band.T)], -1.0, 1.0)
        close = near < 2.5 * GRID  # beside the skin its own normal says which side
        sign[close] = np.where(((q[close] - points[j[close]]) * normals[j[close]]).sum(1) < 0, 1.0, -1.0)
        self.grid[tuple(band.T)] = sign * near
        self.floor = floor

    def depth(self, points):
        """Each point's depth under the skin, mm (negative outside it)."""
        points = np.asarray(points, float)
        if self.floor is not None and len(points) and points[:, 2].min() < self.floor:
            raise ValueError(f"a point lies under the skin's cut at z {self.floor}")
        return ndimage.map_coordinates(self.grid, ((points - self.lo) / GRID).T, order=1, mode="nearest")

    def inward(self, points, h=0.5):
        """The direction each point's depth grows fastest in (a unit vector; zero where the depth is level)."""
        points = np.asarray(points, float)
        g = np.stack([self.depth(points + h * e) - self.depth(points - h * e) for e in np.eye(3)], 1)
        return g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)


def sculpt():
    """(The Sculpt in the head's frame, its file): model/morty's adopted copy (docs/adr/0027) where model/morty
    places it (placed(): his eyes on the Mech's, scaled to their spacing), which his Shells are cut from too. When
    his eye centres or the Mech's move, the scene is rewarped (`just rewarp`): the Warp is fitted to him where he
    stands."""
    path = os.path.join(stages.REPO, morty_.SCULPT)
    mesh = trimesh.load(path, force="mesh").apply_transform(morty_.placed())
    mesh.apply_translation(-np.array(stages.DOCS[morty_.DOC]["eyes"][0]))
    return mesh, path


@functools.cache
def morty():
    """Morty's Skin: the sculpt's, above FLOOR. Built once a sculpt and a placement (about 30 s on the Mac, minutes
    on CI's four shared cores: a test takes it in a fixture, which CI's 60 s a test leaves out) and kept in
    model/build: where he stands is in the key, so his eye centres moving never reads an older grid."""
    mesh, path = sculpt()
    with open(path, "rb") as f:
        numbers = f"{GRID}{BAND}{DENSITY}{FLOOR}".encode() + morty_.placed().tobytes()
        key = hashlib.sha256(f.read() + numbers).hexdigest()[:16]
    cache = os.path.join(stages.REPO, "model", "build", f"envelope-{key}.npz")
    out = Skin.__new__(Skin)
    out.floor = FLOOR
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    with open(cache + ".lock", "w") as lock:
        # one build a machine (2.5 GB, 144 s of CPU): a second process, a test run's other worker, waits and reads it
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not os.path.exists(cache):
            keep = (mesh.vertices[mesh.faces][:, :, 2] > FLOOR - 2 * GRID).any(1)
            built = Skin(trimesh.Trimesh(mesh.vertices, mesh.faces[keep]), floor=FLOOR)
            whole = cache.removesuffix(".npz") + ".tmp.npz"  # renamed once written: a killed build leaves no half
            np.savez_compressed(whole, grid=built.grid, lo=built.lo)
            os.replace(whole, cache)
        with np.load(cache) as z:
            out.grid, out.lo = z["grid"], z["lo"]
    return out
