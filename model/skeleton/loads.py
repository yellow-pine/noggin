"""Physical loads from the exact finished Bone meshes, for inertial-only carrier children (ADR 0020)."""

import json
from pathlib import Path

import numpy as np
import trimesh


def write(parts, source, path):
    """Write head-local g/mm load data; the caller supplies the canonical material and carrier for each bare Bone."""
    assert isinstance(source, str) and source.strip(), "Missing finished-Bone export stamp"
    result = {}
    for stem, part in parts.items():
        assert part["carrier"] in ("head", "jaw", "fixed"), stem
        density = part["density_g_cm3"] / 1000
        assert np.isfinite(density) and density > 0, stem
        mesh = trimesh.load(part["file"], force="mesh")
        assert mesh.is_volume, f"{stem}: finished Bone is not a closed, consistently wound positive volume"
        mesh.density = density
        inertia = mesh.moment_inertia
        assert np.isfinite(inertia).all() and (np.linalg.eigvalsh(inertia) > 0).all(), stem
        result[stem] = {
            "carrier": part["carrier"],
            "mass_g": float(mesh.mass),
            "com_mm": mesh.center_mass.tolist(),
            "inertia_g_mm2": inertia.tolist(),
        }
    assert result, "No finished Bone loads"
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"source": source, "parts": result}, indent=2) + "\n")
