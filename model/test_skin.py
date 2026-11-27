"""Seam: the Skin's Seats and magnets (model/skin.py): the pull of one magnet pair at the Seat's gap, which way each
Shell comes off, and the polarity that keys a Shell to its own Seat; the Motion regions; and Morty's cuts on his
Sculpt."""

import os

import numpy as np
import pytest
import trimesh
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


def test_the_shells_are_the_caps_and_mortys_each_printed_in_a_skin_colour_group():
    """#850 (docs/adr/0027): no Shell is drawn by hand. The caps, the mechanism's own, sit on their Seats; Morty's are
    cut from his Sculpt and drawn whole (DRAWN), with no Seat yet."""
    groups = {group for palette in g.THEMES["Skin palette"].values() for group in palette}
    assert skin.DRAWN == ["morty hair", "morty face", "morty chin", "morty shirt"]
    assert set(skin.SHELLS) == {f"{s} eyeball cap" for s in "LR"} | set(skin.DRAWN)
    assert not {s.shell for s in skin.SEATS} & set(skin.DRAWN)
    for stem in skin.SHELLS:
        assert g.PRINTED[stem][0] in groups, stem


def test_a_shell_comes_off_along_its_seats_normal():
    for s in skin.SEATS:
        assert skin.DIRECTIONS[s.shell] == s.normal


def test_every_shell_belongs_to_one_motion_region():
    """#969: each Shell moves with the Motion region its name shows: the head's on the head, the chin on the jaw, a lid
    cover on its lid, a cap or pupil on its eye, the shirt on the fixed torso; the neck, shoulders and torso have no
    carrier."""
    assert {skin.region(s) for s in skin.SHELLS} <= skin.MOTION.keys()
    assert skin.MOTION["neck"] is skin.MOTION["shoulders"] is skin.MOTION["torso"] is None
    for shell, region in {
        "morty face": "head",
        "morty hair": "head",
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


def _inside(points, poly):
    """Even-odd: which (n, 2) points lie inside the closed polygon."""
    a, b = poly, np.roll(poly, -1, axis=0)
    x, y = points[:, :1], points[:, 1:]
    span = (a[:, 1] > y) != (b[:, 1] > y)
    t = (y - a[:, 1]) / np.where(span, b[:, 1] - a[:, 1], 1.0)
    return (span & (x < a[:, 0] + t * (b[:, 0] - a[:, 0]))).sum(axis=1) % 2 == 1


def test_mortys_cuts_sit_on_his_sculpt_where_it_shows_each_form():
    """#992, docs/adr/0027: every cut is where the Sculpt itself has the form (mm in the head's frame, as measured). The
    hairline is its hair's boundary, from the top of the forehead on the midline back and down behind the ears to the
    collar; each eye white its whole dome, 34 mm round a centre 4 mm outward of its eye (gm.EYE, the Sculpt's eyes on
    ours), and its pupil the Sculpt's ring on it, 14 mm across; the mouth line the middle of the lips' ridge, corner to
    corner; the collar where the head meets the shirt, highest under the ears. No lid has a cut."""
    cuts = skin.cuts()
    whites, pupils = [f"{s} eye white" for s in "LR"], [f"{s} pupil" for s in "LR"]
    assert set(cuts) == {"hairline", *whites, *pupils, "mouth", "collar"}
    assert {n for n, (view, _) in cuts.items() if view == "side"} == {"hairline", "collar"}
    line = skin.contour("sculpt hairline")
    assert line[0] == pytest.approx((0.2, 74.9), abs=0.2) and line[-1] == pytest.approx((84.4, -94.0), abs=0.2)
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
        assert white.mean(axis=0) == pytest.approx((x + 4.0 * out, z + 2.0), abs=1.5)
        assert np.linalg.norm(white - white.mean(axis=0), axis=1) == pytest.approx(34.0, abs=1.5)
        assert _inside(pupil, white).all()
        assert np.linalg.norm(pupil - pupil.mean(axis=0), axis=1) == pytest.approx(7.0, abs=0.7)
    mouth, collar = skin.contour("mouth"), skin.contour("collar")
    assert mouth[0] == pytest.approx((-27.0, -76.6), abs=0.2) and mouth[-1] == pytest.approx((27.5, -77.8), abs=0.2)
    assert mouth[:, 1].max() == pytest.approx(-71.5, abs=0.5)  # a frown: its middle over its corners
    assert collar[0] == pytest.approx((27.6, -117.8), abs=0.2) and collar[-1] == pytest.approx((110.9, -109.8), abs=0.2)
    assert collar[collar[:, 1].argmax()] == pytest.approx((79.0, -94.6), abs=2.0)  # under an ear, the hairline's end
    # the jaw under the mouth line between its corners, the shirt under the collar
    assert _inside(np.array([(0.0, -skin.FAR / 2), (0.0, 0.0), (40.0, -100.0)]), cuts["mouth"][1]).tolist() == [1, 0, 0]
    assert _inside(np.array([(60.0, -120.0), (60.0, -60.0), (120.0, -100.0)]), cuts["collar"][1]).tolist() == [1, 0, 0]


def test_each_cut_lies_on_its_form_on_the_sculpt_git_holds():
    """docs/adr/0011, 0027: the cuts' points are measurements of the Sculpt, so each is held to it. A form's foot is a
    concave crease (two faces meeting inward by over 10 deg): every point of the hairline, an eye white, a pupil or the
    collar lies within 1 mm of one, in its view. The mouth line is the middle of the lips' ridge: its corners on the
    ridge's ends, its middle 2.5 to 4.5 mm from either foot."""
    mesh = trimesh.load(os.path.join(stages.REPO, morty.SCULPT), process=False)
    eyes = {s: np.array(e) for s, e in review.MORTY_EYES.items()}  # the Sculpt's, which sit on ours
    scale = gm.SPACING / np.linalg.norm(eyes["L"] - eyes["R"])
    mesh = trimesh.Trimesh((mesh.vertices - (eyes["L"] + eyes["R"]) / 2) * scale, mesh.faces, process=False)
    sharp = ~mesh.face_adjacency_convex & (mesh.face_adjacency_angles > np.radians(10))
    crease = mesh.vertices[mesh.face_adjacency_edges[sharp]].mean(axis=1)
    views = {"side": cKDTree(crease[:, [1, 2]]), "front": cKDTree(crease[crease[:, 1] < 0][:, [0, 2]])}
    for cut, (view, _) in skin.cuts().items():
        name = "sculpt hairline" if cut == "hairline" else cut
        off, _ = views[view].query(np.array(skin.CONTOURS[name]["points"]) * gm.SPACING)
        if cut == "mouth":
            assert off[[0, -1]].max() < 1.0 and 2.5 < off[2:-2].min() <= off[2:-2].max() < 4.5, off
        else:
            assert off.max() < 1.0, (cut, off)
