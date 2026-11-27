"""Seam: a solid's outer skin (model/morty/shells.py outer()), which Morty's Shells are cut from (docs/adr/0028): on
solids made here, whose answer is known, and on the Sculpt git holds, whose pockets were measured (#850)."""

import manifold3d as m3
import numpy as np
import pytest

from model.morty import shells

# The Sculpt's pockets, measured on it without outer() (#850: its faces whose front is space the open air does not
# reach, on a grid of 0.8 mm): one behind each brow, a slab reaching to the middle of the head and 86 mm back, joined
# to the outside by cracks under 0.8 mm wide at the brow's inner end. Each one's walls, cm2, and its box, (low,
# high) in the head's frame, mirrored in x. The original sculpt has them too (909,718 triangles, measured the same)
POCKET_CM2, POCKET = 89.0, ((0.0, -12.0, 27.0), (75.0, 87.0, 52.0))


def _hollowed(mouth):
    """A 40 mm cube with a 20 mm chamber in its middle, joined to the outside by a square hole `mouth` mm wide."""
    hole = m3.Manifold.cube((12.0, mouth, mouth), True).translate((15.0, 0.0, 0.0))
    return m3.Manifold.cube((40.0,) * 3, True) - (m3.Manifold.cube((20.0,) * 3, True) + hole)


def test_a_pocket_behind_a_pinhole_is_closed():
    """Space the open air reaches only through a hole narrower than the grid is a pocket: its walls go, and the hole
    is capped where it leaves the outside. What is left is the cube, whole."""
    skin = shells.outer(_hollowed(0.4))
    assert skin.volume() == pytest.approx(40.0**3, abs=1.0)
    vertices = shells._mesh(skin).vertices
    assert (np.abs(vertices).max(axis=1) > 20.0 - 1e-3).all()  # every one on the cube's own faces


def test_a_hollow_the_open_air_reaches_stays():
    """A chamber behind a wide mouth is the solid's outside like any other of it."""
    solid = _hollowed(5.0)
    assert shells.outer(solid).volume() == pytest.approx(solid.volume(), abs=1e-3)


def test_a_solid_with_no_pocket_is_its_own_outer_skin():
    solid = m3.Manifold.sphere(15.0, 64)
    assert shells.outer(solid).volume() == pytest.approx(solid.volume(), abs=1e-3)


def test_the_sculpts_outer_skin_leaves_out_the_pockets_behind_its_brows_and_nothing_else():
    """#850: the Sculpt's own triangles, less the two pockets' walls. Nothing of the hair, the ears, the mouth or the
    collar is a pocket."""
    whole, skin = shells._mesh(shells.sculpt()), shells._mesh(shells.outside())
    theirs = {tuple(v) for v in np.round(skin.vertices, 3)}
    left = np.array([tuple(v) not in theirs for v in np.round(whole.vertices, 3)])
    gone = whole.vertices[left]
    (x0, y0, z0), (x1, y1, z1) = POCKET
    assert (
        (np.abs(gone[:, 0]) < x1) & (gone[:, 1] > y0) & (gone[:, 1] < y1) & (gone[:, 2] > z0) & (gone[:, 2] < z1)
    ).all()
    for side in (1, -1):
        walls = left[whole.faces].all(axis=1) & (side * whole.triangles_center[:, 0] > 0)
        # the measure had not the walls nearest the cracks, where the pocket is thinner than its grid: 3 cm2 a side
        assert POCKET_CM2 < whole.area_faces[walls].sum() / 100 < POCKET_CM2 + 4.0, side
    # nothing new but each crack's cap, a fan about one point
    ours = {tuple(v) for v in np.round(whole.vertices, 3)}
    assert sum(tuple(v) not in ours for v in np.round(skin.vertices, 3)) < 30
