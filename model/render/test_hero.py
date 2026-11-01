"""Seam: model/render/hero.py, the README hero's hand-keyed stage 3 timeline: every frame inside the model's limits
(geometry.LIMITS) and, posed on stage 3, clear of any penetration the engine finds."""

import pytest

from model import geometry as g
from model.engine import stages
from model.render import hero

FRAMES = hero.frames()


def test_the_hero_is_an_eight_second_loop_that_moves_every_servo():
    assert len(FRAMES) / hero.FPS == 8
    assert hero.at(0) == hero.at(len(FRAMES) / hero.FPS)
    for servo in g.HORN_LIMITS:
        degs = [f[servo] for f in FRAMES]
        assert max(degs) - min(degs) > 5, servo


@pytest.mark.parametrize("servo,horn,designer", [("rotate", "pan horn", 25), ("tilt", "tilt horn", 15)])
def test_the_head_turns_and_nods_in_head_degrees_as_far_as_the_designer(servo, horn, designer):
    # Cansin (#117): about 25 deg of pan and 15 of nod, the head's own swing near the horn limits; the head keys are the
    # pivot degrees the engine's linkage solve gives for each frame's horn
    joint = horn.replace("horn", "pivot")
    head = [stages.pose(hero.STAGE, horn, f[servo]).joints[joint] for f in FRAMES]
    keyed = [d for _, d in hero.HEAD[servo]]
    assert max(map(abs, head)) == pytest.approx(designer, abs=1.5)
    assert max(head) == pytest.approx(max(keyed), abs=0.1)
    assert min(head) == pytest.approx(min(keyed), abs=0.1)


def test_every_pose_is_within_the_model_limits():
    for i, f in enumerate(FRAMES):
        for servo, deg in f.items():
            lo, hi = g.HORN_LIMITS[servo]
            assert lo - 90 <= deg <= hi - 90, (i, servo, deg)


@pytest.mark.heavy
def test_every_pose_is_clear_of_collisions():
    hits = {i: c for i, f in enumerate(FRAMES) if (c := hero.collisions(f))}
    assert hits == {}


def test_a_pose_past_the_tilt_limit_collides_as_the_engine_sweep_found():
    # geometry.LIMITS tilt: 1.16 mm deep at -70, the tilt horn and bar in the pan turntable
    assert {(a, b) for a, b, _ in hero.collisions({"tilt": -70.0})} == {
        ("pan turntable:1", "tilt horn:1"),
        ("pan turntable:1", "tilt bar:1"),
    }
