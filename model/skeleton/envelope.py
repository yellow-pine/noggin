"""Morty's skin as the bones' and the mechanism's limit (#893's directive of 2026-11-27, #874): the sculpt's outer
surface in the head's frame (mm, the eyes' middle at the origin), read as a depth: how far a point lies under it,
negative outside. A bone or a part stays ROOM under it: the printed Skin's wall, grown inward, and its clearance.

Skin(mesh) is the measure: the mesh's surface sampled, the outside flooded in from a corner of a GRID mm grid so that
sheets the mesh holds inside itself (the sculpt's hair has an under side inside his head) are no skin, then each grid
point within BAND of the skin given its exact distance to the nearest sample (deeper ones a voxel-rounded one), read
between grid points linearly. morty() is the sculpt's, built once and kept in model/build."""

import functools
import hashlib
import os

import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

from model import gimbal, skin, stages

ROOM = skin.WALL + 0.5  # under Morty's surface: the Skin's wall and its clearance (Cansin, 2026-11-27)
GRID, BAND = 1.0, 16.0  # the grid's pitch; how deep the exact distances reach, mm
DENSITY = 8.0  # surface samples a mm2: about 0.35 mm apart, so a depth is good to 0.2 mm
FLOOR = -200.0  # the sculpt is read down to here in the head's frame: under C7 and the shoulders' tops
# the sculpt's own eyeballs' centres in today's head frame: a ball fitted to each eye dome in 3D (#967's measure, its
# comment 7209215753: radius 37.0, rms 0.48 mm), 73.33 mm apart. The Mech's eyes (gimbal.EYE, 72.7 mm apart from
# #872's rougher measure) move onto them in #967 (Cansin, 2026-11-27); the orbits, the lids' shell and the belt are
# fitted to them already, and read gimbal.EYE again once it is these
EYES = {"L": (37.14, -1.39, 1.72), "R": (-36.20, -1.39, 1.72)}
COMMITTED = os.path.join(stages.REPO, "model", "morty", "sculpt.ply")  # in the sculpt's own frame, mm (docs/adr/0027)


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


def sculpt_file():
    """The sculpt's file: the copy #850 commits (COMMITTED) or, until it lands, the local original beside the
    review's reference (docs/references in the main checkout)."""
    from model import review

    return COMMITTED if os.path.exists(COMMITTED) else os.path.join(os.path.dirname(review.MORTY), "morty-fixed.stl")


def sculpt():
    """(The Morty sculpt in the head's frame, its file): ChelsCCT's, CC BY 4.0, its eyes' middle on the Mech's, scaled
    to their spacing, as model/review places it."""
    from model import review  # its eye centres are one source

    path = sculpt_file()
    mesh = trimesh.load(path, force="mesh")
    eyes = np.array([review.MORTY_EYES[s] for s in "LR"])
    mesh.vertices = (mesh.vertices - eyes.mean(0)) * (gimbal.SPACING / np.linalg.norm(eyes[0] - eyes[1]))
    return mesh, path


@functools.cache
def morty():
    """Morty's Skin: the sculpt's, above FLOOR. Built once a sculpt (about 30 s) and kept in model/build."""
    mesh, path = sculpt()
    with open(path, "rb") as f:
        key = hashlib.sha256(f.read() + f"{GRID}{BAND}{DENSITY}{FLOOR}{gimbal.SPACING}".encode()).hexdigest()[:16]
    cache = os.path.join(stages.REPO, "model", "build", f"envelope-{key}.npz")
    out = Skin.__new__(Skin)
    out.floor = FLOOR
    if os.path.exists(cache):
        with np.load(cache) as z:
            out.grid, out.lo = z["grid"], z["lo"]
        return out
    keep = (mesh.vertices[mesh.faces][:, :, 2] > FLOOR - 2 * GRID).any(1)
    built = Skin(trimesh.Trimesh(mesh.vertices, mesh.faces[keep]), floor=FLOOR)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    np.savez_compressed(cache, grid=built.grid, lo=built.lo)
    return built
