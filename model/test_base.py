"""Seam: model/base.py, the next Mech's Base candidates (#642): where the boards go, the tower's sway, the leads that
cross pan and tilt, and the ranking of two sim reports."""

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
    for parts, (x0, x1), back, bottom in base._ROW:
        (lo, hi) = BOXES[parts[0][1]]
        assert (x0, x1) == (lo[0], hi[0])
        assert back == min(BOXES[mesh][0][1] for _, mesh in parts)
        assert bottom == min(BOXES[mesh][0][2] for _, mesh in parts)
    placed = base.boards(10.0, -90.0)
    assert placed["next Shield 1"][1] == pytest.approx((-26.75, 20.68, -91.0))
    assert placed["next Core 1"][1] == placed["next Shield 1"][1]
    assert placed["next switch board"][1] == pytest.approx((28.0, 14.6, -90.0))


def test_the_pack_lies_across_x_as_its_envelope_is_long_and_wide():
    """The Torso's copy of the pack's footprint (ADR 0011) is the battery Envelope's, its length along x."""
    lo, hi = BOXES["battery"]
    assert base.PACK == (hi[1] - lo[1], hi[0] - lo[0])


def test_the_tower_sways_as_a_cantilever_with_the_boards_on_its_tip():
    """A 3 mm PETG rod 150 mm long (across layers: E 1540 MPa, 1.28 g/cm3) under 20 g of boards: k = 3EI/L^3 =
    3 x 1540 x 63.62 / 150^3 = 87.1 N/m, its tip mass 20 g + 0.236 x 5.43 g, so sqrt(87.1 / 0.02128) / 2 pi = 10.18 Hz."""
    assert base.sway(3.0, 20.0, 150.0) == pytest.approx(10.18, abs=0.01)


@pytest.mark.parametrize(
    "doc,crossing",
    [
        # (a) the boards ride the head: the pan servo's lead and the pack's cross both, the only two that leave the
        # Torso for the head's side of pan (#685, #51's wiring rules), the tilt servo's the tilt
        ("next-mech-a", {"pan pivot": 2, "tilt pivot": 3}),
        # (b) the boards stand still: the gimbal's four servos and the mouth's cross both, the tilt servo's the pan
        ("next-mech-b", {"pan pivot": 6, "tilt pivot": 5}),
    ],
)
def test_the_leads_that_cross_pan_and_tilt_go_from_each_servo_and_the_pack_to_the_boards(doc, crossing):
    assert base.leads(stages.STAGES[doc]) == crossing


def _report(pairs=(), hold=0.1, peak=0.2, rest=0.0, hz=20.0, leads=None, tip=30.0, printed=2, sway=None):
    servo = {"hold_kgf_cm": hold, "peak_kgf_cm": peak, "rest_kgf_cm": rest, "rated_kgf_cm": 0.4, "stall_kgf_cm": 1.0}
    return {
        "mujoco": {
            "clearance_mm": 0.1,
            "pairs": [{"pair": list(p), "min_mm": mm} for p, mm in pairs],
            "actuators": {"tilt horn": {"hold_kgf_cm": hold, "rated_kgf_cm": 0.4}},
            "motions": {"servos": {"tilt horn": servo}},
            "vibration": {"tilt horn": {"servo_loop_hz": hz}, "pan horn": {"servo_loop_hz": hz + 5}},
            "tip_over": {"margin_mm": tip, "moving": {"margin_mm": tip}},
        },
        "base": {
            "parts": ["next torso:1", "next board tray:1", "next board tower:1"],
            "printed": printed,
            "leads": leads or {"pan pivot": 2},
            "sway_hz": sway,
        },
    }


def test_a_candidate_whose_base_meets_the_head_ranks_last_whatever_its_figures():
    bad = _report(pairs=[(("next board tower:1", "next yaw servo:1"), -2.0)], hold=0.01)
    ranked = base.rank({"next-mech-a": _report(hold=0.3), "next-mech-b": bad})
    assert ranked["order"] == ["next-mech-a", "next-mech-b"]
    assert ranked["candidates"]["next-mech-b"]["gates"]["clearance"] == [["next board tower:1", "next yaw servo:1"]]


def test_the_first_criterion_in_51s_order_that_differs_decides():
    """Simplicity ties, so the servo torque decides, though the other has the lower rest torque and more leads."""
    ranked = base.rank(
        {
            "next-mech-a": _report(hold=0.12, rest=0.05, leads={"pan pivot": 1}),
            "next-mech-b": _report(hold=0.10, rest=0.0, leads={"pan pivot": 6}),
        }
    )
    assert ranked["order"] == ["next-mech-b", "next-mech-a"]


def test_a_mark_missed_outranks_a_better_figure_after_it():
    """#51's marks (hold at most rated, peak at most half the stall, lowest mode at least MODE_HZ, the moving centre of
    mass inside the footprint) come before any figure: a mode under MODE_HZ (the tower's sway counts) loses to one
    over it, though its rest torque is lower."""
    ranked = base.rank({"next-mech-a": _report(rest=0.05), "next-mech-b": _report(rest=0.0, sway=base.MODE_HZ - 1)})
    assert ranked["order"] == ["next-mech-a", "next-mech-b"]
    assert ranked["candidates"]["next-mech-b"]["criteria"]["mode_hz"] == base.MODE_HZ - 1


@pytest.mark.model
def test_the_tray_is_drawn_at_its_optimum():
    """The tray drawn (ADR 0011) is where optimise() finds the tilt servo's least worst hold, within 0.002 kgf.cm of it
    (the hold is flat there, so COBYLA's stop wanders about a mm), and as clear as optimise() asks: rerun
    `python -m model.candidates` and copy its numbers when this fails."""
    found = candidates.optimise("next-mech-a")
    assert found["drawn_kgf_cm"] <= found["hold_kgf_cm"] + 0.002
    assert found["drawn_clear_mm"] >= -0.05  # COBYLA meets a constraint to within its tolerance


@pytest.mark.model
def test_the_tower_is_drawn_at_its_optimum():
    assert candidates.optimise("next-mech-b")["tower_r_mm"] == pytest.approx(base.TOWER_R, abs=0.05)
