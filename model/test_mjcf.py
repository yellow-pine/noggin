import copy
import functools
import itertools
import json
import math
import os

import mujoco
import numpy as np
import pytest
import trimesh

from model import electrical, mating, mjcf, mujoco_report, stages
from model import geometry as g

pytestmark = pytest.mark.model
PENETRATION_MM = 0.05
# Pairs that touch by design besides the mating joints' (model/mating.py JOINTS).
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
}
# The desk documents only (geometry.DESK): the eyes stand on the plate top, touching.
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


def grouped(docs):
    """Each document's tests on one xdist worker (CI's --dist loadgroup), so it is built and swept once, not per worker."""
    return [pytest.param(doc, marks=pytest.mark.xdist_group(doc)) for doc in docs]


def forward(doc):
    model = built(doc)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data


@pytest.mark.parametrize("doc", grouped(stages.DOCS))
def test_every_part_sits_where_stages_places_it(doc):
    """The tracer (#147): every part is a MuJoCo body whose placement, after MuJoCo's own forward kinematics, puts its
    mesh's bounding-box corners within 0.1 mm of model/stages.py's pose at 0 degrees (carried into MuJoCo's Z-up world)."""
    stage = stages.STAGES[doc]
    model, data = forward(doc)
    placed = stages.pose(stage, next(iter(stage.horns)), 0).parts
    assert {model.body(i).name for i in range(1, model.nbody)} == set(placed)
    for name, matrix in placed.items():
        expected = mjcf.root(doc) @ matrix
        body = data.body(name)
        lo, hi = trimesh.load(stage.parts[name].file, force="mesh").bounds
        corners = np.array([[*c, 1.0] for c in itertools.product(*zip(lo, hi))])
        actual = corners[:, :3] @ body.xmat.reshape(3, 3).T + body.xpos * 1000  # metres in MuJoCo, mm in stages
        worst = np.linalg.norm(actual - (corners @ expected.T)[:, :3], axis=1).max()
        assert worst < 0.1, (name, worst)


@pytest.mark.parametrize("doc", grouped(stages.DOCS))
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
    pieces = np.flatnonzero(model.geom_group == mjcf.COLLISION)
    pos, reach, body = data.geom_xpos, model.geom_rbound, model.geom_bodyid
    for i, a in enumerate(pieces):
        rest = pieces[i + 1 :]  # thousands of pieces: a row at a time, another part's whose bounding spheres meet a's
        for b in rest[(body[rest] != body[a]) & (np.linalg.norm(pos[rest] - pos[a], axis=1) <= reach[rest] + reach[a])]:
            pair = tuple(sorted((model.body(body[a]).name, model.body(body[b]).name)))
            if frozenset(pair) in allowed:
                continue
            mm = -1000 * mujoco.mj_geomDistance(model, data, a, b, 0.01, None)
            if mm > PENETRATION_MM:
                overlaps[pair] = max(overlaps.get(pair, 0), round(mm, 2))
    assert not overlaps, overlaps


# the viewer's tests on the worker that builds noggin-stage1 for its own tests (CI's --dist loadgroup): one build, not three
@pytest.mark.xdist_group("noggin-stage1")
def test_the_viewer_look_stays_as_cansin_kept_it():
    """make view's settings, frozen 2026-11-01: the headlight that keeps colours, black and white pulled in."""
    model, _ = forward("noggin-stage1")
    light = model.vis.headlight
    assert (list(light.ambient), list(light.diffuse), list(light.specular)) == ([0.5] * 3, [0.5] * 3, [0.0] * 3)
    drawn = {model.body(model.geom_bodyid[i]).name: model.geom_rgba[i] for i in np.flatnonzero(model.geom_group == 2)}
    assert np.allclose(drawn["base plate:1"], [0x5A / 255, 0x5A / 255, 0x60 / 255, 1])  # Absolute Black
    assert np.allclose(drawn["L eyeball:1"], [0xE8 / 255] * 3 + [1])  # Pure White


@pytest.mark.xdist_group("noggin-stage1")
def test_the_viewer_adds_a_key_light_that_casts_shadows_and_satin_on_the_drawn_parts():
    """#150: on top of the frozen look, one light from the Mech's upper front-left casts shadows, and every drawn part
    is satin (a little specular), as the pictures' plastic; the collision pieces stay plain."""
    model, _ = forward("noggin-stage1")
    assert model.nlight == 1 and model.light_castshadow[0] and model.light_dir[0][2] < 0
    satin = model.material("satin").id
    assert (model.geom_matid[model.geom_group == mjcf.VISUAL] == satin).all()
    assert (model.geom_matid[model.geom_group == mjcf.COLLISION] == -1).all()


@pytest.mark.xdist_group("noggin-stage1")
def test_make_view_draws_the_mech_on_the_flat_sky_offscreen():
    """A Stage as make view's free camera first sees it, rendered offscreen (CI: MUJOCO_GL=egl): the corners are the
    flat sky, and the Mech covers part of the frame."""
    model, data = forward("noggin-stage1")
    with mujoco.Renderer(model, 240, 320) as r:
        r.update_scene(data)
        img = r.render().astype(int)
    sky = trimesh.visual.color.hex_to_rgba(mjcf.SKY)[:3]
    corners = img[[0, 0, -1, -1], [0, -1, 0, -1]]
    assert np.abs(corners - sky).max() <= 3, corners
    assert 0.05 < (np.abs(img - sky).max(axis=2) > 3).mean() < 0.95


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


def ends(doc):
    """Every geometry.LIMITS end a servo reaches, and the neck's pan x tilt corners (the head at full pan and tilt)."""
    horns = stages.STAGES[doc].horns
    out = [{h: d} for h, horn in horns.items() for d in horn.limits]
    if {"pan horn", "tilt horn"} <= set(horns):
        out += [{"pan horn": p, "tilt horn": t} for p in horns["pan horn"].limits for t in horns["tilt horn"].limits]
    return out


@pytest.mark.parametrize("doc", grouped(MOVING))
def test_every_limit_poses_with_its_four_bars_closed(doc):
    """Each four-bar is closed by a connect at its coupler's rocker pin; at every geometry.LIMITS end the servo
    reaches (and the neck's pan x tilt corners), its two sites stay within 0.05 mm."""
    model = built(doc)
    assert model.neq == sum(len(h.loops) for h in stages.STAGES[doc].horns.values())
    for ctrl in ends(doc):
        worst = max(mjcf.residuals(model, mjcf.pose(model, ctrl)).values())
        assert worst < LOOP_MM, (ctrl, worst)


# Pairs the pieces read deeper than the exact-mesh check did, each verified (docs/research/2026-11-01-coacd-tuning.md 4): it weighed
# an overlap by its deepest vertex and missed edges that cross, MuJoCo by the shortest move that parts the two pieces,
# and the common region of the deepest two pieces lies inside both meshes. How deep they may read (mm), never shallower.
DEEPER = {
    **{frozenset((f"{s} upper lid:1", f"{s} lower lid:1")): 1.3 for s in "LR"},  # the ears cross, 1.09 at +31: #210
    **{frozenset((f"{s} upper lid:1", "eye bracket:1")): 0.45 for s in "LR"},  # 0.36 at +31: #210
}
# Pairs whose pieces fill a corner their meshes leave open, which CoACD's surface-sampled concavity does not see at any
# threshold tried (0.3 to 0.15 mm): how much nearer they may read (mm), measured on the Mac's pieces with a margin.
FILLED = {
    frozenset(("bearing block:1", "pan turntable:1")): 1.0,  # 0.93 into the turntable's recess corner over the rim
    frozenset(("top jaw:1", "bottom jaw:1")): 0.3,  # 0.31 into the hinge pin's hole, where the meshes touch
    frozenset(("pan turntable:1", "tilt horn:1")): 0.1,  # tilt -60: 0.118 where the meshes clear 0.174
}


# The exact-mesh check's last readings (#151 deleted it, model/engine/meshes.py judge): per document and pose (rest and every
# ends() pose, as MuJoCo poses it), every pair a joint moves apart whose boxes came within the report's band, its
# clearance in mm clamped to the band (negative: the depth of the deepest vertex inside). The model has moved on when a
# pose here no longer reads: refreeze from the old check (git show fb9878c:model/engine/meshes.py) or drop the pair.
EXACT = json.load(open(os.path.join(os.path.dirname(__file__), "test_fixtures", "exact-clearance.json")))
DEPTH_MM = 0.1  # the exact check's resolution: a 0 mm contact had nothing deeper than this inside


@pytest.mark.parametrize("doc", grouped(MOVING))
def test_the_pieces_read_the_clearance_the_exact_meshes_do(doc):
    """The convex pieces measure clearance as the exact meshes did (#190, docs/research/2026-11-01-coacd-tuning.md): at
    rest and at every LIMITS end, each pair reads within PENETRATION_MM of the exact check's frozen reading (EXACT, both
    clamped to the report's detection band, the two pieces' margins), but for DEEPER and FILLED. A contact the meshes
    called 0 mm had nothing deeper than DEPTH_MM in it, so the pieces may read that far in."""
    model = copy.copy(built(doc))
    mujoco_report.widen(model)
    band = 2 * mujoco_report.CLEARANCE_MM
    assert [p["at"] for p in EXACT[doc]] == [{}, *ends(doc)]
    off = {}
    for pose in EXACT[doc]:
        pieces = mujoco_report._contacts(model, mjcf.pose(model, pose["at"]))
        for key, mm in pose["mm"].items():
            pair = tuple(key.split(" / "))
            got, both = min(pieces.get(pair, band), band), frozenset(pair)
            low = -DEEPER[both] if both in DEEPER else mm - FILLED.get(both, PENETRATION_MM)
            low -= DEPTH_MM if abs(mm) < 1e-6 else 0
            miss = max(low - got, got - mm - PENETRATION_MM)
            if miss > off.get(pair, (0,))[0]:
                off[pair] = (round(miss, 3), pose["at"], mm, round(got, 3))
    assert not off, off


@pytest.mark.parametrize("doc", grouped(MOVING))
def test_the_joints_turn_as_the_four_bar_kinematics_solve_them(doc):
    """Across each horn's sweep the servo holds its command and every driven joint (lid, eyeball, tilt, pan, jaw) is
    within 0.5 degrees of the four-bar kinematics (model/linkage.py, stages.pose) at that horn angle."""
    stage = stages.STAGES[doc]
    for (h, d), data in sweep(doc).items():
        expected = {h: d, **stages.pose(stage, h, d).joints}
        for joint, deg in expected.items():
            actual = math.degrees(data.joint(joint).qpos[0])
            assert abs(actual - deg) < TURN_DEG, (h, d, joint, actual, deg)


@pytest.mark.parametrize("doc", grouped(MOVING))
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


@pytest.mark.parametrize("doc", grouped(MOVING))
def test_every_screw_and_pin_joint_keeps_its_sites_together(doc):
    """Each screw or pin joint of model/mating.py is a site per part on its own fitted axis; across every sweep
    they stay within the mating check's 0.2 mm (as far apart as the axes miss each other, and any drift a turn adds)."""
    model, stage = built(doc), stages.STAGES[doc]
    for (h, d), data in sweep(doc).items():
        gaps = mjcf.mating_gaps(model, data)
        assert set(gaps) == {j for j, feats in mating.JOINTS if all(p in stage.parts for p, _ in feats)}
        worst = max(gaps, key=gaps.get)
        assert gaps[worst] < mating.COAXIAL_MM, (h, d, worst, gaps[worst])


def test_every_part_weighs_its_mass_spread_over_its_pieces():
    """Each part's CoACD pieces share its mass from its mesh (mjcf.mass) by volume."""
    model, stage = built("noggin-stage3"), stages.STAGES["noggin-stage3"]
    for name, part in stage.parts.items():
        assert model.body(name).mass[0] * 1000 == pytest.approx(
            mjcf.mass(mjcf._mesh(part.file, part.clip), part.material), abs=0.01
        ), name


def test_mass_follows_density_or_the_documented_figure():
    cube = trimesh.creation.box((10.0, 10.0, 10.0))  # 1 cm3
    assert mjcf.mass(cube, (1.24, "PLA Pure")) == pytest.approx(1.24)
    assert mjcf.mass(cube, (16.0, "documented")) == 16.0


def test_printed_part_masses_match_the_recorded_sweep_masses():
    """The recorded sweep (model/reports/noggin-eyes-report.json, history kept as data) weighed the designer's
    parts; ours weigh the same within 2 percent."""
    recorded = json.load(open(os.path.join(os.path.dirname(__file__), "reports", "noggin-eyes-report.json")))["mass"]
    parts = stages.STAGES["noggin-eyes"].parts
    for name in ("L eyeball:1", "L servo bracket:1", "L lid bar:1", "L lid servo:1"):
        g_ = mjcf.mass(mjcf._mesh(parts[name].file, parts[name].clip), parts[name].material)
        assert g_ == pytest.approx(recorded[name], rel=0.02), name
