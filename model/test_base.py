"""Seam: model/base.py, the next Mech's head variants (#686; Back alone since #712): where the boards go, the leads that
cross pan and tilt, and the ranking of their sim reports."""

import itertools

import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

from model import base, candidates, stages
from model import geometry as g
from model.test_envelopes import BOXES

TOUCH_MM = 0.5  # two parts touch: a fit's clearance (a pin in its bore, a servo in its collar) is under it


@pytest.mark.build
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
        if (np.maximum(lo_a - hi_b, lo_b - hi_a) < TOUCH_MM).all() and trees[b].query(points[a])[0].min() < TOUCH_MM:
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
    """The boards ride the head: the pan servo's lead and the pack's cross both, the only two that leave the Torso for
    the head's side of pan (#685, #51's wiring rules), the tilt servo's the tilt."""
    assert base.leads(stages.STAGES["next-mech-back"]) == {"pan pivot": 2, "tilt pivot": 3}


def _report(pairs=(), hold=0.1, peak=0.2, rest=0.0, hz=20.0, leads=None, tip=30.0, printed=2, head=None, tilt=0.03):
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
            "head_mm": head or [138.0, 117.0, 140.0],  # gimbal.HEAD_MM's order: W, D, H,
        },
    }


def test_a_variant_whose_boards_meet_the_head_ranks_last_whatever_its_figures():
    bad = _report(pairs=[(("next shelf:1", "next L lid:1"), -2.0)], hold=0.01)
    ranked = base.rank({"next-mech-back": _report(hold=0.3), "next-mech-later": bad})
    assert ranked["order"] == ["next-mech-back", "next-mech-later"]
    assert ranked["variants"]["next-mech-later"]["gates"]["clearance"] == [["next L lid:1", "next shelf:1"]]
    assert ranked["variants"]["next-mech-later"]["fails"] == ["clearance"]


def test_a_head_past_140_w_150_h_120_d_fails_the_head_gate_and_ranks_after_one_that_fits():
    """#51: everything that rides the head fits a head of at most 140 W x 150 H x 120 D mm; a variant 2 mm too deep
    ranks after one that fits, though its servo holds less."""
    ranked = base.rank(
        {"next-mech-back": _report(hold=0.05, head=[130.0, 122.0, 140.0]), "next-mech-later": _report(hold=0.3)}
    )
    assert ranked["order"] == ["next-mech-later", "next-mech-back"]
    assert ranked["variants"]["next-mech-back"]["gates"]["head"] == ["depth"]
    assert ranked["variants"]["next-mech-back"]["fails"] == ["head size"]
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
            "next-mech-back": _report(head=[139.0, 100.0, 120.0], leads={"pan pivot": 1}),
            "next-mech-later": _report(head=[130.0, 110.0, 140.0], leads={"pan pivot": 6}),
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


@pytest.mark.model
@pytest.mark.parametrize("doc,drawn", [("next-mech-back", {"back_z_mm": base.BACK_Z})])
def test_each_variant_is_drawn_at_its_optimum(doc, drawn):
    """The numbers drawn (ADR 0011) are where optimise() finds the tilt servo's least worst hold, within 0.5 mm, and
    the hold there within 0.002 kgf.cm of it: rerun `python -m model.candidates` and copy its numbers when this
    fails."""
    found = candidates.optimise(doc)
    assert all(np.ravel(found[k]) == pytest.approx(np.ravel(v), abs=0.5) for k, v in drawn.items())
    assert found["drawn_kgf_cm"] <= found["hold_kgf_cm"] + 0.002
