"""Seam: the Skin's Seats and magnets (model/skin.py): the pull of one magnet pair at the Seat's gap, which way each
Shell comes off, and the polarity that keys a Shell to its own Seat."""

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
    pairs = {s.shell for s in skin.SEATS if " L " in s.shell}
    assert pairs
    for left in pairs:
        right = left.replace(" L ", " R ")
        assert {s.polarity for s in skin.SEATS if s.shell == left} == {1}
        assert {s.polarity for s in skin.SEATS if s.shell == right} == {-1}


def test_every_shell_is_printed_in_a_skin_colour_group_and_sits_on_a_seat_or_in_a_keyed_one():
    groups = {group for palette in g.THEMES["Skin palette"].values() for group in palette}
    seated = {s.shell for s in skin.SEATS}
    for stem in skin.SHELLS:
        assert g.PRINTED[stem][0] in groups, stem
        assert stem in seated or stem in skin.GLUED, stem


def test_a_shell_comes_off_along_its_seats_normal():
    for s in skin.SEATS:
        assert skin.DIRECTIONS[s.shell] == s.normal


def test_the_upper_lid_cover_stays_above_where_the_lower_lid_passes_over_the_upper():
    """#698: shut and tracking a look down, the lower lid's edge passes up to ~32 deg over the upper's, outside it; the
    upper cover (inside the lower lid's radius) takes the band above that alone, over the lid servo's whole range."""
    for s in np.linspace(*np.subtract(gm.LID_EDGES, gm.LID_REST), 181):
        lower_top = gm.LOWER_REST + gm.lower(s)  # the lower lid's edge, as the upper lid's at LID_REST + s
        assert lower_top < skin.UPPER_COVER[0] + s - 0.5
    assert gm.LID_R[1] + skin.GAP + skin.COVER < gm.LOWER_R[1] + skin.GAP  # the lower cover rides outside the upper one
    # forward of that band, its skin stays inside the lower lid's path, with the clearance and the mesh's 0.02 to spare
    assert gm.LID_R[1] + skin.GAP + skin.BAND + gm.LID_CLEAR_MM + 0.02 < gm.LOWER_R[0]


def _hidden(r, x, deg, cover_r, span, xs):
    """Whether the ray straight forward (-y) from each lid point (radius r, x across, deg up from forward as turned)
    passes through its cover (from inner radius cover_r out, span deg as turned, over xs)."""
    seen = np.degrees(np.arcsin(np.sqrt(r**2 - x**2) * np.sin(np.radians(deg)) / np.sqrt(cover_r**2 - x**2)))
    return (xs[0] <= x) & (x <= xs[1]) & (span[0] <= seen) & (seen <= span[1])


@pytest.mark.parametrize("lid", ["upper", "lower"])
def test_no_lid_shows_past_its_cover_from_the_front(lid):
    """#881: every point of each lid's main shell (both faces, so its free edge's face too) is behind its cover seen
    from the front, over the lid servo's whole range: the lids turn with their servo alone, which follows the eye's
    look within LID_EDGES. LID_SHELL_X bounds the main shell that printed/gimbal.py _lid draws."""
    xs = np.linspace(*gm.LID_SHELL_X[lid], 47)
    for s in np.linspace(*np.subtract(gm.LID_EDGES, gm.LID_REST), 73):
        if lid == "upper":
            radii, span, turn = gm.LID_R, (gm.LID_REST, gm.LID_REST + gm.LID_SPAN), s
            cover_r, cover, cover_x = gm.LID_R[1] + skin.GAP, skin.UPPER_SKIN, skin.COVER_X
        else:
            radii, span, turn = gm.LOWER_R, (gm.LOWER_REST - gm.LOWER_SPAN, gm.LOWER_REST), gm.lower(s)
            cover_r, cover, cover_x = gm.LOWER_R[1] + skin.GAP, skin.LOWER_COVER, skin.LOWER_X
        x, r, deg = np.meshgrid(xs, radii, np.linspace(*span, 53))
        hidden = _hidden(r, x, deg + turn, cover_r, np.add(cover, turn), cover_x)
        assert hidden.all(), (s, x[~hidden].min(), x[~hidden].max(), deg[~hidden].min(), deg[~hidden].max())


def _on_skeleton(skin_shape):
    """{(the Shell less its Skin's name, carrier, at, normal)}: the Skin's Seats on the Skeleton."""
    prefix = f"{skin_shape} "
    return {
        (s.shell.removeprefix(prefix), s.carrier, s.at, s.normal)
        for s in skin.SEATS
        if s.shell.startswith(prefix) and not s.carrier.startswith(prefix)
    }


def test_every_skin_sits_on_the_same_seats_on_the_skeleton():
    """#51, #813: one Skeleton for every Skin; each Skin's Shells come off and on the same kinematic Seats."""
    assert len(_on_skeleton("morty")) == 13  # 4 lid covers, 2 face, 2 hair, the mouth, 4 shirt
    for skin_shape in g.SKINS:
        assert _on_skeleton(skin_shape) == _on_skeleton("morty"), skin_shape


def test_cansins_sunglasses_hang_by_a_magnet_on_his_tees_neckline():
    """#813: aviators hooked on the tee's neckline, a small separate magnetic part in Apricot."""
    (seat,) = (s for s in skin.SEATS if s.shell == "cansin sunglasses")
    assert seat.carrier == "cansin shirt front" and seat.normal == (0.0, -1.0, 0.0)
    assert g.PRINTED["cansin sunglasses"][0] == "accessories"
    assert g.filament("accessories", g.PRESETS["Default build"])[1] == "Apricot"


def test_a_glued_shell_is_keyed_in_what_carries_it():
    """The pupils (#51: keyed, not held by magnets alone), and Cansin's plugs, brows and teeth (#813)."""
    assert skin.GLUED["morty L pupil"] == ("L eyeball cap", (0.0, -1.0, 0.0))
    assert skin.GLUED["cansin L pupil"][0] == "cansin L pupil plug"
    assert skin.GLUED["cansin L pupil plug"][0] == "L eyeball cap"
    assert skin.GLUED["cansin teeth"][0] == "cansin mouth cover"
    assert skin.GLUED["cansin R brow"][0] == "cansin face"
    assert set(skin.SHELLS) == {n for n in g.PRINTED if n.split()[0] in g.SKINS} | {f"{s} eyeball cap" for s in "LR"}


def test_every_shell_belongs_to_one_motion_region():
    """#969: each Shell moves with the Motion region it shows: the head's on the head, the mouth on the jaw, a lid cover
    on its lid, a cap or pupil on its eye, the shirt on the fixed torso; the neck, shoulders and torso have no carrier."""
    assert {skin.region(s) for s in skin.SHELLS} <= skin.MOTION.keys()
    assert skin.MOTION["neck"] is skin.MOTION["shoulders"] is skin.MOTION["torso"] is None
    for shell, region in {
        "morty face": "head",
        "morty hair": "head",
        "cansin L brow": "head",
        "morty mouth cover": "jaw",
        "cansin teeth": "jaw",
        "morty L upper lid cover": "L upper lid",
        "bart R lower lid cover": "R lower lid",
        "L eyeball cap": "L eye",
        "cansin R pupil plug": "R eye",
        "morty shirt front": "torso",
        "cansin sunglasses": "torso",
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
