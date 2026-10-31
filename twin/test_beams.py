"""Seam: twin/beams.py's hand estimates (cantilever deflection and safety factor from STL sections)."""
import importlib.util, os, pytest

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location("beams", os.path.join(HERE, "beams.py"))   # by path: twin/ must never shadow eyes/
beams = importlib.util.module_from_spec(spec); spec.loader.exec_module(beams)


def test_cantilever_textbook_case():
    # 10 N on a 50 mm PLA cantilever, 4 x 6 mm (bending about the 6 mm depth): I = 72 mm4,
    # sigma = 10*50*3/72 = 20.8 MPa -> SF 2.4; delta = 10*50^3/(3*3500*72) = 1.65 mm
    b = beams.cantilever(F=10.0, L=50.0, b=4.0, h=6.0)
    assert b["sigma_mpa"] == pytest.approx(20.83, abs=0.01) and b["sf"] == pytest.approx(2.4, abs=0.01)
    assert b["deflection_mm"] == pytest.approx(1.654, abs=0.001) and b["ok"] is True


def test_stall_force_at_the_horn_pin():
    assert beams.stall_force_n() == pytest.approx(1.2 * 9.81 * 10 / 12.75, rel=1e-3)   # 1.2 kgf.cm over 12.75 mm


@pytest.mark.skipif(not os.path.isdir(beams.fits.EYES_MODELS), reason="docs/references (local only) missing")
def test_eyes_stage_beams_are_recorded():
    rows = {r["beam"]: (r["sf"], r["ok"]) for r in beams.beam_table(beams.EYES_BEAMS)}
    assert rows == beams.EYES_RECORDED
