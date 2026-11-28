"""Fixed ORIGINAL-anatomy growth allowances (confirmed 2026-11-05); never an optimizer variable.

All lengths may squash only to 75%. Default stretch is 125%. Posterior/inferior cranial source zones (and, from #875,
ribs/cartilages) may reach 150%, with smooth transitions and protected facial/articular neighbourhoods.
Coordinates and protection witnesses are original BodyParts3D Basis millimetres, before any region resize.

One compression exception (Cansin, 2026-11-27, #893's third round): the neck's skin rides the head, and its rim at
the collar swings through C5 and C6 as the head nods. Those two vertebrae alone are slimmed there, toward their canals
(slim()), down to SLIM; every other vertex of every bone keeps LOW.
"""

import numpy as np

LOW = 0.75  # the compression floor, everywhere but the slimmed zones
# the slimmed zones, on each vertebra's own Basis, about its canal's middle in plan: C6 all round it, C5 behind it and
# beside it (all of it from the middle back, less and less of it round to the front, none straight ahead: a share
# that falls with the direction's sine, so no bone is sheared past its cap across a step). There the bone is drawn in toward its canal
# from CANAL mm out (the canal's wall behind it, inferred from its plan view), radially, each length beyond that taken
# to a factor the fit finds, at least SLIM, eased in over BLEND mm
SLIMMED = {"c5": "behind", "c6": "round"}
SLIM, CANAL, BLEND = 0.03, 8.0, 2.0

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


def _zone(bone, basis, canal):
    """(Each vertex's share in its bone's slimmed zone, 0 to 1; its offset from the canal's middle in plan; that
    offset's length)."""
    p = np.asarray(basis)[:, :2] - canal
    r = np.linalg.norm(p, axis=1)
    behind = np.clip(1 + p[:, 1] / np.maximum(r, 1e-9), 0, 1)  # by its direction: 1 from beside the canal back
    share = {"round": 1.0, "behind": behind, None: 0.0}[SLIMMED.get(bone)]
    return share * np.ones(len(p)), p, r


def slim(bone, basis, canal, factor):
    """The Basis's vertices with the bone's slimmed zone drawn in toward its `canal`'s middle (x, y), each radial
    length beyond CANAL taken to `factor`; a bone with no zone comes back as it is. The zone and the rule are fixed
    on the original anatomy; the fit only finds the factor, never under SLIM."""
    share, p, r = _zone(bone, basis, canal)
    t = np.maximum(r - CANAL, 0)
    drawn = CANAL + factor * t + (1 - factor) * BLEND * (1 - np.exp(-t / BLEND))
    scale = 1 + share * (np.where(t > 0, drawn / np.maximum(r, 1e-9), 1.0) - 1)
    return np.c_[canal + p * scale[:, None], np.asarray(basis)[:, 2]]


def floors(bone, basis, canal):
    """Per-source-vertex lower length factor: LOW, and SLIM in the bone's slimmed zone (SLIMMED), wherever slim()
    moves it: beyond CANAL from its `canal`'s middle (x, y). No fitted position, transform or target changes it."""
    share, _, r = _zone(bone, basis, canal)
    return np.where((share > 0) & (r > CANAL), SLIM, LOW)
