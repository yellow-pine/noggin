"""Seam: model/beams.py's hand estimates (cantilever deflection and safety factor from STL sections)."""

import importlib.util
import os

import pytest

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location(
    "beams", os.path.join(HERE, "beams.py")
)  # by path: model/ must never shadow eyes/
beams = importlib.util.module_from_spec(spec)
spec.loader.exec_module(beams)


def test_cantilever_textbook_case():
    # 10 N on a 50 mm cantilever of E 3500 MPa and 50 MPa across layers, 4 x 6 mm (bending about the 6 mm depth):
    # I = 72 mm4, sigma = 10*50*3/72 = 20.8 MPa -> SF 2.4; delta = 10*50^3/(3*3500*72) = 1.65 mm
    material = {"E_mpa": {"xy": 1, "z": 3500.0}, "tensile_mpa": {"xy": 1, "z": 50.0}}
    b = beams.cantilever(F=10.0, L=50.0, b=4.0, h=6.0, material=material)
    assert b["sigma_mpa"] == pytest.approx(20.83, abs=0.01) and b["sf"] == pytest.approx(2.4, abs=0.01)
    assert b["deflection_mm"] == pytest.approx(1.654, abs=0.001)


def test_a_part_is_checked_in_its_own_material():
    assert beams.material(beams.fits.stl("lid bar")) is beams.geometry.MATERIALS["PLA Pure"]  # as printed (#626)


def test_a_held_load_needs_three_times_the_strength(tmp_path):
    # The same 9.23 N on a PLA Pure 4 x 6 mm cantilever, 30 mm: sigma = 9.23*30*3/72 = 11.5 MPa, SF 30/11.5 = 2.6
    # across layers. As the brief stall it passes SF 2; held (a part's weight) it fails 1/3 of the Z strength.
    path = str(tmp_path / "lid bar.stl")  # a printed part's name, so its material
    beams.trimesh.creation.box(extents=(4, 6, 30)).export(path)
    section = (path, lambda v: True, "x", "y")
    brief, held = beams.beam_table(
        [
            ("brief", "cantilever", beams.stall_force_n, 30.0, section),
            ("held", "cantilever", lambda: beams.stall_force_n(), 30.0, section),
        ]
    )
    assert brief["sf"] == held["sf"] == pytest.approx(2.6, abs=0.01)
    assert brief["ok"] is True and held["ok"] is False


def test_stall_force_at_the_horn_pin():
    assert beams.stall_force_n() == pytest.approx(1.2 * 9.81 * 10 / 12.75, rel=1e-3)  # 1.2 kgf.cm over 12.75 mm


@pytest.mark.build
def test_eyes_stage_beams_are_recorded():
    rows = {r["beam"]: (r["sf"], r["ok"]) for r in beams.beam_table(beams.EYES_BEAMS)}
    assert rows == beams.EYES_RECORDED


@pytest.mark.build
def test_pan_tilt_stage_beams_are_recorded():
    rows = {r["beam"]: (r["sf"], r["ok"]) for r in beams.beam_table(beams.PT_BEAMS)}
    assert rows == beams.PT_RECORDED


@pytest.mark.build
def test_mouth_stage_beams_are_recorded():
    rows = {r["beam"]: (r["sf"], r["ok"]) for r in beams.beam_table(beams.MOUTH_BEAMS)}
    assert rows == beams.MOUTH_RECORDED
