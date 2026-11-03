"""Seam: the Skin's Seats and magnets (model/skin.py): the pull of one magnet pair at the Seat's gap, which way each
Shell comes off, and the polarity that keys a Shell to its own Seat."""

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
    look within LID_EDGES. The lid's x is printed/gimbal.py _lid's main shell, from the inboard ears' slab to its boss's."""
    xs = np.linspace(-gm.LID_X["ear"][0], gm.LID_X[f"{lid} boss"][1], 47)
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
