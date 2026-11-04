"""Numerical fitting of public anatomical meshes; private reference meshes stay outside this module."""

import numpy as np
from scipy import ndimage


def canal(mesh):
    """The source vertebra's canal centre in its anatomical frame (mm)."""
    p, cell = np.asarray(mesh.vertices)[:, :2], 0.5
    lo = p.min(axis=0)
    ij = np.floor((p - lo) / cell).astype(int)
    occ = np.zeros(ij.max(axis=0) + 1, bool)
    occ[ij[:, 0], ij[:, 1]] = True
    occ = ndimage.binary_closing(occ, iterations=2)
    holes = ndimage.binary_fill_holes(occ) & ~occ
    label, n = ndimage.label(holes)
    biggest = np.argmax(ndimage.sum(holes, label, range(1, n + 1))) + 1
    return np.argwhere(label == biggest).mean(axis=0) * cell + lo
