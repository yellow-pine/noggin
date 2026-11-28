"""Seam: the eyeball caps (model/printed/skin.py) and the Seats cut into what carries them, as model/stages.py places
them: each a valid solid, each Seat flush in its carrier, and each cap clear of every part but what carries it, at rest
and with each servo at either end."""

import functools

import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

from model import geometry as g
from model import gimbal as gm
from model import skin as sk
from model import stages
from model.printed import PARTS, gimbal, skin, styled

CLEAR_MM = gm.LID_CLEAR_MM  # a Shell's least room to a part it does not sit on (#51 shell containment)
DOC = next(d for d in g.MECH if d in g.SIMULATED)  # the whole Mech, mechanical: as physics runs it
REAL = next(d for d in g.MECH if g.SKULL_SUB in g.MECH[d])  # the realistic one: the skull's bones on it


DRAWN = [s for s in sk.SHELLS if s in PARTS]  # the Shells drawn here; a Sculpt's are held in model/morty/test_shells.py


@pytest.mark.parametrize("stem", DRAWN)
def test_a_shell_is_one_valid_solid(stem):
    shape = PARTS[stem]().val()
    assert shape.isValid() and len(shape.Solids()) == 1


@pytest.mark.model
@pytest.mark.parametrize(
    "seat",
    [s for s in sk.SEATS if s.carrier in PARTS and s.carrier not in sk.SHELLS],  # a Seat in bone: model/skeleton's
    ids=lambda s: f"{s.shell} on {s.carrier} {s.at[0]:+.0f}",
)
def test_a_seat_on_the_skeleton_is_flush_in_its_carriers_surface(seat):
    """#852: nothing of a Skeleton part stands in front of a Seat's face, and the part is there right behind it, round
    its magnet's pocket: no raised pad, the pocket and the grooves sunk into the carrier, in each of its styles."""
    proud = skin._placed(gimbal.cyl("z", (0, 0, 0), sk.PAD_R, (0.05, 3.0)), seat).val()
    ring = gimbal.cyl("z", (0, 0, 0), sk.RING - sk.GROOVE - 0.1, (-0.5, -0.2))  # under a lid's curve at its edge
    behind = skin._placed(ring.cut(gimbal.cyl("z", (0, 0, 0), sk.MAGNET[0] / 2 + sk.FIT + 0.1, (-1, 1))), seat).val()
    for style in dict.fromkeys((seat.carrier, styled(seat.carrier, mechanical=True))):
        carrier = PARTS[style]().val()
        assert carrier.intersect(proud).Volume() < 1e-3, style
        assert carrier.intersect(behind).Volume() == pytest.approx(behind.Volume(), rel=0.02), style


@pytest.mark.model
@pytest.mark.parametrize("pair", sorted({(s.shell, s.carrier) for s in sk.SEATS if s.shell in DRAWN}), ids=" on ".join)
def test_a_shell_meets_what_carries_it_only_where_its_balls_touch(pair):
    """Drawn in the same frame, a Shell and its carrier share at most the balls' contacts in the grooves: no boss or wall
    of the Shell runs into the part it sits on (the clearance test skips that pair)."""
    shell, carrier = (PARTS[s]().val() for s in pair)
    assert shell.intersect(carrier).Volume() < 0.1


SPACING = 0.4  # mm between the points sampled on each surface
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
    """{Shell: the parts it sits on}: its Seats' carriers, the Shell it is glued in, and what it RIDES."""
    out = {s: set() for s in (*sk.SHELLS, *sk.GLUED)}
    for s in sk.SEATS:
        out[s.shell].add(s.carrier)
    for shell, carrier in sk.GLUED.items():
        out[shell].add(carrier)
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
@pytest.mark.bones
@pytest.mark.parametrize("pose", list(_poses(REAL)))
def test_every_shell_clears_the_realistic_skulls_bones(pose):
    """The Shells fit the realistic Skeleton too (#838): each CLEAR_MM off the skull's bones as a Skin wears them
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
            if other == n or o in carriers[stem] or stem in carriers.get(o, ()):
                continue
            if only is not None and o not in only:
                continue
            pts = trimesh.transform_points(_cloud(stages.stem(q.file)), into @ mats[other])
            pts = pts[np.all((pts > lo) & (pts < hi), axis=1)]
            d = _tree(stem).query(pts, distance_upper_bound=CLEAR_MM)[0] if len(pts) else [np.inf]
            if np.min(d) < CLEAR_MM:
                near.append((n, other, round(float(np.min(d)), 2)))
    return near
