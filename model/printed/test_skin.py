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


# W, D, H: the head Cansin set (#838), grown with the eyes (#901), the ears outside its width (#844)
HEAD_LIMIT = sk.grown(140.0, 140.0, 150.0)


@pytest.mark.parametrize("skin_shape", g.SKINS)
def test_each_head_fits_the_head_limit_but_for_its_ears(skin_shape, heads):
    """Its face, hair and mouth cover at rest fit 140 W x 140 D x 150 H mm grown x1.5 (#901), Cansin's tufts too (#813); only the ears
    stand out of its sides."""
    head = list(heads[skin_shape].values())
    lo = [min(getattr(h.BoundingBox(), f"{a}min") for h in head) for a in "xyz"]
    hi = [max(getattr(h.BoundingBox(), f"{a}max") for h in head) for a in "xyz"]
    _, depth, height = np.subtract(hi, lo)
    assert depth <= HEAD_LIMIT[1] and height <= HEAD_LIMIT[2]
    y, z, r, _ = skin.EAR
    earless = cq.Workplane().add(head).cut(gimbal.cyl("x", (0, y, z), r + 0.1, (-300, 300))).val().BoundingBox()
    assert earless.xlen <= HEAD_LIMIT[0] + 1e-3 < max(h.BoundingBox().xlen for h in head)


@pytest.mark.parametrize("skin_shape", g.SKINS)
def test_the_face_and_hair_meet_without_overlapping(skin_shape, heads):
    """Printed apart and pressed together on the face's Seats: the hair's bosses and walls clear the face's, but for
    its balls touching the face's grooves (the clearance test skips a Shell's carrier)."""
    assert heads[skin_shape]["face"].intersect(heads[skin_shape]["hair"]).Volume() < 0.1


@pytest.mark.parametrize("glued", [s for s, (c, _) in sk.GLUED.items() if s.startswith("cansin ")])
def test_cansins_glued_shells_fill_their_pockets_without_overlapping(glued):
    """#813: his brows in the face, his teeth in the mouth cover, each pupil plug in its cap's jagged seat and its dot
    in the plug: each in its pocket, within its fit of what carries it and sharing no volume with it."""
    carrier = sk.GLUED[glued][0]
    shape, held = PARTS[glued]().val(), PARTS[carrier]().val()
    if "brow" in glued:  # drawn in its eye's frame, its pocket in the head's
        shape = shape.translate(cq.Vector(*gm.EYE[glued.split()[1]]))
    assert shape.intersect(held).Volume() < 1e-3
    assert shape.distance(held) <= gm.PUPIL_FIT + 1e-3


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
    hardware (#51 shell containment), in each Skin (#813)."""
    assert _near(doc, pose) == []


@pytest.mark.model
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
