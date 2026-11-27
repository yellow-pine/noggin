"""Seam: Morty's Skin as `just ours` cuts it from his Sculpt (model/morty/shells.py, docs/adr/0027): each Shell's STL in
model/build/ours, in the head's frame at rest, held to the Sculpt git holds."""

import os

import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

from model import geometry as g
from model import gimbal as gm
from model import morty, skin, stages
from model.morty import shells

pytestmark = pytest.mark.model
NAMES = [f"morty {n}" for n in g.SHELLS["morty"]]
# the Sculpt's brows: each a sheet buried in its head behind the brow's ridge, (low, high) in the head's frame, mirrored
# in x. The Skin leaves them out: a wall would follow them 75 mm in
BROWS = ((0.0, -14.0, 27.0), (80.0, 90.0, 60.0))


@pytest.fixture(scope="module")
def built():
    return {name: trimesh.load(stages.stl(name), process=False) for name in NAMES}


@pytest.fixture(scope="module")
def sculpt():
    """The Sculpt in the head's frame at rest, from the base plane up."""
    mesh = trimesh.load(os.path.join(stages.REPO, morty.SCULPT), process=False).apply_transform(shells.head())
    return mesh


def _in_an_eye_opening(points, room=0.0):
    """Which points lie in an eye's opening: its sphere, or in front of the eyes inside its eye white's cut."""
    out = np.zeros(len(points), bool)
    for side, eye in gm.EYE.items():
        white = skin.cuts()[f"{side} eye white"][1]
        centre = white.mean(axis=0)
        reach = np.linalg.norm(white - centre, axis=1).max() + room
        out |= np.linalg.norm(points - eye, axis=1) < skin.EYE_OPENING_R + room
        out |= (points[:, 1] < room) & (np.linalg.norm(points[:, [0, 2]] - centre, axis=1) < reach)
    return out


def _buried(points):
    (x0, y0, z0), (x1, y1, z1) = BROWS
    x, y, z = np.abs(points[:, 0]), points[:, 1], points[:, 2]
    return (x0 <= x) & (x <= x1) & (y0 <= y) & (y <= y1) & (z0 <= z) & (z <= z1)


def test_each_shell_is_one_closed_solid(built):
    """A printable piece: every edge shared by two faces, wound one way, facing out, in one piece."""
    for name, mesh in built.items():
        mesh = trimesh.Trimesh(mesh.vertices, mesh.faces)  # an STL's vertices, merged
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, name
        assert mesh.body_count == 1, name


def test_the_skins_outside_is_the_sculpts_own_surface(built, sculpt):
    """docs/adr/0027: his silhouette is the Sculpt's, exactly. Every vertex of the Sculpt from the base plane up is a
    vertex of a Shell, but those in the eye openings (the caps are the eye whites) and those of the brows' buried
    sheets."""
    every = cKDTree(np.vstack([mesh.vertices for mesh in built.values()]))
    kept = every.query(sculpt.vertices)[0] < 1e-3
    owed = (sculpt.vertices[:, 2] > shells.base() + 0.01) & ~_in_an_eye_opening(sculpt.vertices, room=0.5)
    assert (owed & kept).sum() > 25_000
    missing = sculpt.vertices[owed & ~kept]
    assert _buried(missing).all(), missing[~_buried(missing)][:5]
    # the sheets are finely meshed, 180 cm2 in all: no more of the Sculpt than that is left out
    left_out = sculpt.area_faces[(owed & ~kept)[sculpt.faces].all(axis=1)].sum() / 100
    assert left_out == pytest.approx(180.0, rel=0.05)


def test_every_wall_is_1_6_mm_and_never_open(built, sculpt):
    """docs/adr/0027: the wall grows skin.WALL inward. Each Shell's faces are the Sculpt's own, a seam's (flat along
    its cut's sweep, x or y), the base's, or the inside, which lies within 0.15 mm of WALL under the Sculpt for 99% of
    it and never nearer than 1.4 mm or further than 1.9 mm, short of where bone may begin (WALL and 0.5 mm of room).
    Away from the eye openings, whose rims are cut round a sphere, and from the brows' buried sheets."""
    surface = cKDTree(shells._points(sculpt.triangles, 0.3))
    for name, mesh in built.items():
        seam = (np.abs(mesh.face_normals[:, :2]) < 1e-3).any(axis=1) | (mesh.face_normals[:, 2] < -0.9999)
        points = mesh.triangles_center[~seam & (mesh.area_faces > 0.02)]  # a sliver's normal is noise
        points = points[~_in_an_eye_opening(points, room=3.0) & ~_buried(points)]
        under = surface.query(points, workers=-1)[0]
        inside = under[under > 0.25]  # the rest are the Sculpt's own
        assert len(inside) > 1000, name
        assert inside.min() > 1.4 and inside.max() < 1.9, (name, inside.min(), inside.max())
        assert (np.abs(inside - skin.WALL) < 0.15).mean() > 0.99, name


def test_the_skin_is_open_round_each_eye(built):
    """#967: no wall inside skin.EYE_OPENING_R of an eye's centre, so the lids stow hidden behind the face's rim; and
    nothing in front of an eye's middle, where its cap is the eye white."""
    for name, mesh in built.items():
        for eye in gm.EYE.values():
            assert np.linalg.norm(mesh.triangles_center - eye, axis=1).min() >= skin.EYE_OPENING_R, name
            ahead = mesh.vertices[mesh.vertices[:, 1] < eye[1]]
            assert (np.linalg.norm((ahead - eye)[:, [0, 2]], axis=1) > 20.0).all(), name


def test_the_skin_stands_on_the_base_plane_with_no_floor(built):
    """The shirt ends on the documents' z 0, the Torso's foot, open underneath: its faces on that plane are its wall's
    rim, not a floor."""
    shirt, z = built["morty shirt"], shells.base()
    assert shirt.bounds[0][2] == pytest.approx(z, abs=1e-3)
    assert min(mesh.bounds[0][2] for name, mesh in built.items() if name != "morty shirt") > z + 50
    rim = shirt.area_faces[np.abs(shirt.triangles[:, :, 2] - z).max(axis=1) < 1e-3].sum()
    size = shirt.bounds[1] - shirt.bounds[0]
    assert 0 < rim < 0.1 * size[0] * size[1]


def test_each_shell_fits_the_bed_whole(built):
    """#850: each prints in one piece on a 256 mm bed, 6 mm clear of its edges, as it stands in the head's frame."""
    for name, mesh in built.items():
        assert (mesh.bounds[1] - mesh.bounds[0]).max() <= 256.0 - 2 * 6.0, name


def test_the_shells_are_cut_where_the_cuts_are(built):
    """skin.cuts(): the shirt under the collar and the rest above it, the hair above and behind the hairline, the chin
    under the mouth line in front of the eyes. Read at each Shell's box and weight (g, solid PLA Pure)."""
    grams = {n: m.volume / 1000 * g.MATERIALS["PLA Pure"]["density_g_cm3"] for n, m in built.items()}
    assert grams == pytest.approx(
        {"morty hair": 180, "morty face": 93, "morty chin": 4.3, "morty shirt": 70}, rel=0.05
    ), grams
    collar = skin.contour("collar")[:, 1]
    assert built["morty shirt"].bounds[1][2] == pytest.approx(collar.max(), abs=1.0)
    assert built["morty hair"].bounds[1][2] > 110 and built["morty hair"].bounds[0][1] > -1.0  # the crown; none ahead
    chin = built["morty chin"].bounds
    mouth = skin.contour("mouth")
    assert chin[1][1] <= 1e-3 and chin[1][2] == pytest.approx(mouth[:, 1].max(), abs=1.0)
    assert chin[0][0] == pytest.approx(mouth[0][0], abs=1.0) and chin[1][0] == pytest.approx(mouth[-1][0], abs=1.0)
