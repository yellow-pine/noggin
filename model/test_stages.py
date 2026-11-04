"""Seam: model/stages.py, the document tables (sub-assemblies, the Mech's documents: parts, neutral placements,
chains) and pose(): every part's rigid transform per horn angle. No meshes are read here."""

import numpy as np
import pytest

from model import geometry as g
from model import gimbal, printed, skin, stages


@pytest.mark.parametrize("doc,carrier", [("mech-back", "torso"), ("mech-back-mechanical", "torso mechanical")])
def test_the_mech_is_clean_room_its_owned_hardware_and_its_own_parts_in_its_own_document(doc, carrier):
    """#629, #618, #630, #641, #686: each of the Mech's documents (a head variant) holds our Envelopes of the
    hardware we own (two Cores and Shields, the switch board, the pack, seven servos each with its horn on a drive) and
    buy (the hub, the power-path board and the bulk capacitor, #858), and its own printed parts. Its neck's three servos
    drive it."""
    nxt = stages.STAGES[doc]
    meshes = [stages.stem(p.file) for p in nxt.parts.values()]
    hardware = sorted(m for m in meshes if m not in g.PRINTED)
    bought = ["hub", "power", "capacitor"]
    assert hardware == sorted(["core"] * 2 + ["receiver"] * 2 + ["switch", "battery", *bought] + ["servo", "horn"] * 7)
    assert {m for m in meshes if m in g.PRINTED} <= set(printed.PARTS) | set(g.BONES)  # the skull: meshes
    assert carrier in meshes
    assert set(nxt.horns) == {"pan horn", "tilt horn", "jaw horn", *(f"{d} horn" for d in gimbal.drives())}


@pytest.mark.parametrize("doc", sorted(d for d in stages.DOCS if "pan horn" in stages.STAGES[d].horns))
def test_what_rides_the_head_mount_turns_with_the_tilt_and_the_pan(doc):
    """The gimbal frame is screwed to the head mount (RIDES): the tilt and the pan carry it and its servos."""
    stage = stages.STAGES[doc]
    for horn, deg in (("tilt horn", 10), ("pan horn", 10)):
        moved = stages.pose(stage, horn, deg)
        carrier = moved.parts["head mount:1"] @ np.linalg.inv(stage.parts["head mount:1"].matrix)
        for name in ("gimbal frame:1", "L lid servo:1"):
            assert np.allclose(moved.parts[name] @ np.linalg.inv(stage.parts[name].matrix), carrier), (horn, name)
        assert np.allclose(moved.parts["torso:1"], stage.parts["torso:1"].matrix)


def test_each_mech_variant_is_built_mechanical_too_from_the_same_layout():
    """#704: mech-back-mechanical is mech-back part for part, the same names where the same placements put
    them, each Skeleton part with a mechanical style (model/printed STYLED) drawn mechanical, every other the same; the
    realistic skull's bones on the realistic one alone (#838)."""
    bones, mechanical = stages.STAGES["mech-back"], stages.STAGES["mech-back-mechanical"]
    skull = [f"{g.WORN.get(s, s)}:1" for s in g.SKULL]
    assert list(mechanical.parts) == [n for n in bones.parts if n not in skull] and set(mechanical.horns) == set(
        bones.horns
    )
    assert set(skull) <= set(bones.parts)
    for name, p in mechanical.parts.items():
        q, p, s = p, bones.parts[name], stages.stem(bones.parts[name].file)
        assert np.array_equal(q.matrix, p.matrix) and q.material == p.material, name
        assert stages.stem(q.file) == (s + g.MECHANICAL if s in printed.STYLED else s), name
    assert "mech-back-mechanical" in g.MECH
    assert stages.DOCS["mech-back-mechanical"] == {
        k: f for k, f in stages.DOCS["mech-back"].items() if k != g.SKULL_SUB
    }


def _drawn(skin_shape):
    return [s for s in skin.DRAWN if s.startswith(f"{skin_shape} ")]


def test_stage_3_in_cansins_skin_is_the_same_mech_wearing_his_shells_for_mortys():
    """#813: the Skeleton, its horns and what each moves the same; Cansin's Shells in place of Morty's, each glued one
    riding the part that moves its carrier."""
    for doc in g.MECH:
        three, dressed = stages.STAGES[doc], stages.STAGES[g.dressed(doc, "cansin")]
        morty, cansin = ({n + ":1" for n in _drawn(s)} for s in ("morty", "cansin"))
        assert set(dressed.parts) == set(three.parts) - morty | cansin
        assert set(dressed.horns) == set(three.horns)
        jaw = {n for loop in dressed.horns["jaw horn"].loops for n in loop.rockers}
        assert {"cansin mouth cover:1", "cansin teeth:1"} <= jaw
        tilt = {n for loop in dressed.horns["tilt horn"].loops for n in loop.rockers}
        assert {"cansin hair:1", "cansin L brow:1", "cansin R pupil:1"} <= tilt


def test_the_mechs_stages_build_up_from_the_eye_block_on_its_stand_to_the_whole_mech():
    """#720: Stage 1 the eye block (its gimbal, lids and four servos) on its test stand with the eyes Core; Stage 2 the
    eye block on the Torso's neck (pan, tilt) under the head mount, the neck Core beside the eyes' in the Torso (#838);
    Stage 3 adds the
    jaw and the mouth servo, and Morty's Skin (#665): the whole Mech, the head variant's document. Each Stage in every
    Skeleton."""
    one, two, three = (stages.STAGES[d] for d in list(g.STAGES)[:3])
    assert three is stages.STAGES[next(iter(g.MECH))]
    eye_horns = {f"{d} horn" for d in gimbal.drives()}
    assert set(one.horns) == eye_horns and {"test stand:1", "Shield 1:1", "Core 1:1"} <= set(one.parts)
    assert set(two.horns) == eye_horns | {"pan horn", "tilt horn"} and set(three.horns) == set(two.horns) | {"jaw horn"}
    assert set(one.parts) - {"test stand:1"} < set(two.parts) < set(three.parts)
    assert {"Shield 2:1", "Core 2:1", "torso:1", "head mount:1"} <= set(two.parts) - set(one.parts)
    assert set(three.parts) - set(two.parts) == {
        "jaw:1",
        "jaw bar:1",
        "mouth servo:1",
        "mouth horn:1",
    } | {n + ":1" for n in [*_drawn("morty"), *(g.WORN.get(s, s) for s in g.SKULL)]}
    assert set(g.STAGES) == {d + look for d in list(g.STAGES)[:3] for look in ("", "-mechanical")}


@pytest.mark.parametrize(
    "shell, horn, carrier",
    [
        ("morty face", "tilt horn", "gimbal frame"),
        ("morty hair", "pan horn", "gimbal frame"),
        ("morty mouth cover", "jaw horn", "jaw"),
        ("morty L upper lid cover", "L lid horn", "L upper lid"),
        ("morty R pupil", "yaw horn", "R eyeball cap"),
    ],
)
def test_a_shell_moves_with_what_carries_it(shell, horn, carrier):
    """#665: each Shell is clamped to its carrier (RIDES): turned by a servo, the two move as one."""
    three = stages.STAGES[next(iter(g.MECH))]
    moved = stages.pose(three, horn, 10).parts
    turn = moved[carrier + ":1"] @ np.linalg.inv(three.parts[carrier + ":1"].matrix)
    assert not np.allclose(turn, np.eye(4))
    np.testing.assert_allclose(moved[shell + ":1"], turn @ three.parts[shell + ":1"].matrix, atol=1e-9)


def test_the_jaw_rides_the_head_and_the_stand_carries_nothing():
    """The jaw is clamped to the head mount (RIDES): the tilt carries the jaw and its servo. Stage 1's eye block sits
    still on its stand: only the eye block's own horns move it."""
    three = stages.STAGES[next(iter(g.MECH))]
    moved = stages.pose(three, "tilt horn", 10)
    carrier = moved.parts["head mount:1"] @ np.linalg.inv(three.parts["head mount:1"].matrix)
    for name in ("jaw:1", "mouth servo:1"):
        assert np.allclose(moved.parts[name] @ np.linalg.inv(three.parts[name].matrix), carrier), name
    one = stages.STAGES["stage1"]
    moved = stages.pose(one, "yaw horn", 10)
    for name in ("test stand:1", "gimbal frame:1", "Core 1:1"):
        assert np.allclose(moved.parts[name], one.parts[name].matrix), name
