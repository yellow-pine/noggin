"""Seam: the Skin's Seats and magnets (model/skin.py): the pull of one magnet pair at the Seat's gap, which way each
Shell comes off, and the polarity that keys a Shell to its own Seat; the Motion regions; and Morty's cuts on his
Sculpt."""

import numpy as np
import pytest

from model import geometry as g
from model import gimbal as gm
from model import skin


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


def test_the_eyeball_caps_are_the_only_shells_each_printed_in_a_skin_colour_group():
    """#850 (docs/adr/0027): no Shell is drawn by hand; the caps, the mechanism's own, sit on their Seats."""
    groups = {group for palette in g.THEMES["Skin palette"].values() for group in palette}
    assert set(skin.SHELLS) == {f"{s} eyeball cap" for s in "LR"} and skin.DRAWN == []
    for stem in skin.SHELLS:
        assert g.PRINTED[stem][0] in groups, stem


def test_a_shell_comes_off_along_its_seats_normal():
    for s in skin.SEATS:
        assert skin.DIRECTIONS[s.shell] == s.normal


def test_every_shell_belongs_to_one_motion_region():
    """#969: each Shell moves with the Motion region its name shows: the head's on the head, the mouth on the jaw, a lid
    cover on its lid, a cap or pupil on its eye, the shirt on the fixed torso; the neck, shoulders and torso have no
    carrier."""
    assert {skin.region(s) for s in skin.SHELLS} <= skin.MOTION.keys()
    assert skin.MOTION["neck"] is skin.MOTION["shoulders"] is skin.MOTION["torso"] is None
    for shell, region in {
        "morty face": "head",
        "morty hair": "head",
        "morty mouth cover": "jaw",
        "morty L upper lid cover": "L upper lid",
        "morty R lower lid cover": "R lower lid",
        "L eyeball cap": "L eye",
        "morty R pupil": "R eye",
        "morty shirt front": "torso",
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


def test_mortys_cuts_sit_on_his_sculpt_round_his_eyes():
    """#992, #893's directive of 2026-11-27: the hairline is the sculpt's own hair boundary, from the top of his
    forehead on the midline back and down behind his ears to his collar; each eye white is its whole dome, 34 mm round a
    centre 4 mm outward of its eye (gm.EYE, the sculpt's eyes on ours), its pupil a dot inside it; no lid has a cut; the
    jaw is under the mouth line and the shirt under the collar, on the sculpt's face front (mm in the head's frame, as
    measured)."""
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
        assert _inside(pupil, white).all() and np.ptp(pupil, axis=0).max() < 0.1 * gm.SPACING
    mouth, collar = cuts["mouth"][1], cuts["collar"][1]
    # the jaw under the mouth line, the shirt under the collar
    assert _inside(np.array([(0.0, -skin.FAR / 2), (0.0, 0.0)]), mouth).tolist() == [1, 0]
    assert _inside(np.array([(60.0, -120.0), (60.0, -60.0)]), collar).tolist() == [1, 0]
    # the sheet's collar, moved from its face front to the sculpt's: 13.6 mm forward, as #1017's review measured it
    np.testing.assert_allclose(collar[1:-3] - skin.contour("collar"), [(-13.6, 0.0)] * (len(collar) - 4), atol=0.05)
