"""In Blender, once an adoption (docs/adr/0027): Morty's Sculpt as git holds it. Kept as the record of how, like
model/skeleton/bodyparts.py. It reads the original (`morty-fixed.stl` from the Sculpt's page, LICENSE.md), decimates
it to FACES triangles (Blender's Decimate, collapse) and nothing else, writes sculpt.ply beside this file, and prints
how far the copy strays from the original, each way, in the original's millimetres: LICENSE.md records those numbers.

  python3 scripts/heavy.py "$BLENDER" --factory-startup -P model/morty/adopt.py -- <morty-fixed.stl>
"""

import os
import sys
import traceback

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

FACES = 220_000  # of the original's 909,718
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sculpt.ply")
# where a triangle is sampled: its centroid, its edges' middles and a point toward each corner
WEIGHTS = np.array([[2, 2, 2], [3, 3, 0], [0, 3, 3], [3, 0, 3], [4, 1, 1], [1, 4, 1], [1, 1, 4]]) / 6


def arrays(mesh):
    """(vertices, triangles) of a triangle mesh."""
    v, f = np.empty(len(mesh.vertices) * 3), np.empty(len(mesh.polygons) * 3, dtype=np.int32)
    mesh.vertices.foreach_get("co", v)
    mesh.polygons.foreach_get("vertices", f)
    return v.reshape(-1, 3), f.reshape(-1, 3)


def strays(points, surface):
    """Each point's distance to the surface (vertices, triangles), mm."""
    tree = BVHTree.FromPolygons(surface[0].tolist(), surface[1].tolist())
    return np.array([tree.find_nearest(p)[3] for p in points.tolist()])


def said(name, points, d):
    worst = ", ".join(f"{c:.1f}" for c in points[d.argmax()])
    return (
        f"adopt: {name}: mean {d.mean():.4f}, 99th percentile {np.percentile(d, 99):.4f}, "
        f"most {d.max():.4f} mm at ({worst})"
    )


def adopt(source):
    windows = bpy.context.window_manager.windows  # none under -b
    over = {"window": windows[0]} if windows else {}  # the operators' context, which a windowed script lacks
    with bpy.context.temp_override(**over):
        bpy.ops.wm.stl_import(filepath=source)
    (sculpt,) = bpy.context.selected_objects
    original = arrays(sculpt.data)
    decimate = sculpt.modifiers.new("Decimate", "DECIMATE")
    decimate.ratio = FACES / len(original[1])
    with bpy.context.temp_override(object=sculpt, active_object=sculpt, **over):
        bpy.ops.object.modifier_apply(modifier=decimate.name)
        bpy.ops.wm.ply_export(
            filepath=OUT,
            export_selected_objects=True,
            export_normals=False,
            export_uv=False,
            export_colors="NONE",
            export_triangulated_mesh=True,
            ascii_format=False,
            forward_axis="Y",
            up_axis="Z",
        )
    copy = arrays(sculpt.data)
    print(f"adopt: {len(original[1]):,} triangles to {len(copy[1]):,}, {os.path.getsize(OUT) / 1e6:.1f} MB", flush=True)
    print(said("the original's every vertex to the copy", original[0], strays(original[0], copy)), flush=True)
    samples = np.einsum("wk,fkd->fwd", WEIGHTS, copy[0][copy[1]]).reshape(-1, 3)
    print(said("the copy, seven points a triangle, to the original", samples, strays(samples, original)), flush=True)


try:
    adopt(sys.argv[sys.argv.index("--") + 1])
except Exception:
    traceback.print_exc()  # quitting below would swallow it
finally:  # its window open or not, Blender leaves, and with it the heavy lock
    bpy.ops.wm.quit_blender()
