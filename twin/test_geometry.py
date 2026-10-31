"""Seam: twin/geometry.py public data and functions. Expected values are literals from docs/research/2026-10-31-twin.md."""
from twin import geometry as g


def test_bracket_stem_centre_maps_to_tilt_window():
    assert g.eyes_to_pt((29.5, -45.6, 15.5)) == (0.0, -13.0, 35.9)


def test_transform_round_trips():
    for p in [(0, 0, 0), (59, 0, 0), (29.5, -45.6, 15.5), (-14.8, -25.6, 51)]:
        back = g.pt_to_eyes(g.eyes_to_pt(p))
        assert all(abs(a - b) < 1e-9 for a, b in zip(back, p))
