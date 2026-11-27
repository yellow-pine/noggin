"""Morty's Skin, cut from his Sculpt (GLOSSARY Skin, Shell; docs/adr/0027, #850). shells() is every Shell in the head's
frame at rest, mm, which `just ours` writes beside our parts (write()). No document wears them yet (g.SKINS, #850).

The Sculpt is placed on the Mech's eyes (morty.placed()) and cut at the base plane, the documents' z 0. Its own
triangles stay the Skin's outside. The inside is the surface skin.WALL under it, measured on a grid of PITCH: each
point's distance to the Sculpt's outside, meshed where that is WALL (scikit-image's marching cubes), then made lighter
within FLAT. "Outside" is what
the open air reaches: this Sculpt's brows are sheets buried deep in its head, joined to its surface by pinholes, and a
wall would follow them in. A groove deeper than BACKING still has wall behind it, so no wall is open. The wall has no
floor at the base. It is open round each eye (skin.EYE_OPENING_R, and inside the eye white's cut): the eyeball caps,
the mechanism's own, are the eye whites. Then it is split along skin.cuts(): the shirt under the collar, the hair above
and behind the hairline, the chin under the mouth line, and the face. Solids are cut with manifold3d."""

import os

import manifold3d as m3
import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import measure

from model import geometry as g
from model import gimbal as gm
from model import morty, skin, stages

PITCH = 0.8  # the grid the inside is measured on and meshed at, mm: twice it, and a sharp crease's wall thinned to 0.3
# the inside's mesh is then made lighter, within this of itself (manifold3d's simplify): 0.9 M triangles to 0.1 M, so
# each Shell is under the 200,000 faces MuJoCo reads from an STL
FLAT = 0.05
BACKING = 1.0  # the Sculpt's own surface is kept to this far under its outside; deeper, the wall is filled
UNDER = 12.0  # the Sculpt is kept this far under the base while the inside is measured, so the wall has no floor
# A point of the Sculpt's surface within SEEN grid steps of the open air is its outside. So is a crease's bottom, a
# little further in; a patch of surface that goes on past DEEP steps from the air is buried
# shortcut: a buried sheet's edge within SEEN of the air (under a brow's ridge) counts as outside, so the wall keeps a
# fin of it, more or less of one as the grid falls (11 cm2 of 180 between two placements); tell it by its normal, which
# faces no air, if a Sculpt's buried surface must be left out whole
SEEN, DEEP = 2.0, 5.0
KEEP = 0.01  # a crumb a cut leaves, of its Shell's volume, under which it is dropped
SPHERE, SAG = 128, 0.05  # an eye opening's sphere: segments round, and how far its facets sag inside it at most


def head():
    """4x4 taking the Sculpt's own frame to the head's: his eyes on the Mech's (morty.placed()), at rest."""
    return np.linalg.inv(stages.align(*stages.DOCS[morty.DOC]["eyes"])) @ morty.placed()


def base():
    """The base plane's height in the head's frame: the documents' z 0, the Torso's foot."""
    return float(np.linalg.inv(stages.align(*stages.DOCS[morty.DOC]["eyes"]))[2, 3])


def _solid(vertices, faces):
    out = m3.Manifold(m3.Mesh(np.asarray(vertices, np.float32), np.asarray(faces, np.uint32)))
    assert out.status() == m3.Error.NoError, out.status()  # a mesh that is no closed surface would cut to nothing
    return out


def _mesh(solid):
    """The solid as a trimesh, without the facets whose corners its 32-bit coordinates bring together: two of a
    Shell's 65,000, each an open edge to a reader that merges vertices (as model/ours.py printable() drops OCCT's)."""
    mesh = solid.to_mesh()
    mesh = trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts)
    mesh.update_faces(mesh.nondegenerate_faces())
    return mesh


def _points(triangles, spacing):
    """Points on the triangles, none further than `spacing` from the next: each triangle's own lattice."""
    edge = np.linalg.norm(triangles - np.roll(triangles, 1, axis=1), axis=2).max(axis=1)
    steps = np.ceil(edge / spacing).astype(int)
    out = []
    for k in np.unique(steps):
        i, j = np.meshgrid(np.arange(k + 1), np.arange(k + 1))
        keep = i + j <= k
        weights = np.stack([i[keep], j[keep], k - i[keep] - j[keep]], axis=1) / k
        out.append(np.einsum("wk,fkd->fwd", weights, triangles[steps == k]).reshape(-1, 3))
    return np.vstack(out)


def under(sculpt, levels):
    """The solid each of `levels` mm under the outside of `sculpt` (a manifold3d solid), each closed. The open air is
    the grid's empty space joined to its corner; a buried sheet or a pinhole's far side is not it."""
    surface = _points(_mesh(sculpt).triangles, 0.7 * PITCH)
    low, high = surface.min(axis=0) - 3 * PITCH, surface.max(axis=0) + 3 * PITCH
    cell = tuple(np.round((surface - low) / PITCH).astype(int).T)
    air = np.ones(np.ceil((high - low) / PITCH).astype(int) + 1, bool)
    air[cell] = False
    labels, _ = ndimage.label(air)
    air = labels == labels[0, 0, 0]
    depth = ndimage.distance_transform_edt(~air)  # grid steps to the open air
    far = np.zeros(air.shape, bool)
    far[cell] = depth[cell] > SEEN
    patches, n = ndimage.label(far, structure=np.ones((3, 3, 3)))
    buried = np.flatnonzero(ndimage.maximum(depth, patches, np.arange(1, n + 1)) > DEEP) + 1
    outside = cKDTree(surface[~np.isin(patches[cell], buried)])
    cap = max(levels) + 3 * PITCH
    near = np.argwhere(~air & (depth <= DEEP + cap / PITCH))  # a crease's bottom, DEEP in, is outside too
    field = np.where(air, 0.0, -cap).astype(np.float32)
    field[tuple(near.T)] = -np.minimum(outside.query(near * PITCH + low, workers=-1)[0], cap)
    out = []
    for level in levels:
        v, f, _, _ = measure.marching_cubes(field, level=-level, spacing=(PITCH,) * 3)
        solid = _solid(v + low, f)
        assert solid.volume() > 0, level  # the field falls inward, so marching cubes winds its faces outward
        out.append(solid.simplify(FLAT))
    return out


def _swept(view, region):
    """The region a cut bounds (skin.cuts()), swept through the head along its view's axis: a side view's along x; a
    front view's from the eyes' plane forward, as the review's ahead()."""
    section, far = m3.CrossSection([np.asarray(region)], m3.FillRule.EvenOdd), skin.FAR
    if view == "front":  # (x, z), swept along -y
        return m3.Manifold.extrude(section, far).transform([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0]])
    return m3.Manifold.extrude(section, 2 * far).transform([[0, 0, 1, -far], [1, 0, 0, 0], [0, 1, 0, 0]])


def _whole(name, solid):
    """The Shell's one piece, less what a cut left under KEEP of it: a crumb, or a closed pocket in its wall (a piece
    of negative volume), which prints filled. ValueError when nothing falls in it, or a cut split it or left more."""
    pieces = sorted(solid.decompose(), key=lambda p: -abs(p.volume()))
    if not pieces or pieces[0].volume() <= 0:
        raise ValueError(f"{name}: nothing of the wall falls in it")
    if len(pieces) > 1 and abs(pieces[1].volume()) > KEEP * pieces[0].volume():
        raise ValueError(f"{name}: cut into {[round(p.volume()) for p in pieces[:4]]} mm3, not one piece")
    return pieces[0]


def shells():
    """{Shell: its mesh (trimesh), one closed solid in the head's frame at rest}: g.SHELLS["morty"]."""
    sculpt = trimesh.load(os.path.join(stages.REPO, morty.SCULPT), process=False).apply_transform(head())
    sculpt = _solid(sculpt.vertices, sculpt.faces)
    z = base()
    inside, backed = under(sculpt.trim_by_plane((0, 0, 1), z - UNDER), (skin.WALL, BACKING))
    wall = (sculpt + backed - inside).trim_by_plane((0, 0, 1), z)
    cuts = {name: _swept(*cut) for name, cut in skin.cuts().items() if "pupil" not in name}  # the caps carry those
    for side, eye in gm.EYE.items():
        ball = m3.Manifold.sphere(skin.EYE_OPENING_R + SAG, SPHERE).translate(eye)
        wall -= ball + cuts[f"{side} eye white"]
    moving = wall - cuts["collar"]
    skinned = moving - cuts["hairline"]
    out = {
        "shirt": wall ^ cuts["collar"],
        "hair": moving ^ cuts["hairline"],
        "chin": skinned ^ cuts["mouth"],
        "face": skinned - cuts["mouth"],
    }
    assert set(out) == set(g.SHELLS["morty"]), sorted(out)
    return {f"morty {name}": _mesh(_whole(name, solid)) for name, solid in out.items()}


def write():
    """Each Shell's STL beside our parts (stages.stl)."""
    os.makedirs(stages.OURS, exist_ok=True)
    for name, mesh in shells().items():
        mesh.export(stages.stl(name))
