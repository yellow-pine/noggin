"""Seam: model/stages.py, the document tables (sub-assemblies, the Mech's documents: parts, neutral placements,
chains) and pose(): every part's rigid transform per horn angle. No meshes are read here."""

import numpy as np
import pytest

from model import geometry as g
from model import gimbal, printed, stages


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
    assert hardware == sorted(
        ["core"] * 2
        + ["receiver"] * 2
        + ["switch", "battery", *bought, "pan bearing"]
        + ["standard servo", "standard horn"] * 2
        + ["servo", "horn"] * 5
    )
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


def test_the_mechs_stages_build_up_from_the_eye_block_on_its_stand_to_the_whole_mech():
    """#720: Stage 1 the eye block (its gimbal, lids and four servos) on its test stand with the eyes Core; Stage 2 the
    eye block on the Torso's neck (pan, tilt) under the head mount, the neck Core beside the eyes' in the Torso (#838);
    Stage 3 adds the
    jaw and the mouth servo: the whole Mech, the head variant's document. Each Stage in every Skeleton."""
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
    } | {g.WORN.get(s, s) + ":1" for s in g.SKULL}
    assert set(g.STAGES) == {d + look for d in list(g.STAGES)[:3] for look in ("", "-mechanical")}


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


def test_each_stage_counts_the_fasteners_its_pivots_servos_and_head_mount_take():
    """#964: a Stage's fasteners, counted from the model's pivots, servos and head screws, by hand from the parts' bores:
    Stage 1's eyes take 23 shanks (the yaw 5, the pitch 8 with the bail's and each core's pair, each lid drive 5, its
    lower lid on the upper's shank, the push-rods on balls), 2 screws per servo and the test stand's 4 screws and nuts;
    Stage 2 adds the pan's 3 and the tilt's 4 (its horn's and reaction bar's pins, its trunnions' pair), 4 screws
    per standard servo, and moves the stand's screws to the head mount; Stage 3 the jaw's 4."""
    shank, tab, head, nut = "M3 x 16 mm pivot screw", "M2 x 8 mm servo screw", "M3 x 10 mm head screw", "M3 nut"
    assert [stages.fasteners(d) for d in ("stage1", "stage2", "mech-back")] == [
        {shank: 23, tab: 8, head: 4, nut: 4},
        {shank: 30, tab: 16, head: 4, nut: 4},
        {shank: 34, tab: 18, head: 4, nut: 4},
    ]


def test_every_irregular_pivot_names_a_joint_the_mech_has():
    """#964: each pivot whose shank count is not one (stages.SHANKS) is a joint of the Mech's horns, so a renamed joint
    cannot drop out of the count unseen."""
    mech = stages.STAGES["mech-back"].horns.values()
    joints = {j for h in mech for j in [loop.joint for loop in h.loops] + [r.hinge[0] for r in h.rods]}
    joints |= {h.direct.joint for h in mech if h.direct}
    assert set(stages.SHANKS) <= joints
