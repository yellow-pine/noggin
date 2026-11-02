"""Seam: model/render/pictures.py exploded(), the whole Mech pulled apart for the front doors' side picture (#739), as
the viewer's Explode pulls it (#482, #664)."""

import numpy as np

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
