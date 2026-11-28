"""Seam: the rest of the head's mechanism inside Morty's Sculpt (#1089; #893's directive of 2026-11-27: the
mechanism's limit is his skin, where the compact head's box was): the cranium tray with its boards and the jaw with
its drive, each at least a Shell's wall and its clearance under his outer surface, read on the Sculpt git holds
(model/morty) as test_hidden.py reads the eye gimbal and test_nape.py the neck, so every run of the Model's tests holds
it. At rest against the whole Sculpt. Then, over each horn's range but the eyes', against each piece of his skin that
moves against the part: the head's, and the jaw's, which the jaw carries (skin.MOTION, cut as skin.cuts() cuts the
Shells). The tray and the boards ride the head, so only the jaw's skin moves against them.
The shirt, which stands still, is left out: these parts ride the head or the jaw inside those two's skin, above the
collar's cut, so what the shirt meets first is a Shell, and it gives way to that (model/morty/shells.py cleared(),
#850). Nodding, his chin's own skin runs through his Sculpt's shirt, so no part under it could keep MARGIN from that."""

import numpy as np
import pytest
import trimesh

from model import geometry as g
from model import morty, review, skin, stages
from model.review.test_hidden import HORNS, MARGIN, _cloud, depth

PARTS = sorted({*stages.cranium_sub().parts, *stages.jaw_sub().parts})
PIECES = ("head", "jaw")  # the Motion regions whose skin moves against a part here (review.CARRIERS)
STEP = 0.5  # each horn's range is sampled this often, deg: the jaw's chin end moves 0.4 mm between two poses
# {part: why it fails}, each another ticket's, held as a strict expected failure until that ticket moves the part
REST = {
    "jaw:1": "#968's follow-up: the jaw carrier's chin end lies 1.88 mm under his chin's skin, 0.22 short, where the"
    " two chains meet at the symphysis"
}
MOVING = {
    "jaw:1": "#968's follow-up: the jaw carrier's chin end swings down and back into the skin under his chin, which"
    " stays with the head: within 2.1 mm of it from 15 deg of the jaw's 25, and through it from 16"
}


def _known(why):
    return [
        pytest.param(n, marks=pytest.mark.xfail(strict=True, raises=AssertionError, reason=why[n])) if n in why else n
        for n in PARTS
    ]


def _piece(points):
    """The Motion region whose skin each point of his surface is at rest (the documents' world), of those that move
    against each other: the shirt's under the collar ("torso"), the jaw's under the mouth line ahead of the eyes'
    plane, the head's all else (his neck's skin rides the head)."""
    cuts, out = skin.cuts(), []
    into = np.linalg.inv(stages.align(*stages.DOCS[morty.DOC]["eyes"]))  # the cuts are in the head's frame
    for x, y, z in (p.T for p in np.array_split(trimesh.transform_points(points, into), len(points) // 100_000 + 1)):
        jaw = skin.inside(np.c_[x, z], cuts["mouth"][1]) & (y < 0)
        out.append(np.where(skin.inside(np.c_[y, z], cuts["collar"][1]), "torso", np.where(jaw, "jaw", "head")))
    return np.concatenate(out)


def _sculpt():
    return trimesh.load(stages.REPO + "/" + morty.SCULPT, process=False).apply_transform(morty.placed())


@pytest.fixture(scope="module")
def whole():
    """depth() of Morty's Sculpt, placed on the Mech's eyes in the documents' world."""
    return depth(_sculpt())


@pytest.fixture(scope="module")
def pieces():
    """{piece: (points in the documents' world) -> mm each lies from that piece of his skin at rest}."""
    mesh = _sculpt()
    return {n: depth(mesh, part=lambda points, n=n: _piece(points) == n) for n in PIECES}


def _placed(stage, part):
    return trimesh.transform_points(_cloud(stages.stem(stage.parts[part].file)), stage.parts[part].matrix)


def test_his_skin_is_cut_into_the_pieces_that_move_against_each_other():
    """In the head's frame: his chin's skin is the jaw's, the skin under his chin behind the eyes' plane and his nape's
    the head's, his chest's the shirt's."""
    eyes = stages.align(*stages.DOCS[morty.DOC]["eyes"])
    points = [(0.0, -30.0, -85.0), (0.0, 10.0, -100.0), (0.0, 100.0, -60.0), (0.0, -20.0, -160.0)]
    assert _piece(trimesh.transform_points(points, eyes)).tolist() == ["jaw", "head", "head", "torso"]


@pytest.mark.model
@pytest.mark.parametrize("part", _known(REST))
@pytest.mark.parametrize("doc", list(g.MECH))
def test_each_part_of_the_cranium_and_the_jaw_lies_under_mortys_skin_at_rest(doc, part, whole):
    """#1089: at rest every point of the part lies MARGIN inside his outer surface, above the collar's cut (under it
    the shirt's skin would stand still round a part the head turns); one that comes nearer or pokes through fails with
    its worst mm."""
    cloud = _placed(stages.STAGES[doc], part)
    assert "torso" not in _piece(cloud)
    assert round(float(whole(cloud).max()), 2) <= -MARGIN


@pytest.mark.model
@pytest.mark.parametrize("part", _known(MOVING))
@pytest.mark.parametrize("doc", list(g.MECH))
def test_no_piece_of_his_skin_comes_near_a_part_of_the_cranium_or_the_jaw_it_moves_against(doc, part, pieces):
    """#1089: over the tilt's, the pan's and the jaw's range, each piece of his skin keeps MARGIN from every point of
    a part it then moves against: the head's from the opening jaw, the jaw's from what stays in the head. A part
    that comes nearer fails with its least mm and where. A seam that opens between two pieces is the Skin's own
    (#850)."""
    stage, cloud, near = stages.STAGES[doc], _placed(stages.STAGES[doc], part), (MARGIN, None)
    carriers = {n: review.CARRIERS[n] for n in PIECES}
    rest = {n: np.linalg.inv(stage.parts[n].matrix) for n in (part, *carriers.values())}
    for horn in (h for h in stage.horns if h not in HORNS):
        low, high = stage.horns[horn].limits
        for deg in np.linspace(low, high, int((high - low) / STEP) + 2):
            mats = stages.pose(stage, horn, deg).parts
            for piece, carrier in carriers.items():
                past = np.linalg.inv(mats[carrier] @ rest[carrier]) @ mats[part] @ rest[part]  # in the piece's place
                if np.allclose(past, np.eye(4), atol=1e-9):
                    continue  # it rides with the piece here: the check at rest holds it
                mm = float(np.abs(pieces[piece](trimesh.transform_points(cloud, past))).min())
                if mm < near[0]:
                    near = (round(mm, 2), f"the {piece}'s skin, {horn} {deg:.0f}")
    assert near == (MARGIN, None)
