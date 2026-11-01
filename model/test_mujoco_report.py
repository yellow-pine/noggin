"""Seam: model/mujoco_report.py's tip-over margin, on a plan outline drawn by hand (the report itself: test_report.py)."""

import pytest

from model import mujoco_report


def test_footprint_margin_is_the_distance_to_the_nearest_edge_of_the_plan_hull():
    plate = [(x, y, z) for x in (0, 10) for y in (0, 10) for z in (0, 3)] + [(5, 5, 1)]
    outline = mujoco_report.footprint(plate)
    assert mujoco_report.margin(outline, (2.0, 5.0)) == pytest.approx(2.0)
    assert mujoco_report.margin(outline, (12.0, 5.0)) == pytest.approx(-2.0)
