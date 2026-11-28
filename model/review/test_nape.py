"""Seam: the neck inside Morty's Sculpt as his Skin rides the head (#1039; #893's decision of 2026-11-27). The neck's
skin turns and nods with the head and ends at the collar (skin.cuts()), so above that cut the Sculpt's outer surface is
one rigid skin on the head, and each part of the neck Sub-assembly moves under it by whatever it does not turn with the
head: the cervical carrier with its reaction anchor stands still, the nod plate and the servos on it only tilt, the
tilt lever and its bar swing besides. Through tilt and pan together each keeps a Shell's wall and its clearance from
that skin, read on the Sculpt git holds (model/morty) as test_hidden.py reads the eye gimbal, so every run of the
Model's tests holds it. So does each finished vertebra, C1 to C7 (#874), which stands still with the carrier. The jaw's
parts and the cranium's are test_head.py's."""

import functools

import numpy as np
import pytest
import trimesh

from model import geometry as g
from model import morty, skeleton, skin, stages
from model.review.test_hidden import FRAME, MARGIN, _cloud, depth
from model.skeleton import envelope
from model.test_skin import _inside

PARTS = sorted(stages.neck_sub().parts)
TILT, PAN = "tilt horn", "pan horn"
STEPS = {TILT: 21, PAN: 31}  # each horn's range, sampled: the head every 2 deg of tilt and 3 deg of pan


@pytest.fixture(scope="module")
def head():
    """(points in the documents' world) -> mm each lies outside the head's skin at rest (negative: under it): Morty's
    Sculpt placed on the Mech's eyes, its outer surface above the collar's cut. Under the cut is the shirt's, which
    stands still: a point there is under the head's skin by its distance to the rim."""
    into = np.linalg.inv(stages.align(*stages.DOCS[morty.DOC]["eyes"]))  # the cuts are in the head's frame
    collar = skin.cuts()["collar"][1]

    def under(points):
        yz = trimesh.transform_points(points, into)[:, [1, 2]]
        return np.concatenate([_inside(some, collar) for some in np.array_split(yz, len(yz) // 100_000 + 1)])

    mesh = trimesh.load(stages.REPO + "/" + morty.SCULPT, process=False).apply_transform(morty.placed())
    outside = depth(mesh, part=lambda points: ~under(points))
    return lambda points: np.where(under(points), -np.abs(mm := outside(points)), mm)


@functools.cache
def _moves(doc, horn):
    """[(the head's turn, deg; {part: the 4x4 it moves by from rest})] over the horn's range, rest among them."""
    stage = stages.STAGES[doc]
    rest = {n: np.linalg.inv(stage.parts[n].matrix) for n in (*PARTS, FRAME)}
    out = []
    for deg in sorted({0.0, *np.linspace(*stage.horns[horn].limits, STEPS[horn])}):
        pose = stages.pose(stage, horn, deg)
        out.append((pose.joints[horn.replace("horn", "pivot")], {n: pose.parts[n] @ rest[n] for n in rest}))
    return out


@pytest.mark.model
@pytest.mark.parametrize("part", PARTS)
@pytest.mark.parametrize("doc", list(g.MECH))
def test_each_part_of_the_neck_stays_under_the_skin_that_rides_the_head(doc, part, head):
    """#1039: at every tilt and pan together, every point of the part lies MARGIN under the head's skin, which the
    head carries past it; the pan rides the tilt (model/neck.py HEAD_PARENTS). A part that comes nearer or pokes
    through fails with its worst mm and the head's pose there."""
    stage, worst, seen = stages.STAGES[doc], (-MARGIN, None), set()
    cloud = trimesh.transform_points(_cloud(stages.stem(stage.parts[part].file)), stage.parts[part].matrix)
    for tilt, tilted in _moves(doc, TILT):
        for pan, panned in _moves(doc, PAN):
            past = np.linalg.inv(tilted[FRAME] @ panned[FRAME]) @ tilted[part] @ panned[part]  # in the head's place
            if (key := past.round(9).tobytes()) in seen:
                continue  # a part on the nod plate passes the head by the pan alone
            seen.add(key)
            mm = float(head(trimesh.transform_points(cloud, past)).max())
            if mm > worst[0]:
                worst = (round(mm, 2), f"tilt {tilt:.0f} pan {pan:.0f}")
    assert worst == (-MARGIN, None)


@pytest.mark.model
@pytest.mark.bones
@pytest.mark.parametrize("bone", g.NECK)
def test_each_vertebra_stays_under_the_skin_that_rides_the_head(bone, head):
    """#874 (Cansin, 2026-11-27, #893's third round): at every tilt and pan together, every point of each finished
    vertebra, which stands still, lies a Shell's wall and its clearance (envelope.ROOM) under the head's skin, whose
    rim at the collar swings through the neck as the head nods: forward at the nape as it tilts back, back at the
    throat as it tilts forward. On the fit before, C5's rear arch stood 6 mm and more out of the nape tilted back, C6
    met both swings and C7's body came within 1.65 mm of the throat's."""
    doc = skeleton.DOC
    stage, worst = stages.STAGES[doc], (-envelope.ROOM, None)
    cloud = trimesh.transform_points(_cloud(bone), stage.parts[f"{bone}:1"].matrix)
    for tilt, tilted in _moves(doc, TILT):
        for pan, panned in _moves(doc, PAN):
            past = np.linalg.inv(tilted[FRAME] @ panned[FRAME])  # the still neck, in the head's place
            mm = float(head(trimesh.transform_points(cloud, past)).max())
            if mm > worst[0]:
                worst = (round(mm, 2), f"tilt {tilt:.0f} pan {pan:.0f}")
    assert worst == (-envelope.ROOM, None)
