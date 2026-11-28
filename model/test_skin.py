"""Seam: the Skin's Seats and magnets (model/skin.py): the pull of one magnet pair at the Seat's gap, which way each
Shell comes off, and the polarity that keys a Shell to its own Seat; the Motion regions; and Morty's cuts on his
Sculpt."""

import os

import numpy as np
import pytest
import trimesh
from scipy import optimize
from scipy.spatial import cKDTree

from model import geometry as g
from model import gimbal as gm
from model import morty, review, skin, stages


def test_a_seated_pair_of_4x2_n52_discs_pulls_about_4_5_newtons():
    """Two 4x2 mm N52 discs face to face pull ~6 N touching (a 4x2 N52 disc pulls 0.3-0.4 kgf off steel, its maker's
    figure); the Seat's balls hold them about 0.2 mm apart, which leaves ~4.5 N."""
    assert skin.GAP == pytest.approx(0.21, abs=0.01)
    assert 4.0 < skin.hold_n() < 5.0 < skin.hold_n(0.0) < 7.0


def test_a_magnet_pair_turned_the_wrong_way_pushes_the_shell_off():
    assert skin.hold_n(polarity=-1) < -4.0


def test_each_left_and_right_shell_keys_to_its_own_seat():
    """One polarity rule (#51): the R Shell of an L/R pair has its Seats' magnets reversed, so on the L Seat it is pushed
    off instead of held."""
    pairs = {s.shell for s in skin.SEATS if s.shell.startswith("L ")}
    assert pairs
    for left in pairs:
        right = "R" + left[1:]
        assert {s.polarity for s in skin.SEATS if s.shell == left} == {1}
        assert {s.polarity for s in skin.SEATS if s.shell == right} == {-1}


def test_the_caps_are_the_only_shells_worn_and_mortys_are_printed_in_skin_colour_groups():
    """#850 (docs/adr/0027): no Shell is drawn by hand. The caps, the mechanism's own, sit on their Seats and are the
    only Shells a document wears; Morty's, cut from his Sculpt (g.SHELLS), are printed in PLA Pure, each in its Colour
    group, and worn by no document until the gates on a worn Shell pass (g.SKINS)."""
    groups = {group for palette in g.THEMES["Skin palette"].values() for group in palette}
    assert set(skin.SHELLS) == {*(f"{s} eyeball cap" for s in "LR"), "morty face"}  # the Shells on Seats so far
    assert skin.DRAWN == [] and g.SKINS == {}
    assert {n: g.PRINTED[f"morty {n}"] for n in g.SHELLS["morty"]} == {
        "hair crown": ("hair", "PLA Pure"),
        "hair back": ("hair", "PLA Pure"),
        "L brow": ("hair", "PLA Pure"),
        "R brow": ("hair", "PLA Pure"),
        "face": ("face", "PLA Pure"),
        "chin": ("face", "PLA Pure"),
        "shirt": ("clothes", "PLA Pure"),
    }
    for stem in skin.SHELLS:
        assert g.PRINTED[stem][0] in groups, stem


def test_the_face_sits_on_the_gimbal_frames_beam_and_comes_off_forward():
    """#850: the face's two lower Seats are in the front of the gimbal frame's beam, under the eyes, one each side,
    facing forward: the pocket and the grooves fit the beam's front whole (its flat, clear of its cut corners), and the
    Seat stands on a boss in from the face's wall. Neither is an L/R pair's: both show N."""
    seats = [s for s in skin.SEATS if s.shell == "morty face"]
    assert {(s.carrier, s.normal, s.polarity, s.pad) for s in seats} == {("gimbal frame", (0.0, -1.0, 0.0), 1, 0.0)}
    assert sorted(s.at[0] for s in seats) == [-42.0, 42.0]
    reach = skin.RING + skin.GROOVE  # the grooves' far ends
    for s in seats:
        assert s.at[1] == gm.CHEEK_Y[0] and s.at[2] == pytest.approx(sum(gm.BEAM_Z) / 2)
        assert abs(s.at[0]) + skin.PAD_R <= gm.BEAM_X - gm.BEAM_CUT
        assert gm.BEAM_Z[0] <= s.at[2] - reach and s.at[2] + reach <= gm.BEAM_Z[1]
        assert s.boss > 0


def test_each_brow_is_glued_in_the_face_and_rides_the_head_with_it():
    """#850: a brow has no Seat. It is glued in the face, which carries it on and off the head."""
    assert skin.GLUED == {"morty L brow": "morty face", "morty R brow": "morty face"}
    assert not {s.shell for s in skin.SEATS} & skin.GLUED.keys()
    for brow, face in skin.GLUED.items():
        assert skin.MOTION[skin.region(brow)] == skin.MOTION[skin.region(face)]


def test_a_shell_comes_off_along_its_seats_normal():
    for s in skin.SEATS:
        assert skin.DIRECTIONS[s.shell] == s.normal


def test_mortys_hair_comes_off_in_two_pieces_the_crown_up_and_the_back_back():
    """#893 (Cansin, 2026-11-28): no straight way takes the hair off the skull in one piece, so it is two Shells: the
    crown lifts straight up and the back slides straight back, in the head's frame. Their Seats, in bone, are not
    built yet (#874's cap)."""
    assert skin.DIRECTIONS["morty hair crown"] == (0.0, 0.0, 1.0)
    assert skin.DIRECTIONS["morty hair back"] == (0.0, 1.0, 0.0)
    assert {"hair crown", "hair back"} <= g.SHELLS["morty"].keys() and "hair" not in g.SHELLS["morty"]


def test_every_shell_belongs_to_one_motion_region():
    """#969: each Shell moves with the Motion region its name shows: the head's on the head (a brow rides the face), the
    chin on the jaw, a lid cover on its lid, a cap or pupil on its eye, the shirt on the fixed torso. The neck's skin
    rides the head, down to the collar (Cansin, 2026-11-27, docs/adr/0030); the shoulders and torso have no carrier."""
    assert {skin.region(s) for s in skin.SHELLS} <= skin.MOTION.keys()
    assert skin.MOTION["shoulders"] is skin.MOTION["torso"] is None
    assert skin.MOTION["neck"] == skin.MOTION["head"] == "gimbal frame"
    for shell, region in {
        "morty face": "head",
        "morty hair crown": "head",
        "morty hair back": "head",
        "morty L brow": "head",
        "morty chin": "jaw",
        "morty L upper lid cover": "L upper lid",
        "morty R lower lid cover": "R lower lid",
        "L eyeball cap": "L eye",
        "morty R pupil": "R eye",
        "morty shirt": "torso",
    }.items():
        assert skin.region(shell) == region, shell
    with pytest.raises(KeyError):
        skin.region("morty tail")


_inside = skin.inside  # model/review's and model/morty's tests read it here


def test_mortys_cuts_sit_on_his_sculpt_where_it_shows_each_form():
    """#992, docs/adr/0027: every cut is where the Sculpt itself has the form (mm in the head's frame, as measured). The
    hairline is its hair's boundary, from the top of the forehead on the midline back and down behind the ears to the
    collar; each eye white its whole dome, 34 mm round a centre 3 mm outward of its eyeball's (gm.EYE, the Sculpt's
    eyes on ours: the dome faces outward), and its pupil the Sculpt's ring on it, 14 mm across; the mouth line the
    middle of the lips' ridge, corner to corner; the collar where the head meets the shirt, highest under the ears.
    Each brow is its ridge's outline (Cansin, 2026-11-27: the brows are dark), seen from the front turned skin.TURNED
    toward its side, since it rounds the temple: 55 mm long there and 8.5 mm across, from 9 mm off that view's middle
    up over its eye and down to the temple. No lid has a cut."""
    cuts = skin.cuts()
    whites, pupils = [f"{s} eye white" for s in "LR"], [f"{s} pupil" for s in "LR"]
    brows = {"L brow": "front left", "R brow": "front right"}
    assert set(cuts) == {"hairline", *whites, *pupils, *brows, "mouth", "collar"}
    assert {n for n, (view, _) in cuts.items() if view == "side"} == {"hairline", "collar"}
    assert {n: view for n, (view, _) in cuts.items() if view in brows.values()} == brows
    assert skin.TURNED == {"front": 0.0, "front left": 40.0, "front right": -40.0}
    for s, out in (("L", 1), ("R", -1)):
        brow = cuts[f"{s} brow"][1] * (out, 1)
        low, high = brow.min(axis=0), brow.max(axis=0)
        assert low == pytest.approx((8.6, 27.2), abs=0.3) and high == pytest.approx((64.0, 51.1), abs=0.3)
        (a, b), (c, d) = brow.T, np.roll(brow, -1, axis=0).T
        assert abs((a * d - b * c).sum()) / 2 / (high[0] - low[0]) == pytest.approx(8.5, abs=0.2)  # across, on average
    line = skin.contour("sculpt hairline")
    assert line[0] == pytest.approx((1.5, 73.2), abs=0.2) and line[-1] == pytest.approx((85.7, -95.7), abs=0.2)
    # (y, z): hair on the crown, at the nape and all the way down behind the ears; none on the forehead, an ear, the chin
    crown, nape, behind, forehead, ear, chin = (
        (0.0, 100.0),
        (120.0, 0.0),
        (100.0, -110.0),
        (-10.0, 40.0),
        (70.0, -30.0),
        (20.0, -110.0),
    )
    assert _inside(np.array([crown, nape, behind, forehead, ear, chin]), cuts["hairline"][1]).tolist() == [
        1,
        1,
        1,
        0,
        0,
        0,
    ]
    for s, out in (("L", 1), ("R", -1)):
        white, pupil = cuts[f"{s} eye white"][1], cuts[f"{s} pupil"][1]
        x, _, z = gm.EYE[s]
        assert white.mean(axis=0) == pytest.approx((x + 3.1 * out, z + 1.2), abs=0.5)
        assert np.linalg.norm(white - white.mean(axis=0), axis=1) == pytest.approx(34.0, abs=1.5)
        assert _inside(pupil, white).all()
        assert np.linalg.norm(pupil - pupil.mean(axis=0), axis=1) == pytest.approx(7.0, abs=0.7)
    mouth, collar = skin.contour("mouth"), skin.contour("collar")
    assert mouth[0] == pytest.approx((-27.5, -78.4), abs=0.2) and mouth[-1] == pytest.approx((27.0, -79.6), abs=0.2)
    assert mouth[:, 1].max() == pytest.approx(-73.3, abs=0.5)  # a frown: its middle over its corners
    assert collar[0] == pytest.approx((28.9, -119.6), abs=0.2) and collar[-1] == pytest.approx((112.1, -111.6), abs=0.2)
    assert collar[collar[:, 1].argmax()] == pytest.approx((80.2, -96.3), abs=2.0)  # under an ear, the hairline's end
    # the jaw under the mouth line between its corners, the shirt under the collar
    assert _inside(np.array([(0.0, -skin.FAR / 2), (0.0, 0.0), (40.0, -100.0)]), cuts["mouth"][1]).tolist() == [1, 0, 0]
    assert _inside(np.array([(60.0, -120.0), (60.0, -60.0), (120.0, -100.0)]), cuts["collar"][1]).tolist() == [1, 0, 0]


# an eye's dome: his surface this many deg off straight ahead of its centre, and this near its ball, mm
DOME, NEAR = 50.0, 1.5


def test_the_mechs_eyes_sit_on_the_sculpts_own_each_ball_fitted_to_its_dome():
    """#967 (Cansin, 2026-11-27), docs/adr/0011: review.MORTY_EYES are the centres of the Sculpt's eyeballs, each a
    sphere fitted to its dome by least squares, its centre and radius free, settled from the listed centre; gm.SPACING
    is their distance at his life size (#872, #901), and his eye a 37.1 mm ball. The domes' feet seen from the front
    are 80 mm apart (their cuts): each dome faces outward, so its foot's centre is not its ball's."""
    mesh = trimesh.load(os.path.join(stages.REPO, morty.SCULPT), process=False)
    listed = {s: np.array(e) for s, e in review.MORTY_EYES.items()}
    scale = gm.SPACING / np.linalg.norm(listed["L"] - listed["R"])
    assert scale == pytest.approx(7.126, abs=0.005)
    for s, eye in listed.items():
        c, r = eye, 37.0 / scale
        near = np.linalg.norm(mesh.triangles_center - eye, axis=1) < 2 * r  # the git copy's faces are large on a dome
        v = np.asarray(trimesh.sample.sample_surface(mesh.submesh([near], append=True), 40000, seed=0)[0])
        for _ in range(8):
            d = np.linalg.norm(v - c, axis=1)
            dome = v[(np.abs(d - r) < NEAR / scale) & ((c - v)[:, 1] / d > np.cos(np.radians(DOME)))]
            fit = optimize.least_squares(
                lambda x, dome=dome: np.linalg.norm(dome - x[:3], axis=1) - x[3], [*c, r], loss="soft_l1", f_scale=0.05
            )
            c, r = fit.x[:3], fit.x[3]
        assert len(dome) > 2000
        assert (c - eye) * scale == pytest.approx(0.0, abs=0.1), s
        assert r * scale == pytest.approx(37.1, abs=0.1)


def test_each_cut_lies_on_its_form_on_the_sculpt_git_holds():
    """docs/adr/0011, 0027: the cuts' points are measurements of the Sculpt, so each is held to it. A form's foot is a
    concave crease (two faces meeting inward by over 10 deg): every point of the hairline, an eye white, a pupil or
    the collar lies within 1 mm of one, in its view. A brow is a slab standing proud, and its outline is what its
    view sees of it: its foot, or its top's own edge (a crease the other way) where that hides the foot under it; every
    point of it lies within 0.6 mm of one or the other. The mouth line is the middle of the lips' ridge: its corners on
    the ridge's ends, its middle 2.5 to 4.5 mm from either foot."""
    mesh = trimesh.load(os.path.join(stages.REPO, morty.SCULPT), process=False)
    eyes = {s: np.array(e) for s, e in review.MORTY_EYES.items()}  # the Sculpt's, which sit on ours
    scale = gm.SPACING / np.linalg.norm(eyes["L"] - eyes["R"])
    mesh = trimesh.Trimesh((mesh.vertices - (eyes["L"] + eyes["R"]) / 2) * scale, mesh.faces, process=False)
    edge = mesh.vertices[mesh.face_adjacency_edges].mean(axis=1)
    sharp = mesh.face_adjacency_angles > np.radians(10)
    crease = edge[sharp & ~mesh.face_adjacency_convex]
    views = {"side": cKDTree(crease[:, [1, 2]])}

    def ahead(points, view):
        """A front view sees what is ahead of the eyes' plane, turned with it."""
        seen = skin.facing(points, view)
        return cKDTree(seen[seen[:, 1] < 0][:, [0, 2]])

    views |= {view: ahead(crease, view) for view in skin.TURNED}
    for cut, (view, _) in skin.cuts().items():
        name = "sculpt hairline" if cut == "hairline" else cut
        points = np.array(skin.CONTOURS[name]["points"]) * gm.SPACING
        off, _ = views[view].query(points)
        if cut == "mouth":
            assert off[[0, -1]].max() < 1.0 and 2.5 < off[2:-2].min() <= off[2:-2].max() < 4.5, off
        elif cut.endswith("brow"):
            assert ahead(edge[sharp], view).query(points)[0].max() < 0.6, (cut, off)
            # its foot, where the view sees it: the lower edge and the temple
            assert (off < 1.0).mean() > 0.5, (cut, off)
        else:
            assert off.max() < 1.0, (cut, off)
