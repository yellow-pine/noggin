"""The realistic Skeleton's skull (#838): 3Demon's cranium and mandible (model/skull/3demon, CC BY-SA 4.0) and Isopropyl
Alcohol's atlas and axis (model/skull/atlas-axis, CC BY-NC-SA 4.0), each adaptation under its source's licence (its
folder's LICENSE.md; docs/adr/0023). Placed in the head's frame: the skull scaled to the head's height, its orbits on
the eyes, sunk SUNK behind the caps; the vertebrae scaled with it, their canal on the pan axis, the atlas under the
head's tilt lugs. Then carved for the mechanism: voxelised at PITCH, the cranium shelled to WALL, the orbits opened round
the lids, every part that moves against the bone (over each horn's range) or rides with it cut out CLEAR_MM round, and
remeshed smooth for printing. Mesh parts, not CadQuery: model/ours.py writes them after the rest, from their STLs."""

import os

import numpy as np
import trimesh
from scipy import ndimage
from skimage.measure import marching_cubes

from model import geometry as g
from model import gimbal as gm
from model import neck as nk
from model import stages

SOURCES = os.path.join(stages.REPO, "model", "skull")
CRANIUM, MANDIBLE = "model/skull/3demon/cranium.stl", "model/skull/3demon/mandible.stl"
ATLAS, AXIS = "model/skull/atlas-axis/atlas.stl", "model/skull/atlas-axis/axis.stl"
# the source skull's orbits, in its units turned to the head's axes (measured on its front depth map, #838's prototype;
# inferred): their centres' |x| and z, and the plane of their rims (y); the caps stand SUNK proud of that plane
ORBIT, SUNK = (30.5, -154.4, 12.45), 7.0
ATLAS_MM = 78.0 * 0.83  # the atlas's width in life, at the skull model's scale of life (its size: 0.83)
PITCH, CLEAR_MM, WALL = 0.8, 1.6, 4.0  # the voxels; the room round every part (Grid.solid's voxel in it); the shell
HEIGHT_SPARE = 2.0  # the skull this much under the head gate's height: its remesh grows it a little
KEEP = 0.02  # a piece carving leaves, of the bone's largest, under which it is dropped
REACH = 16.0  # the orbits opened round each eye to its lids' outer radius, back to where their spokes reach
DOC = "next-mech-back"  # the realistic document the bones are carved for


def _source(path, turn=True):
    """A source mesh in the head's axes: the skull's front +z and up +y turned to -y forward and z up; the vertebrae's
    already z up (turn False)."""
    m = trimesh.load(os.path.join(stages.REPO, path), force="mesh")
    if turn:
        m.vertices = np.c_[m.vertices[:, 0], -m.vertices[:, 2], m.vertices[:, 1]]
    return m


def placed():
    """{bone: its mesh in the head's frame, mm} before carving: the skull scaled to gimbal.HEAD_MM's height from the
    mandible's chin to the cranium's top, its orbits' centres level with the eyes and their rims SUNK behind the caps'
    fronts; the atlas and axis as their source sets them together, at the skull's scale, the dens forward, the atlas's
    canal on the pan axis and its top under the head's tilt lugs, below what the head sweeps as it tilts (#838: the
    gimbal frame's plate and the head mount at the skull's base, where the atlas is in life)."""
    cranium, mandible = _source(CRANIUM), _source(MANDIBLE)
    scale = (gm.HEAD_MM[2] - HEIGHT_SPARE) / (cranium.vertices[:, 2].max() - mandible.vertices[:, 2].min())
    shift = np.array([0.0, -gm.CAP_R + SUNK - ORBIT[1] * scale, -ORBIT[2] * scale])
    for m in (cranium, mandible):
        m.vertices = m.vertices * scale + shift
    atlas, axis = _source(ATLAS, False), _source(AXIS, False)
    k = ATLAS_MM * scale / np.ptp(atlas.vertices[:, 0])
    dens = axis.vertices[axis.vertices[:, 2] > axis.vertices[:, 2].max() - 0.3][:, 1].mean()
    flip = 1.0 if dens < axis.vertices[:, 1].mean() else -1.0  # the dens forward: a half turn about z
    for m in (atlas, axis):
        m.vertices = m.vertices * k * np.array([flip, flip, 1.0])
    canal = _canal(atlas)
    y, z = nk.AXIS
    top = z - nk.BOSS_R - CLEAR_MM - 1.0  # under the head's tilt lugs, clear of the head's sweep over it
    move = np.array([-canal[0], y - canal[1], top - atlas.vertices[:, 2].max()])
    for m in (atlas, axis):
        m.vertices = m.vertices + move
    return {"next skull": cranium, "next mandible": mandible, "next atlas": atlas, "next axis": axis}


def _canal(atlas, b=0.5):
    """(x, y) of the atlas's vertebral canal: the largest hole in its plan view (its surface sampled, b mm bins)."""
    p = trimesh.sample.sample_surface(atlas, int(atlas.area / b**2 * 4), seed=0)[0][:, :2]
    lo = p.min(axis=0)
    ij = np.floor((p - lo) / b).astype(int)
    occ = np.zeros(ij.max(axis=0) + 1, bool)
    occ[ij[:, 0], ij[:, 1]] = True
    occ = ndimage.binary_closing(occ, iterations=2)
    holes = ndimage.binary_fill_holes(occ) & ~occ
    label, n = ndimage.label(holes)
    biggest = np.argmax(ndimage.sum(holes, label, range(1, n + 1))) + 1
    return np.argwhere(label == biggest).mean(axis=0) * b + lo


def surface(mesh):
    """Points on `mesh`'s surface, a few a voxel: its vertices and samples."""
    return np.vstack(
        [mesh.vertices, trimesh.sample.sample_surface(mesh, int(mesh.area / PITCH**2 * 4) + 64, seed=0)[0]]
    )


class Grid:
    """A voxel grid over a box (lo, hi), PITCH a side."""

    def __init__(self, lo, hi):
        self.lo = np.asarray(lo, float) - 3 * PITCH
        self.shape = tuple(np.ceil((np.asarray(hi, float) + 3 * PITCH - self.lo) / PITCH).astype(int) + 1)

    def solid(self, points, at=None):
        """The voxels inside the closed surface `points` sample (surface(); moved by the 4x4 `at`), grown a voxel so
        it closes, and filled."""
        if at is not None:
            points = trimesh.transform_points(points, at)
        ij = np.round((points - self.lo) / PITCH).astype(int)
        ij = ij[((ij >= 0) & (ij < self.shape)).all(axis=1)]
        out = np.zeros(self.shape, bool)
        if len(ij):  # filled in a crop round the points, a voxel to spare inside the grid
            a, b = np.maximum(ij.min(axis=0) - 1, 0), np.minimum(ij.max(axis=0) + 2, self.shape)
            crop = np.zeros(b - a, bool)
            crop[tuple((ij - a).T)] = True
            out[tuple(slice(*s) for s in zip(a, b))] = ndimage.binary_fill_holes(ndimage.binary_dilation(crop))
        return out

    def centres(self):
        return [self.lo[i] + np.arange(n) * PITCH for i, n in enumerate(self.shape)]

    def mesh(self, occ, sigma=0.8):
        """The voxels' surface, smoothed: a Gaussian blur's half level, Taubin-smoothed."""
        v, f, _, _ = marching_cubes(ndimage.gaussian_filter(occ.astype(np.float32), sigma), 0.5)
        out = trimesh.Trimesh(v * PITCH + self.lo, f)
        pieces = out.split(only_watertight=False)
        big = max(abs(p.volume) for p in pieces)
        # a blur's thin bridge leaves crumbs the voxels' _kept could not see
        out = trimesh.util.concatenate([p for p in pieces if abs(p.volume) >= KEEP * big])
        trimesh.smoothing.filter_taubin(out, iterations=4)
        out.fix_normals()
        return out


def _kept(occ):
    """The voxels' pieces of at least KEEP of the largest one's volume: the crumbs carving leaves dropped."""
    label, n = ndimage.label(occ)
    if n < 2:
        return occ
    sizes = ndimage.sum(occ, label, range(1, n + 1))
    return np.isin(label, 1 + np.flatnonzero(sizes >= KEEP * sizes.max()))


def poses(stage):
    """[{part: 4x4}]: the document at rest and each horn at points over its range (the lids' finer: they sweep the
    orbits)."""
    out = [{n: p.matrix for n, p in stage.parts.items()}]
    for horn, h in stage.horns.items():
        for deg in np.linspace(*h.limits, 9 if " lid " in horn else 5):
            out.append(stages.pose(stage, horn, deg).parts)
    return out


def carved():
    """{bone: its mesh, carved and remeshed}, in the head's frame at rest."""
    stage = stages.STAGES[DOC]
    rest = {n: p.matrix for n, p in stage.parts.items()}
    cutters = {
        n: trimesh.load(p.file, force="mesh")
        for n, p in stage.parts.items()
        if not stages.stem(p.file).startswith("next morty ") and stages.stem(p.file) not in g.SKULL
    }
    clouds = {n: surface(m) for n, m in cutters.items()}
    frame = np.array(stages.DOCS[DOC]["next-eyes"][0], float)  # the head's frame in the document's
    out = {}
    for bone, mesh in placed().items():
        grid = Grid(*mesh.bounds)
        occ = ndimage.binary_erosion(grid.solid(surface(mesh)))  # the voxel solid() grew it by taken back
        if bone == "next skull":  # a shell, the eyes' orbits opened round their lids
            occ &= ndimage.distance_transform_edt(occ) * PITCH <= WALL
            x, y, z = np.meshgrid(*grid.centres(), indexing="ij", sparse=True)
            for cx, _, _ in gm.EYE.values():
                ball = (x - cx) ** 2 + y**2 + z**2 <= (gm.LOWER_R[1] + CLEAR_MM) ** 2
                occ &= ~(ball & (y <= REACH))
        carrier, seen = stages.RIDES[bone + ":1"], {}  # cutter -> (its places as the bone sees it, distinct)
        for pose in poses(stage):
            back = rest[carrier] @ np.linalg.inv(pose[carrier])  # the document as the bone sees it there
            for n in cutters:
                at = back @ pose[n]
                places = seen.setdefault(n, [])
                if not any(np.allclose(at, q, atol=1e-6) for q in places):
                    places.append(at)
        rigid, moving = np.zeros(grid.shape, bool), np.zeros(grid.shape, bool)
        for n, places in seen.items():
            for at in places:
                at = at.copy()
                at[:3, 3] -= frame
                box = trimesh.transform_points(trimesh.bounds.corners(cutters[n].bounds), at)
                if (box.max(axis=0) > grid.lo).all() and (
                    box.min(axis=0) < grid.lo + np.multiply(grid.shape, PITCH)
                ).all():
                    target = rigid if len(places) == 1 else moving
                    target |= grid.solid(clouds[n], at)
        # what rides with the bone it lies on (the voxel Grid.solid grew it by taken back); what moves, CLEAR_MM off
        occ &= ~ndimage.binary_erosion(rigid)
        occ &= ~ndimage.binary_dilation(moving, iterations=max(1, round(CLEAR_MM / PITCH) - 1))
        out[bone] = grid.mesh(ndimage.binary_fill_holes(_kept(occ)))  # no void sealed inside
    return out
