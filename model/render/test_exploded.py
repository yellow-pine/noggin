"""Seam: model/render/pictures.py exploded(), the whole Mech pulled apart for the front doors' side picture (#739), as
the viewer's Explode pulls it (#482, #664)."""

import numpy as np
import pytest

from model import geometry as g
from model import stages
from model.render import pictures


def test_each_part_moves_by_its_sub_assemblys_offset_and_turns_not_at_all():
    """Stage 3 at rest (metres): the eyes lift 95 mm, the neck 45 mm, the jaw 45 mm and 40 mm forward, the Cores in the
    cranium 160 mm (#858), the base stays."""
    doc = next(iter(g.MECH))
    rest = {}
    for n, p in stages.STAGES[doc].parts.items():
        rest[n] = p.matrix.copy()
        rest[n][:3, 3] /= 1000
    apart = pictures.exploded(doc, rest)
    moved = {
        stages.eyes_sub: (0, 0, 0.095),
        stages.neck_sub: (0, 0, 0.045),
        stages.jaw_sub: (0, -0.04, 0.045),
        stages.cranium_sub: (0, 0, 0.16),
        stages.base_sub: (0, 0, 0),
    }
    assert apart.keys() == rest.keys()
    for sub, offset in moved.items():
        for n in sub().parts:
            assert np.allclose(apart[n][:3, 3] - rest[n][:3, 3], offset), n
            assert np.allclose(apart[n][:3, :3], rest[n][:3, :3]), n
    for shell, carrier in [  # a Shell with what carries it (#665)
        ("morty face:1", "gimbal frame:1"),
        ("morty mouth cover:1", "jaw:1"),
        ("morty shirt front:1", "torso:1"),
    ]:
        assert np.allclose(apart[shell][:3, 3] - rest[shell][:3, 3], apart[carrier][:3, 3] - rest[carrier][:3, 3])


def test_the_front_doors_show_the_mechanism_bare_of_every_shell():
    """#843: the front doors' Stage 3 drops the Skin's Shells, every Morty one and the eyeball caps, and keeps the
    rest."""
    doc = pictures.DRAWN[pictures.STAGE3][0]
    rest = {n: p.matrix for n, p in stages.STAGES[doc].parts.items()}
    bare = pictures.bare(doc, rest)
    caps = {"L eyeball cap:1", "R eyeball cap:1"}
    assert set(rest) - set(bare) == {n for n in rest if n.startswith("morty ")} | caps
    assert "gimbal frame:1" in bare and all(bare[n] is rest[n] for n in bare)


def test_the_bare_look_shows_the_skull_bare_where_a_skin_wears_its_worn_copy():
    """#838 (Cansin's B): the realistic document carries the skull and mandible a Skin wears (g.WORN); bare, the
    bones as they show bare stand in their places, and the atlas and axis stay."""
    doc = next(d for d in g.MECH if g.SKULL_SUB in g.MECH[d])
    rest = {n: p.matrix for n, p in stages.STAGES[doc].parts.items()}
    bare = pictures.bare(doc, rest)
    for full, worn in g.WORN.items():
        assert f"{worn}:1" in rest and f"{worn}:1" not in bare and bare[f"{full}:1"] is rest[f"{worn}:1"]
    assert {"atlas:1", "axis:1"} <= set(bare)


def _apart(doc, level):
    """{part: its mm offset at the level} (pictures.offsets) and {part: its world box at rest, mm}."""
    return pictures.offsets(doc, level), pictures.boxes(doc)


@pytest.mark.model
@pytest.mark.parametrize("doc", g.STAGES)
def test_at_the_parts_level_no_two_parts_boxes_overlap(doc):
    """#811: every part of each Stage, in each Skeleton, out of every other part's bounding box."""
    offsets, boxes = _apart(doc, 2)
    lo, hi = (np.array([boxes[n][i] + offsets[n] for n in boxes]) for i in (0, 1))
    names = list(boxes)
    for i, n in enumerate(names):
        inside = np.all((lo[i] < hi - 1e-6) & (hi[i] > lo + 1e-6), axis=1)
        inside[i] = False
        assert not inside.any(), (n, [names[j] for j in np.flatnonzero(inside)])


@pytest.mark.model
def test_each_part_slides_out_along_its_assembly_direction_on_its_sub_assemblys_offset():
    """Stage 3 (#811): the pack and the switch board up off the Torso's floor, each Core off the cranium tray (#858), each lid
    bar out along its Pivot's axis (the left eye's to +x), the pan horn up its servo's shaft beyond the servo; the
    Torso stays."""
    doc = next(iter(g.MECH))
    subs, parts = pictures.offsets(doc, 1), pictures.offsets(doc, 2)
    out = {n: np.subtract(parts[n], subs[n]) for n in parts}
    unit = {n: v / np.linalg.norm(v) for n, v in out.items() if np.linalg.norm(v)}
    assert np.allclose(out["torso:1"], 0)
    for n, d in {
        "pack:1": g.Z,
        "Core 1:1": g.Z,
        "switch board:1": g.Z,  # up off the Torso's floor (#828)
        "L lid bar:1": g.X,
        "R lid bar:1": (-1, 0, 0),
        "pan servo:1": g.Z,
        "pan horn:1": g.Z,
        "morty face:1": (0, -1, 0),  # forward off its Seats (#665)
        "morty hair:1": g.Z,
    }.items():
        assert np.allclose(unit[n], d), (n, out[n])
    assert out["pan horn:1"][2] > out["pan servo:1"][2]
