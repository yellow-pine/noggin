"""Seam: each Skin's Shells, Morty's and Bart's (model/printed/skin.py) and the Seats cut into what carries them, as
model/stages.py places them: each a valid solid, the pupils keyed in their caps, and every Shell clear of every part
but what carries it, at rest and with each servo at either end."""

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
# each in every Skin shape drawn (#807): Morty's, then Bart's
DOCS, REALS = ([d + s for s in g.SKIN_SUFFIX.values()] for d in (DOC, REAL))
HEADS = {}


@pytest.fixture(scope="module", params=sk.SKINS)
def head(request):
    """{face, hair, mouth cover: its shape} of a Skin, built once (CI times a test, not its fixtures: #808)."""
    k = request.param
    return HEADS.setdefault(k, {s: PARTS[f"next {k} {s}"]().val() for s in ("face", "hair", "mouth cover")})


@pytest.mark.parametrize("stem", sk.SHELLS)
def test_a_shell_is_one_valid_solid(stem):
    k, s = stem.split()[1], stem.split(maxsplit=2)[-1]
    shape = HEADS.get(k, {}).get(s) or PARTS[stem]().val()
    assert shape.isValid() and len(shape.Solids()) == 1


def test_a_head_shell_built_again_is_the_same(head):
    """#838: every Shell shares the head's shapes (skin._head), and on Linux's OCCT a second build over shapes an
    earlier one's booleans used came out broken; each build starts from its own copy."""
    k = next(k for k, h in HEADS.items() if h is head)
    for s, shape in head.items():
        again = PARTS[f"next {k} {s}"]().val()
        assert len(again.Solids()) == 1 and again.Volume() == pytest.approx(shape.Volume(), rel=1e-6), s


HEAD_LIMIT = (140.0, 140.0, 150.0)  # W, D, H: the head Cansin set (#838), the ears outside its width (#844)


def test_a_head_fits_the_head_limit_but_for_its_ears_and_barts_spikes(head):
    """His face, hair and mouth cover at rest fit 140 W x 140 D x 150 H mm; only his ears stand out of its sides, and
    Bart's spikes out of its top (#807)."""
    spiky = head["hair"] is HEADS.get("bart", {}).get("hair")
    if spiky:
        top = head["hair"].BoundingBox().zmax
        assert top == pytest.approx(sk.HEAD_Z[1] + skin.SPIKE[1], abs=0.01)
        cut = gimbal.cyl("z", (0, 0, 0), 200, (sk.HEAD_Z[1] + 0.01, top + 1))
        crown = cq.Workplane().add(head["hair"]).cut(cut).val()
        assert len(cq.Workplane().add(head["hair"]).intersect(cut).val().Solids()) == 9  # his nine spikes
        head = {**head, "hair": crown}
    head = list(head.values())
    lo = [min(getattr(h.BoundingBox(), f"{a}min") for h in head) for a in "xyz"]
    hi = [max(getattr(h.BoundingBox(), f"{a}max") for h in head) for a in "xyz"]
    _, depth, height = np.subtract(hi, lo)
    assert depth <= HEAD_LIMIT[1] and height <= HEAD_LIMIT[2]
    y, z, r, _ = skin.EAR
    earless = cq.Workplane().add(head).cut(gimbal.cyl("x", (0, y, z), r + 0.1, (-100, 100))).val().BoundingBox()
    assert earless.xlen <= HEAD_LIMIT[0] + 1e-3 < max(h.BoundingBox().xlen for h in head)


def test_a_face_and_its_hair_meet_without_overlapping(head):
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


@pytest.mark.parametrize("side", ["L", "R"])
def test_barts_pupil_is_a_dot_over_the_caps_jagged_seat_clear_of_the_lid(side):
    """#807: the caps are every Skin's, their seat Morty's star; Bart's pupil keys in it and covers it with a round dot,
    DOT[1] proud of the dome, so the cap shows no seat round it and the upper lid passes CLEAR_MM over it."""
    pupil, cap = PARTS[f"next bart {side} pupil"]().val(), PARTS[f"next {side} eyeball cap"]().val()
    assert pupil.intersect(cap).Volume() < 1e-6
    box = pupil.BoundingBox()
    r = gm.CAP_R * math.sin(math.radians(gm.PUPIL_DEG)) + skin.DOT[0]
    assert box.xlen == pytest.approx(2 * r, abs=0.01) and box.zlen == pytest.approx(2 * r, abs=0.01)  # round
    star = skin._pupil_prism(side).intersect(gimbal.ball(gm.CAP_R + 0.2).cut(gimbal.ball(gm.CAP_R - 0.2))).val()
    seat = star.cut(cap).cut(pupil)  # the seat's opening on the dome, less what the cap and the dot fill
    assert seat.Volume() < 0.02 * star.Volume()
    far = max(np.linalg.norm(v.toTuple()) for v in pupil.Vertices())
    assert far == pytest.approx(gm.CAP_R + skin.DOT[1], abs=0.01) and far + CLEAR_MM <= gm.LID_R[0]


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
SEAMS = {frozenset((f"next {k} shirt front", f"next {k} shirt back")) for k in sk.SKINS}  # 0.2 mm apart by design
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
@pytest.mark.parametrize("doc, pose", [(d, p) for d in DOCS for p in _poses(d)])
def test_every_shell_clears_every_part_but_what_carries_it(doc, pose):
    """At rest and at each servo's ends, each Shell keeps CLEAR_MM from each part it does not sit on, printed or
    hardware (#51 shell containment), in each Skin (#807)."""
    assert _near(doc, pose) == []


@pytest.mark.model
@pytest.mark.parametrize("doc, pose", [(d, p) for d in REALS for p in _poses(d)])
def test_every_shell_clears_the_realistic_skulls_bones(doc, pose):
    """The Skins fit the realistic Skeleton too (#838): each Shell CLEAR_MM off the skull's bones as a Skin wears them
    (g.WORN), which the mechanical document has none of; Bart's too (#807), the bones carved round Morty's."""
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
