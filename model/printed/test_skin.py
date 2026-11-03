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


@pytest.mark.parametrize("stem", sk.SHELLS)
def test_a_shell_is_one_valid_solid(stem):
    shape = PARTS[stem]().val()
    assert shape.isValid() and len(shape.Solids()) == 1


HEAD_LIMIT = (140.0, 140.0, 150.0)  # W, D, H: the head Cansin set (#838), the ears outside its width (#844)


def test_mortys_head_fits_the_head_limit_but_for_his_ears():
    """His face, hair and mouth cover at rest fit 140 W x 140 D x 150 H mm; only his ears stand out of its sides."""
    head = [PARTS[f"next morty {s}"]().val() for s in ("face", "hair", "mouth cover")]
    lo = [min(getattr(h.BoundingBox(), f"{a}min") for h in head) for a in "xyz"]
    hi = [max(getattr(h.BoundingBox(), f"{a}max") for h in head) for a in "xyz"]
    _, depth, height = np.subtract(hi, lo)
    assert depth <= HEAD_LIMIT[1] and height <= HEAD_LIMIT[2]
    y, z, r, _ = skin.EAR
    earless = cq.Workplane().add(head).cut(gimbal.cyl("x", (0, y, z), r + 0.1, (-100, 100))).val().BoundingBox()
    assert earless.xlen <= HEAD_LIMIT[0] + 1e-3 < max(h.BoundingBox().xlen for h in head)


def test_mortys_face_and_hair_meet_without_overlapping():
    """Printed apart and pressed together on the face's Seats: the hair's bosses and walls clear the face's, but for
    its balls touching the face's grooves (the clearance test skips a Shell's carrier)."""
    face, hair = (PARTS[f"next morty {s}"]().val() for s in ("face", "hair"))
    assert face.intersect(hair).Volume() < 0.1


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


def _poses():
    stage = stages.STAGES[DOC]
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
    stage, mats, carriers, near = stages.STAGES[DOC], _poses()[pose], _carriers(), []
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
            pts = trimesh.transform_points(_cloud(stages.stem(q.file)), into @ mats[other])
            pts = pts[np.all((pts > lo) & (pts < hi), axis=1)]
            d = _tree(stem).query(pts, distance_upper_bound=CLEAR_MM)[0] if len(pts) else [np.inf]
            if np.min(d) < CLEAR_MM:
                near.append((n, other, round(float(np.min(d)), 2)))
    assert near == []
