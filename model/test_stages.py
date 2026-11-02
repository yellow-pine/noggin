"""Seam: model/stages.py, the document tables (sub-assemblies, the next Mech's documents: parts, neutral placements,
chains) and pose(): every part's rigid transform per horn angle. No meshes are read here."""

import numpy as np
import pytest

from model import geometry as g
from model import gimbal, printed, stages


@pytest.mark.parametrize(
    "doc,carrier", [("next-mech-back", "next board rack"), ("next-mech-back-plain", "next board rack plain")]
)
def test_the_next_mech_is_clean_room_its_owned_hardware_and_its_own_parts_in_its_own_document(doc, carrier):
    """#629, #618, #630, #641, #686: each of the next Mech's documents (a head variant) holds our Envelopes of the
    hardware we own (two Cores and Shields, the switch board, the pack, seven servos each with its horn on a drive) and
    its own printed parts, all named "next", its boards on its carrier. Its neck's three servos drive it."""
    nxt = stages.STAGES[doc]
    meshes = [stages.stem(p.file) for p in nxt.parts.values()]
    hardware = sorted(m for m in meshes if not m.startswith("next "))
    assert hardware == sorted(["core"] * 2 + ["receiver"] * 2 + ["switch", "battery"] + ["servo"] * 7 + ["horn"] * 7)
    assert {m for m in meshes if m.startswith("next ")} <= set(printed.PARTS)
    assert carrier in meshes
    assert set(nxt.horns) == {"pan horn", "tilt horn", "jaw horn", *(f"next {d} horn" for d in gimbal.drives())}


@pytest.mark.parametrize("doc", sorted(stages.DOCS))
def test_what_rides_the_head_mount_turns_with_the_tilt_and_the_pan(doc):
    """The gimbal frame and the board rack are screwed to the head mount (RIDES): the tilt and the pan carry them."""
    stage = stages.STAGES[doc]
    for horn, deg in (("tilt horn", 10), ("pan horn", 10)):
        moved = stages.pose(stage, horn, deg)
        carrier = moved.parts["next head mount:1"] @ np.linalg.inv(stage.parts["next head mount:1"].matrix)
        for name in ("next gimbal frame:1", "next board rack:1", "next L lid servo:1"):
            assert np.allclose(moved.parts[name] @ np.linalg.inv(stage.parts[name].matrix), carrier), (horn, name)
        assert np.allclose(moved.parts["next torso:1"], stage.parts["next torso:1"].matrix)


def test_each_next_mech_variant_is_built_plain_too_from_the_same_layout():
    """#704: next-mech-back-plain is next-mech-back part for part, the same names where the same placements put them,
    each Skeleton part with a plain style (model/printed STYLED) drawn plain, every other the same."""
    bones, plain = stages.STAGES["next-mech-back"], stages.STAGES["next-mech-back-plain"]
    assert list(plain.parts) == list(bones.parts) and set(plain.horns) == set(bones.horns)
    for name, p in bones.parts.items():
        q, s = plain.parts[name], stages.stem(p.file)
        assert np.array_equal(q.matrix, p.matrix) and q.material == p.material, name
        assert stages.stem(q.file) == (s + g.PLAIN if s in printed.STYLED else s), name
    assert "next-mech-back-plain" in g.NEXT and stages.DOCS["next-mech-back-plain"] == stages.DOCS["next-mech-back"]
