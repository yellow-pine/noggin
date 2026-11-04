"""Seam: model/base.py, the next Mech's head variants (#686; Back alone since #712): where the boards go, the leads that
cross pan and tilt, and the ranking of their sim reports."""

import itertools

import cadquery as cq
import numpy as np
import pytest
import trimesh
from scipy.spatial import ConvexHull, cKDTree

from model import base, envelopes, skeleton, stages
from model import geometry as g
from model import neck as nk
from model.printed import base as printed_base
from model.test_envelopes import BOXES, solid

TOUCH_MM = 0.5  # two parts touch: a fit's clearance (a pin in its bore, a servo in its collar) is under it


@pytest.mark.model
@pytest.mark.parametrize("doc", sorted(g.STAGES))
def test_every_part_of_the_next_mech_is_mounted_on_the_assembly(doc):
    """#687: the Viewer and the pictures draw the next Mech assembled, nothing lying apart: every part of each document
    touches one that leads, part on part, down to the Torso (Stage 1's test stand, #720). Each part's surface sampled about 1 mm apart, plus its
    vertices: two touching faces have samples closer than TOUCH_MM, two 1 mm apart none."""
    parts = stages.STAGES[doc].parts
    meshes = {n: trimesh.load(p.file, force="mesh").apply_transform(p.matrix) for n, p in parts.items()}
    points = {
        n: np.vstack([m.vertices, trimesh.sample.sample_surface(m, int(m.area), seed=0)[0]]) for n, m in meshes.items()
    }
    trees = {n: cKDTree(p) for n, p in points.items()}
    near = {n: set() for n in meshes}
    for a, b in itertools.combinations(meshes, 2):
        (lo_a, hi_a), (lo_b, hi_b) = meshes[a].bounds, meshes[b].bounds
        if not (np.maximum(lo_a - hi_b, lo_b - hi_a) < TOUCH_MM).all():
            continue
        close = points[a][((points[a] > lo_b - TOUCH_MM) & (points[a] < hi_b + TOUCH_MM)).all(axis=1)]  # by b alone
        if len(close) and trees[b].query(close, distance_upper_bound=TOUCH_MM)[0].min() < TOUCH_MM:
            near[a].add(b)
            near[b].add(a)
    reached, todo = set(), ["next torso:1" if "next torso:1" in parts else "next test stand:1"]
    while todo:
        n = todo.pop()
        if n not in reached:
            reached.add(n)
            todo += near[n]
    assert sorted(set(parts) - reached) == []


def test_the_boards_stand_in_a_row_from_their_envelopes_extents():
    """The row's copy of the Envelopes' extents (ADR 0011) is theirs, and the boards stand side by side GAP apart with
    their backs on the plane asked for and their bottoms level (#687): the switch board, 32 tall, its middle on -90, the
    Shield, 30 tall, on -91."""
    for parts, (x0, x1), back, bottom in base.ROW:
        (lo, hi) = BOXES[parts[0][1]]
        assert (x0, x1) == (lo[0], hi[0])
        assert back == min(BOXES[mesh][0][1] for _, mesh in parts)
        assert bottom == min(BOXES[mesh][0][2] for _, mesh in parts)
    placed = {n: at[:3, 3] for n, (_, at) in base.standing(10.0, -90.0).items()}
    assert placed["next Shield 1"] == pytest.approx((-26.75, 20.68, -91.0))
    assert placed["next Core 1"] == pytest.approx(placed["next Shield 1"])
    assert placed["next switch board"] == pytest.approx((28.0, 14.6, -90.0))


def _box(mesh, m):
    """The Envelope's box placed by m: (low, high corner)."""
    v = np.array(list(itertools.product(*zip(*BOXES[mesh])))) @ m[:3, :3].T + m[:3, 3]
    return v.min(axis=0).round(2).tolist(), v.max(axis=0).round(2).tolist()


def test_the_cores_lie_on_the_cranium_tray_and_the_switch_board_the_dongle_and_both_packs_on_the_torsos_floor():
    """#858: each Core under its Shield lies flat on the cranium tray (base.TRAY_Z), Core 1 at -x, Core 2 its mirror
    image, 3 mm apart, the Core's USB-C end back; the switch board flat on the Torso's floor beside the pack's lead end
    (-x), the charger dongle beside the neck mount's foot, its socket's end forward to the spare pack's lead, both
    within the Torso's walls, the opening in its -x wall over them."""
    boards, ((x0, x1), (y0, y1), _) = base.cranium(), base.TORSO
    shield, core = (_box(*boards[f"next {n} 1"]) for n in ("Shield", "Core"))
    assert core[0][2] == pytest.approx(base.TRAY_Z[1]) and shield[1][2] - core[0][2] == pytest.approx(21.46, abs=0.01)
    assert shield[0][0] == pytest.approx(-30.5) and shield[1][0] == pytest.approx(-1.5)
    assert core[1][1] > shield[1][1] - 2  # its USB-C end
    assert _box(*boards["next Shield 2"]) == ([-shield[1][0], *shield[0][1:]], [-shield[0][0], *shield[1][1:]])
    switch, dongle = _box(*base.switch_board()["next switch board"]), _box(*base.dongle()["next charger dongle"])
    for lo, hi in (switch, dongle):
        assert lo[2] == pytest.approx(nk.MOUNT_Z[0]) and x0 + 2 < lo[0] and hi[0] < x1 - 2
        assert y0 + 2 < lo[1] < hi[1] < y1 - 2 and base.OPENING[0][0] < max(lo[1], hi[1] - 20) < base.OPENING[0][1]
    assert switch[1][0] < -base.PACK[0] / 2 - 2.5 and dongle[1][0] < -base.PACK[0] / 2 - 2.5
    assert dongle[0][1] == pytest.approx(base.DONGLE_AT[1]) and abs(base.SPARE_Y - dongle[0][1]) < base.PACK[1]
    assert envelopes.CORE["parts"][2] == base.USB  # its copy of the Envelope's USB-C (ADR 0011)


@pytest.mark.model
def test_the_cores_lie_inside_the_realistic_skull_each_usb_c_opening_straight_back_out_of_it():
    """#858: each Core and Shield, and the tray's plate under them, at least the finished skull's WALL inside the
    cranium's hull, so the finish (model/skeleton) leaves its outside whole over them but for each Core's
    USB-C opening: a plug's box from its socket's mouth straight back, side by side, out past the hull, clear of the
    tray."""
    hull = ConvexHull(trimesh.load(stages.stl("next skull"), force="mesh").vertices)

    def inside(points):  # mm in from the hull's nearest face
        return -(hull.equations[:, :3] @ np.transpose(points) + hull.equations[:, 3:]).max(axis=0)

    boards, openings = base.cranium(), base.openings()
    for name in ("next Core 1", "next Shield 1", "next Core 2", "next Shield 2"):
        mesh, m = boards[name]
        points = np.array([v.toTuple() for v in solid(mesh).tessellate(0.5)[0]]) @ m[:3, :3].T + m[:3, 3]
        assert inside(points).min() >= skeleton.WALL, name
    plate = [
        (x, y, z) for x in (-30.5, 30.5) for y in (base.CORES_AT[1] - 15, base.CORES_AT[1] + 15) for z in base.TRAY_Z
    ]
    assert inside(plate).min() >= skeleton.WALL
    tray = printed_base.tray().val()
    for name, (lo, hi) in openings.items():
        socket = _box("core", boards[name][1])
        assert lo[1] == pytest.approx(socket[1][1]) and inside([(sum(lo[::2]) / 2, hi[1], lo[2])])[0] < 0  # out
        assert lo[0] < socket[0][0] + 7 and socket[1][0] - 7 < hi[0] and lo[2] < base.TRAY_Z[1] < hi[2]
        cut = cq.Solid.makeBox(*(hi - lo), cq.Vector(*lo))
        assert tray.intersect(cut).Volume() < 0.01, name
    (a, _), (b, _) = openings.values()
    assert a[1:] == pytest.approx(b[1:]) and a[0] < 0 < b[0]  # side by side


def test_the_heads_box_takes_in_the_skull_over_the_parts():
    """#828, #838: the gates measure the head's shell, the realistic skull's box: from its chin 78.2 under the eyes to
    its top 69.8 over them, about 50 each side, so parts within it make a head 148 tall, the eyes 0.528 up it; a part
    out past it still counts."""
    lo, hi = base.shelled(np.array((-50.0, -40.0, -74.5)), np.array((50.0, 80.0, 30.0)))
    assert lo == pytest.approx((-50.0, -40.0, -78.2)) and hi == pytest.approx((50.6, 102.3, 69.8))
    assert -lo[2] / (hi[2] - lo[2]) == pytest.approx(0.5284, abs=1e-4)


def test_stage_1s_test_stand_stands_on_the_desk():
    """#720: geometry's copy of the stand's height (ADR 0011): Stage 1's frame puts the stand's foot (base.STAND_Z, the
    gimbal frame plate's underside less STAND_H) on z 0, the eye block on it."""
    (origin, x, z), *rest = g.STAGES["next-stage1"].values()
    assert rest == [(origin, x, z)] and origin[2] + base.STAND_Z == 0


def test_the_pack_lies_across_x_as_its_envelope_is_long_and_wide():
    """The Torso's copy of the pack's footprint (ADR 0011) is the battery Envelope's, its length along x."""
    lo, hi = BOXES["battery"]
    assert base.PACK == (hi[1] - lo[1], hi[0] - lo[0])


def test_the_leads_that_cross_pan_and_tilt_are_the_neck_servos_and_the_packs_y_lead():
    """The Cores ride the head (#858): the pan servo's lead crosses both up to them, the tilt servo's the tilt, and the
    pack's Y lead's one pair from the switch board both; the eyes' and the mouth's stay on the head, the packs', the
    switch board's and the dongle's in the Torso."""
    assert base.leads(stages.STAGES["next-mech-back"]) == {"pan pivot": 2, "tilt pivot": 3}


def _report(
    pairs=(), hold=0.1, peak=0.2, rest=0.0, hz=20.0, leads=None, tip=30.0, printed=2, head=None, tilt=0.03, eyes=0.45
):
    servo = {"hold_kgf_cm": hold, "peak_kgf_cm": peak, "rest_kgf_cm": rest, "rated_kgf_cm": 0.4, "stall_kgf_cm": 1.0}
    return {
        "mujoco": {
            "clearance_mm": 0.1,
            "loop_mm": 0.05,
            "pairs": [{"pair": list(p), "min_mm": mm} for p, mm in pairs],
            "residuals": {"tilt pivot": {"max_mm": tilt}, "pan pivot": {"max_mm": 0.01}},
            "actuators": {"tilt horn": {"hold_kgf_cm": hold, "rated_kgf_cm": 0.4}},
            "motions": {"servos": {"tilt horn": servo}},
            "vibration": {"tilt horn": {"servo_loop_hz": hz}, "pan horn": {"servo_loop_hz": hz + 5}},
            "tip_over": {"margin_mm": tip, "moving": {"margin_mm": tip}},
        },
        "variant": {
            "parts": ["next torso:1", "next Shield 1:1", "next shelf:1"],
            "printed": printed,
            "leads": leads or {"pan pivot": 2},
            "head_mm": head or [118.0, 117.0, 140.0],  # gimbal.HEAD_MM's order: W, D, H,
            "eyes_up": eyes,
        },
    }


def test_a_variant_whose_boards_meet_the_head_ranks_last_whatever_its_figures():
    bad = _report(pairs=[(("next shelf:1", "next L upper lid:1"), -2.0)], hold=0.01)
    ranked = base.rank({"next-mech-back": _report(hold=0.3), "next-mech-later": bad})
    assert ranked["order"] == ["next-mech-back", "next-mech-later"]
    assert ranked["variants"]["next-mech-later"]["gates"]["clearance"] == [["next L upper lid:1", "next shelf:1"]]
    assert ranked["variants"]["next-mech-later"]["fails"] == ["clearance"]


def test_a_head_past_140_w_140_d_150_h_fails_the_head_gate_and_ranks_after_one_that_fits():
    """#51, #838: everything that rides the head fits a head of at most 140 W x 140 D x 150 H mm, the realistic skull's
    length; a variant 2 mm too deep ranks after one that fits, though its servo holds less."""
    ranked = base.rank(
        {"next-mech-back": _report(hold=0.05, head=[120.0, 142.0, 140.0]), "next-mech-later": _report(hold=0.3)}
    )
    assert ranked["order"] == ["next-mech-later", "next-mech-back"]
    assert ranked["variants"]["next-mech-back"]["gates"]["head"] == ["depth"]
    assert ranked["variants"]["next-mech-back"]["fails"] == ["head size"]
    assert ranked["variants"]["next-mech-later"]["fails"] == []


def test_a_variant_whose_eyes_sit_in_its_heads_upper_half_fails_the_eyes_gate_and_ranks_after_one_that_fits():
    """#708, #838: the eye centres at most 0.55 of the way up what rides the head (the realistic skull's 0.53); 0.56 up
    ranks after 0.5, though its servo holds less."""
    ranked = base.rank(
        {"next-mech-back": _report(hold=0.05, eyes=0.56), "next-mech-later": _report(hold=0.3, eyes=0.5)}
    )
    assert ranked["order"] == ["next-mech-later", "next-mech-back"]
    assert ranked["variants"]["next-mech-back"]["fails"] == ["eyes up"]
    assert ranked["variants"]["next-mech-later"]["fails"] == []


def test_a_variant_whose_tilt_loop_opens_past_the_gate_ranks_last_and_names_it():
    """#705: a variant's tilt pivot opened 0.0557 mm at the tilt's back end (the gate 0.05): it stays in the ranking, last
    though its servo holds least, its gates listing the loop and its `fails` saying "tilt loop"; 0.0483 passes."""
    ranked = base.rank(
        {
            "next-mech-back": _report(hold=0.3, tilt=0.0411),
            "next-mech-later": _report(hold=0.01, tilt=0.0557),
            "next-mech-third": _report(hold=0.2, tilt=0.0483),
        }
    )
    assert ranked["order"] == ["next-mech-third", "next-mech-back", "next-mech-later"]
    assert ranked["variants"]["next-mech-later"]["gates"]["loops"] == ["tilt pivot"]
    assert ranked["variants"]["next-mech-later"]["fails"] == ["tilt loop"]
    assert ranked["variants"]["next-mech-third"]["fails"] == []


def test_the_first_criterion_in_51s_order_that_differs_decides():
    """Simplicity ties, so the servo torque decides, though the other has the lower rest torque and more leads."""
    ranked = base.rank(
        {
            "next-mech-back": _report(hold=0.12, rest=0.05, leads={"pan pivot": 1}),
            "next-mech-later": _report(hold=0.10, rest=0.0, leads={"pan pivot": 6}),
        }
    )
    assert ranked["order"] == ["next-mech-later", "next-mech-back"]


def test_the_head_fit_decides_after_the_mode_and_before_the_leads():
    """#51's order: ... lowest mode, fits the big head, fewest leads: of two that fit, the one with more room left
    in its tightest direction ranks first, though it has more leads."""
    ranked = base.rank(
        {
            "next-mech-back": _report(head=[135.0, 100.0, 120.0], leads={"pan pivot": 1}),
            "next-mech-later": _report(head=[115.0, 110.0, 140.0], leads={"pan pivot": 6}),
        }
    )
    assert ranked["order"] == ["next-mech-later", "next-mech-back"]


def test_a_mark_missed_outranks_a_better_figure_after_it_and_names_what_it_fails():
    """#51's marks (hold at most rated, peak at most half the stall, lowest mode at least MODE_HZ, the moving centre of
    mass inside the footprint) come before any figure: a mode under MODE_HZ loses to one
    over it, though its rest torque is lower; a peak over half the stall fails the torque."""
    ranked = base.rank(
        {
            "next-mech-back": _report(rest=0.05, peak=0.6),
            "next-mech-later": _report(rest=0.0, hz=base.MODE_HZ - 1, peak=0.6, tip=-1.0),
        }
    )
    assert ranked["order"] == ["next-mech-back", "next-mech-later"]
    assert ranked["variants"]["next-mech-later"]["criteria"]["mode_hz"] == base.MODE_HZ - 1
    assert ranked["variants"]["next-mech-later"]["fails"] == ["torque", "mode", "tip-over"]
    assert ranked["variants"]["next-mech-back"]["fails"] == ["torque"]
