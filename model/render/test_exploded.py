"""Seam: model/render/pictures.py exploded(), the whole Mech pulled apart for the front doors' side picture (#739), as
the viewer's Explode pulls it (#482, #664)."""

import numpy as np
import pytest

from model import geometry as g
from model import stages
from model.render import pictures


def test_each_part_moves_by_its_sub_assemblys_offset_and_turns_not_at_all():
    """Stage 3 at rest (metres): the eyes lift 95 mm, the rack 95 mm and 60 mm back, the neck 45 mm, the jaw 45 mm and
    40 mm forward, the base stays."""
    doc = next(iter(g.NEXT))
    rest = {}
    for n, p in stages.STAGES[doc].parts.items():
        rest[n] = p.matrix.copy()
        rest[n][:3, 3] /= 1000
    apart = pictures.exploded(doc, rest)
    moved = {
        stages.next_eyes: (0, 0, 0.095),
        stages.next_back: (0, 0.06, 0.095),
        stages.next_neck: (0, 0, 0.045),
        stages.next_jaw: (0, -0.04, 0.045),
        stages.next_base: (0, 0, 0),
    }
    assert apart.keys() == rest.keys()
    for sub, offset in moved.items():
        for n in sub().parts:
            assert np.allclose(apart[n][:3, 3] - rest[n][:3, 3], offset), n
            assert np.allclose(apart[n][:3, :3], rest[n][:3, :3]), n
    for shell, carrier in [  # a Shell with what carries it (#665)
        ("next morty face:1", "next gimbal frame:1"),
        ("next morty mouth cover:1", "next jaw:1"),
        ("next morty shirt front:1", "next torso:1"),
    ]:
        assert np.allclose(apart[shell][:3, 3] - rest[shell][:3, 3], apart[carrier][:3, 3] - rest[carrier][:3, 3])


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
    """Stage 3 (#811): the pack up off the Torso's floor, a board back off the rack's face, each lid bar out along its
    Pivot's axis (the left eye's to +x), the pan horn up its servo's shaft beyond the servo; the Torso stays."""
    doc = next(iter(g.NEXT))
    subs, parts = pictures.offsets(doc, 1), pictures.offsets(doc, 2)
    out = {n: np.subtract(parts[n], subs[n]) for n in parts}
    unit = {n: v / np.linalg.norm(v) for n, v in out.items() if np.linalg.norm(v)}
    assert np.allclose(out["next torso:1"], 0)
    for n, d in {
        "next pack:1": g.Z,
        "next Core 1:1": g.Y,
        "next switch board:1": g.Y,
        "next L lid bar:1": g.X,
        "next R lid bar:1": (-1, 0, 0),
        "next pan servo:1": g.Z,
        "next pan horn:1": g.Z,
        "next morty face:1": (0, -1, 0),  # forward off its Seats (#665)
        "next morty hair:1": g.Z,
    }.items():
        assert np.allclose(unit[n], d), (n, out[n])
    assert out["next pan horn:1"][2] > out["next pan servo:1"][2]
