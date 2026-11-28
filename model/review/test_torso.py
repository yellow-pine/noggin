"""Seam: the Torso and what is in it inside Morty's Sculpt (#879; #893's directive of 2026-11-27: his shirt is the
body's Skin, and everything else keeps a Shell's wall and its clearance under it): the Torso, its lid, the pack, the
switch board, the power-path board, and the neck socket and the neck tube that stand on its floor, at rest, read on
the Sculpt git holds (model/morty) as test_head.py reads the cranium and the jaw, so every run of the Model's tests
holds it. These stand still, as his shirt does, so rest is every pose.
Four of them stand outside his shirt today, each a strict xfail with its mm (OUTSIDE): the Torso is still the box
drawn before his Sculpt was the Skin. Whoever brings one inside drops its mark.
The skin that rides the head (test_nape.py) is not read here: that test's measure holds only near the neck's line,
and the box's nearest point is 14.7 mm from it at the nine poses measured directly (tilt 0 and +-20, pan 0 and +-45,
#879). Whoever grows the Torso up under the collar holds that too."""

import pytest

from model import geometry as g
from model import stages
from model.review.test_head import _placed, _sculpt
from model.review.test_hidden import MARGIN, depth

# {part: mm its worst point stands outside his Sculpt's outer surface at rest}, measured on main at 4f706fca: the
# Torso's and its lid's front corners, the power-path board's front corners, the switch board's back outer corner
OUTSIDE = {"torso:1": 33.39, "torso lid:1": 31.38, "power-path board:1": 27.64, "switch board:1": 1.18}
PARTS = sorted({*stages.base_sub().parts, "neck socket:1", "neck tube:1"})


@pytest.fixture(scope="module")
def whole():
    """depth() of Morty's Sculpt, placed on the Mech's eyes in the documents' world."""
    return depth(_sculpt())


@pytest.mark.model
@pytest.mark.parametrize(
    "part",
    [
        pytest.param(n, marks=pytest.mark.xfail(strict=True, reason=f"#879: {OUTSIDE[n]} mm outside his shirt"))
        if n in OUTSIDE
        else n
        for n in PARTS
    ],
)
@pytest.mark.parametrize("doc", list(g.MECH))
def test_each_part_of_the_torso_lies_under_mortys_shirt_at_rest(doc, part, whole):
    """#879: at rest every point of the part lies MARGIN inside his outer surface; one that comes nearer or pokes
    through fails with its worst mm."""
    assert round(float(whole(_placed(stages.STAGES[doc], part)).max()), 2) <= -MARGIN
