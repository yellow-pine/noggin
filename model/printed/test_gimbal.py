"""Seam: the Mech's eye gimbal parts (model/printed/gimbal.py) as model/stages.py places them at rest, the lids'
shank beside them: no two overlap."""

import itertools
import math

import cadquery as cq
import mujoco
import numpy as np
import pytest

from model import beams, linkage
from model import geometry as g
from model import gimbal as gm
from model.printed import bone, gimbal

# a horn's hub on its servo's spline: the Envelopes overlap there by design
ON_SPLINE = {frozenset((f"{d} servo:1", f"{d} horn:1")) for d in gm.drives()}


GROW_MM = 0.1  # a box read off the tessellation can fall short of a curved face: grown, it misses no touching pair


def _overlaps(shapes, pairs):
    """[a / b: mm3] for each pair of `shapes` (names) among `pairs` overlapping past 0.01 mm3: only a pair whose grown
    bounding boxes touch is intersected (#808)."""
    box = {n: s.BoundingBox() for n, s in shapes.items()}
    lo = {n: np.array([b.xmin, b.ymin, b.zmin]) - GROW_MM for n, b in box.items()}
    hi = {n: np.array([b.xmax, b.ymax, b.zmax]) + GROW_MM for n, b in box.items()}
    return [
        f"{a} / {b}: {v:.2f} mm3"
        for a, b in pairs
        if (lo[a] <= hi[b]).all() and (lo[b] <= hi[a]).all() and (v := shapes[a].intersect(shapes[b]).Volume()) > 0.01
    ]


@pytest.fixture(scope="module")
def rest():
    """{part: its solid at rest} (gimbal.at_rest), built once a module: CI's 15 s times the test alone. The Skeleton
    mechanical, which the Bones are carved from (#809)."""
    return gimbal.at_rest(mechanical=True)


@pytest.mark.model
def test_no_two_parts_overlap_at_rest(rest):
    pairs = [(a, b) for a, b in itertools.combinations(rest, 2) if frozenset((a, b)) not in ON_SPLINE]
    assert _overlaps(rest, pairs) == []


# what turns or stands between the eyes, where each cap's shell sweeps as its eye yaws in (#967)
BETWEEN = ("upper lid:1", "lower lid:1", "lid bar:1", "lid link:1")


@pytest.mark.model
@pytest.mark.parametrize("side", "LR")
def test_each_open_upper_lids_tail_keeps_the_lids_room_from_the_yaw_bearings_neck(rest, side):
    """#1102: open, the upper lid's tail lies beside the yaw bearing's neck behind the eye, and it was 0.02 mm into
    it. The lid drives' sweep reads the pair over the lid's travel, but only the sim runs it."""
    for lid in (0.0, gm.LID_WIDE):
        tail = _posed(rest, gm.moved(lid, 0.0), f"{side} upper lid:1")
        assert tail.distance(rest["gimbal frame:1"]) >= gm.LID_CLEAR_MM, lid


@pytest.mark.model
@pytest.mark.parametrize("side", "LR")
@pytest.mark.parametrize("yaw", [-gm.YAW, gm.YAW])
@pytest.mark.parametrize("pitch", [-gm.PITCH, gm.PITCH])
@pytest.mark.parametrize("lid", list(np.subtract(gm.LID_EDGES, gm.LID_REST)))
def test_each_cap_clears_the_lids_and_their_drive_at_every_combined_travel_end(rest, side, yaw, pitch, lid):
    """#937, #967: the cap's shell reaches its opening's inner corner and yaws 25 deg further in, between the eyes;
    each lid's band rides gm.LID_CLEAR_MM over it, and each lid's sleeve, spoke and crank, the bar, the link, the
    lids' shank and the frame with its wall keep that from it, with the eye yawed and pitched under the lids open and
    shut (the sweep reads the lids over their travel at yaw 0)."""
    moved = gm.moved(lid, pitch, yaw)
    cap = _posed(rest, moved, f"{side} eyeball cap:1")
    for name in (*(f"{side} {part}" for part in BETWEEN), "lid shank", "gimbal frame:1"):
        assert cap.distance(_posed(rest, moved, name)) >= gm.LID_CLEAR_MM - 1e-4, name
    # grown round its sphere (#967), it comes by the yoke, the push-rod and the tie-bar too
    for name in (f"{side} yaw yoke:1", f"{side} push-rod:1", "tie-bar:1"):
        assert cap.distance(_posed(rest, moved, name)) >= gm.LID_CLEAR_MM, name


# what turns inside a cap's shell, where its liner stands still (#967)
INSIDE = ("eyeball cap:1", "eyeball core:1", "yaw yoke:1", "push-rod:1", *BETWEEN)


@pytest.mark.model
@pytest.mark.parametrize("side", "LR")
@pytest.mark.parametrize("yaw", [-gm.YAW, gm.YAW])
@pytest.mark.parametrize("pitch", [-gm.PITCH, gm.PITCH])
@pytest.mark.parametrize("lid", list(np.subtract(gm.LID_EDGES, gm.LID_REST)))
def test_each_liner_clears_all_that_turns_by_it_at_every_combined_travel_end(rest, side, yaw, pitch, lid):
    """#967: the liner stands on the frame inside its cap's shell, gm.LID_CLEAR_MM under it and round its stem as the
    eye yaws and pitches, and that far from the core, the yoke over its collar, the push-rod, the tie-bar, each lid's
    crank and spoke, the bar, the link and the lids' shank, with the lids open and shut."""
    moved = gm.moved(lid, pitch, yaw)
    liner = rest[f"{side} eye liner:1"]
    for name in (*(f"{side} {part}" for part in INSIDE), "lid shank", "tie-bar:1"):
        assert liner.distance(_posed(rest, moved, name)) >= gm.LID_CLEAR_MM - 1e-4, name


@pytest.mark.model
@pytest.mark.parametrize("side", "LR")
def test_each_liners_collar_sits_on_its_yaw_bearing_and_the_rest_of_it_clears_the_frame(rest, side):
    """#967: the liner's foot is a collar round the yaw bearing's post, on the pad's top, its ends on the pad's front
    face (gm.RAIL_TURN lays that face out as gimbal.rail does): it meets the frame there and shares no volume with
    it, and but for that collar the liner keeps gm.LID_CLEAR_MM from the frame."""
    liner, frame = rest[f"{side} eye liner:1"], rest["gimbal frame:1"]
    assert liner.intersect(frame).Volume() < 1e-3 and liner.distance(frame) < 1e-6
    collar = gimbal.cyl("z", (gm.EYE[side][0], 0, 0), gm.POST_R + gm.CLIP["wall"] + 0.01, (-99, 0)).val()
    assert liner.cut(collar).distance(frame) >= gm.LID_CLEAR_MM - 1e-4


@pytest.mark.model
@pytest.mark.parametrize("mechanical", [False, True])
@pytest.mark.parametrize("pitch", [-gm.PITCH, 0.0, gm.PITCH])
def test_the_bail_turns_clear_of_the_frame(mechanical, pitch):
    """#967: over the pitch the bail shares no volume with the frame, in either style: its rod turns in the uprights'
    bores, over the lid servos' collars."""
    from model.printed import PARTS, styled

    frame, bail = (PARTS[styled(stem, mechanical)]().val() for stem in ("gimbal frame", "bail"))
    turned = bail.moved(gimbal._at(gm.moved(0.0, pitch)["bail:1"]))
    assert turned.intersect(frame).Volume() < 1e-3


def _posed(rest, moved, name):
    return rest[name].moved(gimbal._at(moved[name])) if name in moved else rest[name]


@pytest.mark.model
@pytest.mark.parametrize("pitch", [-gm.PITCH, 0.0, gm.PITCH])
@pytest.mark.parametrize("yaw", [-gm.YAW, 0.0, gm.YAW])
def test_each_push_rod_turns_on_its_balls_clear_of_its_core_and_the_bail(rest, pitch, yaw):
    """#967: the leaned rod passes over the core's top and its cups turn on a neck that leans too, so over the pitch
    and the yaw each rod shares no volume with its core or the bail, and past its lever cup its bar keeps the room
    the plate's back edge keeps (gm.BACK_ROOM_MM: more than a collision piece strays) from the core, whose top is cut
    to a cone under it; each cup's mouth keeps gm.LID_CLEAR_MM from its ball's neck."""
    moved = gm.moved(0.0, pitch, yaw)
    bail = _posed(rest, moved, "bail:1")
    for s, (x, _, _) in gm.EYE.items():
        rod, core = (_posed(rest, moved, f"{s} {part}:1") for part in ("push-rod", "eyeball core"))
        assert rod.intersect(core).Volume() < 1e-3 and rod.intersect(bail).Volume() < 1e-3
        ball = (moved[f"{s} eyeball core:1"] @ (x, 0, gm.LEVER, 1))[:3]
        bar = rod.cut(gimbal.ball(8.0, tuple(ball)).val())  # past its cup, which turns on the lever's ball
        assert bar.distance(core) >= gm.BACK_ROOM_MM
        # each cup's mouth turns round the neck its ball stands on, two printed parts moving against each other: the
        # lids' room from it (before the mouths were opened, 0.36 mm at the lever's with the pitch up and the yaw at
        # an end, 0.48 at the bail's with the pitch down), read without the ball in its socket, a hundredth over
        arm = (moved["bail:1"] @ (x, *gm.BAIL_BALL, 1))[:3]
        for part, at in ((core, ball), (bail, arm)):
            socket = gimbal.ball(gm.BALL_R + 0.11, tuple(at)).val()
            assert rod.distance(part.cut(socket)) >= gm.LID_CLEAR_MM


@pytest.mark.model
@pytest.mark.parametrize("pitch", list(np.linspace(-gm.PITCH, gm.PITCH, 5)))
def test_the_pitch_drive_keeps_room_from_the_lid_servos_and_the_cranium_tray(rest, pitch):
    """#967: each lid servo stands where the bail's axis was, so the bail turns over them and under the cranium tray,
    and each push-rod's cup comes back at its lid servo's case as the eyes pitch up: over the pitch each keeps
    gm.BACK_ROOM_MM, on the exact solids (the prototype's cup came 0.9 mm from the case)."""
    from model import stages
    from model.printed import PARTS

    moved = gm.moved(0.0, pitch)
    tray = PARTS["cranium tray"]().val().moved(gimbal._at(stages.cranium_sub().parts["cranium tray:1"].matrix))
    bail = _posed(rest, moved, "bail:1")
    assert bail.distance(tray) >= gm.BACK_ROOM_MM
    for s in gm.EYE:
        servo = rest[f"{s} lid servo:1"]
        assert bail.distance(servo) >= gm.BACK_ROOM_MM
        assert _posed(rest, moved, f"{s} push-rod:1").distance(servo) >= gm.BACK_ROOM_MM


@pytest.mark.model
@pytest.mark.parametrize("side", "LR")
def test_each_lid_servo_keeps_room_from_the_pitch_servo_and_its_horn_from_the_pans_moving_cap(rest, side):
    """#967: behind the belt each lid servo stands between the bail's ball and the pitch servo, its horn's hub over
    the pan's moving cap: gm.BACK_ROOM_MM from each, on the exact solids."""
    from model.printed import PARTS

    cap = PARTS["pan moving cap"]().val()  # drawn where it rides, in the gimbal's frame
    assert rest[f"{side} lid servo:1"].distance(rest["pitch servo:1"]) >= gm.BACK_ROOM_MM
    for lid in np.subtract(gm.LID_EDGES, gm.LID_REST):
        horn = _posed(rest, gm.moved(float(lid), 0.0), f"{side} lid horn:1")
        assert horn.distance(cap) >= gm.BACK_ROOM_MM


def _rims(outline, a):
    """(lowest, highest) lid angle, deg, at which the column `a` deg along the eye line crosses `outline` (x, z) on his
    eyeball."""
    x, rho = (gm.MORTY_BALL_R * f(math.radians(a)) for f in (math.sin, math.cos))
    p, q = outline, np.roll(outline, -1, axis=0)
    cross = (p[:, 0] - x) * (q[:, 0] - x) < 0
    z = p[cross, 1] + (x - p[cross, 0]) / (q[cross, 0] - p[cross, 0]) * (q[cross, 1] - p[cross, 1])
    return tuple(math.degrees(math.asin(min(1.0, max(-1.0, v / rho)))) for v in (z.min(), z.max()))


def test_the_lids_travels_and_the_caps_reach_are_read_off_his_eye_openings():
    """#967 (ADR 0011): the lower lid turns from where the cap's bottom edge shows at the eye's middle (the bottom rim
    drawn in by gm.CAP_LOW, as the front sees it) up to gm.LID_SHUT; the upper lid from there up by the greatest height
    either opening has over that curve, less half a degree; and a cap reaches gm.CAP_IN toward the other eye,
    where the front sees the further of the two openings' inner corners on it. All read off the eye whites' cuts."""
    heights, corners = [], []
    for side in gm.EYE:
        rim = gimbal.opening(side)
        low = np.where(rim[:, 1:] < 0, rim * gm.CAP_LOW, rim)
        assert gm.LID_SHUT - _rims(low, 0.0)[0] == pytest.approx(gm.LOWER_TRAVEL, abs=0.1)
        heights.append(max(_rims(rim, a)[1] - _rims(low, a)[0] for a in np.arange(-50.0, 80.0)))
        corners.append(math.degrees(math.asin(-rim[:, 0].min() / gm.CAP_R)))
    assert max(heights) - gm.LOWER_TRAVEL - 0.5 == pytest.approx(gm.UPPER_TRAVEL, abs=0.1)
    assert max(corners) - 3.0 < gm.CAP_IN < min(corners)  # short of the corner: the lids' sleeves (gm.CAP_IN)


def _seen(mesh, points, eye, least=gm.LID_R[0] - 0.01):
    """Which of the (x, z) `points` about `eye` a line of sight from the front meets the lid `mesh`'s band at: its
    triangles ahead of the eyes' plane, on the band's radii (`least` mm or more from the eye's centre: 0 for all of
    a cap or a liner)."""
    t = mesh.triangles - eye
    t = t[(t[:, :, 1] < 0).all(axis=1) & (np.linalg.norm(t, axis=2) > least).all(axis=1)][:, :, [0, 2]]
    a, b, c = t[:, 0], t[:, 1], t[:, 2]
    d = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])
    a, b, c, d = (v[np.abs(d) > 1e-9] for v in (a, b, c, d))
    out = np.zeros(len(points), bool)
    for i in range(0, len(points), 200):
        p = points[i : i + 200, None, :]
        u = ((p[..., 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (p[..., 1] - a[:, 1])) / d
        v = ((b[:, 0] - a[:, 0]) * (p[..., 1] - a[:, 1]) - (p[..., 0] - a[:, 0]) * (b[:, 1] - a[:, 1])) / d
        out[i : i + 200] = ((u >= 0) & (v >= 0) & (u + v <= 1)).any(axis=1)
    return out


@pytest.mark.model
@pytest.mark.parametrize("side", "LR")
def test_from_the_front_each_openings_lids_are_hidden_open_and_close_it_shut(side):
    """#967 (Cansin, 2026-11-28): each opening is his Sculpt's own, and the eye is sunk 2.2 mm under it, so the opening
    is larger than the eyeball as the front sees it. Seen from the front, on a 0.5 mm grid inside its outline: open,
    the upper lid's band shows only along the top rim, edge on, where no cap can reach (under 50 mm2), and the lower
    lid only under the cap's bottom edge, the sliver along the bottom rim (120 to 180 mm2: 2.2 mm wide; two thirds of
    it wide open, as it drops under the cap's edge: under half when the sliver was 1.2 mm); shut, the two lids cover it all but 1.5%: 0.9 mm along the
    middle of the top rim, where the upper lid's back edge stops short of the bail's arm, and its outer corner."""
    import trimesh

    from model import skin, stages

    eye, sign = np.array(gm.EYE[side]), 1 if side == "L" else -1
    rim = gimbal.opening(side) * (sign, 1)
    low = np.where(rim[:, 1:] < 0, rim * gm.CAP_LOW, rim)
    grid = np.stack(np.meshgrid(np.arange(-34, 38, 0.5), np.arange(-36, 37, 0.5)), axis=-1).reshape(-1, 2)
    inside = grid[skin.inside(grid, gimbal._offset(rim, -0.3))]
    lids = {
        k: trimesh.load(stages.stl(f"{side} {k} lid"), force="mesh").apply_translation(eye) for k in ("upper", "lower")
    }
    under = _seen(lids["lower"], inside, eye)
    assert _seen(lids["upper"], inside, eye).sum() * 0.25 < 50.0
    assert 120.0 < under.sum() * 0.25 < 180.0 and not (under & skin.inside(inside, gimbal._offset(low, -0.3))).any()
    shut, wide = (
        [lids[k].copy().apply_transform(gm.moved(float(e - gm.LID_REST), 0.0)[f"{side} {k} lid:1"]) for k in lids]
        for e in gm.LID_EDGES
    )
    assert (~(_seen(shut[0], inside, eye) | _seen(shut[1], inside, eye))).sum() <= 0.015 * len(inside)
    assert _seen(wide[0], inside, eye).sum() * 0.25 < 50.0 and _seen(wide[1], inside, eye).sum() < 0.75 * under.sum()


# The dark inside the head seen in an opening from the front, mm2 at most, with its eye at (yaw toward its outside,
# pitch): the figures Cansin picked the grown cap and the liner on were 1, 60, 1, 3 and 1 (#967's preview, comment
# 7236532060, read on points with the lid bar at rest); these are the built parts'. Yawed out, 70 of it is the slit
# between the cap's edge at the lids' hubs (gm.CAP_IN) and the liner's window, which ends where the stem comes yawed
# in, and the rest lies along the rim where the lid bar's sweep keeps the liner back
DARK_MM2 = {(0.0, 0.0): 3.0, (gm.YAW, 0.0): 97.0, (-gm.YAW, 0.0): 2.0, (0.0, gm.PITCH): 5.0, (0.0, -gm.PITCH): 3.0}


@pytest.mark.model
@pytest.mark.parametrize("side", "LR")
def test_from_the_front_each_opening_shows_white_beside_its_turned_eye(side):
    """#967 (Cansin, 2026-11-28, #893's eighth round): a turned eye's cap left its opening and showed the dark inside
    the head beside it (560 mm2 of an opening's 3,650 yawed out, 275 pitched up). Seen from the front as the lids'
    test sees it, inside the eyeball's own outline (past it no cap can stand), with the lids open at rest: what
    neither the cap, grown round its sphere, nor the liner inside it, nor a lid covers stays under DARK_MM2."""
    import trimesh

    from model import skin, stages

    eye, sign = np.array(gm.EYE[side]), 1 if side == "L" else -1
    rim = gimbal.opening(side) * (sign, 1)
    grid = np.stack(np.meshgrid(np.arange(-34, 38, 0.5), np.arange(-36, 37, 0.5)), axis=-1).reshape(-1, 2)
    inside = grid[skin.inside(grid, gimbal._offset(rim, -0.3)) & (np.linalg.norm(grid, axis=1) < gm.CAP_R)]
    load = lambda stem: trimesh.load(stages.stl(f"{side} {stem}"), force="mesh").apply_translation(eye)  # noqa: E731
    white = _seen(load("eye liner"), inside, eye, 0.0)
    for lid in ("upper lid", "lower lid"):
        white |= _seen(load(lid), inside, eye)
    cap = load("eyeball cap")
    for (out, pitch), most in DARK_MM2.items():
        turned = cap.copy().apply_transform(gm.moved(0.0, pitch, sign * out)[f"{side} eyeball cap:1"])
        assert (~(white | _seen(turned, inside, eye, 0.0))).sum() * 0.25 <= most, (out, pitch)


def _lids_shell(side):
    """What the hidden lids and their cap sweep about the `side` eye where the yaw drive stands (#967): the shell
    gm.LIDS_SHELL through gm.LIDS_SWEEP about the eye line, from the lids' bands' inboard ends out to 30 mm outboard."""
    eye, (lo, hi) = gm.EYE[side], gm.LIDS_SHELL
    arc = np.radians(np.linspace(*gm.LIDS_SWEEP, 64))
    fan = [(0.0, 0.0)] + [(-(hi + 5) * math.cos(t), (hi + 5) * math.sin(t)) for t in arc]
    # along the eye line, + outboard: from the lids' inboard ends, 58 deg inboard of straight ahead (#967's layout)
    reach = (-hi * math.sin(math.radians(58.0)), gm.FOOT_X[0] - 3.0)
    x = sorted(eye[0] + (1 if side == "L" else -1) * u for u in reach)
    wedge = cq.Workplane("YZ", origin=(x[0], 0, 0)).polyline(fan).close().extrude(x[1] - x[0])
    return gimbal.ball(hi, eye).cut(gimbal.ball(lo, eye)).intersect(wedge).val()


@pytest.mark.model
@pytest.mark.parametrize("side", "LR")
def test_the_yaw_drive_leaves_each_eyes_sphere_through_the_belt_behind_it_alone(rest, side):
    """#967: the tie-bar, over the yaw, and the frame with its yaw bearings share no volume with the shell the hidden
    lids and their cap will sweep: each finger and each bearing's neck cross it behind the eye, past the stowed lower
    lid's back edge."""
    shell = _lids_shell(side)
    assert rest["gimbal frame:1"].intersect(shell).Volume() < 1e-3
    for yaw in (-gm.YAW, 0.0, gm.YAW):
        assert _posed(rest, gm.moved(0.0, 0.0, yaw), "tie-bar:1").intersect(shell).Volume() < 1e-3


@pytest.mark.model
@pytest.mark.parametrize("yaw", [-gm.YAW, 0.0, gm.YAW])
def test_the_tie_bar_keeps_room_from_the_frame_the_lid_servos_and_the_shut_lower_lids(rest, yaw):
    """#967: behind the eyes the cross-bar passes in front of the lid servos and their collars and behind the shut
    lower lids' hoops, and each finger over its yaw bearing's pad: gm.BACK_ROOM_MM from each over the yaw, on the exact
    solids (more than a collision piece strays)."""
    moved = gm.moved(float(gm.LID_EDGES[0] - gm.LID_REST), 0.0, yaw)  # the lids shut
    tie = _posed(rest, moved, "tie-bar:1")
    assert tie.distance(rest["gimbal frame:1"]) >= gm.BACK_ROOM_MM
    for s in gm.EYE:
        assert tie.distance(rest[f"{s} lid servo:1"]) >= gm.BACK_ROOM_MM
        assert tie.distance(_posed(rest, moved, f"{s} lower lid:1")) >= gm.BACK_ROOM_MM


@pytest.mark.model
@pytest.mark.parametrize("side", "LR")
@pytest.mark.parametrize("yaw", [-gm.YAW, 0.0, gm.YAW])
def test_each_yoke_turns_on_its_post_clear_of_the_rest_of_its_yaw_bearing(rest, side, yaw):
    """#967: the yoke's bottom bar rides the post; yawed, its crank's head swings over the bearing's pad and beside
    its web, gm.BACK_ROOM_MM from both."""
    post = gimbal.cyl("z", (gm.EYE[side][0], 0, 0), gm.POST_R + 0.01, (-99, gm.YAW_CRANK_Z[0] + 0.01)).val()
    yoke = _posed(rest, gm.moved(0.0, 0.0, yaw), f"{side} yaw yoke:1")
    assert yoke.distance(rest["gimbal frame:1"].cut(post)) >= gm.BACK_ROOM_MM


SAG_DEG = 0.5  # how far past either end of the pan its loaded servo sags, inside its band (#978)


@pytest.mark.model
@pytest.mark.parametrize(("end", "other"), [(1, "tilt servo:1"), (-1, "nod plate:1")])
def test_the_plates_back_edge_keeps_room_from_the_neck_past_the_pans_ends(end, other):
    """#967, #978: nodded, with the pan SAG_DEG past its end, the frame plate's back edge keeps gm.BACK_ROOM_MM from
    the tilt servo's tab and from the nod plate, on the exact solids: more than those parts' collision pieces stray,
    which read the frame 0.35 mm into each on Linux while it passed 0.5 and 0.9 mm from them."""
    from model import envelopes, stages
    from model.printed import PARTS

    stage = stages.STAGES["mech-back-mechanical"]  # the sim's document
    rest = {n: p.matrix for n, p in stage.parts.items()}

    def seen(mats):  # the other part from the frame
        return np.linalg.inv(mats["gimbal frame:1"]) @ mats[other]

    def moved(horn, deg):  # how the horn moves it against the frame, in the frame's own coordinates
        return seen(stages.pose(stage, horn, deg).parts) @ np.linalg.inv(seen(rest))

    def solid(name):
        stem = stages.stem(stage.parts[name].file)
        return (PARTS.get(stem) or envelopes.ENVELOPES[stem])().val()

    tilt, pan = (stage.horns[h].limits for h in ("tilt horn", "pan horn"))
    at = moved("pan horn", end * (pan[1] + SAG_DEG)) @ moved("tilt horn", tilt[1]) @ seen(rest)
    y1 = gm.PLATE_Y[1]  # the edge alone, behind the plate's opening: the nod plate's tube stands in that by design
    edge = solid("gimbal frame:1").intersect(envelopes.box((-99, 99), (y1 - 2.0, y1), gm.PLATE_Z).val())
    assert edge.distance(solid(other).moved(gimbal._at(at))) >= gm.BACK_ROOM_MM


@pytest.fixture(scope="module")
def skeleton(rest):
    return gimbal.skeleton(rest)


@pytest.mark.model
def test_the_skeleton_moves_every_part_as_the_gimbal_does(skeleton):
    """The hinges gates.certify reads (#655): at each (lid, pitch) row every part sits where gimbal.moved() puts it, the
    parts that turn alike about one line on one hinge."""
    poses = [(-36, -12), (-20, 0), (10, 14)]
    model, rows = skeleton
    data = mujoco.MjData(model)
    for (lid, pitch), q in zip(poses, rows(poses)):
        data.qpos[:] = q
        mujoco.mj_kinematics(model, data)
        for name, m in gm.moved(lid, pitch).items():
            assert data.body(name).xmat.reshape(3, 3) == pytest.approx(m[:3, :3], abs=1e-9)
            assert data.body(name).xpos * 1000 == pytest.approx(m[:3, 3], abs=1e-6)
    # the upper lids, the lower lids, their horns, their bars, their links, the cores with their caps, the push-rods
    # (each L and R alike); the pitch horn, the bail, the pitch bar
    assert model.njnt == 10


# The tie-bar's pins (x, y, z): each yoke's, under its crank, and the yaw horn's (#967)
TIE_PINS = [(s * gm.EYE["L"][0], gm.CRANK, sum(gm.FINGER_Z) / 2) for s in (-1, 1)]
TIE_PINS += [(0.0, gm.YAW_Y + gm.CRANK, sum(gm.TIE_Z) / 2)]
TIE_BED = np.linalg.inv(gimbal.tie_bed())  # onto the tie-bar's bed, as it prints
ROD_BALLS = [(0.0, 0.0, gm.LEVER), (0.0, *gm.BAIL_BALL)]
ROD_BED = np.linalg.inv(gimbal.rod_bed())  # onto the push-rod's bed, as it prints
# each cup's mouth's way from its ball: the lever's down its bed's normal, the bail's up its neck
_NECK = np.array([0.0, *np.subtract(gimbal.bail_foot(), gm.BAIL_BALL)])
ROD_MOUTHS = [-gimbal.rod_bed()[:3, 2], _NECK / np.linalg.norm(_NECK)]


def _pitch_loads():
    """(the pitch bar's, each push-rod's) load per N of the pitch servo's stall at its horn pin, the worst over the
    pitch: the bar takes it through the angle it meets the horn at, the rod through the bail's ratio and the angles the
    bar meets the input arm and the rod its arm at (#967: none of them square)."""

    def sin(u, v):
        return float(np.linalg.norm(np.cross(u, v)) / np.linalg.norm(u) / np.linalg.norm(v))

    horn, axis, x = np.array([0, *gm.PITCH_HORN]), np.array([0, *gm.BAIL]), gm.EYE["L"][0]
    bar, rod = [], []
    for pitch in np.linspace(-gm.PITCH, gm.PITCH, 13):
        m = gm.moved(0.0, pitch)
        a = (m["pitch horn:1"] @ (0, gm.PITCH_HORN[0] + gm.CRANK, gm.PITCH_HORN[1], 1))[:3]
        b = (m["bail:1"] @ (0, *gm.BAIL_TIP, 1))[:3]
        ball = (m["L eyeball core:1"] @ (x, 0, gm.LEVER, 1))[:3]
        pin = (m["bail:1"] @ (x, *gm.BAIL_BALL, 1))[:3]
        bar.append(1 / sin(b - a, a - horn))
        arm = math.dist(gm.BAIL, gm.BAIL_BALL)
        rod.append(bar[-1] * gm.BAIL_IN * sin(b - a, b - axis) / (arm * sin(pin - ball, pin - (x, *gm.BAIL))))
    return max(bar), max(rod)


BAR_LOAD, ROD_LOAD = _pitch_loads()


@pytest.mark.parametrize("mechanical", [False, True])
def test_the_tie_bar_keeps_its_three_pin_bores(mechanical):
    """Each bore takes the M3 shank (PIN_R) through the bar's 3 mm, with wall round it, in both styles (#1052)."""
    tie = gimbal.tie_bar(mechanical=mechanical).val()
    for x, y, z in TIE_PINS:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            assert not tie.isInside(cq.Vector(x + dx * (gm.PIN_R - 0.05), y + dy * (gm.PIN_R - 0.05), z))
            assert tie.isInside(cq.Vector(x + dx * (gm.PIN_R + 0.5), y + dy * (gm.PIN_R + 0.5), z))


def test_the_pitch_bar_keeps_its_two_pin_bores():
    """#967: the bar leans from the pitch horn's pin to the bail's input arm's, a bore for the M3 shank at each."""
    bar, x = gimbal.pitch_bar().val(), sum(gm.PITCH_BAR_X) / 2
    for y, z in ((gm.PITCH_HORN[0] + gm.CRANK, gm.PITCH_HORN[1]), gm.BAIL_TIP):
        for dy, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            assert not bar.isInside(cq.Vector(x, y + dy * (gm.PIN_R - 0.05), z + dz * (gm.PIN_R - 0.05)))
            assert bar.isInside(cq.Vector(x, y + dy * (gm.PIN_R + 0.5), z + dz * (gm.PIN_R + 0.5)))


def test_each_push_rod_cup_closes_on_its_ball_under_the_equator():
    """The socket (0.1 over the ball) is clear, the cup's wall round it behind and to the sides, and its mouth open
    past the ball's centre for the neck (gimbal.CUP_MOUTH): the lever's cup's toward the lever's neck, under it on its bed, the
    bail's the other way, up the bail's neck (#967)."""
    rod = gimbal.push_rod().val()
    for at, mouth in zip(ROD_BALLS, ROD_MOUTHS):
        r, side = gm.BALL_R + 0.05, np.cross(mouth, (1, 0, 0))
        for d in (-mouth, (1, 0, 0), (-1, 0, 0), side, -side):
            assert not rod.isInside(cq.Vector(*np.add(at, np.multiply(d, r))))
            assert rod.isInside(cq.Vector(*np.add(at, np.multiply(d, r + 0.6))))
        assert not rod.isInside(cq.Vector(*np.add(at, 2.05 * mouth)))


def test_the_bones_print_as_drawn_with_no_overhang_past_45_deg():
    """The tie-bar on its cross-bar's back edge, as Bones and mechanical (gimbal.tie_bed, #967, #1052: its fingers and
    its tail rising, its pins' bores across the layers, their crowns excused); the push-rod on its bed (gimbal.rod_bed:
    the lever's cup's rim and the bail's cup's skirt on it; each socket's crown, an exact interface, excused)."""
    bore = lambda c: all(math.dist((gimbal.tie_bed() @ (*c, 1))[:2], p[:2]) > gm.PIN_R + 0.2 for p in TIE_PINS)  # noqa: E731
    for mechanical in (False, True):
        tie = gimbal.tie_bar(mechanical=mechanical).val().moved(gimbal._at(TIE_BED))
        assert bone.overhang_deg(tie, keep=bore) <= 45, mechanical
    crown = lambda c: min(math.dist(gimbal.rod_bed() @ (*c, 1), (*b, 1)) for b in ROD_BALLS) > gm.BALL_R + 0.2  # noqa: E731
    assert bone.overhang_deg(gimbal.push_rod().val().moved(gimbal._at(ROD_BED)), keep=crown) <= 45


def _section(solid, a, b, t, eps=0.01):
    """(mm2, the least mm4) of `solid`'s section square to the span a-b at t: its area and second moment."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    along = (b - a) / np.linalg.norm(b - a)
    side, up = np.cross(along, (0, 0, 1)), np.array([0.0, 0.0, 1.0])
    plane = cq.Plane(origin=tuple(a + (b - a) * t), xDir=tuple(side), normal=tuple(along))
    cut = solid.intersect(cq.Workplane(plane).rect(60, 60).extrude(eps / 2, both=True).val())
    inertia = np.array(cq.Shape.matrixOfInertia(cut)) / eps
    basis = np.array([side, up])
    return cut.Volume() / eps, float(np.linalg.eigvalsh(basis @ inertia @ basis.T).min())


def test_the_push_rod_holds_the_pitch_servo_at_stall():
    """SF 2 (beams.MIN_SF) in PETG across its layers along its waist, pinned at both joints: on its strength and against
    Euler buckling over its span. On the mechanical part, which its Bone is carved from (#809). Along its bar, on its
    bed: the joints at the bar's ends, its span the balls'."""
    a, b = (0.0, 0.0, 2.25), (0.0, math.dist(*ROD_BALLS), 2.25)
    solid = gimbal.push_rod(mechanical=True).val().moved(gimbal._at(ROD_BED))
    mat = g.MATERIALS[g.PRINTED["push-rod"][1]]
    force = beams.stall_force_n() * ROD_LOAD
    area, least = min(_section(solid, a, b, t) for t in (0.3, 0.4, 0.5, 0.6, 0.7))
    assert mat["tensile_mpa"]["z"] * area / force >= beams.MIN_SF
    assert math.pi**2 * mat["E_mpa"]["z"] * least / math.dist(a, b) ** 2 / force >= beams.MIN_SF


def _twisted_sf(solid, at, along, pin):
    """The SF in PETG across its layers of `solid`'s section at `at`, square to `along` (in the plane across x), with
    the yaw servo's stall along x at `pin`: von Mises of its bending (about the section's axis across x, its width b
    along x) and its torsion about `along` (a b x t rectangle, Roark's beta)."""
    along = np.asarray(along, float) / np.linalg.norm(along)
    e2 = np.cross(along, (1.0, 0.0, 0.0))
    plane = cq.Plane(origin=tuple(map(float, at)), xDir=(1, 0, 0), normal=tuple(along))
    cut = solid.intersect(cq.Workplane(plane).rect(30, 14).extrude(0.005, both=True).val())
    b = cut.BoundingBox().xlen
    t = cut.Volume() / 0.01 / b
    moment = np.cross(np.subtract(pin, at), (beams.stall_force_n(), 0.0, 0.0))
    bending = abs(float(moment @ e2)) / (t * b**2 / 6)
    beta = np.interp(b / t, (1.0, 1.5, 2.0, 2.5, 3.0, 4.0), (0.208, 0.231, 0.246, 0.258, 0.267, 0.282))
    torsion = abs(float(moment @ along)) / (beta * b * t**2)
    return g.MATERIALS[g.PRINTED["tie-bar"][1]]["tensile_mpa"]["z"] / math.hypot(bending, math.sqrt(3) * torsion)


_FINGER_X = gm.EYE["L"][0] + sum(gm.FINGER_X) / 2
_BACK = (gm.CROSS_Y[1] - 1.5, sum(gm.CROSS_Z) / 2)  # where the tail meets the cross-bar's back edge
# (where on the tie-bar, the member's way there (y, z), the pin that loads it), each (x, y, z)
TIE_SECTIONS = {
    "the finger's rise": (
        (_FINGER_X, *np.add(gm.FINGER[0], gm.FINGER[1]) / 2),
        np.subtract(gm.FINGER[1], gm.FINGER[0]),
        TIE_PINS[1],
    ),
    "the finger in the belt": ((_FINGER_X, gm.FINGER[1][0] + 3.0, gm.FINGER[1][1]), (1.0, 0.0), TIE_PINS[1]),
    "the finger at the cross-bar": ((_FINGER_X, gm.CROSS_Y[0] - 0.5, gm.FINGER[1][1]), (1.0, 0.0), TIE_PINS[1]),
    "the tail": (
        (0.0, *np.add(TIE_PINS[2][1:], _BACK) / 2),
        np.subtract(_BACK, TIE_PINS[2][1:]),
        TIE_PINS[2],
    ),
}


@pytest.mark.parametrize("where", TIE_SECTIONS)
def test_the_tie_bar_holds_the_yaw_servo_at_stall(where):
    """#967: SF 2 (beams.MIN_SF) with the servo's whole stall on one finger (the other yoke free) and on the tail: each
    is bent across its width, and the finger is twisted too where it leaves the eye's sphere level, 10 mm over its
    pin (so it is as thick as the cross-bar there)."""
    at, way, pin = TIE_SECTIONS[where]
    assert _twisted_sf(gimbal.tie_bar(mechanical=True).val(), at, (0.0, *way), pin) >= beams.MIN_SF


def _bent_sf(solid, at, normal, load_at, force):
    """The SF in PETG across its layers of `solid`'s section through `at`, square to `normal`, with `force` (N, a
    vector) at `load_at`: its pull and its bending about the section's two principal axes, at the extreme fibres."""
    normal = np.asarray(normal, float) / np.linalg.norm(normal)
    e1 = np.cross(normal, (1.0, 0.0, 0.0) if abs(normal[0]) < 0.9 else (0.0, 1.0, 0.0))
    e1 /= np.linalg.norm(e1)
    plane = cq.Plane(origin=tuple(map(float, at)), xDir=tuple(e1), normal=tuple(normal))
    cut = solid.intersect(cq.Workplane(plane).rect(80, 80).extrude(0.005, both=True).val())
    centre = np.array(cq.Shape.centerOfMass(cut).toTuple())
    basis = np.array([e1, np.cross(normal, e1)])
    seconds, axes = np.linalg.eigh(basis @ (np.array(cq.Shape.matrixOfInertia(cut)) / 0.01) @ basis.T)
    fibres = np.array([v.toTuple() for v in cut.Vertices()]) - centre
    moment = np.cross(np.subtract(load_at, centre), force)
    stress = abs(float(np.dot(force, normal))) / (cut.Volume() / 0.01)
    for second, axis in zip(seconds, axes.T @ basis):
        stress += abs(float(moment @ axis)) * np.abs(fibres @ np.cross(normal, axis)).max() / second
    return g.MATERIALS["PETG HF"]["tensile_mpa"]["z"] / stress


def _rail_sections():
    """{where on the L yaw bearing: (a point of the section, its normal)}: upright sections across its pad where the
    web gives way under the tie-bar's boss, sections along the web, the neck, and the pylon at its knee and its foot."""
    eye, down = np.array(gm.EYE["L"]), np.array([0.0, 0.0, -1.0])
    a, phi = math.radians(-gm.RAIL_EXIT[0]), math.radians(gm.RAIL_EXIT[1])
    way = np.array([math.sin(a), -math.cos(a) * math.cos(phi), math.cos(a) * math.sin(phi)])
    back = np.cross(np.cross(down, way), down)
    back /= np.linalg.norm(back)
    end, tip = math.acos(float(down @ way)), eye + gimbal.RAIL_OUT * way

    def along(deg):
        return math.cos(math.radians(deg)) * down + math.sin(math.radians(deg)) * back

    neck = math.degrees(end) + gimbal.RAIL_NECK / 2
    return {
        **{f"the pad {mm} mm back": (eye + mm * back + (0, 0, -30), back) for mm in (15.0, 17.0, 18.6, 19.3, 21.0)},
        **{f"the web {deg} deg along": (eye + 32.0 * along(deg), along(deg + 90)) for deg in (10.0, 50.0)},
        "the neck": (eye + 37.0 * along(neck), along(neck)),
        "the pylon's knee": ((tip[0], tip[1], gimbal.PYLON_KNEE + 0.1), (0.0, 0.0, 1.0)),
        "the pylon's foot": ((tip[0], tip[1], gm.PLATE_Z[1] + 0.2), (0.0, 0.0, 1.0)),
    }


RAIL_SECTIONS = _rail_sections()
_ROD = np.array([0.0, *np.subtract(gm.BAIL_BALL, (0.0, gm.LEVER))])
# (where the load meets the L eye, the force): the pitch servo's stall down the push-rod with the eye held, at the
# pitch axle; the yaw servo's with the yoke held, at the crank's level on the yaw axis
RAIL_LOADS = {
    "pitch": (gm.EYE["L"], beams.stall_force_n() * ROD_LOAD * _ROD / np.linalg.norm(_ROD)),
    "yaw": (np.add(gm.EYE["L"], (0.0, 0.0, sum(gm.YAW_CRANK_Z) / 2)), (beams.stall_force_n(), 0.0, 0.0)),
}


@pytest.fixture(scope="module")
def rail():
    return gimbal.rail().val()


@pytest.mark.model
@pytest.mark.parametrize("load", RAIL_LOADS)
@pytest.mark.parametrize("where", RAIL_SECTIONS)
def test_each_yaw_bearing_holds_the_eyes_servos_at_stall(rail, where, load):
    """#967: SF 2 (beams.MIN_SF) in bending on the yaw bearing's sections, from its post back to its pylon's foot,
    with the eye held against the pitch servo's stall and with the yoke held against the yaw servo's: the eye stands
    on it alone. (A strip of the sphere alone, 1.5 mm thick, read 0.2 there.)"""
    assert _bent_sf(rail, *RAIL_SECTIONS[where], *RAIL_LOADS[load]) >= beams.MIN_SF


# The full pass (#704): the yaw yoke prints as drawn, on its stem and crank (its yaw and crank pins along Z, the pitch
# axle's bores across the layers); the bail as drawn, on its rod's flat underside (all three bores along x: standing
# on an end would hang an arm and its ball in the air)
Y = gm.YOKE
BALLS = [(s * gm.EYE["L"][0], *gm.BAIL_BALL) for s in (-1, 1)]
TIP = (sum(gm.BAIL_INPUT_X) / 2, *gm.BAIL_TIP)
BAIL_BED = np.linalg.inv(gimbal.bail_bed())  # onto the bail's bed, as it prints


def test_the_yoke_keeps_its_bores():
    """The yaw shank's bore through the bottom bar (#967: no stem), the crank's pin bore at that level, and the pitch
    axle's bore through each arm, each with wall round it."""
    yoke, r = gimbal.yoke().val(), gm.PIN_R
    z = zc = sum(gm.YAW_CRANK_Z) / 2
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for x, y, zz in ((0, 0, z), (0, gm.CRANK, zc)):
            assert not yoke.isInside(cq.Vector(x + dx * (r - 0.05), y + dy * (r - 0.05), zz))
            assert yoke.isInside(cq.Vector(x + dx * (r + 0.5), y + dy * (r + 0.5), zz))
        for s in (-1, 1):
            x = s * (Y["inner"] + Y["wall"] / 2)
            assert not yoke.isInside(cq.Vector(x, dx * (r - 0.05), dy * (r - 0.05)))
            assert yoke.isInside(cq.Vector(x, dx * (r + 0.5), dy * (r + 0.5)))


def test_the_bail_keeps_its_bores_and_balls():
    """The shanks' bores in the rod's ends and the pitch bar's pin bore in the input arm's tip, each with wall round
    it; a ball on its neck behind each eye."""
    bail, r, (by, bz), end = gimbal.bail().val(), gm.PIN_R, gm.BAIL, gm.EYE["L"][0] + gm.BAIL_END
    for dy, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for x, y, z in [(s * (end - 4), by, bz) for s in (-1, 1)] + [TIP]:
            assert not bail.isInside(cq.Vector(x, y + dy * (r - 0.05), z + dz * (r - 0.05)))
            assert bail.isInside(cq.Vector(x, y + dy * (r + 0.5), z + dz * (r + 0.5)))
    off = -ROD_MOUTHS[1]  # past its neck
    for at in BALLS:
        assert bail.isInside(cq.Vector(*np.add(at, (gm.BALL_R - 0.05) * off)))
        assert not bail.isInside(cq.Vector(*np.add(at, 3.1 * off)))


def _off_bore(c, axis_points, r=gm.PIN_R + 0.2):
    """False on a bore's wall along x through any of the (y, z) points: its crown, an exact interface, is excused."""
    return all(math.hypot(c[1] - y, c[2] - z) > r for y, z in axis_points)


def test_the_yoke_and_the_bail_print_as_drawn_with_no_overhang_past_45_deg():
    """The pitch axle's and the bail's bores across the layers, the bail's balls on their necks: exact interfaces,
    excused."""
    shank = lambda c: math.hypot(c[0], c[1]) > gm.PIN_R + 0.2  # noqa: E731  the yaw shank's blind bore's crown
    assert bone.overhang_deg(gimbal.yoke().val(), keep=lambda c: _off_bore(c, [(0, 0)]) and shank(c)) <= 45
    foot, at = ((BAIL_BED @ (0, *p, 1))[1:3] for p in (gimbal.bail_foot(), gm.BAIL_BALL))  # on its bed: (y, z)
    neck = (at - foot) / np.linalg.norm(at - foot)

    def ball(c):  # off each ball and the neck it stands on
        x = min(abs(c[0] - b[0]) for b in BALLS)
        along = float((c[1:] - foot) @ neck)
        beside = math.hypot(x, float(np.linalg.norm(c[1:] - foot - along * neck)))
        return math.hypot(x, *(c[1:] - at)) > gm.BALL_R + 0.2 and not (0 < along and beside <= gimbal.NECK_R + 0.2)

    tip = (BAIL_BED @ (*TIP, 1))[1:3]
    keep = lambda c: _off_bore(c, [(0.0, 0.0), tip]) and ball(c)  # noqa: E731
    assert bone.overhang_deg(gimbal.bail().val().moved(gimbal._at(BAIL_BED)), keep=keep) <= 45


def _bending_sf(solid, a, b, force, d, lever, ts=(0.0, 0.25, 0.5, 0.75)):
    """The least SF in PETG across its layers on the member a-b's sections at ts, a `force` N along the axis `d` (x, y
    or z) `lever` mm from a: the section's second moment about its axis square to d, its extreme fibre along d."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    along, i = (b - a) / np.linalg.norm(b - a), "xyz".index(d)
    n = np.cross(along, np.eye(3)[i])
    mat, out = g.MATERIALS["PETG HF"], []
    for t in ts:
        plane = cq.Plane(origin=tuple(a + (b - a) * t), xDir=tuple(n), normal=tuple(along))
        cut = solid.intersect(cq.Workplane(plane).rect(80, 80).extrude(0.005, both=True).val())
        inertia = n @ np.array(cq.Shape.matrixOfInertia(cut)) @ n / 0.01
        box, mid = cut.BoundingBox(), cq.Shape.centerOfMass(cut).toTuple()[i]
        c = max(getattr(box, f"{d}max") - mid, mid - getattr(box, f"{d}min"))
        moment = force * (lever - t * np.linalg.norm(b - a))
        out.append(mat["tensile_mpa"]["z"] * inertia / (moment * c))
    return min(out)


F = beams.stall_force_n()
# the bail with an arm standing up z from its axis at the origin, as _bending_sf reads a member; its ball's lever there
ARM_UP = linkage.rotation((1, 0, 0), 90.0 - gimbal.BAIL_ARM_DEG, (0, *gm.BAIL))
ARM_UP[:3, 3] -= (0, *gm.BAIL)
ARM_LEVER = math.dist(gm.BAIL, gm.BAIL_BALL)
_CRANK_Z = sum(gm.YAW_CRANK_Z) / 2
# (part, how it is turned, a, b, force, its axis, lever) per member: split, so each test holds CI's 15 s (#808)
MEMBERS = {
    "crank": (gimbal.yoke, np.eye(4), (0, 0, _CRANK_Z), (0, gm.CRANK, _CRANK_Z), F, "x", gm.CRANK),
    **{
        f"arm at x {x:+.1f}": (gimbal.bail, ARM_UP, (x, 0, 4), (x, 0, 11), F * ROD_LOAD, "y", ARM_LEVER - 4)
        for x, _, _ in BALLS
    },
    # on its bed, the input arm along -y from the axis
    "input arm": (gimbal.bail, BAIL_BED, (TIP[0], -5, 0), (TIP[0], -gm.BAIL_IN, 0), F * BAR_LOAD, "z", gm.BAIL_IN - 5),
}


@pytest.mark.parametrize("member", MEMBERS)
def test_the_yokes_crank_and_the_bails_arms_hold_the_servos_at_stall(member):
    """SF 2 (beams.MIN_SF) in bending: the crank under the yaw servo's stall at its pin; each bail arm under the pitch
    servo's at its ball (one arm taking it all: the push-rod's load, square to the arm, at the ball's reach from the
    axis); the input arm under the pitch bar's load at its pin. On the mechanical parts, which their Bones are carved
    from (#809)."""
    part, turned, *beam = MEMBERS[member]
    assert _bending_sf(part(mechanical=True).val().moved(gimbal._at(turned)), *beam) >= beams.MIN_SF


def test_each_push_rod_stays_within_its_cups_reach_of_the_balls_line():
    """gimbal.report reads the lids' clearance to a push-rod as a capsule CUP_R round the line between its balls."""
    v, _ = gimbal.push_rod().val().tessellate(0.01, 0.1)
    a, b = (np.array(p) for p in ROD_BALLS)
    along = (b - a) / np.linalg.norm(b - a)
    assert max(np.linalg.norm(np.cross(np.subtract(p.toTuple(), a), along)) for p in v) <= gm.ROD_R + 1e-6


# The lid drives' arms (#698, #967): each lies on its slab's face, its pins along x; (part, its joints in turn, how
# many times the lid servo's stall force at the bar's pin it carries: the link pins nearer the horn's hub)
LID_HORN_PIN = tuple(np.add(gm.LID_HORN, gm.LID_PIN))
LID_BONES = {
    "lid bar": (gimbal.lid_bar, [gm.LID_PIN, tuple(np.add(LID_HORN_PIN, gimbal.BAR_JOG)), LID_HORN_PIN], 1.0),
    "lid link": (
        gimbal.lid_link,
        [gm.LOWER_PIN, tuple(np.add(gm.LINK_PIN, gimbal.LINK_JOG)), gm.LINK_PIN],
        gm.CRANK / gm.LINK_CRANK,
    ),
}


def _bed_down(solid):
    """`solid` turned so its slab's lower face (along x) lies on the bed (z), as it prints."""
    return solid.moved(gimbal._at([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]]))


@pytest.mark.parametrize("part", LID_BONES)
def test_the_lid_bones_print_as_drawn_with_no_overhang_past_45_deg(part):
    assert bone.overhang_deg(_bed_down(LID_BONES[part][0]().val())) <= 45


@pytest.mark.parametrize("mechanical", [False, True])
@pytest.mark.parametrize("part", LID_BONES)
def test_each_lid_arm_keeps_its_end_pins_bores_in_both_styles(part, mechanical):
    """#1097: a bore for the M3 shank at each end pin, with wall round it through the slab's whole 3 mm, as a Bone and
    mechanical: the same interfaces (docs/adr/0020)."""
    make, joints, _ = LID_BONES[part]
    arm, w = make(mechanical=mechanical).val(), (gm.LID_X["bar"][1] - gm.LID_X["bar"][0]) / 2
    for y, z in (joints[0], joints[-1]):
        for x in (-w + 0.05, 0.0, w - 0.05):
            for dy, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                assert not arm.isInside(cq.Vector(x, y + dy * (gm.PIN_R - 0.05), z + dz * (gm.PIN_R - 0.05)))
                assert arm.isInside(cq.Vector(x, y + dy * (gm.PIN_R + 0.5), z + dz * (gm.PIN_R + 0.5)))


def _slice(solid, a, b, t, eps=0.01):
    """(mm2, the least mm4, the in-plane mm4, mm) of `solid`'s section square to the span a-b ((y, z), in its slab
    about x 0) at t: its area, its least second moment, the one that bends it in its plane, and its half-width there."""
    a, b = (np.array([0.0, *p]) for p in (a, b))
    along = (b - a) / np.linalg.norm(b - a)
    plane = cq.Plane(origin=tuple(a + (b - a) * t), xDir=(1, 0, 0), normal=tuple(along))
    cut = solid.intersect(cq.Workplane(plane).rect(60, 60).extrude(eps / 2, both=True).val())
    inertia = np.array(cq.Shape.matrixOfInertia(cut)) / eps
    basis = np.array([np.cross(along, (1, 0, 0)), (1.0, 0.0, 0.0)])
    mid = float(np.dot(cut.Center().toTuple(), basis[0]))
    half = max(abs(float(np.dot(v.toTuple(), basis[0])) - mid) for v in cut.Vertices())
    return cut.Volume() / eps, float(np.linalg.eigvalsh(basis @ inertia @ basis.T).min()), float(inertia[0, 0]), half


@pytest.mark.parametrize("part", LID_BONES)
def test_each_lid_bone_holds_its_lid_servo_at_stall(part):
    """SF 2 (beams.MIN_SF) in PETG across its layers along every span, the servo's stall force pulling or pushing it
    between its end pins: on its strength, a span's offset from that line bending it in its plane (out to its
    half-width), and against Euler buckling out of its slab between its end pins."""
    make, joints, load = LID_BONES[part]
    solid, mat = make().val(), g.MATERIALS[g.PRINTED[part][1]]
    force, (y0, z0), (y1, z1) = load * beams.stall_force_n(), joints[0], joints[-1]
    for a, b in zip(joints, joints[1:]):
        for t in (0.3, 0.5, 0.7):
            area, _, bend, half = _slice(solid, a, b, t)
            y, z = np.add(a, np.multiply(t, np.subtract(b, a)))
            off = abs((y - y0) * (z1 - z0) - (z - z0) * (y1 - y0)) / math.dist(joints[0], joints[-1])
            stress = force / area + force * off * half / bend
            assert mat["tensile_mpa"]["z"] / stress >= beams.MIN_SF, (a, b, t)
    least = min(_slice(solid, joints[0], joints[1], t)[1] for t in (0.3, 0.5, 0.7))
    assert math.pi**2 * mat["E_mpa"]["z"] * least / math.dist(joints[0], joints[-1]) ** 2 / force >= beams.MIN_SF
