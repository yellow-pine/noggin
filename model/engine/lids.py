"""The lids seen from the front, for the gesture replay (#39): where each lid pair's edges sit at a lid horn angle and
the horn angles at which the model's lids are closed and open. Angles are elevations about the lid pivot axis (X)
through the eye centre, 0 straight ahead (-Z), positive up, measured on the vertical plane through the eye centre:
the inside lid is the upper one, the outside lid the lower one. Closed: the two edges just meet over the eyeball.
Open: both edges have turned far enough that the lid shell's outer surface projects outside the eyeball's silhouette
(the eyeball's front cap is clear from the front)."""

import math
from functools import cache

import numpy as np
import trimesh

from model import geometry as g
from model.engine import linkage, meshes, stages

DOC = "noggin-eyes"
COLUMN_MM = 2.0  # half-width of the vertical slab through the eye centre the edges are read on


@cache
def _local(side):
    """Vertices (world mm, neutral pose) of the side's inside lid, outside lid, eyeball and pupil."""
    stage = stages.STAGES[DOC]
    names = [f"{side} {p}:1" for p in ("inside lid", "outside lid", "eyeball", "pupil")]
    loaded = meshes.load(stage, names)
    return [trimesh.transform_points(loaded[n].vertices, stage.parts[n].matrix) for n in names]


def _centre(side):
    return np.array(g.EYE_L if side == "L" else g.EYE_R)


def _elevation(v, side):
    """Elevation (deg) of each point about the X axis through the eye centre, for points on the column in front."""
    d = v - _centre(side)
    d = d[(np.abs(d[:, 0]) < COLUMN_MM) & (d[:, 2] < 0)]
    return np.degrees(np.arctan2(d[:, 1], -d[:, 2]))


def edges(side, deg):
    """(upper, lower) edge elevations with the side's lid horn at `deg` from neutral: the inside lid's lowest point and
    the outside lid's highest on the front of the column (+-90 once an edge has gone past the top or bottom)."""
    stage = stages.STAGES[DOC]
    pose = stages.pose(stage, f"{side} lid horn", deg)
    inside, outside, _, _ = _local(side)
    out = []
    for v, name, pick, none in ((inside, "inside", min, 90.0), (outside, "outside", max, -90.0)):
        m = pose.parts[f"{side} {name} lid:1"] @ np.linalg.inv(stage.parts[f"{side} {name} lid:1"].matrix)
        e = _elevation(trimesh.transform_points(v, m), side)
        out.append(float(pick(e)) if len(e) else none)
    return tuple(out)


def gap(side, deg):
    """The opening between the edges in degrees (negative once the lids overlap)."""
    upper, lower = edges(side, deg)
    return upper - lower


@cache
def _sizes(side):
    """(pupil half-span deg, edge elevation that clears the eyeball's silhouette) from the meshes."""
    inside, outside, eyeball, pupil = _local(side)
    c = _centre(side)
    pupil_deg = float(_elevation(pupil, side).max())
    eye_r = float(np.linalg.norm(eyeball - c, axis=1).max())
    lid_r = float(np.linalg.norm(np.vstack([inside, outside])[:, 1:] - c[1:], axis=1).max())
    return pupil_deg, math.degrees(math.asin(eye_r / lid_r))


def pupil_shown(side, deg):
    """Fraction (0..1) of the pupil's vertical span between the edges."""
    p = _sizes(side)[0]
    upper, lower = edges(side, deg)
    return max(0.0, min(upper, p) - max(lower, -p)) / (2 * p)


def _root(f, lo, hi):
    """Bisection for an increasing f with f(lo) < 0 < f(hi), to 0.01 deg."""
    while hi - lo > 0.01:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return round((lo + hi) / 2, 1)


@cache
def ends(side):
    """(closed, open) lid horn degrees from neutral for the side (L or R)."""
    clear = _sizes(side)[1]

    def opening(d):
        upper, lower = edges(side, d)
        return min(upper, -lower) - clear

    try:
        return _root(lambda d: gap(side, d), -50.0, 0.0), _root(opening, 0.0, 50.0)
    except linkage.Unreachable as e:  # the search window left the linkage's reach: geometry changed
        raise AssertionError(f"lid ends outside -50..50 deg: {e}") from e
