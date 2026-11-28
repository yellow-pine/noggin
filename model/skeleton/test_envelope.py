"""Seam: model/skeleton/envelope.py's Skin, on a ball small enough to build in a test: a point's depth is its distance
under the outer surface, whatever sheets the mesh holds inside, and `inward` points away from that surface."""

import threading
import time

import numpy as np
import pytest
import trimesh

from model import stages
from model.skeleton import envelope


@pytest.fixture(scope="module")
def ball():
    """A 30 mm ball with a 12 mm one inside it, as the sculpt holds its hair's under side inside its head."""
    outer, inner = (trimesh.creation.icosphere(subdivisions=4, radius=r) for r in (30.0, 12.0))
    return envelope.Skin(trimesh.util.concatenate([outer, inner]))


def test_a_points_depth_is_its_distance_under_the_outer_surface(ball):
    at = np.array(((27.0, 0, 0), (0, 0, -25.0), (0, 33.0, 0), (20.0, 0, 0)))
    assert ball.depth(at) == pytest.approx((3.0, 5.0, -3.0, 10.0), abs=0.2)


def test_a_sheet_inside_the_mesh_is_not_its_skin(ball):
    """13 mm from the middle is 1 mm off the inner ball and 17 under the outer one; the middle, past the exact band, is
    deep to a voxel or two."""
    assert ball.depth(np.array(((13.0, 0, 0),))) == pytest.approx(17.0, abs=1.5)
    assert ball.depth(np.zeros((1, 3))) > 25.0


def test_inward_points_away_from_the_skin(ball):
    at = np.array(((27.0, 0, 0), (0, 33.0, 0)))
    assert ball.inward(at) == pytest.approx(np.array(((-1, 0, 0), (0, -1, 0))), abs=0.05)


def test_a_cut_mesh_is_closed_at_its_floor():
    """The sculpt is cut under the shoulders: the open end is no way in for the outside."""
    cup = trimesh.creation.icosphere(subdivisions=4, radius=30.0)
    cup = trimesh.Trimesh(cup.vertices, cup.faces[(cup.vertices[cup.faces][:, :, 2] > -10).all(1)])
    assert envelope.Skin(cup, floor=-8.0).depth(np.array(((0, 0, 20.0),))) == pytest.approx(10.0, abs=0.2)


def test_mortys_skin_is_built_once_and_read_from_its_file_by_whoever_waited(tmp_path, monkeypatch):
    """morty() on a small cut ball, asked for twice at once (two of a test run's workers): one builds it and keeps
    the grid in model/build, the other waits on the build's lock and reads that file."""
    ball = trimesh.creation.icosphere(subdivisions=4, radius=30.0)
    monkeypatch.setattr(envelope, "sculpt", lambda: (ball, __file__))
    monkeypatch.setattr(envelope, "FLOOR", -8.0)
    monkeypatch.setattr(stages, "REPO", str(tmp_path))
    builds, made = [], envelope.Skin.__init__

    def slow(self, *args, **kwargs):
        builds.append(1)
        time.sleep(0.5)  # long enough for the other to arrive
        made(self, *args, **kwargs)

    monkeypatch.setattr(envelope.Skin, "__init__", slow)
    skins = []
    both = [threading.Thread(target=lambda: skins.append(envelope.morty.__wrapped__())) for _ in range(2)]
    for t in both:
        t.start()
    for t in both:
        t.join()
    build = tmp_path / "model" / "build"
    assert len(builds) == 1 and len(list(build.glob("envelope-*.npz"))) == 1
    for skin in skins:
        assert skin.depth(np.array(((0, 0, 20.0),))) == pytest.approx(10.0, abs=0.2)


def test_a_still_point_reads_its_least_depth_under_the_skin_that_rides_the_head():
    """A 30 mm tube, upright, its upper half (z over 0) riding a head that nods 20 deg either way about an axis 40 mm
    over the cut, as Morty's neck rides his (#874): a still point 4 mm under the tube's back, just over the cut, is
    6.4 mm out of it when the nod swings the back forward past it, and so is one at the front; one at the side, on
    the nod's axis, stays under it (1.4 mm, the tube turning past it); one deep under the cut is hidden there, by its
    distance to the rim as it swings nearest (26.5 mm), which is less than its depth under the still skin (30)."""
    tube = trimesh.creation.cylinder(radius=30.0, height=120.0, sections=96)
    turn = trimesh.transformations.rotation_matrix
    moves = [np.linalg.inv(turn(np.radians(deg), (1, 0, 0), (0, 0, 40.0))) for deg in np.linspace(-20, 20, 41)]
    seen = envelope.turning(
        envelope.Skin(tube), tube, lambda p: p[:, 2] > 0, moves, np.array((-34.0, -34, -40)), np.array((34.0, 34, 20))
    )
    at = np.array(((0, 26.0, 5), (0, -26.0, 5), (26.0, 0, 5), (0, 0, -30.0)))
    assert seen.depth(at) == pytest.approx((-6.4, -6.4, 1.4, 26.5), abs=0.5)
