"""Seam: model/engine/lids.py, the lids' closed and open horn angles and the lid edges seen from the front."""

import pytest

from model import geometry as g
from model.engine import lids


@pytest.mark.parametrize("side", "LR")
def test_closed_and_open_lie_either_side_of_the_fusion_renders(side):
    closed, opened = lids.ends(side)
    # Fusion front render 2026-10-31 (noggin-eyes): horn -25 shows a slit, +25 the whole eyeball
    assert -35 < closed < -25 and 25 < opened <= g.HORN_LIMITS[f"{side.lower()}_lid"][1] - 90


def test_mirror_mounted_sides_share_their_ends():
    assert lids.ends("L") == pytest.approx(lids.ends("R"), abs=0.1)


def test_edges_meet_when_closed_and_part_as_the_horn_opens():
    closed, opened = lids.ends("L")
    upper, lower = lids.edges("L", closed)
    assert upper == pytest.approx(lower, abs=0.5)
    gaps = [lids.gap("L", d) for d in (closed, closed + 10, 0, opened)]
    assert gaps == sorted(gaps) and gaps[0] == pytest.approx(0, abs=0.5)


def test_the_pupil_shows_at_rest_and_hides_when_closed():
    closed, opened = lids.ends("L")
    assert lids.pupil_shown("L", closed) == pytest.approx(0, abs=0.01)
    assert lids.pupil_shown("L", opened) == pytest.approx(1)
    assert 0 < lids.pupil_shown("L", (closed + opened) / 2) <= 1
