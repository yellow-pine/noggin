import functools
import itertools
import math

import mujoco
import numpy as np
import pytest
import trimesh

from model import geometry as g
from model import gimbal, mjcf, skin, stages

pytestmark = pytest.mark.model
PENETRATION_MM = 0.05
# Pairs that touch by design.
TOUCH = {
    # the next Mech's eye gimbal (#630): its exact solids overlap nowhere but the horns' splines
    # (model/printed/test_gimbal.py); the convex pieces fill its cups, bores and windows where parts meet
    **{
        frozenset((f"next {s} push-rod:1", p)): "the push-rod's cup round the ball"
        for s in "LR"
        for p in (f"next {s} eyeball core:1", "next bail:1")
    },
    **{
        frozenset((f"next {d} servo:1", p)): "the horn on its spline, the tabs on the frame's collar"
        for d in gimbal.drives()
        for p in (f"next {d} horn:1", "next gimbal frame:1")
    },
    **{
        frozenset(pair): "a horn on its bar, pin-joined faces, the cap on its seat (0.0 mm, designed contacts)"
        for pair in [
            ("next yaw horn:1", "next tie-bar:1"),
            ("next pitch horn:1", "next pitch bar:1"),
            ("next pitch bar:1", "next bail:1"),
            ("next bail:1", "next gimbal frame:1"),
            *[(f"next {s} lid horn:1", f"next {s} lid bar:1") for s in "LR"],
            *[(f"next {s} upper lid:1", f"next {s} lid bar:1") for s in "LR"],
            *[(f"next {s} lid bar:1", f"next {s} lid link:1") for s in "LR"],
            *[(f"next {s} lid link:1", f"next {s} lower lid:1") for s in "LR"],
            *[(f"next {s} upper lid:1", f"next {s} lower lid:1") for s in "LR"],  # bosses side by side on the shank
            *[(f"next {s} yaw yoke:1", p) for s in "LR" for p in ("next tie-bar:1", "next gimbal frame:1")],
            *[(f"next {s} eyeball cap:1", f"next {s} eyeball core:1") for s in "LR"],
        ]
    },
    # the next Mech's neck and jaw (#641): the same, the head mount screwed under the gimbal frame's plate
    **{
        frozenset((f"next {d} servo:1", p)): "the horn on its spline, the tabs on their collar"
        for d, mount in (("pan", "next neck mount:1"), ("tilt", "next pan yoke:1"), ("mouth", "next head mount:1"))
        for p in (f"next {d} horn:1", mount)
    },
    **{
        frozenset(
            pair
        ): "screwed faces, the yoke on the mount's thrust face, pin-joined faces (0.0 mm, designed contacts)"
        for pair in [
            ("next head mount:1", "next gimbal frame:1"),
            ("next head mount:1", "next pan yoke:1"),
            ("next pan yoke:1", "next neck mount:1"),
            ("next pan bar:1", "next pan yoke:1"),
            ("next pan bar:1", "next pan horn:1"),
            ("next tilt bar:1", "next tilt horn:1"),
            ("next tilt bar:1", "next head mount:1"),
            ("next jaw bar:1", "next mouth horn:1"),
            ("next jaw bar:1", "next jaw:1"),
            ("next jaw:1", "next head mount:1"),
        ]
    },
    # the Torso (#685) and Back's board rack (#686, #712): the same
    **{frozenset((f"next Core {n}:1", f"next Shield {n}:1")): "the Core plugged into its Shield" for n in (1, 2)},
    **{
        frozenset(pair): "standing on, screwed under or lying in (0.0 mm, designed contacts)"
        for pair in [
            *(
                ("next board rack:1", f"{b}:1")
                for b in ("next Core 1", "next Core 2", "next Shield 1", "next Shield 2")
            ),
            ("next board rack:1", "next switch board:1"),
            ("next board rack:1", "next gimbal frame:1"),
            # Stage 1's test stand (#720): under the gimbal frame's plate, the eyes Core against its back face
            *(("next test stand:1", p) for p in ("next gimbal frame:1", "next Core 1:1", "next Shield 1:1")),
        ]
    },
    **{
        frozenset(pair): "standing on, screwed under or lying in (0.0 mm, designed contacts)"
        for pair in [
            ("next torso:1", "next neck mount:1"),
            ("next torso:1", "next pack:1"),
        ]
    },
}
DOC = g.SIMULATED[-1]  # the whole Mech, mechanical: physics runs on it (#809)
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


@pytest.mark.parametrize("doc", grouped(g.SIMULATED))
def test_every_part_sits_where_stages_places_it(doc):
    """The tracer (#147): every part is a MuJoCo body whose placement, after MuJoCo's own forward kinematics, puts its
    mesh's bounding-box corners within 0.1 mm of model/stages.py's pose at 0 degrees (the document's frame is MuJoCo's)."""
    stage = stages.STAGES[doc]
    model, data = forward(doc)
    placed = {n: p.matrix for n, p in stage.parts.items()}  # pose()'s at 0 deg
    assert {model.body(i).name for i in range(1, model.nbody)} == set(placed)
    for name, expected in placed.items():
        body = data.body(name)
        lo, hi = trimesh.load(stage.parts[name].file, force="mesh").bounds
        corners = np.array([[*c, 1.0] for c in itertools.product(*zip(lo, hi))])
        actual = corners[:, :3] @ body.xmat.reshape(3, 3).T + body.xpos * 1000  # metres in MuJoCo, mm in stages
        worst = np.linalg.norm(actual - (corners @ expected.T)[:, :3], axis=1).max()
        assert worst < 0.1, (name, worst)


@pytest.mark.parametrize("doc", grouped(g.SIMULATED))
def test_no_two_parts_overlap_at_rest_unless_they_touch_by_design(doc):
    """No two parts that do not touch by design (TOUCH) overlap by more than 0.05 mm (MuJoCo's signed distance between
    their convex pieces): a sub-assembly in the wrong frame cannot hide."""
    model, data = forward(doc)
    allowed = set(TOUCH)
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


# the viewer's tests on the worker that builds DOC for its own tests (CI's --dist loadgroup): one build, not three
@pytest.mark.xdist_group(DOC)
def test_the_viewer_look_stays_as_cansin_kept_it():
    """just view's settings, frozen 2026-11-01: the headlight that keeps colours, black and white pulled in; each part
    in its Colour group's filament in the document's Theme (geometry.THEMES, #805)."""
    model, _ = forward(DOC)
    light = model.vis.headlight
    assert (list(light.ambient), list(light.diffuse), list(light.specular)) == ([0.5] * 3, [0.5] * 3, [0.0] * 3)
    drawn = {model.body(model.geom_bodyid[i]).name: model.geom_rgba[i] for i in np.flatnonzero(model.geom_group == 2)}

    def rgba(hexc):
        return [*trimesh.visual.color.hex_to_rgba(hexc)[:3] / 255, 1]

    theme = g.theme(DOC)
    for part, group in (
        ("next torso:1", "Bones"),
        ("next board rack:1", "Mounts"),
        ("next L eyeball cap:1", "eye whites"),
    ):
        hexc = g.filament(group, theme)[3]
        assert np.allclose(drawn[part], rgba(mjcf.VIEW.get(hexc, hexc))), part
    assert mjcf.VIEW == {"#000000": "#5A5A60", "#FFFFFF": "#E8E8E8"}  # black and white pulled in


@pytest.mark.xdist_group(DOC)
def test_the_viewer_adds_a_key_light_that_casts_shadows_and_satin_on_the_drawn_parts():
    """#150: on top of the frozen look, one light from the Mech's upper front-left casts shadows, and every drawn part
    is satin (a little specular), as the pictures' plastic; the collision pieces stay plain."""
    model, _ = forward(DOC)
    assert model.nlight == 1 and model.light_castshadow[0] and model.light_dir[0][2] < 0
    satin = model.material("satin").id
    assert (model.geom_matid[model.geom_group == mjcf.VISUAL] == satin).all()
    assert (model.geom_matid[model.geom_group == mjcf.COLLISION] == -1).all()


@pytest.mark.xdist_group(DOC)
def test_make_view_draws_the_mech_on_the_flat_sky_offscreen():
    """A document as just view's free camera first sees it, rendered offscreen (CI: MUJOCO_GL=egl): the corners are the
    flat sky, and the Mech covers part of the frame."""
    model, data = forward(DOC)
    with mujoco.Renderer(model, 240, 320) as r:
        r.update_scene(data)
        img = r.render().astype(int)
    sky = trimesh.visual.color.hex_to_rgba(mjcf.SKY)[:3]
    corners = img[[0, 0, -1, -1], [0, -1, 0, -1]]
    assert np.abs(corners - sky).max() <= 3, corners
    assert 0.05 < (np.abs(img - sky).max(axis=2) > 3).mean() < 0.95


@functools.cache
def sweep(doc):
    """{(horn, deg): MjData} with each horn driven by its servo from its lower to its upper limit in SWEEP_DEG steps,
    the other horns held at neutral."""
    model = built(doc)
    return {
        (h, d): mjcf.pose(model, {h: d})
        for h, horn in stages.STAGES[doc].horns.items()
        for d in [*np.arange(*horn.limits, SWEEP_DEG).tolist(), horn.limits[1]]
    }


MOVING = [doc for doc in g.SIMULATED if stages.STAGES[doc].horns]


@pytest.mark.parametrize("doc", grouped(MOVING))
def test_every_four_bar_and_push_rod_closes_by_a_connect(doc):
    """Each four-bar and push-rod is closed by a connect at its coupler's rocker pin; its loops are gated by the sim
    report's sweep, where the ranking can mark them (#705, model/test_report.py)."""
    model = built(doc)
    assert model.neq == sum(len(h.loops) + len(h.rods) for h in stages.STAGES[doc].horns.values())


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


def test_every_part_weighs_its_mass_spread_over_its_pieces():
    """Each part's CoACD pieces share its mass from its mesh (mjcf.mass) by volume; a Skin's drawn Shells weigh
    nothing (model/skin.py DRAWN)."""
    model, stage = built(DOC), stages.STAGES[DOC]
    for name, part in stage.parts.items():
        drawn = stages.stem(part.file) in skin.DRAWN
        grams = 0.0 if drawn else mjcf.mass(mjcf._mesh(part.file, part.clip), part.material)
        assert model.body(name).mass[0] * 1000 == pytest.approx(grams, abs=0.01), name


@pytest.mark.parametrize("stem", sorted(mjcf.MAX_PIECES))
def test_a_grown_part_cuts_into_no_more_pieces_than_its_cap(stem):
    assert 0 < len(mjcf.convex(stages.stl(stem))) <= mjcf.MAX_PIECES[stem]


def test_mass_follows_density_or_the_documented_figure():
    cube = trimesh.creation.box((10.0, 10.0, 10.0))  # 1 cm3
    assert mjcf.mass(cube, (1.24, "PLA Pure")) == pytest.approx(1.24)
    assert mjcf.mass(cube, (16.0, "documented")) == 16.0
