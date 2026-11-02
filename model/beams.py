"""Hand beam estimates (no FEA on the personal license): each link as a cantilever under the servo stall force at
the horn pin, and the lid ears under the lid's weight. Sections and lid masses are read from our parts' STLs, each part
in its own material (geometry.PRINTED) at its across-layer (Z) values (#626). Threshold SF >= 2 on the brief stall (#20),
>= 3 on a held load (creep: ~1/3 of the Z strength, #626). `python model/beams.py` prints the eyes table."""

import importlib.util
import math
import os
import sys

import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "fits", os.path.join(HERE, "fits.py")
)  # by path: model/ must never shadow eyes/
fits = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fits)
_spec = importlib.util.spec_from_file_location("geometry", os.path.join(HERE, "geometry.py"))
geometry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(geometry)

STALL_KGF_CM, HORN_PIN_MM = 1.2, 12.75  # the 9 g servo at 6 V (#20); bar pin radius on the horn
G, MIN_SF, HELD_SF = 9.81, 2.0, 3.0  # held: printed plastic creeps (PETG plastically above ~50%, cams-am [ST])


def stall_force_n():
    return STALL_KGF_CM * G * 10 / HORN_PIN_MM  # kgf.cm -> N.mm over the pin radius


def material(path):
    """The geometry.MATERIALS entry of the printed part an STL holds."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return geometry.MATERIALS[next(m for k, (_, m) in geometry.PRINTED.items() if k.split(" (")[0] == stem)]


def cantilever(F, L, b, h, material):
    """Tip load F (N) on length L (mm), rectangular section b x h (mm) bending about b (h is the depth), in a
    geometry.MATERIALS entry across its layers."""
    I = b * h**3 / 12
    sigma = F * L * (h / 2) / I
    return {
        "sigma_mpa": round(sigma, 2),
        "deflection_mm": round(F * L**3 / (3 * material["E_mpa"]["z"] * I), 3),
        "sf": round(min(material["tensile_mpa"]["z"] / sigma, 999), 2),
    }


def extents(path, keep=lambda v: True):
    """(lo, hi) per axis over the STL vertices `keep` accepts."""
    vs = fits.vertices(path)
    vs = vs[[bool(keep(v)) for v in vs]]
    return [(float(lo), float(hi)) for lo, hi in zip(vs.min(axis=0), vs.max(axis=0))]


def mass_g(path):
    """Printed mass from the mesh volume at the part's density."""
    return abs(trimesh.load_mesh(path, process=False).volume) / 1000 * material(path)["density_g_cm3"]


def beam_table(beams):
    """beams: (name, model, F in N or a callable giving N, L mm, (stl, keep, b_axis, h_axis)). model "axial": a pinned
    link, thresholded as a two-force member (sf = strength / (F / area)); "cantilever": thresholded on bending. The
    cantilever numbers are always reported (sf_cantilever, deflection_mm) as information. Every load but the stall is
    held (a part's weight), so it needs HELD_SF."""
    out = []
    for name, model, F, L, (path, keep, b_axis, h_axis) in beams:
        ext = extents(path, keep)
        b, h = (ext["xyz".index(a)][1] - ext["xyz".index(a)][0] for a in (b_axis, h_axis))
        held, F = F is not stall_force_n, F() if callable(F) else F
        m = material(path)
        c = cantilever(F, L, b, h, m)
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
        sf = min(m["tensile_mpa"]["z"] / (F / (b * h)), 999) if model == "axial" else c["sf"]
        out.append({**row, "sf": round(sf, 2), "ok": sf >= (HELD_SF if held else MIN_SF)})
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
EYES_RECORDED = {  # (sf, ok) read 2026-11-02 in PLA Pure across layers (#626); axially the 3 x 5 mm links are far from
    # failing (the cantilever bound gives 0.99)
    "lid bar": (48.74, True),
    "lid crank": (48.74, True),
    "eyeball bar": (48.74, True),
    "upper lid ear": (999, True),
    "lower lid ear": (999, True),
}

# Stack sub-assembly (pan-tilt): the two bars as axial links under the stall force across their pivot spacing.
PT_BEAMS = [
    ("tilt bar", "axial", stall_force_n, 20.0, (fits.stl("tilt bar"), lambda v: True, "z", "y")),
    ("pan bar", "axial", stall_force_n, 15.0, (fits.stl("pan bar"), lambda v: True, "z", "y")),
]
PT_RECORDED = {
    "tilt bar": (48.74, True),
    "pan bar": (48.74, True),
}  # read 2026-11-02: the same 3 x 5 mm section as the eyes bars

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
MOUTH_RECORDED = {"jaw bar": (48.74, True)}  # read 2026-11-02 on ours


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
