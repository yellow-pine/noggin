"""Fixed ORIGINAL-anatomy growth allowances (confirmed 2026-11-05); never an optimizer variable.

All lengths may squash only to 75%. Default stretch is 125%. Posterior/inferior cranial source zones (and, from #875,
ribs/cartilages) may reach 150%, with smooth transitions and protected facial/articular neighbourhoods.
Coordinates and protection witnesses are original BodyParts3D Basis millimetres, before any region resize.
"""

import numpy as np

CRANIAL = {
    "occipital bone",
    "L parietal bone",
    "R parietal bone",
    "L temporal bone",
    "R temporal bone",
    "sphenoid bone",
}


def smooth(t):
    t = np.clip(t, 0, 1)
    return t**3 * (t * (6 * t - 15) + 10)


def cranial_weight(y, z, reference):
    c0, eyes = np.asarray(reference["c0"]), np.asarray(reference["eyes"])
    posterior = smooth((y - c0[1]) / 20)
    inferior = smooth((eyes[:, 2].mean() - 20 - z) / 20) * smooth((y - (c0[1] - 20)) / 20)
    return 1 - (1 - posterior) * (1 - inferior)


def protected(reference):
    for key, radius in (("c0", 35), ("eyes", 45), ("condyles", 20)):
        centres = np.asarray(reference[key]).reshape(-1, 3)
        for centre in centres:
            yield centre, radius


def caps(bone, basis, reference):
    """Per-source-vertex upper length factor. No fitted position, transform or target changes this mask.

    Cranial planes are tied to the occipital condyles (c0) and orbital height; the protections round C0, the eyes and
    the condyles are spheres on the original anatomy. The upper chest's rib/cartilage allowance is #875's.
    """
    basis = np.asarray(basis)
    weight = np.zeros(len(basis))
    if bone in CRANIAL:
        weight = cranial_weight(basis[:, 1], basis[:, 2], reference)
        for centre, radius in protected(reference):
            weight *= smooth((np.linalg.norm(basis - centre, axis=1) - radius) / 10)
    return 1.25 + 0.25 * weight
