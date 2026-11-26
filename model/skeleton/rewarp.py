"""In Blender, on the Skeleton scene (docs/adr/0025): the Warp's two ends. `export` writes every bone's Basis (the
document's frame), its triangles and the Landmarks (each "LM <name>" empty on the Basis's anatomy) to an .npz;
`apply` reads the fitted vertices back into each Warp key, the Sculpt key over it, Cansin's hand edits, keeping its
deltas, puts the fit's report on the scene and saves it. model/skeleton/fit.py runs the fit between them (`just
rewarp`).

  blender -b --factory-startup model/skeleton/skeleton.blend -P model/skeleton/rewarp.py -- export|apply <npz> [json]"""

import json
import sys

import bpy
import numpy as np

BONES = "Skull"  # the collection of the bones the Warp moves (the skull's 21 in its child, `skull bones`)


def _co(key, n):
    out = np.empty(n * 3)
    key.data.foreach_get("co", out)
    return out.reshape(n, 3)


def bones():
    return [o for o in bpy.data.collections[BONES].all_objects if o.type == "MESH" and o.data.shape_keys]


def export(path):
    out = {}
    for o in bones():
        me, m = o.data, np.array(o.matrix_world)
        out[f"basis|{o.name}"] = _co(me.shape_keys.key_blocks["Basis"], len(me.vertices)) @ m[:3, :3].T + m[:3, 3]
        me.calc_loop_triangles()
        tri = np.empty(len(me.loop_triangles) * 3, np.int32)
        me.loop_triangles.foreach_get("vertices", tri)
        out[f"faces|{o.name}"] = tri.reshape(-1, 3)
    for e in bpy.data.collections["Landmarks"].all_objects:
        out[f"landmark|{e.name}"] = np.array(e.matrix_world.translation)
    np.savez(path, **out)


def apply(path, report):
    warped = np.load(path)
    for o in bones():
        me, m = o.data, np.array(o.matrix_world)
        keys, n = me.shape_keys.key_blocks, len(me.vertices)
        delta = _co(keys["Sculpt"], n) - _co(keys["Warp"], n)
        local = (warped[o.name] - m[:3, 3]) @ np.linalg.inv(m[:3, :3]).T
        keys["Warp"].data.foreach_set("co", local.ravel())
        keys["Sculpt"].data.foreach_set("co", (local + delta).ravel())
        me.update()
    bpy.context.scene["warp"] = open(report).read()
    print("rewarp:", json.loads(bpy.context.scene["warp"]), flush=True)
    bpy.context.preferences.filepaths.save_version = 0  # no skeleton.blend1 beside it
    bpy.ops.wm.save_mainfile(compress=True)


if __name__ == "__main__":
    mode, *args = sys.argv[sys.argv.index("--") + 1 :]
    export(*args) if mode == "export" else apply(*args)
    print(f"rewarp: {mode} done", flush=True)
    if not bpy.app.background:  # run with its window open (Cansin watches local Blender runs)
        bpy.ops.wm.quit_blender()
