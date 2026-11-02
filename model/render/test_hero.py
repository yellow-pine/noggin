"""Seam: model/render/hero.py, the README hero's hand-keyed stage 3 timeline: every frame inside the model's limits
(geometry.LIMITS) and, posed on stage 3 by MuJoCo, no pair of parts deeper than at rest (as just sim's report judges a
sweep, model/mujoco_report.py)."""

import functools

import pytest

from model import geometry as g
from model import mjcf, mujoco_report, neck, stages
from model.render import hero, scene
from model.test_report import KNOWN_PAIRS

FRAMES = hero.frames()


@functools.cache
def stage3():
    """Stage 3's MJCF, widened as the report's (mujoco_report.widen), and its pairs' readings at rest."""
    model = mjcf.model("noggin-stage3")
    mujoco_report.widen(model)
    return model, mujoco_report._contacts(model, mjcf.pose(model, {}))


def collisions(joints):
    """{(part, part)} whose pieces go PENETRATION_MM deeper than at rest with each servo at joints[servo] (model horn
    degrees), the report's listed KNOWN_PAIRS aside."""
    model, rest = stage3()
    posed = mujoco_report._contacts(model, mjcf.pose(model, {scene.HORNS[s]: d for s, d in joints.items()}))
    return {
        pair
        for pair, mm in posed.items()
        if min(rest.get(pair, 0), 0) - mm > mujoco_report.PENETRATION_MM and frozenset(pair) not in KNOWN_PAIRS
    }


def test_the_hero_is_an_eight_second_loop_that_moves_every_servo():
    assert len(FRAMES) / hero.FPS == 8
    assert hero.at(0) == hero.at(len(FRAMES) / hero.FPS)
    for servo in g.HORN_LIMITS:
        degs = [f[servo] for f in FRAMES]
        assert max(degs) - min(degs) > 5, servo


@pytest.mark.parametrize("servo,horn,designer", [("rotate", "pan horn", 25), ("tilt", "tilt horn", 15)])
def test_the_head_turns_and_nods_in_head_degrees_as_far_as_the_designer(servo, horn, designer):
    # Cansin (#117): about 25 deg of pan and 15 of nod, the head's own swing near the horn limits; the head keys are the
    # pivot degrees the four-bar kinematics give for each frame's horn
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


@pytest.mark.model
@pytest.mark.parametrize("frame", range(len(FRAMES)))  # a test per frame: xdist spreads the sweep over its workers
def test_every_pose_is_clear_of_collisions(frame):
    assert collisions(FRAMES[frame]) == set()


@pytest.mark.model
def test_a_pose_past_the_tilt_limit_collides_as_the_sweep_found():
    # geometry.LIMITS tilt: 1.16 mm deep at -70 on the exact meshes, the tilt horn and bar in the pan turntable
    assert {("pan turntable:1", "tilt horn:1"), ("pan turntable:1", "tilt bar:1")} <= collisions({"tilt": -70.0})


@pytest.mark.parametrize("servo,horn,drive", [("rotate", "pan horn", "pan"), ("tilt", "tilt horn", "tilt")])
@pytest.mark.parametrize("doc", g.NEXT)
def test_the_next_mech_plays_the_heros_head_keys_through_its_own_neck(doc, servo, horn, drive):
    """#642: the next Mech's hero turns its head the hero's head degrees through its own four-bars (model/neck.py), each
    frame inside the horn's limits; its jaw talks from shut to the jaw's open end."""
    stage, joint = stages.STAGES[doc], horn.replace("horn", "pivot")
    frames = [hero.next_at(i / hero.FPS) for i in range(len(FRAMES))]
    head = [stages.pose(stage, horn, f[servo]).joints[joint] for f in frames]
    keyed = [d for _, d in hero.HEAD[servo]]
    assert (min(head), max(head)) == pytest.approx((min(keyed), max(keyed)), abs=0.1)
    for f in frames:
        for s, deg in f.items():
            lo, hi = stage.horns[scene.HORNS[s]].limits
            assert lo - 1e-6 <= deg <= hi + 1e-6, (s, deg)
    jaw = [stages.pose(stage, "jaw horn", f["mouth"]).joints["jaw pivot"] for f in frames]
    assert (min(jaw), max(jaw)) == pytest.approx((0.0, max(neck.RANGES["jaw"])), abs=0.5)
