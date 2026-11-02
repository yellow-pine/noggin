"""Seam: model/base.py, the next Mech's head variants (#686): where the boards go, the crown wall's sway, the leads that
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
@pytest.mark.parametrize("doc", sorted(g.NEXT))
def test_every_part_of_the_next_mech_is_mounted_on_the_assembly(doc):
    """#687: the Viewer and the pictures draw the next Mech assembled, nothing lying apart: every part of each document
    touches one that leads, part on part, down to the Torso. Each part's surface sampled about 1 mm apart, plus its
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
    reached, todo = set(), ["next torso:1"]
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


def test_lying_boards_rest_on_their_backs_with_their_tops_forward():
    """Crown and Split (#686): turned 90 deg about x onto their backs, the Shield's back (y -10.68) on z 40, its
    bottom (z -15) on y 30 + 16 = 46 and its top (z 15) 30 mm forward of it, on y 16."""
    _, at = base.lying(30.0, 40.0)["next Shield 1"]
    back, bottom, top = (at @ [0, -10.68, 0, 1], at @ [0, 0, -15, 1], at @ [0, 0, 15, 1])
    assert back[2] == pytest.approx(40.0) and bottom[1] == pytest.approx(46.0) and top[1] == pytest.approx(16.0)
    assert set(base.lying(30.0, 40.0, base.PAIR)) == {"next Shield 1", "next Core 1", "next Shield 2", "next Core 2"}


def test_the_pack_lies_across_x_as_its_envelope_is_long_and_wide():
    """The Torso's copy of the pack's footprint (ADR 0011) is the battery Envelope's, its length along x."""
    lo, hi = BOXES["battery"]
    assert base.PACK == (hi[1] - lo[1], hi[0] - lo[0])


def test_the_crown_wall_sways_as_a_cantilever_with_the_boards_on_its_tip():
    """A PETG plate 100 x 3 mm, 100 mm long (across layers: E 1540 MPa, 1.28 g/cm3) under 30 g of boards: I = 100 x
    3^3 / 12 = 225 mm^4, k = 3EI/L^3 = 3 x 1540 x 225 / 100^3 = 1.0395 N/mm, its tip mass 30 g + 0.236 x 38.4 g =
    39.06 g, so sqrt(1039.5 / 0.03906) / 2 pi = 25.96 Hz."""
    assert base.sway(100.0, 3.0, 30.0, 100.0) == pytest.approx(25.96, abs=0.01)


@pytest.mark.parametrize(
    "doc,crossing",
    [
        # the boards ride the head: the pan servo's lead and the pack's cross both, the only two that leave the Torso
        # for the head's side of pan (#685, #51's wiring rules), the tilt servo's the tilt
        ("next-mech-back", {"pan pivot": 2, "tilt pivot": 3}),
        ("next-mech-crown", {"pan pivot": 2, "tilt pivot": 3}),
        # the switch board rides the pan alone: the pack's pair crosses the pan to it, its own the tilt to the Shields
        ("next-mech-split", {"pan pivot": 2, "tilt pivot": 3}),
    ],
)
def test_the_leads_that_cross_pan_and_tilt_go_from_each_servo_and_the_pack_to_the_boards(doc, crossing):
    assert base.leads(stages.STAGES[doc]) == crossing


def _report(
    pairs=(), hold=0.1, peak=0.2, rest=0.0, hz=20.0, leads=None, tip=30.0, printed=2, sway=None, head=None, tilt=0.03
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
            "parts": ["next torso:1", "next board rack:1", "next crown shelf:1"],
            "printed": printed,
            "leads": leads or {"pan pivot": 2},
            "sway_hz": sway,
            "head_mm": head or [118.0, 117.0, 140.0],  # gimbal.HEAD_MM's order: W, D, H,
        },
    }


def test_a_variant_whose_boards_meet_the_head_ranks_last_whatever_its_figures():
    bad = _report(pairs=[(("next crown shelf:1", "next L upper lid:1"), -2.0)], hold=0.01)
    ranked = base.rank({"next-mech-back": _report(hold=0.3), "next-mech-crown": bad})
    assert ranked["order"] == ["next-mech-back", "next-mech-crown"]
    assert ranked["variants"]["next-mech-crown"]["gates"]["clearance"] == [["next L upper lid:1", "next crown shelf:1"]]
    assert ranked["variants"]["next-mech-crown"]["fails"] == ["clearance"]


def test_a_head_past_126_w_150_h_120_d_fails_the_head_gate_and_ranks_after_one_that_fits():
    """#51, #698: everything that rides the head fits a head of at most 126 W x 150 H x 120 D mm; a variant 2 mm too deep
    ranks after one that fits, though its servo holds less."""
    ranked = base.rank(
        {"next-mech-back": _report(hold=0.05, head=[120.0, 122.0, 140.0]), "next-mech-crown": _report(hold=0.3)}
    )
    assert ranked["order"] == ["next-mech-crown", "next-mech-back"]
    assert ranked["variants"]["next-mech-back"]["gates"]["head"] == ["depth"]
    assert ranked["variants"]["next-mech-back"]["fails"] == ["head size"]
    assert ranked["variants"]["next-mech-crown"]["fails"] == []


def test_a_variant_whose_tilt_loop_opens_past_the_gate_ranks_last_and_names_it():
    """#705: Crown's tilt pivot opened 0.0557 mm at the tilt's back end (the gate 0.05): it stays in the ranking, last
    though its servo holds least, its gates listing the loop and its `fails` saying "tilt loop"; 0.0483 passes."""
    ranked = base.rank(
        {
            "next-mech-back": _report(hold=0.3, tilt=0.0411),
            "next-mech-crown": _report(hold=0.01, tilt=0.0557),
            "next-mech-split": _report(hold=0.2, tilt=0.0483),
        }
    )
    assert ranked["order"] == ["next-mech-split", "next-mech-back", "next-mech-crown"]
    assert ranked["variants"]["next-mech-crown"]["gates"]["loops"] == ["tilt pivot"]
    assert ranked["variants"]["next-mech-crown"]["fails"] == ["tilt loop"]
    assert ranked["variants"]["next-mech-split"]["fails"] == []


def test_the_first_criterion_in_51s_order_that_differs_decides():
    """Simplicity ties, so the servo torque decides, though the other has the lower rest torque and more leads."""
    ranked = base.rank(
        {
            "next-mech-back": _report(hold=0.12, rest=0.05, leads={"pan pivot": 1}),
            "next-mech-crown": _report(hold=0.10, rest=0.0, leads={"pan pivot": 6}),
        }
    )
    assert ranked["order"] == ["next-mech-crown", "next-mech-back"]


def test_the_head_fit_decides_after_the_mode_and_before_the_leads():
    """#51's order: ... lowest mode, fits the big head, fewest leads: of two that fit, the one with more room left
    in its tightest direction ranks first, though it has more leads."""
    ranked = base.rank(
        {
            "next-mech-back": _report(head=[124.0, 100.0, 120.0], leads={"pan pivot": 1}),
            "next-mech-crown": _report(head=[115.0, 110.0, 140.0], leads={"pan pivot": 6}),
        }
    )
    assert ranked["order"] == ["next-mech-crown", "next-mech-back"]


def test_a_mark_missed_outranks_a_better_figure_after_it_and_names_what_it_fails():
    """#51's marks (hold at most rated, peak at most half the stall, lowest mode at least MODE_HZ, the moving centre of
    mass inside the footprint) come before any figure: a mode under MODE_HZ (the crown's sway counts) loses to one
    over it, though its rest torque is lower; a peak over half the stall fails the torque."""
    ranked = base.rank(
        {
            "next-mech-back": _report(rest=0.05, peak=0.6),
            "next-mech-crown": _report(rest=0.0, sway=base.MODE_HZ - 1, peak=0.6, tip=-1.0),
        }
    )
    assert ranked["order"] == ["next-mech-back", "next-mech-crown"]
    assert ranked["variants"]["next-mech-crown"]["criteria"]["mode_hz"] == base.MODE_HZ - 1
    assert ranked["variants"]["next-mech-crown"]["fails"] == ["torque", "mode", "tip-over"]
    assert ranked["variants"]["next-mech-back"]["fails"] == ["torque"]


@pytest.mark.model
@pytest.mark.parametrize(
    "doc,drawn",
    [
        ("next-mech-back", {"back_z_mm": base.BACK_Z}),
        ("next-mech-crown", {"crown_mm": [base.CROWN_Y, base.CROWN_Z]}),
        ("next-mech-split", {"crown_mm": [base.SPLIT_Y, base.CROWN_Z]}),
    ],
)
def test_each_variant_is_drawn_at_its_optimum(doc, drawn):
    """The numbers drawn (ADR 0011) are where optimise() finds the tilt servo's least worst hold (and, for a crown, its
    shelf the lowest that clears the gimbal), within 0.5 mm, and the hold there within 0.002 kgf.cm of it: rerun
    `python -m model.candidates` and copy its numbers when this fails."""
    found = candidates.optimise(doc)
    assert all(np.ravel(found[k]) == pytest.approx(np.ravel(v), abs=0.5) for k, v in drawn.items())
    assert found["drawn_kgf_cm"] <= found["hold_kgf_cm"] + 0.002
