"""Seam: model/base.py, the next Mech's head variants (#686; Back alone since #712): where the boards go, the leads that
cross pan and tilt, and the ranking of their sim reports."""

import itertools

import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

from model import base, stages
from model import geometry as g
from model.test_envelopes import BOXES

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


def test_back_stands_a_core_on_edge_in_each_cheek_and_lies_the_switch_board_in_the_torso():
    """#828: Core 1 and its Shield in the -x cheek, Core 2's the mirror image, each on edge on its cradle's floor (3 mm
    on the gimbal frame's plate, z -64) behind the bail's upright (y 44), 62 out at most, its USB-C end back (the
    Core's y reaches 72.89, its antenna end 45); the switch board flat on the Torso's floor (z -144), in front of the
    pack's cradle (y 24.82), 2.5 inside the ribcage's side ribs (#823, |x| 40.5)."""
    boards = base.back_boards()
    shield, core = (_box(*boards[f"next {n} 1"]) for n in ("Shield", "Core"))
    assert [min(a, b) for a, b in zip(shield[0], core[0])] == pytest.approx([-61.98, 44.5, -61.0])
    assert [max(a, b) for a, b in zip(shield[1], core[1])] == pytest.approx([-40.52, 74.5, -32.0])
    assert (core[0][1], core[1][1]) == pytest.approx((45.0, 72.89))
    mirror = _box(*boards["next Core 2"])
    assert mirror == ([-core[1][0], *core[0][1:]], [-core[0][0], *core[1][1:]])
    lo, hi = _box(*base.switch_board()["next switch board"])
    assert lo + hi == pytest.approx([-38.0, -8.0, -144.0, -17.5, 24.0, -124.24])


def test_the_heads_box_takes_in_the_skull_dome_over_the_parts():
    """#828: the gates measure the head's shell. The stand-in dome (until #824 draws it) rises to 75.25 over the eyes
    and reaches 68 each side, so parts reaching 30 over the eyes and 74.5 under them make a head 149.75 tall, the eyes
    0.497 up it; a part out past the dome still counts."""
    lo, hi = base.shelled(np.array((-50.0, -40.0, -74.5)), np.array((50.0, 80.0, 30.0)))
    assert lo == pytest.approx((-68.0, -42.6, -74.5)) and hi == pytest.approx((68.0, 80.0, 75.25))
    assert -lo[2] / (hi[2] - lo[2]) == pytest.approx(0.4975, abs=1e-4)


def test_stage_1s_test_stand_stands_on_the_desk():
    """#720: geometry's copy of the stand's height (ADR 0011): Stage 1's frame puts the stand's foot (base.STAND_Z, the
    gimbal frame plate's underside less STAND_H) on z 0, the eye block on it."""
    (origin, x, z), *rest = g.STAGES["next-stage1"].values()
    assert rest == [(origin, x, z)] and origin[2] + base.STAND_Z == 0


def test_the_pack_lies_across_x_as_its_envelope_is_long_and_wide():
    """The Torso's copy of the pack's footprint (ADR 0011) is the battery Envelope's, its length along x."""
    lo, hi = BOXES["battery"]
    assert base.PACK == (hi[1] - lo[1], hi[0] - lo[0])


def test_the_leads_that_cross_pan_and_tilt_go_from_each_servo_and_the_pack_to_the_boards():
    """The Cores ride the head: the pan servo's lead and the switch board's power lead cross both, the only two that
    leave the Torso for the head's side of pan (#685, #828, #51's wiring rules), the tilt servo's the tilt."""
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
            "parts": ["next torso:1", "next board rack:1", "next shelf:1"],
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


def test_a_head_past_124_6_w_150_h_120_d_fails_the_head_gate_and_ranks_after_one_that_fits():
    """#51, #698: everything that rides the head fits a head of at most 124.6 W x 150 H x 120 D mm; a variant 2 mm too deep
    ranks after one that fits, though its servo holds less."""
    ranked = base.rank(
        {"next-mech-back": _report(hold=0.05, head=[120.0, 122.0, 140.0]), "next-mech-later": _report(hold=0.3)}
    )
    assert ranked["order"] == ["next-mech-later", "next-mech-back"]
    assert ranked["variants"]["next-mech-back"]["gates"]["head"] == ["depth"]
    assert ranked["variants"]["next-mech-back"]["fails"] == ["head size"]
    assert ranked["variants"]["next-mech-later"]["fails"] == []


def test_a_variant_whose_eyes_sit_in_its_heads_upper_half_fails_the_eyes_gate_and_ranks_after_one_that_fits():
    """#708: the eye centres at most half way up what rides the head (cartoon proportions); 0.51 up ranks after 0.5,
    though its servo holds less."""
    ranked = base.rank(
        {"next-mech-back": _report(hold=0.05, eyes=0.51), "next-mech-later": _report(hold=0.3, eyes=0.5)}
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
