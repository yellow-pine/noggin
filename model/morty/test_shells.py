"""Seam: Morty's Skin as `just ours` cuts it from his Sculpt (model/morty/shells.py, docs/adr/0027): each Shell's STL in
model/build/ours, in the head's frame at rest, held to the Sculpt git holds."""

import functools
import os

import manifold3d as m3
import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

from model import geometry as g
from model import gimbal as gm
from model import mjcf, morty, review, skeleton, skin, stages
from model.morty import shells
from model.test_skin import _inside

pytestmark = pytest.mark.model
NAMES = [f"morty {n}" for n in g.SHELLS["morty"]]
HAIR = ["morty hair crown", "morty hair back"]
# What gives way to a Shell that moves against it (shells.cleared()), measured. The shirt to the turning head and the
# opening chin: no deeper under the collar's top, mm, and this much of the Sculpt's shirt, cm2 (of 329; the collar's
# own gap among it). The face to the chin, under the jaw behind it: inside this box, (low, high) in the head's frame,
# and this much of the Sculpt's head, cm2
SHIRT_MM, SHIRT_CM2 = 40.0, 48.6
UNDER_JAW, UNDER_JAW_CM2 = ((-30.0, -27.0, -120.0), (30.0, 24.0, -70.0)), 9.8
# How far from a brow's cut the face's skin ends at the most, mm, as the brow's view sees it: shells.FIT along the
# brow, and 0.45 at its two tips (measured), where the view sees the slab's end edge on and the strip of face between
# the fit and the slab's end stands free of the face: seven flakes at the four tips, 0.18 mm3 in all, which the
# cutter drops as crumbs
BROW_TIP = 0.45


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
    owed = (sculpt.vertices[:, 2] > shells.base() + 0.01) & ~_in_an_eye_opening(sculpt.vertices, room=0.01)
    return owed & ~kept & ~buried


def _off(points, polygon):
    """Each (n, 2) point's distance to the closed polygon's sides."""
    a = np.asarray(polygon)
    d = np.roll(a, -1, axis=0) - a
    t = np.clip(((points[:, None] - a) * d).sum(-1) / np.maximum((d * d).sum(-1), 1e-12), 0, 1)
    return np.linalg.norm(points[:, None] - (a + t[..., None] * d), axis=-1).min(axis=1)


def _at_a_seam(points, room=0.05):
    """Which points lie in a seam's gap: within shells.SEAM of the hairline's or the collar's cut, or of the mouth's
    in front of the eyes, or behind the chin by it; in the hair's level seam, half shells.SEAM each side of
    shells.LEVEL; or in a brow's fit round it, within BROW_TIP of its cut as its view sees it (a brow is glued on the
    face: no seam's gap)."""
    cuts, gap, fit = skin.cuts(), shells.SEAM + room, BROW_TIP + room
    out = (_off(points[:, [1, 2]], cuts["hairline"][1]) < gap) | (_off(points[:, [1, 2]], cuts["collar"][1]) < gap)
    out |= _inside(points[:, [1, 2]], cuts["hairline"][1]) & (np.abs(points[:, 2] - shells.LEVEL) < gap / 2)
    for side in gm.EYE:
        view, brow = cuts[f"{side} brow"]
        seen = skin.facing(points, view)
        out |= (seen[:, 1] < fit) & (_off(seen[:, [0, 2]], brow) < fit)
    mouth, xz = cuts["mouth"][1], points[:, [0, 2]]
    return out | ((points[:, 1] < gap) & ((_off(xz, mouth) < gap) | (_inside(xz, mouth) & (points[:, 1] > -room))))


def _box(points, box):
    return ((points > box[0]) & (points < box[1])).all(axis=1)


def _in_an_eye_opening(points, room=0.0):
    """Which points lie in an eye's opening: in front of the eyes, inside its eye white's cut or within `room` of it."""
    out = np.zeros(len(points), bool)
    for side in gm.EYE:
        white = skin.cuts()[f"{side} eye white"][1]
        out |= (points[:, 1] < room) & (_inside(points[:, [0, 2]], white) | (_off(points[:, [0, 2]], white) < room))
    return out


def _on_a_seat(name, points):
    """Which points are a Seat's of the Shell `name`: within its boss's radius (skin.PAD_R, and 0.5 mm) of its axis,
    out of its carrier's face. A boss is no wall: it stands in from it to the Seat (shells.seated())."""
    out = np.zeros(len(points), bool)
    for seat in (s for s in skin.SEATS if s.shell == name):
        local = trimesh.transform_points(points, np.linalg.inv(skin.frame(seat)))
        out |= (np.hypot(local[:, 0], local[:, 1]) < skin.PAD_R + 0.5) & (local[:, 2] > -skin.BALL_R)
    return out


def _under_a_brow(name, points):
    """Which points are the face's under a brow: inside its outline or within its fit (and 0.5 mm) of it, as its view
    sees it, in the brows' box. There the face's outside is the brow's bed, shells.BROW + shells.GLUE under the
    Sculpt's surface (the test for a laid-on brow holds it)."""
    out = np.zeros(len(points), bool)
    if name == "morty face":
        for side in gm.EYE:
            view, cut = skin.cuts()[f"{side} brow"]
            seen = skin.facing(points, view)[:, [0, 2]]
            out |= _box(points, shells.BROWS) & (_inside(seen, cut) | (_off(seen, cut) < shells.FIT + 0.5))
    return out


def test_each_shell_is_one_closed_solid(built):
    """A printable piece: every edge shared by two faces, wound one way, facing out, in one piece."""
    for name, mesh in built.items():
        mesh = trimesh.Trimesh(mesh.vertices, mesh.faces)  # an STL's vertices, merged
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, name
        assert mesh.body_count == 1, name


def test_the_skins_outside_is_the_sculpts_own_surface(sculpt, kept, gone):
    """docs/adr/0027: his silhouette is the Sculpt's, exactly. Every vertex of the Sculpt's outer skin from the base
    plane up is a vertex of a Shell, but those in the eye openings (the caps are the eye whites; an opening is its
    eye white's cut and no larger, #893), those in a seam's gap, and those where a Shell gives way to one that moves
    against it: the top of the shirt, and the face under the jaw behind the chin."""
    owed = (sculpt.vertices[:, 2] > shells.base() + 0.01) & ~_in_an_eye_opening(sculpt.vertices, room=0.01)
    assert (owed & kept).sum() > 25_000
    top = skin.contour("collar")[:, 1].max()
    shirt = _inside(sculpt.vertices[:, [1, 2]], skin.cuts()["collar"][1]) & (sculpt.vertices[:, 2] > top - SHIRT_MM)
    stray = gone & ~_at_a_seam(sculpt.vertices) & ~shirt & ~_box(sculpt.vertices, UNDER_JAW)
    assert not stray.any(), sculpt.vertices[stray][:5]


def test_no_shell_holds_surface_buried_under_the_outer_skin(built, sculpt, outer, kept, buried):
    """#850: the Shells are cut from the Sculpt's outer skin alone. None of the walls of the pockets behind its brows
    is a Shell's, so each brow is its ridge on the face and nothing behind it; and no Shell reaches deeper under the
    outer skin than its wall and 0.5 mm, a pocket's walls followed in (2.4 mm at each brow's inner end before), but
    at its Seats, each on a boss in from the wall. The face under a brow is no deeper than anywhere else: a brow is
    laid on it, in a bed cut into its wall's outside (#893)."""
    assert (buried & (sculpt.vertices[:, 2] > shells.base())).sum() > 20_000  # the pockets are there to be left out
    assert not (kept & buried).any(), sculpt.vertices[kept & buried][:5]
    surface = cKDTree(shells._points(outer.triangles, 0.3))
    for name, mesh in built.items():
        centres = mesh.triangles_center
        centres = centres[~_on_a_seat(name, centres)]
        deep = surface.query(centres, workers=-1)[0]
        assert deep.max() < skin.WALL + 0.5, (name, deep.max(), centres[deep.argmax()])


def test_every_wall_is_1_6_mm_and_never_open(built, sculpt, outer, gone):
    """docs/adr/0027: the wall grows skin.WALL inward. Each Shell's faces are the outer skin's own, a seam's (flat
    along its cut's sweep: x, or y as a front view turns it; or level, the hair's), the base's, or the inside, which
    lies within 0.15 mm of WALL under the outer skin for 98% of it and never nearer than 1.4 mm or further than 1.9 mm, short of where bone
    may begin (WALL and 0.5 mm of room). Away from within 3 mm of where a Shell gave way, whose cut runs through the
    wall, from its Seats' bosses and from the face under each brow, whose outside is the brow's bed. A brow is laid on
    the face (#893): shells.BROW thick, not a wall, 8 mm across, all of it within 3 mm of its own seam, and a slab
    with a step each side. Its whole inside is held within 0.25 mm of BROW, and 90% of it within 0.15."""
    surface = cKDTree(shells._points(outer.triangles, 0.3))
    gave = cKDTree(shells._points(sculpt.triangles[gone[sculpt.faces].any(axis=1)], 0.5))
    sweeps = [
        (1.0, 0.0, 0.0),
        *(skin.facing(np.eye(3), view)[:, 1] for view in skin.TURNED),
    ]  # each in the head's frame
    for name, mesh in built.items():
        seam = (np.abs(mesh.face_normals @ np.transpose(sweeps)) < 1e-3).any(axis=1)
        seam |= mesh.face_normals[:, 2] < -0.9999  # the base's, and the crown's at the hair's level seam
        seam |= (name == HAIR[1]) & (mesh.face_normals[:, 2] > 0.9999)  # the back's at that seam
        points = mesh.triangles_center[~seam & (mesh.area_faces > 0.02)]  # a sliver's normal is noise
        points = points[~_on_a_seat(name, points) & ~_under_a_brow(name, points)]
        brow = "brow" in name
        if not brow:
            points = points[gave.query(points)[0] > 3.0]
        under = surface.query(points, workers=-1)[0]
        inside = under[under > 0.25]  # the rest are the Sculpt's own
        assert len(inside) > 1000, name
        thick = shells.BROW if brow else skin.WALL
        low, high = (thick - 0.25, thick + 0.25) if brow else (1.4, 1.9)
        assert inside.min() > low and inside.max() < high, (name, inside.min(), inside.max())
        assert (np.abs(inside - thick) < 0.15).mean() > (0.9 if brow else 0.98), name


def test_the_skin_is_open_round_each_eye(built):
    """#893 (Cansin, 2026-11-27): an eye's opening is its eye white's cut, the Sculpt's own dome's edge, exactly. No
    wall in front of the eyes inside it (to 1% of its size, its rim's own vertices), where the eyeball is the eye
    white; and the face comes up to it all round: its rim is within 0.05 mm of the cut at every point of it. Its
    wall then comes to 36.3 mm from the eye's centre at its nearest (measured): the room #967's eyeball and lids have
    under the rim."""
    for name, mesh in built.items():
        ahead = mesh.vertices[mesh.vertices[:, 1] < 0]
        for side, eye in gm.EYE.items():
            white = skin.cuts()[f"{side} eye white"][1]
            if name == "morty face":
                assert cKDTree(ahead[:, [0, 2]]).query(white)[0].max() < 0.05, side
                assert np.linalg.norm(mesh.vertices - eye, axis=1).min() == pytest.approx(36.3, abs=0.2), side
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


SEATS = [s for s in skin.SEATS if s.shell in NAMES]


@pytest.mark.parametrize("seat", SEATS, ids=lambda s: f"{s.shell} on {s.carrier} {s.at[0]:+.0f}")
def test_a_shells_half_of_a_seat_is_a_boss_three_balls_and_its_magnets_pocket(built, seat):
    """#850, model/skin.py: in the Seat's own frame, z out of its carrier's face. The Shell's boss comes in from its
    wall to a flat face skin.GAP off the carrier's, whole round the magnet out past the balls. Three balls stand out
    of that face, to rest in the carrier's grooves. The magnet's pocket is open from the face, the magnet's depth and
    its fit round, with at least skin.SKIN of the Shell left over it. Nothing else of the Shell comes nearer the
    carrier's face than the boss's, as far round as the boss reaches. And the Shell meets its carrier nowhere: the
    balls rest in the grooves (under 0.1 mm3 shared, as drawn)."""
    shell = _solids({seat.shell: built[seat.shell]})[seat.shell]
    to = np.array(skin.frame(seat))[:3]

    def share(solid):
        """How much of `solid`, drawn in the Seat's frame, is the Shell's."""
        return (shell ^ solid.transform(to)).volume() / solid.volume()

    def disc(r, z0, z1):
        return m3.Manifold.cylinder(z1 - z0, r, circular_segments=96).translate((0, 0, z0))

    bore = skin.MAGNET[0] / 2 + skin.FIT
    balls = [
        m3.Manifold.sphere(skin.BALL_R, 48).translate(
            (skin.RING * np.cos(np.radians(deg)), skin.RING * np.sin(np.radians(deg)), skin.GAP)
        )
        for deg in (0, 120, 240)
    ]
    for ball in balls:
        assert share(ball) > 0.99
    face = disc(skin.RING + skin.BALL_R, skin.GAP, skin.GAP + 1.0) - disc(bore + 0.05, skin.GAP - 1, skin.GAP + 2)
    assert share(face) > 0.999
    assert share(disc(skin.MAGNET[0] / 2, -1.0, skin.GAP + skin.MAGNET[1])) < 1e-6  # the magnet's way in, and its room
    assert share(disc(bore, skin.GAP + skin.MAGNET[1] + 0.01, skin.GAP + skin.MAGNET[1] + skin.SKIN)) > 0.999
    under = disc(skin.PAD_R, -3.0, skin.GAP - 0.01)
    for ball in balls:
        under -= ball
    assert share(under) < 1e-6
    carrier = trimesh.load(stages.stl(seat.carrier), force="mesh")  # merged: an STL's vertices are each facet's own
    assert (shell ^ shells._solid(carrier.vertices, carrier.faces)).volume() < 0.1


def test_shells_that_ride_together_keep_the_seams_gap(built):
    """#850: the hair's two pieces, each brow and the face, all on the head, are never nearer than the room a worn
    Shell keeps from a part it does not sit on (model/printed/test_skin.py CLEAR_MM), nor further apart at their seam
    than SEAM and a bit: each piece of the hair from the face, and the crown from the back."""
    solid = _solids(built)
    for a, b in ((HAIR[0], "morty face"), (HAIR[1], "morty face"), HAIR):
        gap = solid[a].min_gap(solid[b], 5.0)
        assert gm.LID_CLEAR_MM < gap < shells.SEAM + 0.1, (a, b, gap)


@functools.cache
def _places(carrier):
    """{part: [its solid, in the head's frame at rest, at each place `carrier` sees it in]}: every part of the
    document the review wears the Shells on, at rest and with each servo at either end, the carrier held still.
    Each part's mesh is closed as physics closes it (mjcf._mesh): Linux's OCCT leaves slivers on a few seams, and a
    solid needs none. A part still open after that stands in as its convex hull."""
    stage, eyes = review.worn(), stages.align(*stages.DOCS[morty.DOC]["eyes"])
    rest = {n: p.matrix for n, p in stage.parts.items()}
    head = f"{carrier}:1"
    poses = [rest, *(stages.pose(stage, horn, deg).parts for horn, h in stage.horns.items() for deg in h.limits)]
    out = {}
    for name, part in stage.parts.items():
        mesh = mjcf._mesh(part.file, None)
        if not mesh.is_volume:  # Linux's OCCT leaves a part physics never reads open (the Bones' L upper lid, #1095)
            mesh = mesh.convex_hull  # all of it lies in its hull: what is clear of the hull is clear of the part
        solid, seen = shells._solid(mesh.vertices, mesh.faces), []
        for pose in poses:
            at = np.linalg.inv(eyes) @ rest[head] @ np.linalg.inv(pose[head]) @ pose[name]
            if not any(np.allclose(at, q, atol=1e-6) for q in seen):
                seen.append(at)
        out[name.removesuffix(":1")] = [solid.transform(at[:3]) for at in seen]
    return out


@pytest.mark.bones
@pytest.mark.parametrize("piece", [*HAIR, "morty chin"])
def test_each_shell_in_bone_comes_off_straight(piece):
    """#893 (Cansin, 2026-11-28): the hair is cut in two on a level seam so that each piece comes off the head a
    straight way (skin.DIRECTIONS), the crown up and the back back, the other piece still on; and the chin comes
    off the mandible forward, the mandible still on its carrier (the sixth round). Exact solids, a millimetre at a
    time until the piece is past everything: it never comes nearer a part than a worn Shell's room
    (gm.LID_CLEAR_MM, so it touches nothing between two steps). Every part of the Skeleton at rest and wherever each
    servo's ends put it as the part that carries the piece sees it (the head, or the jaw); every other Shell at
    rest. The bone its Seats are in it rests on, its balls in their grooves; once off them, a millimetre on, it
    keeps its bosses' room in their flats from that bone (skeleton.SEAT_ROOM, as two meshed rounds read it). And it
    comes no nearer the worn skull or its calvaria on its way than where it rests."""
    places = _places(skin.MOTION[skin.region(piece)])
    way = np.array(skin.DIRECTIONS[piece])
    carriers = {g.WORN[s.carrier] for s in skin.SEATS if s.shell == piece}
    (seated,) = places[piece]
    box = np.reshape(seated.bounding_box(), (2, 3))
    # a Shell at its first place, rest: the shirt stands in the back's way once the head is turned or nodded
    seen = {name: solids[:1] if name in NAMES else solids for name, solids in places.items() if name != piece}
    others = [(name, s, np.reshape(s.bounding_box(), (2, 3))) for name, solids in seen.items() for s in solids]
    far = max((b @ way).max() for _, _, b in others) - (box @ way).min()  # until all of it is past all of them
    near, off = {}, {}  # {part: (its least gap, how far along)}; {carrier: its least gap once the piece is off it}
    for t in np.arange(0.0, far + 1.0, 1.0):
        moved, low, high = seated.translate(tuple(t * way)), box[0] + t * way, box[1] + t * way
        for name, solid, b in others:
            if (low < b[1] + 3.0).all() and (high > b[0] - 3.0).all():
                gap = moved.min_gap(solid, 3.0)
                near[name] = min(near.get(name, (3.0, t)), (gap, t))
                if t and name in carriers:
                    off[name] = min(off.get(name, 3.0), gap)
    free = {name: gap for name, gap in near.items() if name not in carriers}
    assert far > 50 and min(free.values())[0] > gm.LID_CLEAR_MM, sorted(free.items(), key=lambda kv: kv[1])[:5]
    assert carriers and min(off[name] for name in carriers) > skeleton.SEAT_ROOM - 0.1, off
    for bone in ("worn skull", "worn calvaria"):  # the skull as a Skin wears it, and its cap (#874)
        assert near.get(bone, (3.0, 0.0))[1] == 0.0, (bone, near[bone])


@pytest.mark.bones
def test_the_mandible_comes_off_its_carrier_with_the_chin_still_on_it():
    """#968, #850: the chin sits on the mandible, which leaves its carrier along skeleton.OFF. Riding the bone that
    way a millimetre at a time, the chin never comes nearer anything but the bone it sits on than a worn Shell's
    room (gm.LID_CLEAR_MM): every part at rest, the head level and the jaw shut (nodded down or the jaw open, the
    shirt's collar stands in its way after 8 and 13 mm, measured). The bone's own way is model/skeleton's test."""
    places = _places(skin.MOTION["jaw"])
    way, far = skeleton.OFF["mandible"]
    (chin,) = places["morty chin"]
    least = min(
        (chin.translate(tuple(t * np.array(way))).min_gap(solids[0], 3.0), name, float(t))
        for t in np.arange(0.0, far + 0.5, 1.0)
        for name, solids in places.items()
        if name not in ("morty chin", g.WORN["mandible"])
    )
    assert least[0] > gm.LID_CLEAR_MM, least


def test_each_brow_is_laid_on_the_face_which_runs_on_under_it(built, outer):
    """#893 (Cansin, 2026-11-28): a brow is laid on the face, not let into a cut through it. It is glued there
    (skin.GLUED), so it needs no seam's gap: its own outline locates it, the fit shells.FIT off the face all round,
    in a bed cut into the outside of the face's wall. The brow is shells.BROW thick and its bed shells.GLUE under it
    (each face of the bed within 0.25 mm of that depth under the Sculpt's surface, half of them within 0.1). The
    face runs on under all of the brow: pushed down into its bed (BROW and GLUE along its view), a brow lies in the
    face with over 40% of itself (46% measured: its view is not square to its surface; 3% when it lay over a cut
    on two tabs), from its nose end to its temple end. And under a brow the face's inside is its wall's own,
    skin.WALL under the Sculpt's surface as everywhere (1.4 to 1.9 mm, as the wall is held), so a laid-on brow asks
    nothing of the lids or the bone behind it: the face there stays outside the lids' shell (gm.LIDS_SHELL) and
    0.5 mm, about its eye's centre."""
    solid = _solids(built)
    face, mesh = solid["morty face"], built["morty face"]
    surface = cKDTree(shells._points(outer.triangles[_box(outer.triangles_center, shells.BROWS)], 0.3))
    under = (mesh.area_faces > 0.02) & _under_a_brow("morty face", mesh.triangles_center)
    under &= ~_on_a_seat("morty face", mesh.triangles_center)
    deep = surface.query(mesh.triangles_center[under], workers=-1)[0]
    for side in gm.EYE:
        brow = solid[f"morty {side} brow"]
        assert 0.1 < brow.min_gap(face, 5.0) < shells.FIT + 0.1, side
        view, cut = skin.cuts()[f"{side} brow"]
        into = skin.facing(np.eye(3), view)[:, 1]  # the head's direction the view sees as depth, into the head
        mine = (mesh.triangles_center[under][:, 0] > 0) == (gm.EYE[side][0] > 0)
        facing = mesh.face_normals[under][mine] @ into
        # across the view (the fit's sides run along it): the bed, short of the wall's depth, and the inside, at it
        flat = deep[mine][(np.abs(facing) > 0.5) & (deep[mine] > 0.25)]  # the rest are the Sculpt's own, round the brow
        bed, inside = flat[flat < 1.3], flat[flat >= 1.3]
        assert len(bed) > 500 and len(inside) > 500, side
        assert np.abs(bed - shells.BROW - shells.GLUE).max() < 0.25, (side, bed.min(), bed.max())
        assert abs(np.median(bed) - shells.BROW - shells.GLUE) < 0.1, (side, np.median(bed))
        assert inside.min() > 1.4 and inside.max() < 1.9, (side, inside.min(), inside.max())
        pushed = (brow.translate(tuple((shells.BROW + shells.GLUE) * into)) ^ face).to_mesh()
        met = trimesh.Trimesh(pushed.vert_properties[:, :3], pushed.tri_verts)
        assert met.volume > 0.4 * brow.volume(), (side, met.volume, brow.volume())
        across = np.abs(skin.facing(met.vertices, view)[:, 0])
        assert across.min() < np.abs(cut[:, 0]).min() + 1.0 and across.max() > np.abs(cut[:, 0]).max() - 1.0, side
        seen = skin.facing(mesh.vertices, view)[:, [0, 2]]
        below = mesh.vertices[_box(mesh.vertices, shells.BROWS) & _inside(seen, cut)]
        assert np.linalg.norm(below - gm.EYE[side], axis=1).min() > gm.LIDS_SHELL[1] + 0.5, side  # 38.97 measured


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
    for other in ("morty face", *HAIR):
        near[other, "chin"] = chin.min_gap(solid[other], 5.0)
    for tilt in np.linspace(0, 1, 13):
        for pan in np.linspace(0, 1, 13):
            turn = moved("tilt horn", "gimbal frame:1", tilt) @ moved("pan horn", "gimbal frame:1", pan)
            for name, mover in (*((n, solid[n]) for n in (*HAIR, "morty face")), ("chin", chin)):
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


def test_each_brow_is_cut_along_its_ridges_foot(built, outer):
    """#850 (Cansin, 2026-11-27: the brows are dark): a brow's Shell is the Sculpt's own ridge, a slab standing proud
    of the forehead, cut along the slab's outline as its view sees it: its foot, or its top's own edge where that
    hides the foot. Every 2 mm round its cut the outer skin has a crease (two faces meeting by over 10 deg, either
    way) within 0.6 mm, so no stretch of the cut runs over smooth skin. The Shell runs from 19.3 mm off the midline,
    over the eye, round the temple to 78 mm off it and 9 mm behind the eyes' plane."""
    sharp = outer.face_adjacency_angles > np.radians(10)
    crease = outer.vertices[outer.face_adjacency_edges[sharp]].mean(axis=1)
    for side in gm.EYE:
        view, cut = skin.cuts()[f"{side} brow"]
        seen = skin.facing(crease, view)
        assert cKDTree(seen[seen[:, 1] < 0][:, [0, 2]]).query(cut)[0].max() < 0.6, side
        (x0, y0, z0), (x1, y1, z1) = built[f"morty {side} brow"].bounds
        assert sorted((abs(x0), abs(x1))) == pytest.approx((19.3, 78.1), abs=0.5), side
        assert (y0, y1, z0, z1) == pytest.approx((-13.9, 9.4, 27.3, 51.1), abs=0.5), side


def test_the_shells_are_cut_where_the_cuts_are(built):
    """skin.cuts(): the shirt under the collar and the rest above it, the hair above and behind the hairline, the chin
    under the mouth line in front of the eyes, each brow out of the face. Read at each Shell's box and weight (g,
    solid PLA Pure)."""
    grams = {n: m.volume / 1000 * g.MATERIALS["PLA Pure"]["density_g_cm3"] for n, m in built.items()}
    # each with its Seats' bosses: the face's three (3.3 g), the crown's (1.5 g) and the back's, its two low ones
    # 13 mm long (5.9 g); the face runs on under each brow, which is BROW thick
    weighed = {"hair crown": 107.2, "hair back": 80.6, "L brow": 0.59, "R brow": 0.59, "face": 92.4, "chin": 4.1}
    weighed |= {"shirt": 57}
    assert grams == pytest.approx({f"morty {n}": w for n, w in weighed.items()}, rel=0.05), grams
    collar = skin.contour("collar")[:, 1]
    assert collar.max() - 10.0 < built["morty shirt"].bounds[1][2] < collar.max()  # its top gave way to the head
    crown, back = (built[n].bounds for n in HAIR)
    assert crown[1][2] > 110 and min(crown[0][1], back[0][1]) > -1.0  # the crown; no hair ahead of the eyes
    # the hair's level seam: the crown above it, the back below, down to the collar
    assert crown[0][2] == pytest.approx(shells.LEVEL + shells.SEAM / 2, abs=1e-3)
    assert back[1][2] == pytest.approx(shells.LEVEL - shells.SEAM / 2, abs=1e-3) and back[0][2] < -100
    chin = built["morty chin"].bounds
    mouth = skin.contour("mouth")
    assert chin[1][1] <= 1e-3 and chin[1][2] == pytest.approx(mouth[:, 1].max(), abs=1.0)
    assert chin[0][0] == pytest.approx(mouth[0][0], abs=1.0) and chin[1][0] == pytest.approx(mouth[-1][0], abs=1.0)
