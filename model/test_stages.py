"""Seam: model/stages.py, the document tables (sub-assemblies, the next Mech's documents: parts, neutral placements,
chains) and pose(): every part's rigid transform per horn angle. No meshes are read here."""

import numpy as np
import pytest

from model import geometry as g
from model import gimbal, printed, skin, stages


@pytest.mark.parametrize(
    "doc,carrier", [("next-mech-back", "next torso"), ("next-mech-back-mechanical", "next torso mechanical")]
)
def test_the_next_mech_is_clean_room_its_owned_hardware_and_its_own_parts_in_its_own_document(doc, carrier):
    """#629, #618, #630, #641, #686: each of the next Mech's documents (a head variant) holds our Envelopes of the
    hardware we own (two Cores and Shields, the switch board, both packs and the kit's charger dongle, #858, seven
    servos each with its horn on a drive) and its own printed parts, all named "next". Its neck's three servos drive
    it."""
    nxt = stages.STAGES[doc]
    meshes = [stages.stem(p.file) for p in nxt.parts.values()]
    hardware = sorted(m for m in meshes if not m.startswith("next "))
    boards = ["core", "receiver"] * 2 + ["switch", "battery", "battery", "dongle"]
    assert hardware == sorted(boards + ["servo", "horn"] * 7)
    assert {m for m in meshes if m.startswith("next ")} <= set(printed.PARTS) | set(g.BONES)  # the skull: meshes
    assert carrier in meshes
    assert set(nxt.horns) == {"pan horn", "tilt horn", "jaw horn", *(f"next {d} horn" for d in gimbal.drives())}


@pytest.mark.parametrize("doc", sorted(d for d in stages.DOCS if "pan horn" in stages.STAGES[d].horns))
def test_what_rides_the_head_mount_turns_with_the_tilt_and_the_pan(doc):
    """The gimbal frame is screwed to the head mount (RIDES): the tilt and the pan carry it and its servos."""
    stage = stages.STAGES[doc]
    for horn, deg in (("tilt horn", 10), ("pan horn", 10)):
        moved = stages.pose(stage, horn, deg)
        carrier = moved.parts["next head mount:1"] @ np.linalg.inv(stage.parts["next head mount:1"].matrix)
        for name in ("next gimbal frame:1", "next L lid servo:1"):
            assert np.allclose(moved.parts[name] @ np.linalg.inv(stage.parts[name].matrix), carrier), (horn, name)
        assert np.allclose(moved.parts["next torso:1"], stage.parts["next torso:1"].matrix)


def test_each_next_mech_variant_is_built_mechanical_too_from_the_same_layout():
    """#704: next-mech-back-mechanical is next-mech-back part for part, the same names where the same placements put
    them, each Skeleton part with a mechanical style (model/printed STYLED) drawn mechanical, every other the same; the
    realistic skull's bones on the realistic one alone (#838)."""
    bones, mechanical = stages.STAGES["next-mech-back"], stages.STAGES["next-mech-back-mechanical"]
    skull = [f"{g.WORN.get(s, s)}:1" for s in g.SKULL]
    assert list(mechanical.parts) == [n for n in bones.parts if n not in skull] and set(mechanical.horns) == set(
        bones.horns
    )
    assert set(skull) <= set(bones.parts)
    for name, p in mechanical.parts.items():
        q, p, s = p, bones.parts[name], stages.stem(bones.parts[name].file)
        assert np.array_equal(q.matrix, p.matrix) and q.material == p.material, name
        assert stages.stem(q.file) == (s + g.MECHANICAL if s in printed.STYLED else s), name
    assert "next-mech-back-mechanical" in g.NEXT
    assert stages.DOCS["next-mech-back-mechanical"] == {
        k: f for k, f in stages.DOCS["next-mech-back"].items() if k != g.SKULL_SUB
    }


def test_the_next_mechs_stages_build_up_from_the_eye_block_on_its_stand_to_the_whole_mech():
    """#720: Stage 1 the eye block (its gimbal, lids and four servos) on its test stand with the eyes Core; Stage 2 the
    eye block on the Torso's neck (pan, tilt) under the head mount, the neck Core beside the eyes' in the Torso (#838);
    Stage 3 adds the
    jaw and the mouth servo, and Morty's Skin (#665): the whole Mech, the head variant's document. Each Stage in every
    Skeleton."""
    one, two, three = (stages.STAGES[d] for d in list(g.STAGES)[:3])
    assert three is stages.STAGES[next(iter(g.NEXT))]
    eye_horns = {f"next {d} horn" for d in gimbal.drives()}
    assert set(one.horns) == eye_horns and {"next test stand:1", "next Shield 1:1", "next Core 1:1"} <= set(one.parts)
    assert set(two.horns) == eye_horns | {"pan horn", "tilt horn"} and set(three.horns) == set(two.horns) | {"jaw horn"}
    assert set(one.parts) - {"next test stand:1"} < set(two.parts) < set(three.parts)
    assert {"next Shield 2:1", "next Core 2:1", "next torso:1", "next head mount:1"} <= set(two.parts) - set(one.parts)
    assert set(three.parts) - set(two.parts) == {
        "next jaw:1",
        "next jaw bar:1",
        "next mouth servo:1",
        "next mouth horn:1",
    } | {n + ":1" for n in [*(s for s in skin.DRAWN if "next morty " in s), *(g.WORN.get(s, s) for s in g.SKULL)]}
    looks = ("", "-mechanical")
    assert set(g.STAGES) == {d + look for d in list(g.STAGES)[:3] for look in looks} | {
        f"next-mech-back{look}-bart" for look in looks
    }


@pytest.mark.parametrize("look", ["", "-mechanical"])
def test_stage_3_is_drawn_in_barts_skin_his_shells_on_mortys_seats(look):
    """#807: Stage 3 in each Skeleton shape and in Bart's Skin shape too (-bart, after the Skeleton's suffix, as the
    viewer names its GLBs): Morty's document with Bart's Shells in place of Morty's, each where Morty's sits and riding
    what Morty's rides, on the same Seats."""
    morty, bart = stages.STAGES[f"next-mech-back{look}"], stages.STAGES[f"next-mech-back{look}-bart"]
    swap = {n: n.replace("next morty ", "next bart ") for n in morty.parts}
    assert sorted(bart.parts) == sorted(swap.values()) and any(k != v for k, v in swap.items())
    for n, p in morty.parts.items():
        assert np.array_equal(bart.parts[swap[n]].matrix, p.matrix), n
    assert {swap.get(r, r): c for r, c in stages.RIDES.items() if "next morty " in r} == {
        r: c for r, c in stages.RIDES.items() if "next bart " in r
    }
    assert {(s.shell.replace("morty", "bart"), s.at) for s in skin.SEATS if "morty" in s.shell} == {
        (s.shell, s.at) for s in skin.SEATS if "bart" in s.shell
    }
    assert g.shape(f"next-mech-back{look}-bart") == g.shape(f"next-mech-back{look}")


@pytest.mark.parametrize(
    "shell, horn, carrier",
    [
        ("next morty face", "tilt horn", "next gimbal frame"),
        ("next morty hair", "pan horn", "next gimbal frame"),
        ("next morty mouth cover", "jaw horn", "next jaw"),
        ("next morty L upper lid cover", "next L lid horn", "next L upper lid"),
        ("next morty R pupil", "next yaw horn", "next R eyeball cap"),
    ],
)
def test_a_shell_moves_with_what_carries_it(shell, horn, carrier):
    """#665: each Shell is clamped to its carrier (RIDES): turned by a servo, the two move as one."""
    three = stages.STAGES[next(iter(g.NEXT))]
    moved = stages.pose(three, horn, 10).parts
    turn = moved[carrier + ":1"] @ np.linalg.inv(three.parts[carrier + ":1"].matrix)
    assert not np.allclose(turn, np.eye(4))
    np.testing.assert_allclose(moved[shell + ":1"], turn @ three.parts[shell + ":1"].matrix, atol=1e-9)


def test_the_jaw_rides_the_head_and_the_stand_carries_nothing():
    """The jaw is clamped to the head mount (RIDES): the tilt carries the jaw and its servo. Stage 1's eye block sits
    still on its stand: only the eye block's own horns move it."""
    three = stages.STAGES[next(iter(g.NEXT))]
    moved = stages.pose(three, "tilt horn", 10)
    carrier = moved.parts["next head mount:1"] @ np.linalg.inv(three.parts["next head mount:1"].matrix)
    for name in ("next jaw:1", "next mouth servo:1"):
        assert np.allclose(moved.parts[name] @ np.linalg.inv(three.parts[name].matrix), carrier), name
    one = stages.STAGES["next-stage1"]
    moved = stages.pose(one, "next yaw horn", 10)
    for name in ("next test stand:1", "next gimbal frame:1", "next Core 1:1"):
        assert np.allclose(moved.parts[name], one.parts[name].matrix), name
