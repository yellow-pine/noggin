"""Seam: model/render/hero.py, the hero's hand-keyed timeline (#642) through the Mech's own neck."""

import pytest

from model import geometry as g
from model import neck, stages
from model.render import hero, scene

FPS = 10  # the trajectories' frames


@pytest.mark.parametrize("servo,horn", [("rotate", "pan horn"), ("tilt", "tilt horn")])
@pytest.mark.parametrize("doc", g.MECH)
def test_the_mech_plays_the_heros_head_keys_through_its_own_neck(doc, servo, horn):
    """#642: the Mech's hero turns its head the hero's head degrees through its own four-bars (model/neck.py), each
    frame inside the horn's limits; its jaw talks from shut to the jaw's open end, and the loop ends where it starts."""
    stage, joint = stages.STAGES[doc], horn.replace("horn", "pivot")
    frames = [hero.keys_at(i / FPS) for i in range(round(hero.SECONDS * FPS))]
    assert hero.keys_at(0) == hero.keys_at(hero.SECONDS)
    head = [stages.pose(stage, horn, f[servo]).joints[joint] for f in frames]
    keyed = [d for _, d in hero.HEAD[servo]]
    assert (min(head), max(head)) == pytest.approx((min(keyed), max(keyed)), abs=0.1)
    for f in frames:
        for s, deg in f.items():
            lo, hi = stage.horns[scene.HORNS[s]].limits
            assert lo - 1e-6 <= deg <= hi + 1e-6, (s, deg)
    jaw = [stages.pose(stage, "jaw horn", f["mouth"]).joints["jaw pivot"] for f in frames]
    assert (min(jaw), max(jaw)) == pytest.approx((0.0, max(neck.RANGES["jaw"])), abs=0.5)
