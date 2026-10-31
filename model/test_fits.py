"""Seam: model/fits.py's fit table (hole radius fitted to our part's STL vs the fastener). The synthetic test
is the spec; the live tests record our sub-assemblies' parts."""

import importlib.util
import math
import os
import struct

import pytest

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location(
    "fits", os.path.join(HERE, "fits.py")
)  # by path: model/ must never shadow eyes/
fits = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fits)


def ring_stl(path, centre, axis, r, thickness, n=24):
    """Binary STL of a cylinder wall (a hole) with its axis along `axis` through `centre`, mm."""
    i = "xyz".index(axis)
    u, v = [k for k in range(3) if k != i]

    def pt(k, side):
        p = list(centre)
        p[u] += r * math.cos(2 * math.pi * k / n)
        p[v] += r * math.sin(2 * math.pi * k / n)
        p[i] += side * thickness / 2
        return p

    tris = []
    for k in range(n):
        a, b, c, d = pt(k, -1), pt(k + 1, -1), pt(k + 1, 1), pt(k, 1)
        tris += [(a, b, c), (a, c, d)]
    with open(path, "wb") as f:
        f.write(b"\0" * 80 + struct.pack("<I", len(tris)))
        for t in tris:
            f.write(struct.pack("<12f", 0, 0, 0, *t[0], *t[1], *t[2]) + b"\0\0")


def test_fit_circle_recovers_an_offset_hole(tmp_path):
    p = tmp_path / "ring.stl"
    ring_stl(p, (10.0, -4.3, 2.0), "y", 1.15, 3.0)
    fit = fits.fit_circle(str(p), (10.2, -4.3, 2.0), "y", 2.0, expect_r=1.0)
    assert fit["r"] == pytest.approx(1.15, abs=1e-3) and fit["rms"] < 1e-3
    assert fit["offset"] == pytest.approx(0.2, abs=1e-3)


def test_fit_table_flags_clearance_outside_the_window(tmp_path):
    tight, loose, ok = (tmp_path / f"{n}.stl" for n in ("tight", "loose", "ok"))
    ring_stl(tight, (0, 0, 0), "z", 1.0, 3.0)
    ring_stl(loose, (0, 0, 0), "z", 1.6, 3.0)
    ring_stl(ok, (0, 0, 0), "z", 1.2, 3.0)
    joints = [
        ("tight", (str(tight), (0, 0, 0), "z", 1.5), 2.0),
        ("loose", (str(loose), (0, 0, 0), "z", 1.5), 2.0),
        ("ok", (str(ok), (0, 0, 0), "z", 1.5), 2.0),
        ("tapped", (str(tight), (0, 0, 0), "z", 1.5), 2.0, "self_tapping"),
    ]
    table = fits.fit_table(joints)
    assert [(row["joint"], row["clearance"], row["ok"]) for row in table] == [
        ("tight", 0.0, False),
        ("loose", 0.6, False),
        ("ok", 0.2, True),
        ("tapped", 0.0, True),
    ]
    assert table[3]["tag"] == "self_tapping"


def test_eyes_stage_fits_are_recorded():
    rows = {r["joint"]: (r["hole_r"], r["pin_r"], r["ok"]) for r in fits.fit_table(fits.EYES_JOINTS)}
    assert rows == fits.EYES_RECORDED


def test_pan_tilt_stage_fits_are_recorded():
    rows = {r["joint"]: (r["hole_r"], r["pin_r"], r["ok"]) for r in fits.fit_table(fits.PT_JOINTS)}
    assert rows == fits.PT_RECORDED


def test_mouth_stage_fits_are_recorded():
    rows = {r["joint"]: (r["hole_r"], r["pin_r"], r["ok"]) for r in fits.fit_table(fits.MOUTH_JOINTS)}
    assert rows == fits.MOUTH_RECORDED
