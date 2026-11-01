import functools
import itertools
import math

import mujoco
import numpy as np
import pytest
import trimesh

from model import electrical, mjcf
from model import geometry as g
from model.engine import masses, mating, stages

PENETRATION_MM = 0.05
# Pairs that touch by design besides the mating joints' (model/engine/mating.py JOINTS), and the pairs whose CoACD pieces
# overlap though the parts do not (MuJoCo collides each piece's convex hull; the exact clearance measured on the meshes
# with model/engine/meshes.judge at rest is given).
TOUCH = {
    **{
        frozenset((f"Core {n}:1", f"receiver shield {n}:1")): "the Core plugged into its shield's headers"
        for n in (1, 2)
    },
    **{
        frozenset(("base plate:1", p)): "on its posts or in its pocket"
        for p in ("receiver shield 1:1", "receiver shield 2:1", "switch board 1:1", "battery 1:1", "cable holder:1")
    },
    frozenset(("tilt arm:1", "eye bracket:1")): "the stem in the tilt arm window (STEM_IN)",
    frozenset(("base plate:1", "bearing block:1")): "the bearing block in the pan recess",
    frozenset(("bearing block:1", "pan turntable:1")): "the turntable on its bearing",
    **{frozenset((f"{s} eyeball:1", f"{s} pupil:1")): "the pupil glued in" for s in "LR"},
    **{
        frozenset((f"{s} upper lid:1", f"{s} lower lid:1")): "nested lid shells, 0.0 mm (a designed contact)"
        for s in "LR"
    },
    **{
        frozenset((f"{s} eyeball:1", f"{s} {lid} lid:1")): "the lid shell's pieces cut its 0.48 mm gap to the eyeball"
        for s in "LR"
        for lid in ("upper", "lower")
    },
    frozenset(("base plate:1", "pan servo:1")): "the plate's pieces fill the pan servo's pocket, 0.05 mm clear",
    frozenset(("base plate:1", "upright:1")): "the plate's pieces fill the recess under the upright, 0.5 mm clear",
}
# The desk documents only (geometry.DESK): the plate's front piece fills its stem slot and bridges the pan boss, so it
# overlaps the eyes standing on the plate top; on the meshes they touch, nothing inside (model/engine/test_meshes.py).
ON_PLATE = {frozenset(("base plate:1", p)) for p in ("eye bracket:1", "L servo bracket:1", "R servo bracket:1")}
# noggin-mouth carries the desk base as context, as its recorded sweep did: a pairing never built (the mouth rides the
# neck, stage 3): the eyes stand on the plate as on the desk, and its jaw parts and the rail bracket they hang on reach
# into the plate there.
MOUTH_ON_DESK = ON_PLATE | {
    frozenset(("base plate:1", p))
    for p in ("top jaw:1", "bottom jaw:1", "jaw servo mount:1", "jaw servo:1", "eye bracket:1")
}
MOUNTED = {frozenset((a, b)) for _, feats in mating.JOINTS for (a, _), (b, _) in itertools.combinations(feats, 2)}


LOOP_MM, TURN_DEG, SWEEP_DEG = 0.05, 0.5, 10


@functools.cache
def built(doc):
    return mjcf.model(doc)


def forward(doc):
    model = built(doc)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data


@pytest.mark.parametrize("doc", list(stages.DOCS))
def test_every_part_sits_where_the_engine_puts_it(doc):
    """The tracer (#147): every part is a MuJoCo body whose placement, after MuJoCo's own forward kinematics, puts its
    mesh's bounding-box corners within 0.1 mm of the old engine's pose at 0 degrees (carried into MuJoCo's Z-up world)."""
    stage = stages.STAGES[doc]
    model, data = forward(doc)
    engine = stages.pose(stage, next(iter(stage.horns)), 0).parts
    assert {model.body(i).name for i in range(1, model.nbody)} == set(engine)
    for name, matrix in engine.items():
        expected = mjcf.root(doc) @ matrix
        body = data.body(name)
        lo, hi = trimesh.load(stage.parts[name].file, force="mesh").bounds
        corners = np.array([[*c, 1.0] for c in itertools.product(*zip(lo, hi))])
        actual = corners[:, :3] @ body.xmat.reshape(3, 3).T + body.xpos * 1000  # metres in MuJoCo, mm in the engine
        worst = np.linalg.norm(actual - (corners @ expected.T)[:, :3], axis=1).max()
        assert worst < 0.1, (name, worst)


@pytest.mark.parametrize("doc", list(stages.DOCS))
def test_no_two_parts_overlap_at_rest_unless_they_are_mounted(doc):
    """No two parts that are not mounted to each other overlap by more than 0.05 mm (MuJoCo's signed distance between
    their convex pieces): a sub-assembly in the wrong frame cannot hide."""
    model, data = forward(doc)
    allowed = (
        MOUNTED
        | set(TOUCH)
        | (MOUTH_ON_DESK if doc == "noggin-mouth" else set())
        | (ON_PLATE if doc in g.DESK else set())
    )
    overlaps = {}
    for a, b in itertools.combinations(np.flatnonzero(model.geom_group == mjcf.COLLISION), 2):
        ba, bb = model.geom_bodyid[a], model.geom_bodyid[b]
        pair = tuple(sorted((model.body(ba).name, model.body(bb).name)))
        far = np.linalg.norm(data.geom_xpos[a] - data.geom_xpos[b]) > model.geom_rbound[a] + model.geom_rbound[b]
        if ba == bb or far or frozenset(pair) in allowed:
            continue
        mm = -1000 * mujoco.mj_geomDistance(model, data, a, b, 0.01, None)
        if mm > PENETRATION_MM:
            overlaps[pair] = max(overlaps.get(pair, 0), round(mm, 2))
    assert not overlaps, overlaps


def test_the_viewer_look_stays_as_cansin_kept_it():
    """make view's settings, frozen 2026-11-01: the headlight that keeps colours, black and white pulled in."""
    model, _ = forward("noggin-stage1")
    light = model.vis.headlight
    assert (list(light.ambient), list(light.diffuse), list(light.specular)) == ([0.5] * 3, [0.5] * 3, [0.0] * 3)
    drawn = {model.body(model.geom_bodyid[i]).name: model.geom_rgba[i] for i in np.flatnonzero(model.geom_group == 2)}
    assert np.allclose(drawn["base plate:1"], [0x5A / 255, 0x5A / 255, 0x60 / 255, 1])  # Absolute Black
    assert np.allclose(drawn["L eyeball:1"], [0xE8 / 255] * 3 + [1])  # Pure White


@functools.cache
def sweep(doc):
    """{(horn, deg): MjData} with each horn driven by its servo from its lower to its upper limit (geometry.LIMITS)
    in SWEEP_DEG steps, the other horns held at neutral."""
    model = built(doc)
    return {
        (h, d): mjcf.pose(model, {h: d})
        for h, horn in stages.STAGES[doc].horns.items()
        for d in [*range(horn.limits[0], horn.limits[1], SWEEP_DEG), horn.limits[1]]
    }


MOVING = [doc for doc in stages.DOCS if stages.STAGES[doc].horns]


@pytest.mark.parametrize("doc", MOVING)
def test_every_limit_poses_with_its_four_bars_closed(doc):
    """Each four-bar is closed by a connect at its coupler's rocker pin; at every geometry.LIMITS end the servo
    reaches (and the neck's pan x tilt corners), its two sites stay within 0.05 mm."""
    model = built(doc)
    assert model.neq == sum(len(h.loops) for h in stages.STAGES[doc].horns.values())
    horns = stages.STAGES[doc].horns
    ends = [{h: d} for h, horn in horns.items() for d in horn.limits]
    if {"pan horn", "tilt horn"} <= set(horns):  # the neck's corners too: the head at full pan and full tilt
        ends += [{"pan horn": p, "tilt horn": t} for p in horns["pan horn"].limits for t in horns["tilt horn"].limits]
    for ctrl in ends:
        worst = max(mjcf.residuals(model, mjcf.pose(model, ctrl)).values())
        assert worst < LOOP_MM, (ctrl, worst)


@pytest.mark.parametrize("doc", MOVING)
def test_the_joints_turn_as_the_old_engine_solves_the_four_bars(doc):
    """Across each horn's sweep the servo holds its command and every driven joint (lid, eyeball, tilt, pan, jaw) is
    within 0.5 degrees of the old engine's four-bar solve (model/engine/linkage.py) at that horn angle."""
    stage = stages.STAGES[doc]
    for (h, d), data in sweep(doc).items():
        expected = {h: d, **stages.pose(stage, h, d).joints}
        for joint, deg in expected.items():
            actual = math.degrees(data.joint(joint).qpos[0])
            assert abs(actual - deg) < TURN_DEG, (h, d, joint, actual, deg)


@pytest.mark.parametrize("doc", MOVING)
def test_every_lead_stays_within_its_length(doc):
    """Each lead (electrical.leads) whose two Ports the document has is a spatial tendon limited to the lead's real
    length; across every sweep it stays under it, the limit never pulling on the Mech."""
    model, stage = built(doc), stages.STAGES[doc]
    leads = {name: mm for name, a, b, mm in electrical.leads() if a in stage.ports and b in stage.ports}
    assert {model.tendon(i).name: model.tendon_range[i][1] * 1000 for i in range(model.ntendon)} == pytest.approx(leads)
    for (h, d), data in sweep(doc).items():
        pulling = data.efc_type[: data.nefc] == mujoco.mjtConstraint.mjCNSTR_LIMIT_TENDON
        assert not pulling.any(), (h, d, [model.tendon(i).name for i in data.efc_id[: data.nefc][pulling]])
        for i in range(model.ntendon):
            assert data.ten_length[i] < model.tendon_range[i][1], (h, d, model.tendon(i).name)


@pytest.mark.parametrize("doc", MOVING)
def test_every_screw_and_pin_joint_keeps_its_sites_together(doc):
    """Each screw or pin joint of model/engine/mating.py is a site per part on its own fitted axis; across every sweep
    they stay within the mating check's 0.2 mm (as far apart as the axes miss each other, and any drift a turn adds)."""
    model, stage = built(doc), stages.STAGES[doc]
    for (h, d), data in sweep(doc).items():
        gaps = mjcf.mating_gaps(model, data)
        assert set(gaps) == {j for j, feats in mating.JOINTS if all(p in stage.parts for p, _ in feats)}
        worst = max(gaps, key=gaps.get)
        assert gaps[worst] < mating.COAXIAL_MM, (h, d, worst, gaps[worst])


def test_every_part_weighs_what_the_engine_weighs_it():
    """Each part's CoACD pieces share the old engine's mass for it (model/engine/masses.py) by volume."""
    model, stage = built("noggin-stage3"), stages.STAGES["noggin-stage3"]
    for name, part in stage.parts.items():
        g = masses.mass(mjcf._mesh(part.file, part.clip), part.material)["g"]
        assert model.body(name).mass[0] * 1000 == pytest.approx(g, abs=0.01), name
