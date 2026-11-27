"""Throwaway (#967): which of the lower lid's Bones Linux's OCCT builds and carves, read from CI's log. Every test
here fails on purpose, with its reading; the file goes before the PR merges."""

import itertools
import math

import pytest

from model import gimbal as gm
from model.printed import bone, gimbal

VARIANTS = list(itertools.product((160.0, 150.0, 140.0), ("single", "inboard halved", "both halved")))


@pytest.mark.parametrize(("spoke", "how"), VARIANTS)
def test_probe_lower_lid(spoke, how, monkeypatch):
    real = gimbal.lid_bone

    def lid_bone(points, x, sizes=gimbal.LID_BONE):
        outboard = tuple(points[0]) == (0, 0)
        halve = how == "both halved" or (how == "inboard halved" and not outboard)
        monkeypatch.setattr(gimbal, "LID_SPAN", 0.0 if halve else 1e9)
        return real(points, x, sizes)

    monkeypatch.setattr(gimbal, "lid_bone", lid_bone)
    span = (gm.LOWER_REST - gm.LOWER_SPAN, gm.LOWER_REST)

    def build(mechanical):
        return gimbal._lid(gm.LOWER_R, span, (-131.0, spoke), "lower boss", gm.LOWER_PIN, mechanical)

    try:
        bones = build(False)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"PROBE {spoke} {how}: bones {type(e).__name__} {str(e)[:80]}")
    mech, out = build(True), []
    for label, cut in (("b^m", lambda: bones.intersect(mech)), ("m^b", lambda: mech.intersect(bones))):
        try:
            v = cut().val()
            out.append(f"{label} valid {v.isValid()} solids {[round(s.Volume(), 1) for s in v.Solids()]}")
        except Exception as e:  # noqa: BLE001
            out.append(f"{label} {type(e).__name__}")
    b = bones.val()
    pytest.fail(f"PROBE {spoke} {how}: bones valid {b.isValid()} solids {len(b.Solids())}; " + "; ".join(out))


def _tries(a, b):
    out = ""
    for f, (p, q) in itertools.product((1.0, 0.99, 0.98, 0.97), ((a, b), (b, a))):
        size = [tuple(f * 0.95 * v for v in s) for s in gimbal.LID_BONE]
        try:
            s = bone.bone((*p, 0), (*q, 0), *size, swell=1.0)
            out += "Y" if (bone._headed(s.val(), a, b, size[0][0]) and s.val().isValid()) else "i"
        except ValueError:
            out += "E"
    return out


def test_probe_spans():
    a, t = gm.LOWER_PIN, math.radians(44.7)
    lengths = (16, 20, 24, 28, 30, 31, 32, 32.2, 33, 34, 36, 38, 40)
    table = {n: _tries(a, (a[0] + n * math.cos(t), a[1] + n * math.sin(t))) for n in lengths}
    pytest.fail(f"PROBE spans: {table}")
