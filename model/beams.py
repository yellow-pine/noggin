"""Hand beam estimates (no FEA on the personal license): each link as a cantilever under the servo stall force at
the horn pin, and the lid ears under the lid's weight. Sections and lid masses are read from our parts' STLs.
PLA E 3.5 GPa, yield 50 MPa; threshold SF >= 2 (#20). `python model/beams.py` prints the eyes table."""

import importlib.util
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "fits", os.path.join(HERE, "fits.py")
)  # by path: model/ must never shadow eyes/
fits = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fits)
_spec = importlib.util.spec_from_file_location("geometry", os.path.join(HERE, "geometry.py"))
geometry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(geometry)

E_MPA, YIELD_MPA, DENSITY = 3500.0, 50.0, geometry.MATERIALS["PLA Pure"]["density_g_cm3"]  # PLA (g/cm3)
STALL_KGF_CM, HORN_PIN_MM = 1.2, 12.75  # the 9 g servo at 6 V (#20); bar pin radius on the horn
G, MIN_SF = 9.81, 2.0


def stall_force_n():
    return STALL_KGF_CM * G * 10 / HORN_PIN_MM  # kgf.cm -> N.mm over the pin radius


def cantilever(F, L, b, h):
    """Tip load F (N) on length L (mm), rectangular section b x h (mm) bending about b (h is the depth)."""
    I = b * h**3 / 12
    sigma = F * L * (h / 2) / I
    return {
        "sigma_mpa": round(sigma, 2),
        "deflection_mm": round(F * L**3 / (3 * E_MPA * I), 3),
        "sf": round(min(YIELD_MPA / sigma, 999), 2),
        "ok": YIELD_MPA / sigma >= MIN_SF,
    }


def extents(path, keep=lambda v: True):
    """(lo, hi) per axis over the STL vertices `keep` accepts."""
    vs = [v for v in fits.vertices(path) if keep(v)]
    return [(min(v[i] for v in vs), max(v[i] for v in vs)) for i in range(3)]


def mass_g(path):
    """Printed mass from the mesh volume (signed tetrahedra) at PLA density."""
    d = open(path, "rb").read()
    n = struct.unpack_from("<I", d, 80)[0]
    vol = 0.0
    for i in range(n):
        a, b, c = (struct.unpack_from("<3f", d, 84 + i * 50 + 12 + 12 * k) for k in range(3))
        vol += (
            a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6
    return abs(vol) / 1000 * DENSITY


def beam_table(beams):
    """beams: (name, model, F in N or a callable giving N, L mm, (stl, keep, b_axis, h_axis)). model "axial": a pinned
    link, thresholded as a two-force member (sf = yield / (F / area)); "cantilever": thresholded on bending. The
    cantilever numbers are always reported (sf_cantilever, deflection_mm) as information."""
    out = []
    for name, model, F, L, (path, keep, b_axis, h_axis) in beams:
        ext = extents(path, keep)
        b, h = (ext["xyz".index(a)][1] - ext["xyz".index(a)][0] for a in (b_axis, h_axis))
        F = F() if callable(F) else F
        c = cantilever(F, L, b, h)
        row = {
            "beam": name,
            "model": model,
            "F_n": round(F, 2),
            "L_mm": L,
            "b_mm": round(b, 2),
            "h_mm": round(h, 2),
            "sigma_cantilever_mpa": c["sigma_mpa"],
            "deflection_mm": c["deflection_mm"],
            "sf_cantilever": c["sf"],
        }
        sf = min(YIELD_MPA / (F / (b * h)), 999) if model == "axial" else c["sf"]
        out.append({**row, "sf": round(sf, 2), "ok": sf >= MIN_SF})
    return out


def _ear(v):
    return v[0] < -20 and math.hypot(v[1], v[2]) < 6  # the L ear lug around the lid pivot (X axis)


def _lid_weight(name):
    return lambda: mass_g(fits.stl(name)) / 1000 * G / 2  # half the lid on each ear


# Eyes sub-assembly. Links: full stall force across the pivot spacing (BARS), axial (pinned both ends, decided 2026-10-31);
# the cantilever bound (bending about the pin axis, depth h = in-plane width) is reported alongside. Ears: the lug from
# the lid body to the pin (~5 mm) as a cantilever under half the lid, bending about the pin, depth across the lug.
EYES_BEAMS = [
    ("lid bar", "axial", stall_force_n, 41.0, (fits.stl("lid bar"), lambda v: True, "z", "y")),
    (
        "lid crank",
        "axial",
        stall_force_n,
        41.0,
        (fits.stl("lid crank"), lambda v: v[2] < 3.5, "z", "y"),
    ),  # the lower tab; the step is 3 mm higher
    ("eyeball bar", "axial", stall_force_n, 27.0, (fits.stl("eyeball bar"), lambda v: True, "y", "x")),
    ("upper lid ear", "cantilever", _lid_weight("upper lid"), 5.0, (fits.stl("upper lid"), _ear, "x", "y")),
    ("lower lid ear", "cantilever", _lid_weight("lower lid"), 5.0, (fits.stl("lower lid"), _ear, "x", "y")),
]
EYES_RECORDED = {  # (sf, ok) read 2026-10-31; axially the 3 x 5 mm links are far from yield (the cantilever bound gave 1.65)
    "lid bar": (81.23, True),
    "lid crank": (81.23, True),
    "eyeball bar": (81.23, True),
    "upper lid ear": (999, True),
    "lower lid ear": (999, True),
}

# Stack sub-assembly (pan-tilt): the two bars as axial links under the stall force across their pivot spacing.
PT_BEAMS = [
    ("tilt bar", "axial", stall_force_n, 20.0, (fits.stl("tilt bar"), lambda v: True, "z", "y")),
    ("pan bar", "axial", stall_force_n, 15.0, (fits.stl("pan bar"), lambda v: True, "z", "y")),
]
PT_RECORDED = {
    "tilt bar": (81.23, True),
    "pan bar": (81.23, True),
}  # read 2026-10-31: the same 3 x 5 mm section as the eyes bars

# Mouth sub-assembly: the jaw bar as an axial link across its 44.1 mm in-plane pivot spacing (the 13 mm crank along
# the pins is not modelled); section from its lower tab (x > 8: the
# 5 x 3 tab plus its edge rounding, since the STL carries no vertices on the tab's flat top).
MOUTH_BEAMS = [
    (
        "jaw bar",
        "axial",
        stall_force_n,
        44.1,
        (fits.stl("jaw bar"), lambda v: v[0] > 8, "y", "z"),
    ),
]
MOUTH_RECORDED = {"jaw bar": (81.23, True)}  # read 2026-10-31 on ours


if __name__ == "__main__":
    for r in beam_table(EYES_BEAMS + PT_BEAMS + MOUTH_BEAMS):
        print(
            "%-16s %-10s F %5.2f N  L %4.1f  b x h %4.2f x %4.2f  SF %6.2f  (cantilever: %6.2f MPa, %6.3f mm, SF %6.2f)  %s"
            % (
                r["beam"],
                r["model"],
                r["F_n"],
                r["L_mm"],
                r["b_mm"],
                r["h_mm"],
                r["sf"],
                r["sigma_cantilever_mpa"],
                r["deflection_mm"],
                r["sf_cantilever"],
                "ok" if r["ok"] else "FLAG",
            )
        )
    sys.exit(0)
