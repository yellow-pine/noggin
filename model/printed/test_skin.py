"""Seam: the Skins' Shells (model/printed/skin.py: Morty's, Cansin's) and the Seats cut into what carries them, as
model/stages.py places them: each a valid solid, the pupils keyed in their caps, and every Shell clear of every part but
what carries it, at rest and with each servo at either end, in each Skin."""

import functools
import math

import cadquery as cq
import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

from model import geometry as g
from model import gimbal as gm
from model import skin as sk
from model import stages
from model.printed import PARTS, gimbal, skin

CLEAR_MM = gm.LID_CLEAR_MM  # a Shell's least room to a part it does not sit on (#51 shell containment)
DOC = next(d for d in g.MECH if d in g.SIMULATED)  # the whole Mech, mechanical: as physics runs it
REAL = next(d for d in g.MECH if g.SKULL_SUB in g.MECH[d])  # the realistic one: the skull's bones on it
HEADS = ("face", "hair", "mouth cover")


@pytest.fixture(scope="module")
def heads():
    """{Skin: {face, hair, mouth cover: its shape}}, built once (CI times a test, not its fixtures: #808)."""
    return {skin: {s: PARTS[f"{skin} {s}"]().val() for s in HEADS} for skin in g.SKINS}


def _built(stem, heads):
    skin_shape, _, rest = stem.partition(" ")
    return heads.get(skin_shape, {}).get(rest) or PARTS[stem]().val()


@pytest.mark.parametrize("stem", sk.SHELLS)
def test_a_shell_is_one_valid_solid(stem, heads):
    shape = _built(stem, heads)
    assert shape.isValid() and len(shape.Solids()) == 1


@pytest.mark.parametrize("skin_shape", g.SKINS)
def test_a_head_shell_built_again_is_the_same(skin_shape, heads):
    """#838: every Shell shares the head's shapes (skin._head), and on Linux's OCCT a second build over shapes an
    earlier one's booleans used came out broken; each build starts from its own copy."""
    for s, shape in heads[skin_shape].items():
        again = PARTS[f"{skin_shape} {s}"]().val()
        assert len(again.Solids()) == 1 and again.Volume() == pytest.approx(shape.Volume(), rel=1e-6), s


TURN = 35.0  # deg the head's surface may turn from one ring to the next: a shelf over the frame's beam turned 45


def test_mortys_head_is_one_smooth_surface_round_from_every_angle():
    """#850: the head every Shell is cut from has no crease where outlines meet, as the old head's three did (Cansin:
    "a soft box"): one curved face through his rings and their apex, closed by a flat floor under the head's own; and
    from the small rings under the apex down to the floor, no ring turns it more than TURN deg."""
    faces = skin._head(0.0).val().Faces()
    assert sorted(f.geomType() for f in faces) == ["BSPLINE", "PLANE"]
    floor = next(f for f in faces if f.geomType() == "PLANE")
    assert floor.BoundingBox().zmax < sk.HEAD_Z[0]
    rings = sk.head_grid()[3 : int(np.argmax(sk.RINGS[:, 0] < sk.HEAD_Z[0])) + 1]  # to the first under the floor
    along = np.diff(rings, axis=0)
    along /= np.linalg.norm(along, axis=2, keepdims=True)
    turn = np.degrees(np.arccos(np.clip((along[:-1] * along[1:]).sum(axis=2), -1.0, 1.0)))
    assert turn.max() < TURN


@pytest.mark.parametrize("skin_shape", g.SKINS)
def test_each_head_stands_on_mortys_rings_but_for_its_ears_and_nose(skin_shape, heads):
    """#850: its face, hair and mouth cover at rest stand within the box of the rings they are drawn round
    (model/head.json), HAIR proud at most (Bart's crown 0.6 mm round them); only the ears stand out of its sides, the
    nose out of its front and Bart's spikes out of his crown (#807)."""
    head = dict(heads[skin_shape])
    if skin_shape == "bart":
        top = sk.HEAD_Z[1] + skin.BART_UP + 0.01
        above = gimbal.cyl("z", (0, 0, 0), 200, (top, top + 100))
        spikes = cq.Workplane().add(head["hair"]).intersect(above).val()
        assert len(spikes.Solids()) == 9  # his nine, on the flat crown
        assert spikes.BoundingBox().zmax == pytest.approx(sk.HEAD_Z[1] + skin.SPIKE[1], abs=0.01)
        head["hair"] = cq.Workplane().add(head["hair"]).cut(above).val()
    y, z, r, _ = sk.EAR
    nose_r, nose_z, _ = sk.NOSE
    features = gimbal.cyl("x", (0, y, z), r + 0.1, (-300, 300)).union(
        gimbal.cyl("z", (0, sk.head_front(0.0, nose_z), 0), nose_r + 5.0, (nose_z - nose_r - 1, nose_z + nose_r + 1))
    )
    bare = [cq.Workplane().add(h).cut(features).val().BoundingBox() for h in head.values()]
    over = sk.HAIR + 0.6
    assert min(b.xmin for b in bare) >= -sk.HEAD_X - over and max(b.xmax for b in bare) <= sk.HEAD_X + over
    assert min(b.ymin for b in bare) >= sk.HEAD_Y[0] - over and max(b.ymax for b in bare) <= sk.HEAD_Y[1] + over
    assert min(b.zmin for b in bare) >= sk.HEAD_Z[0] - 1e-3 and max(b.zmax for b in bare) <= sk.HEAD_Z[1] + over
    assert max(h.BoundingBox().xmax for h in head.values()) > sk.HEAD_X + over  # the ears


@pytest.mark.parametrize("skin_shape", g.SKINS)
def test_the_face_and_hair_meet_without_overlapping(skin_shape, heads):
    """Printed apart and pressed together on the face's Seats: the hair's bosses and walls clear the face's, but for
    its balls touching the face's grooves (the clearance test skips a Shell's carrier)."""
    assert heads[skin_shape]["face"].intersect(heads[skin_shape]["hair"]).Volume() < 0.1


@pytest.mark.parametrize("glued", [s for s in sk.GLUED if s.split()[0] in sk.DOTTED])
def test_the_glued_shells_fill_their_pockets_without_overlapping(glued):
    """#813, #807: Cansin's brows in the face, his teeth in the mouth cover, each pupil plug (Bart's too) in its cap's
    jagged seat and its dot in the plug: each in its pocket, within its fit of what carries it, sharing no volume."""
    carrier = sk.GLUED[glued][0]
    shape, held = PARTS[glued]().val(), PARTS[carrier]().val()
    if "brow" in glued:  # drawn in its eye's frame, its pocket in the head's
        shape = shape.translate(cq.Vector(*gm.EYE[glued.split()[1]]))
    assert shape.intersect(held).Volume() < 1e-3
    assert shape.distance(held) <= gm.PUPIL_FIT + 1e-3


def test_barts_head_holds_mortys_whole_with_a_flat_crown():
    """#807: Bart's head is Morty's with a flat crown in the same box, so whatever clears Morty's Shells inside clears
    Bart's; his crown is level over the cranium where Morty's is round (#850: up to his apex)."""
    morty, bart = (skin._head(0.0, k).val() for k in ("morty", "bart"))
    assert morty.cut(bart).Volume() < 1e-3
    corners = [[getattr(b.BoundingBox(), f"{a}{e}") for a in "xyz" for e in ("min", "max")] for b in (morty, bart)]
    assert np.allclose(*corners, atol=0.6)  # the same box: his crown 0.5 mm round Morty's rings, BART_UP over the apex
    crown = gimbal.cyl("z", (0, 30, 0), 1.0, (sk.HEAD_Z[1] - 0.5, sk.HEAD_Z[1] - 0.1)).val()
    for x in (-40.0, 0.0, 40.0):  # level across, where Morty's falls away from his middle
        at = crown.translate(cq.Vector(x, 0, 0))
        assert bart.intersect(at).Volume() == pytest.approx(at.Volume(), rel=1e-3)
    assert morty.intersect(crown.translate(cq.Vector(40, 0, 0))).Volume() < 1e-3


def test_the_hair_is_the_head_over_his_model_sheets_hairline_and_behind_the_nape():
    """#992: the hair's region is the sheet's hairline (model/skin.py outline, which the review's reference is cut by
    too) swept across the head, its face front on the Shells' (FACE_Y), and all behind NAPE: 1 mm over the line is hair
    and 1 mm under it face, at the middle and at either side, down to the nape."""
    region = skin._hair(0.0).val()
    line = sk.contour("hairline") + (sk.FACE_Y - sk.FACE_FRONT[0] * gm.SPACING, 0.0)
    t = np.gradient(line, axis=0)
    over = np.c_[-t[:, 1], t[:, 0]] / np.linalg.norm(t, axis=1)[:, None]  # forehead first: left of it is up and back
    for (y, z), (dy, dz) in zip(line, over, strict=True):
        for x in (-60.0, 0.0, 60.0):
            assert region.isInside(cq.Vector(x, y + dy, z + dz))
            assert region.isInside(cq.Vector(x, y - dy, z - dz)) == (y - dy > sk.NAPE)


@pytest.mark.parametrize("side, inward", [("L", -1), ("R", 1)])
def test_the_pupil_sits_in_its_seat_toward_the_other_eye(side, inward):
    """The pupil fills its jagged seat to PUPIL_FIT a side, which keys it, and the seat turns TOE_IN toward the other
    eye (#630)."""
    pupil, cap = PARTS[f"morty {side} pupil"]().val(), PARTS[f"{side} eyeball cap"]().val()
    assert pupil.intersect(cap).Volume() < 1e-6
    # the pupil's centre a little inside its seat's shift: Morty's big pupil clipped by the cap's curve (#901)
    assert pupil.Center().x == pytest.approx(inward * gm.CAP_R * math.sin(math.radians(gm.TOE_IN)), abs=0.3)
    seat = cq.Workplane().add(cap).union(cq.Workplane().add(pupil)).val()
    dome = gimbal.ball(gm.CAP_R).val().Volume()
    assert seat.Volume() < dome  # the cap and its pupil fill no more than the dome: the pupil is in the seat


@pytest.mark.model
@pytest.mark.parametrize(
    "seat",
    [s for s in sk.SEATS if s.carrier not in sk.SHELLS],
    ids=lambda s: f"{s.shell} on {s.carrier} {s.at[0]:+.0f}",
)
def test_a_seat_on_the_skeleton_is_flush_in_its_carriers_surface(seat):
    """#852: nothing of a Skeleton part stands in front of a Seat's face, and the part is there right behind it, round
    its magnet's pocket: no raised pad, the pocket and the grooves sunk into the carrier."""
    carrier = PARTS[seat.carrier]().val()
    proud = skin._placed(gimbal.cyl("z", (0, 0, 0), sk.PAD_R, (0.05, 3.0)), seat).val()
    ring = gimbal.cyl("z", (0, 0, 0), sk.RING - sk.GROOVE - 0.1, (-0.5, -0.2))  # under a lid's curve at its edge
    behind = skin._placed(ring.cut(gimbal.cyl("z", (0, 0, 0), sk.MAGNET[0] / 2 + sk.FIT + 0.1, (-1, 1))), seat).val()
    assert carrier.intersect(proud).Volume() < 1e-3
    assert carrier.intersect(behind).Volume() == pytest.approx(behind.Volume(), rel=0.02)


@pytest.mark.model
@pytest.mark.parametrize("pair", sorted({(s.shell, s.carrier) for s in sk.SEATS}), ids=" on ".join)
def test_a_shell_meets_what_carries_it_only_where_its_balls_touch(pair):
    """Drawn in the same frame, a Shell and its carrier share at most the balls' contacts in the grooves: no boss or wall
    of the Shell runs into the part it sits on (the clearance test skips that pair)."""
    shell, carrier = (PARTS[s]().val() for s in pair)
    assert shell.intersect(carrier).Volume() < 0.1


SPACING = 0.4  # mm between the points sampled on each surface
SEAMS = {frozenset((f"{s} shirt front", f"{s} shirt back")) for s in g.SKINS}  # meeting 0.2 mm apart
# shortcut: sampled surfaces read a distance up to SPACING long; OCCT's exact distance took minutes a pose (#665)


@functools.cache
def _cloud(stem):
    """Points on the part's mesh (just ours): its vertices and its surface every SPACING."""
    mesh = trimesh.load(stages.stl(stem), force="mesh")
    return np.vstack([mesh.vertices, trimesh.sample.sample_surface_even(mesh, int(mesh.area / SPACING**2), seed=0)[0]])


@functools.cache
def _tree(stem):
    return cKDTree(_cloud(stem))


@functools.cache
def _poses(doc=DOC):
    stage = stages.STAGES[doc]
    out = {"rest": {n: p.matrix for n, p in stage.parts.items()}}
    for horn, h in stage.horns.items():
        out |= {f"{horn} {deg:.0f}": stages.pose(stage, horn, deg).parts for deg in h.limits}
    return out


def _carriers():
    """{Shell: the parts it sits on}: its Seats' carriers, and what it RIDES."""
    out = {s: set() for s in sk.SHELLS}
    for s in sk.SEATS:
        out[s.shell].add(s.carrier)
    for s, (carrier, _) in sk.GLUED.items():
        out[s].add(carrier)
    for rider, carrier in stages.RIDES.items():
        if rider.removesuffix(":1") in out:
            out[rider.removesuffix(":1")].add(carrier.removesuffix(":1"))
    return out


@pytest.mark.model
@pytest.mark.parametrize("doc", [g.dressed(DOC, s) for s in g.SKINS])  # its id the document's: its Model shard's -k
@pytest.mark.parametrize("pose", list(_poses()))
def test_every_shell_clears_every_part_but_what_carries_it(pose, doc):
    """At rest and at each servo's ends, each Shell keeps CLEAR_MM from each part it does not sit on, printed or
    hardware (#51 shell containment), in each Skin (#813): since #850 the hair too, round the life-size head's
    hardware (#978)."""
    assert _near(doc, pose) == []


@pytest.mark.model
def test_the_hair_lifts_off_upward_and_the_face_forward_past_what_they_cover():
    """#850: off their Seats along their normals, at rest. The hair's wall follows the head in under its widest, behind
    the hairline down to the floor: nothing of the Mech lies over that wall, so the hair lifts straight up. The face
    reaches back to the hairline, past where the head is widest: nothing ahead of its back edge is as wide, so it comes
    off forward."""
    stage, mats = stages.STAGES[DOC], _poses(DOC)["rest"]
    face = next(n for n, p in stage.parts.items() if stages.stem(p.file) == "morty face")  # the head's frame
    parts = [n for n, p in stage.parts.items() if stages.stem(p.file) not in sk.SHELLS]
    pts = np.vstack(
        [
            trimesh.transform_points(_cloud(stages.stem(stage.parts[n].file)), np.linalg.inv(mats[face]) @ mats[n])
            for n in parts
        ]
    )
    pts = pts[pts[:, 2] > sk.HEAD_Z[0]]
    inner, round_ = sk.head_grid(sk.WALL), np.r_[sk.THETA, 2 * np.pi - sk.THETA[-2:0:-1], 2 * np.pi]
    for z, c, ring in zip(sk.RINGS[:, 0], sk.RINGS[:, 1], inner, strict=True):
        if z < sk.HEAD_Z[0]:
            continue
        over = pts[(pts[:, 2] > z) & (pts[:, 1] > sk.face_back(z))]  # over this ring's hair
        radius = np.hypot(ring[:, 0], ring[:, 1] - c)
        at = np.arctan2(over[:, 0], c - over[:, 1]) % (2 * np.pi)
        room = np.interp(at, round_, np.r_[radius, radius[0]]) - np.hypot(over[:, 0], over[:, 1] - c)
        assert room.min(initial=np.inf) > CLEAR_MM, z
    ahead = pts[pts[:, 1] < sk.face_back(pts[:, 2])]
    heights = np.arange(sk.HEAD_Z[0], sk.HEAD_Z[1])
    edge = np.interp(ahead[:, 2], heights, [sk.head_x(float(sk.face_back(z)), z) - sk.WALL for z in heights])
    assert (edge - np.abs(ahead[:, 0])).min() > CLEAR_MM


@pytest.mark.model
@pytest.mark.bones
@pytest.mark.parametrize("doc", [g.dressed(REAL, s) for s in g.SKINS])
@pytest.mark.parametrize("pose", list(_poses(REAL)))
def test_every_shell_clears_the_realistic_skulls_bones(pose, doc):
    """The Skins fit the realistic Skeleton too (#838): each Shell CLEAR_MM off the skull's bones as a Skin wears them
    (g.WORN), which the mechanical document has none of."""
    assert _near(doc, pose, only=set(g.BONES)) == []


def _near(doc, pose, only=None):
    """[(Shell, part, mm)] closer than CLEAR_MM in `doc` at `pose`: of the parts `only` names, if given."""
    stage, mats, carriers, near = stages.STAGES[doc], _poses(doc)[pose], _carriers(), []
    for n, p in stage.parts.items():
        stem = stages.stem(p.file)
        if stem not in carriers:
            continue
        into = np.linalg.inv(mats[n])  # the other parts into the Shell's own frame, where its tree is
        lo, hi = _cloud(stem).min(axis=0) - CLEAR_MM, _cloud(stem).max(axis=0) + CLEAR_MM
        for other, q in stage.parts.items():
            o = stages.stem(q.file).removesuffix(g.MECHANICAL)
            if other == n or o in carriers[stem] or stem in carriers.get(o, ()) or {stem, o} in SEAMS:
                continue
            if only is not None and o not in only:
                continue
            pts = trimesh.transform_points(_cloud(stages.stem(q.file)), into @ mats[other])
            pts = pts[np.all((pts > lo) & (pts < hi), axis=1)]
            d = _tree(stem).query(pts, distance_upper_bound=CLEAR_MM)[0] if len(pts) else [np.inf]
            if np.min(d) < CLEAR_MM:
                near.append((n, other, round(float(np.min(d)), 2)))
    return near


@pytest.mark.model
@pytest.mark.parametrize("doc", [g.dressed(DOC, s) for s in g.SKINS])
def test_every_shell_moves_with_its_motion_region_and_the_body_never_moves(doc):
    """#969: with each servo at either end, each Shell moves exactly as its Motion region's carrier (sk.MOTION) does, and
    the torso's Shells not at all: no head motion reaches the shirt, no jaw motion the face."""
    stage = stages.STAGES[doc]
    rest = {n: p.matrix for n, p in stage.parts.items()}
    shells = {
        n: sk.MOTION[sk.region(stages.stem(p.file))] for n, p in stage.parts.items() if stages.stem(p.file) in sk.SHELLS
    }
    assert {sk.region(stages.stem(stage.parts[n].file)) for n in shells} >= {"head", "jaw", "torso"}
    for horn, h in stage.horns.items():
        for deg in h.limits:
            mats = _poses(doc)[f"{horn} {deg:.0f}"]
            for n, carrier in shells.items():
                moved = mats[n] @ np.linalg.inv(rest[n])
                by = np.eye(4) if carrier is None else mats[f"{carrier}:1"] @ np.linalg.inv(rest[f"{carrier}:1"])
                assert np.allclose(moved, by, atol=1e-6), (n, horn, deg)
