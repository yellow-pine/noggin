"""Mass, centre of mass and inertia of every part from its mesh (trimesh volume integrals) and the material the Stage
tables give it: the spool density for printed parts (geometry.PRINTED), the documented servo mass, and STEP volume at a
PCB-like density for the other hardware (flagged in the source). Gravity torque per horn as model/sim.py: the slope of
the chain's potential energy over the engine's poses."""
import numpy as np
import trimesh

from model import sim
from model.engine import stages


def mass(mesh, material):
    """{g, com (local mm), inertia_g_mm2 (about the com, local axes), source} for a mesh of `material` = (g/cm3, label)
    or (g, 'documented') for hardware whose mass is known."""
    density, source = material
    volume = abs(mesh.volume)
    g = density if source == "documented" else density * volume / 1000
    inertia = mesh.moment_inertia * (g / volume if volume else 0.0)   # trimesh integrates at unit density
    return {"g": round(g, 3), "com": tuple(mesh.center_mass), "inertia_g_mm2": inertia.round(3).tolist(), "source": source,
            "watertight": bool(mesh.is_watertight)}


def table(stage, loaded):
    return {name: mass(loaded[name], stage.parts[name].material) for name in loaded}


def com_at(m, matrix):
    return tuple(trimesh.transform_points([m["com"]], matrix)[0])


def gravity_torque(stage, horn_name, table, degs):
    """kgf.cm at each horn angle (sim.gravity_torque over the chain's centres of mass at the engine's poses)."""
    horn = stage.horns[horn_name]
    chain = [horn.crank] + [n for loop in horn.loops for n in (loop.coupler, *loop.rockers)]
    poses = {d: {"com": {n: com_at(table[n], stages.pose(stage, horn_name, d).parts[n]) for n in chain}} for d in degs}
    return sim.gravity_torque(poses, {n: table[n]["g"] for n in chain}, stage.up)
