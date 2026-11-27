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
from model.test_skin import _inside

pytestmark = pytest.mark.model
NAMES = [f"morty {n}" for n in g.SHELLS["morty"]]
# What gives way to a Shell that moves against it (shells.cleared()), measured. The shirt to the turning head and the
# opening chin: no deeper under the collar's top, mm, and this much of the Sculpt's shirt, cm2 (of 329; the collar's
# own gap among it). The face to the chin, under the jaw behind it: inside this box, (low, high) in the head's frame,
# and this much of the Sculpt's head, cm2
SHIRT_MM, SHIRT_CM2 = 40.0, 48.6
UNDER_JAW, UNDER_JAW_CM2 = ((-30.0, -27.0, -120.0), (30.0, 24.0, -70.0)), 9.8


@pytest.fixture(scope="module")
def built():
    return {name: trimesh.load(stages.stl(name), process=False) for name in NAMES}


@pytest.fixture(scope="module")
def sculpt():
    """The Sculpt in the head's frame at rest, from just under the base plane up."""
    mesh = trimesh.load(os.path.join(stages.REPO, morty.SCULPT), process=False).apply_transform(shells.head())
    mesh.update_faces(mesh.triangles[:, :, 2].max(axis=1) > shells.base() - 2.0)
    return mesh


@pytest.fixture(scope="module")
def outer():
    """The Sculpt's outer skin, in the head's frame at rest (shells.outside(), which model/morty/test_outer.py holds
    to the pockets measured on the Sculpt)."""
    return shells._mesh(shells.outside())


@pytest.fixture(scope="module")
def kept(built, sculpt):
    """Which of the Sculpt's vertices are a Shell's, to 0.001 mm."""
    every = cKDTree(np.vstack([mesh.vertices for mesh in built.values()]))
    return every.query(sculpt.vertices)[0] < 1e-3


@pytest.fixture(scope="module")
def buried(sculpt, outer):
    """Which of the Sculpt's vertices are not its outer skin's: the walls of the pockets behind its brows."""
    return cKDTree(outer.vertices).query(sculpt.vertices)[0] > 1e-3


@pytest.fixture(scope="module")
def gone(sculpt, kept, buried):
    """The Sculpt's vertices no Shell has at a seam's gap or where a Shell gave way: all but the eye openings' and the
    pockets' walls'."""
    owed = (sculpt.vertices[:, 2] > shells.base() + 0.01) & ~_in_an_eye_opening(sculpt.vertices, room=0.5)
    return owed & ~kept & ~buried


def _off(points, polygon):
    """Each (n, 2) point's distance to the closed polygon's sides."""
    a = np.asarray(polygon)
    d = np.roll(a, -1, axis=0) - a
    t = np.clip(((points[:, None] - a) * d).sum(-1) / np.maximum((d * d).sum(-1), 1e-12), 0, 1)
    return np.linalg.norm(points[:, None] - (a + t[..., None] * d), axis=-1).min(axis=1)


def _at_a_seam(points, room=0.05):
    """Which points lie in a seam's gap: within shells.SEAM of the hairline's or the collar's cut, or of the mouth's
    in front of the eyes, or behind the chin by it."""
    cuts, gap = skin.cuts(), shells.SEAM + room
    out = (_off(points[:, [1, 2]], cuts["hairline"][1]) < gap) | (_off(points[:, [1, 2]], cuts["collar"][1]) < gap)
    mouth, xz = cuts["mouth"][1], points[:, [0, 2]]
    return out | ((points[:, 1] < gap) & ((_off(xz, mouth) < gap) | (_inside(xz, mouth) & (points[:, 1] > -room))))


def _box(points, box):
    return ((points > box[0]) & (points < box[1])).all(axis=1)


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


def test_each_shell_is_one_closed_solid(built):
    """A printable piece: every edge shared by two faces, wound one way, facing out, in one piece."""
    for name, mesh in built.items():
        mesh = trimesh.Trimesh(mesh.vertices, mesh.faces)  # an STL's vertices, merged
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, name
        assert mesh.body_count == 1, name


def test_the_skins_outside_is_the_sculpts_own_surface(sculpt, kept, gone):
    """docs/adr/0027: his silhouette is the Sculpt's, exactly. Every vertex of the Sculpt's outer skin from the base
    plane up is a vertex of a Shell, but those in the eye openings (the caps are the eye whites), those in a seam's
    gap, and those where a Shell gives way to one that moves against it: the top of the shirt, and the face under the
    jaw behind the chin."""
    owed = (sculpt.vertices[:, 2] > shells.base() + 0.01) & ~_in_an_eye_opening(sculpt.vertices, room=0.5)
    assert (owed & kept).sum() > 25_000
    top = skin.contour("collar")[:, 1].max()
    shirt = _inside(sculpt.vertices[:, [1, 2]], skin.cuts()["collar"][1]) & (sculpt.vertices[:, 2] > top - SHIRT_MM)
    stray = gone & ~_at_a_seam(sculpt.vertices) & ~shirt & ~_box(sculpt.vertices, UNDER_JAW)
    assert not stray.any(), sculpt.vertices[stray][:5]


def test_no_shell_holds_surface_buried_under_the_outer_skin(built, sculpt, outer, kept, buried):
    """#850: the Shells are cut from the Sculpt's outer skin alone. None of the walls of the pockets behind its brows
    is a Shell's, so each brow is its ridge on the face and nothing behind it; and no Shell reaches deeper under the
    outer skin than its wall and 0.5 mm, a pocket's walls followed in (2.4 mm at each brow's inner end before)."""
    assert (buried & (sculpt.vertices[:, 2] > shells.base())).sum() > 20_000  # the pockets are there to be left out
    assert not (kept & buried).any(), sculpt.vertices[kept & buried][:5]
    surface = cKDTree(shells._points(outer.triangles, 0.3))
    for name, mesh in built.items():
        deep = surface.query(mesh.triangles_center, workers=-1)[0]
        assert deep.max() < skin.WALL + 0.5, (name, deep.max(), mesh.triangles_center[deep.argmax()])


def test_every_wall_is_1_6_mm_and_never_open(built, sculpt, outer, gone):
    """docs/adr/0027: the wall grows skin.WALL inward. Each Shell's faces are the outer skin's own, a seam's (flat
    along its cut's sweep, x or y), the base's, or the inside, which lies within 0.15 mm of WALL under the outer skin
    for 98% of it and never nearer than 1.4 mm or further than 1.9 mm, short of where bone may begin (WALL and 0.5 mm
    of room). Away from the eye openings, whose rims are cut round a sphere, and from within 3 mm of where a Shell
    gave way, whose cut runs through the wall."""
    surface = cKDTree(shells._points(outer.triangles, 0.3))
    gave = cKDTree(shells._points(sculpt.triangles[gone[sculpt.faces].any(axis=1)], 0.5))
    for name, mesh in built.items():
        seam = (np.abs(mesh.face_normals[:, :2]) < 1e-3).any(axis=1) | (mesh.face_normals[:, 2] < -0.9999)
        points = mesh.triangles_center[~seam & (mesh.area_faces > 0.02)]  # a sliver's normal is noise
        points = points[~_in_an_eye_opening(points, room=3.0)]
        points = points[gave.query(points)[0] > 3.0]
        under = surface.query(points, workers=-1)[0]
        inside = under[under > 0.25]  # the rest are the Sculpt's own
        assert len(inside) > 1000, name
        assert inside.min() > 1.4 and inside.max() < 1.9, (name, inside.min(), inside.max())
        assert (np.abs(inside - skin.WALL) < 0.15).mean() > 0.98, name


def test_the_skin_is_open_round_each_eye(built):
    """#967: no wall inside skin.EYE_OPENING_R of an eye's centre, so the lids stow hidden behind the face's rim; and
    none in front of the eyes inside an eye white's cut (to 1% of its size, its rim's own vertices), where the cap is
    the eye white."""
    for name, mesh in built.items():
        ahead = mesh.vertices[mesh.vertices[:, 1] < 0]
        for side, eye in gm.EYE.items():
            assert np.linalg.norm(mesh.triangles_center - eye, axis=1).min() >= skin.EYE_OPENING_R, name
            white = skin.cuts()[f"{side} eye white"][1]
            centre = white.mean(axis=0)
            assert not _inside(ahead[:, [0, 2]], centre + 0.99 * (white - centre)).any(), name


def test_the_skin_stands_on_the_base_plane_with_no_floor(built):
    """The shirt ends on the documents' z 0, the Torso's foot, open underneath: its faces on that plane are its wall's
    rim, not a floor."""
    shirt, z = built["morty shirt"], shells.base()
    assert shirt.bounds[0][2] == pytest.approx(z, abs=1e-3)
    assert min(mesh.bounds[0][2] for name, mesh in built.items() if name != "morty shirt") > z + 50
    rim = shirt.area_faces[np.abs(shirt.triangles[:, :, 2] - z).max(axis=1) < 1e-3].sum()
    size = shirt.bounds[1] - shirt.bounds[0]
    assert 0 < rim < 0.1 * size[0] * size[1]


def _solids(built):
    return {
        n: shells._solid(*(lambda m: (m.vertices, m.faces))(trimesh.Trimesh(m.vertices, m.faces)))
        for n, m in built.items()
    }


def test_shells_that_ride_together_keep_the_seams_gap(built):
    """#850: the hair and the face, both on the head, are never nearer than the room a worn Shell keeps from a part it
    does not sit on (model/printed/test_skin.py CLEAR_MM), nor further apart at their seam than SEAM and a bit."""
    solid = _solids(built)
    gap = solid["morty hair"].min_gap(solid["morty face"], 5.0)
    assert gm.LID_CLEAR_MM < gap < shells.SEAM + 0.1, gap


@pytest.mark.parametrize("jaw", [0.0, 0.07, 0.5, 1.0])
def test_no_seam_closes_as_the_head_turns_and_the_jaw_opens(built, jaw):
    """#850: through tilt and pan together (13 poses each way, none the cutter's own but the ends) with the jaw at
    `jaw` of its range, the hair, the face and the chin stay gm.LID_CLEAR_MM off the fixed shirt, and the chin off the
    face and the hair it opens away from."""
    solid = _solids(built)
    stage, eyes = stages.STAGES[morty.DOC], stages.align(*stages.DOCS[morty.DOC]["eyes"])

    def moved(horn, part, share):
        low, high = stage.horns[horn].limits
        deg = low + share * (high - low)
        return (
            np.linalg.inv(eyes)
            @ stages.pose(stage, horn, deg).parts[part]
            @ np.linalg.inv(stage.parts[part].matrix)
            @ eyes
        )

    opened = moved("jaw horn", "jaw:1", 1.0 - jaw)  # its horn's high end is the jaw shut
    chin = solid["morty chin"].transform(opened[:3])
    near = {}
    for other in ("morty face", "morty hair"):
        near[other, "chin"] = chin.min_gap(solid[other], 5.0)
    for tilt in np.linspace(0, 1, 13):
        for pan in np.linspace(0, 1, 13):
            turn = moved("tilt horn", "gimbal frame:1", tilt) @ moved("pan horn", "gimbal frame:1", pan)
            for name, mover in (
                ("morty hair", solid["morty hair"]),
                ("morty face", solid["morty face"]),
                ("chin", chin),
            ):
                gap = mover.transform(turn[:3]).min_gap(solid["morty shirt"], 5.0)
                near[name, "shirt"] = min(near.get((name, "shirt"), 5.0), gap)
    assert min(near.values()) > gm.LID_CLEAR_MM, near


def test_a_shell_gives_way_only_as_much_as_was_measured(sculpt, gone):
    """#850: where the head's Shells turn into it the shirt is cut back, and the face where the chin opens into it,
    and no more than was measured: all of the Sculpt's shirt more than SHIRT_MM under the collar's top is the Shell's
    own, what is cut away above is SHIRT_CM2 of it, and UNDER_JAW_CM2 of the head's under the jaw."""
    under = gone & _inside(sculpt.vertices[:, [1, 2]], skin.cuts()["collar"][1])
    assert sculpt.vertices[under][:, 2].min() > skin.contour("collar")[:, 1].max() - SHIRT_MM
    assert sculpt.area_faces[under[sculpt.faces].all(axis=1)].sum() / 100 == pytest.approx(SHIRT_CM2, abs=2.0)
    jaw = gone & ~under & ~_at_a_seam(sculpt.vertices)  # the head's, off its seams: under the jaw (the test above)
    assert sculpt.area_faces[jaw[sculpt.faces].all(axis=1)].sum() / 100 == pytest.approx(UNDER_JAW_CM2, abs=1.0)


def test_each_shell_fits_the_bed_whole(built):
    """#850: each prints in one piece on the bed, as it stands in the head's frame."""
    for name, mesh in built.items():
        assert (mesh.bounds[1] - mesh.bounds[0]).max() <= g.BED, name


def test_the_shells_are_cut_where_the_cuts_are(built):
    """skin.cuts(): the shirt under the collar and the rest above it, the hair above and behind the hairline, the chin
    under the mouth line in front of the eyes. Read at each Shell's box and weight (g, solid PLA Pure)."""
    grams = {n: m.volume / 1000 * g.MATERIALS["PLA Pure"]["density_g_cm3"] for n, m in built.items()}
    assert grams == pytest.approx(
        {"morty hair": 181, "morty face": 90, "morty chin": 4.1, "morty shirt": 57}, rel=0.05
    ), grams
    collar = skin.contour("collar")[:, 1]
    assert collar.max() - 10.0 < built["morty shirt"].bounds[1][2] < collar.max()  # its top gave way to the head
    assert built["morty hair"].bounds[1][2] > 110 and built["morty hair"].bounds[0][1] > -1.0  # the crown; none ahead
    chin = built["morty chin"].bounds
    mouth = skin.contour("mouth")
    assert chin[1][1] <= 1e-3 and chin[1][2] == pytest.approx(mouth[:, 1].max(), abs=1.0)
    assert chin[0][0] == pytest.approx(mouth[0][0], abs=1.0) and chin[1][0] == pytest.approx(mouth[-1][0], abs=1.0)
