"""Temporary probe (#901): which lower lid spokes build on Linux's OCCT. Removed before merge."""

import itertools

import pytest

from model import gimbal as gm
from model.printed import gimbal as pg


@pytest.mark.timeout(1200)
def test_probe_lower_lid_spokes():
    span = (gm.LOWER_REST - gm.LOWER_SPAN, gm.LOWER_REST)
    rows = []
    for out_s, in_s in itertools.product((-62.0, -65.0), (-60.0, -68.0, -75.0, -90.0)):
        res = []
        for mech in (True, False):
            try:
                v = pg._lid(gm.LOWER_R, span, (out_s, in_s), "lower boss", gm.LOWER_PIN, mech).val()
                res.append(f"{int(v.isValid())}{len(v.Solids())}")
            except Exception as e:
                res.append(type(e).__name__[:6])
        try:
            m = pg._lid(gm.LOWER_R, span, (out_s, in_s), "lower boss", gm.LOWER_PIN, True)
            b = pg._lid(gm.LOWER_R, span, (out_s, in_s), "lower boss", gm.LOWER_PIN, False)
            c = b.intersect(m)
            c2 = m.intersect(b)
            res.append(f"c{len(c.val().Solids()) if c.vals() else 0}{len(c2.val().Solids()) if c2.vals() else 0}")
        except Exception as e:
            res.append(type(e).__name__[:6])
        rows.append(f"{out_s},{in_s}:{'/'.join(res)}")
    raise AssertionError(" ".join(rows))
