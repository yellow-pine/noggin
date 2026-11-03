"""Seam: Morty's Shells (model/printed/skin.py) and the Seats cut into what carries them, as model/stages.py places
them: each a valid solid, the pupils keyed in their caps, and every Shell clear of every part but what carries it, at
rest and with each servo at either end."""

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
DOC = next(d for d in g.NEXT if d in g.SIMULATED)  # the whole Mech, mechanical: as physics runs it
REAL = next(d for d in g.NEXT if g.SKULL_SUB in g.NEXT[d])  # the realistic one: the skull's bones on it


@pytest.fixture(scope="module")
def head():
    """{face, hair, mouth cover: its shape}, built once (CI times a test, not its fixtures: #808)."""
    return {s: PARTS[f"next morty {s}"]().val() for s in ("face", "hair", "mouth cover")}


@pytest.mark.parametrize("stem", sk.SHELLS)
def test_a_shell_is_one_valid_solid(stem, head):
    shape = head.get(stem.removeprefix("next morty ")) or PARTS[stem]().val()
    assert shape.isValid() and len(shape.Solids()) == 1


def test_a_head_shell_built_again_is_the_same(head):
    """#838: every Shell shares the head's shapes (skin._head), and on Linux's OCCT a second build over shapes an
    earlier one's booleans used came out broken; each build starts from its own copy."""
    for s, shape in head.items():
        again = PARTS[f"next morty {s}"]().val()
        assert len(again.Solids()) == 1 and again.Volume() == pytest.approx(shape.Volume(), rel=1e-6), s


HEAD_LIMIT = (140.0, 140.0, 150.0)  # W, D, H: the head Cansin set (#838)


def test_mortys_head_fits_the_head_limit_ears_and_all(head):
    """His face (its ears and nose on), hair and mouth cover at rest fit 140 W x 140 D x 150 H mm (#850)."""
    lo = [min(getattr(h.BoundingBox(), f"{a}min") for h in head.values()) for a in "xyz"]
    hi = [max(getattr(h.BoundingBox(), f"{a}max") for h in head.values()) for a in "xyz"]
    assert all(s <= limit + 1e-3 for s, limit in zip(np.subtract(hi, lo), HEAD_LIMIT, strict=True))


def test_mortys_head_is_one_smooth_shape_round_from_every_angle():
    """The head every Shell is cut from (skin._head) has no crease: across each edge its two faces meet within 5 deg,
    so it never reads as a soft box where outlines meet (Cansin, #850)."""
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape

    shape, creases = skin._head(0.0).val(), []
    edges = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape.wrapped, TopAbs_EDGE, TopAbs_FACE, edges)
    for i in range(1, edges.Extent() + 1):
        e, faces = cq.Edge(edges.FindKey(i)), [cq.Face(f) for f in edges.FindFromIndex(i)]
        if len(faces) == 2 and e.Length() > 1.0:  # a loft's end caps are sub-mm
            for t in (0.25, 0.5, 0.75):
                p = e.positionAt(t)
                if faces[0].normalAt(p).getAngle(faces[1].normalAt(p)) > math.radians(5):
                    creases.append((round(p.x), round(p.y), round(p.z)))
    assert creases == []


def test_mortys_face_and_hair_meet_without_overlapping(head):
    """Printed apart and pressed together on the face's Seats: the hair's bosses and walls clear the face's, but for
    its balls touching the face's grooves (the clearance test skips a Shell's carrier)."""
    assert head["face"].intersect(head["hair"]).Volume() < 0.1


@pytest.mark.parametrize("side, inward", [("L", -1), ("R", 1)])
def test_the_pupil_sits_in_its_seat_toward_the_other_eye(side, inward):
    """The pupil fills its jagged seat to PUPIL_FIT a side, which keys it, and the seat turns TOE_IN toward the other
    eye (#630)."""
    pupil, cap = PARTS[f"next morty {side} pupil"]().val(), PARTS[f"next {side} eyeball cap"]().val()
    assert pupil.intersect(cap).Volume() < 1e-6
    assert pupil.Center().x == pytest.approx(inward * gm.CAP_R * math.sin(math.radians(gm.TOE_IN)), abs=0.1)
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
SEAMS = {frozenset(("next morty shirt front", "next morty shirt back"))}  # Shells meeting 0.2 mm apart by design
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
    for rider, carrier in stages.RIDES.items():
        if rider.removesuffix(":1") in out:
            out[rider.removesuffix(":1")].add(carrier.removesuffix(":1"))
    return out


@pytest.mark.model
@pytest.mark.parametrize("pose", list(_poses()))
def test_every_shell_clears_every_part_but_what_carries_it(pose):
    """At rest and at each servo's ends, each Shell keeps CLEAR_MM from each part it does not sit on, printed or
    hardware (#51 shell containment)."""
    assert _near(DOC, pose) == []


@pytest.mark.model
@pytest.mark.parametrize("pose", list(_poses(REAL)))
def test_every_shell_clears_the_realistic_skulls_bones(pose):
    """The Skins fit the realistic Skeleton too (#838): each Shell CLEAR_MM off the skull's bones as a Skin wears them
    (g.WORN), which the mechanical document has none of."""
    assert _near(REAL, pose, only=set(g.BONES)) == []


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
