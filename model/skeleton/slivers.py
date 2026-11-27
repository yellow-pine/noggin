"""In Blender, once (#874, #991): the Basis's slivers turned. BodyParts3D's decimated meshes hold triangles under SLIVER mm
tall and up to 15 mm long, three vertices nearly in line, which any smooth Warp can fold over: 6 of the skull's did, 2
of them at the eyes and nose, where model/skeleton/fit.py's gate refuses a fold. Each sliver's longest edge is turned
onto its quad's other diagonal where that leaves both triangles at least twice as tall and the quad as flat (FLAT). No
vertex moves, so every shape key stands (checked here). Kept as the record of how, like build.py and bodyparts.py.

  blender --factory-startup model/skeleton/skeleton.blend -P model/skeleton/slivers.py"""

import os
import sys

import bmesh
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rewarp  # noqa: E402

SLIVER, FLAT = 0.2, 0.9  # a sliver's height, mm; the least cosine between the turned quad's faces and the old ones


def height(a, b, c):
    """A triangle's least height: its area over its longest edge."""
    longest = max((a - b).length, (b - c).length, (c - a).length)
    return (b - a).cross(c - a).length / longest if longest else 0.0


def turn(me):
    """The mesh's slivers' longest edges turned, in passes until none is left to turn; returns how many."""
    bm = bmesh.new()
    bm.from_mesh(me)
    at = bm.verts.layers.shape["Basis"]
    turned = 0
    for _ in range(4):
        bm.normal_update()
        edges, used = [], set()
        for f in sorted(bm.faces, key=lambda f: height(*(v[at] for v in f.verts))):
            h = height(*(v[at] for v in f.verts))
            if h >= SLIVER:
                break
            loop = max(f.loops, key=lambda x: x.edge.calc_length())
            e, others = loop.edge, [g for g in loop.edge.link_faces if g != f]
            if len(others) != 1 or len(others[0].verts) != 3 or f in used or others[0] in used:
                continue
            g = others[0]
            p, q, r = loop.vert, loop.link_loop_next.vert, loop.link_loop_prev.vert
            s = next(v for v in g.verts if v not in (p, q))
            if bm.edges.get((r, s)):
                continue
            new = [(r[at], p[at], s[at]), (r[at], s[at], q[at])]
            normals = [(b - a).cross(c - a).normalized() for a, b, c in new]
            least = min(h, height(*(v[at] for v in g.verts)))
            if (
                min(height(*t) for t in new) >= 2 * least
                and normals[0].dot(normals[1]) > FLAT
                and all(n.dot(g.normal) > FLAT for n in normals)
            ):
                edges.append(e)
                used |= {f, g}
        if not edges:
            break
        bmesh.ops.rotate_edges(bm, edges=edges)
        turned += len(edges)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return turned


if __name__ == "__main__":
    total = 0
    for o in rewarp.bones():
        keys, n = o.data.shape_keys.key_blocks, len(o.data.vertices)
        before = {k.name: rewarp._co(k, n) for k in keys}
        total += turn(o.data)
        assert len(o.data.vertices) == n and all(np.array_equal(rewarp._co(k, n), before[k.name]) for k in keys), o.name
    print(f"slivers: {total} edges turned", flush=True)
    bpy.context.preferences.filepaths.save_version = 0  # no skeleton.blend1 beside it
    bpy.ops.wm.save_mainfile(compress=True)
    print("slivers: done", flush=True)
    if not bpy.app.background:  # run with its window open (Cansin watches local Blender runs)
        bpy.ops.wm.quit_blender()
