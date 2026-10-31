"""Seam: model/render/camera.py, the camera that frames a picture (fitted to the posed parts' points)."""

import numpy as np
import pytest

from model.render import camera

CUBE = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], float)


def test_orthographic_front_view_of_a_unit_cube_spans_its_width_at_four_by_three():
    cam = camera.fit(CUBE, eye_dir=(0, -1, 0), up=(0, 0, 1), aspect=4 / 3)
    assert cam.ortho_scale == pytest.approx(4 / 3)  # the height (1) binds: 1 x 4/3 across
    assert cam.matrix[:3, 2] == pytest.approx([0, -1, 0])  # Blender cameras look down their local -Z
    assert cam.matrix[:3, 1] == pytest.approx([0, 0, 1])
    assert cam.matrix[0, 3] == pytest.approx(0.5) and cam.matrix[2, 3] == pytest.approx(0.5)
    assert cam.matrix[1, 3] < 0  # in front of the cube


def test_perspective_fit_backs_off_until_the_widest_points_touch_the_frame_edge():
    # two points 2 apart across the view, 50 mm lens on a 36 mm sensor: half-width tan = 18/50, distance 1/0.36
    cam = camera.fit([(-1, 0, 0), (1, 0, 0)], eye_dir=(0, -1, 0), up=(0, 0, 1), aspect=4 / 3, lens=50)
    assert cam.lens == 50 and cam.ortho_scale is None
    assert cam.matrix[:3, 3] == pytest.approx([0, -1 / 0.36, 0])


def test_three_quarter_is_halfway_between_front_and_side_and_raised():
    # the Mech's front faces -Y, its right side -X (PT frame): front-right corner, 25 degrees up
    c, s = np.cos(np.radians(25)), np.sin(np.radians(25))
    assert camera.three_quarter((0, -1, 0), (-1, 0, 0), (0, 0, 1), 25) == pytest.approx(
        [-c / np.sqrt(2), -c / np.sqrt(2), s]
    )


def test_perspective_fit_keeps_every_point_in_frame_and_one_on_an_edge():
    pts = np.random.default_rng(1).normal(size=(200, 3)) * (60, 90, 40)
    eye_dir = camera.three_quarter((0, -1, 0), (-1, 0, 0), (0, 0, 1), 25)
    cam = camera.fit(pts, eye_dir, (0, 0, 1), aspect=4 / 3, lens=60, margin=1.1)
    local = (pts - cam.matrix[:3, 3]) @ cam.matrix[:3, :3]  # camera frame: x right, y up, -z ahead
    u = local[:, 0] / -local[:, 2] / (camera.SENSOR_MM / 2 / 60)  # +-1 at the frame's side edges
    v = local[:, 1] / -local[:, 2] / (camera.SENSOR_MM / 2 / 60 / (4 / 3))
    assert (local[:, 2] < 0).all()
    assert max(np.abs(u).max(), np.abs(v).max()) == pytest.approx(1 / 1.1)


def test_a_strip_panel_shares_the_scale_and_stands_the_lowest_point_on_the_frame_bottom():
    cam = camera.fit(CUBE, eye_dir=(0, -1, 0), up=(0, 0, 1), aspect=4 / 3)
    panel = camera.stand(cam, CUBE, scale=4.0, aspect=4 / 3, gap=0.1)
    assert panel.ortho_scale == 4.0
    # frame 4 x 3 high: the cube's bottom (z=0) sits 0.1 x 3 above the frame bottom, so the centre is 1.5 - 0.3 up
    assert panel.matrix[:3, 3] == pytest.approx([0.5, cam.matrix[1, 3], 1.2])
